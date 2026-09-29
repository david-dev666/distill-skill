#!/usr/bin/env python3
"""extract.py — 会话轨迹 -> 六类信号

六类信号:
  goal      目标 / 成功判据
  trigger   触发条件
  actions   动作序列（SOP 主体）
  decisions 决策点（分支判断）
  pitfalls  坑与修正（硬约束）
  assets    可复用资产（scripts / files）

用法:
  python3 scripts/extract.py <transcript.md> [-o signals.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SIGNAL_KINDS = ("goal", "trigger", "actions", "decisions", "pitfalls", "assets")

GOAL_PAT = re.compile(
    r"(目标|目的|要做到|成功判据|验收标准|完成标准|需要实现|期望效果|帮我(做|修|实现|加|排查))"
)
TRIGGER_PAT = re.compile(
    r"(当[^，。;,\n]{2,30}(时|的时候)|每当|如果遇到|触发条件|适用于|什么场景|什么情况下"
    r"|OOM|内存(持续|不断)(上涨|增长)|(越来越|持续)(慢|卡|大))"
)
DECISION_PAT = re.compile(
    r"((如果|若).+?(则|就|改成|→|->)|否则|分情况|分两种|判断是否|先检查|根据.+?(选|决定)|case\b)", re.I
)
PITFALL_PAT = re.compile(
    r"(error|traceback|exception|failed|失败|报错|报了|踩?坑|白费|不要这样|别用|禁止|注意[:：]|wrong)"
)
FIX_PAT = re.compile(
    r"(修正|改成|换成|fix(ed)?\b|解决|改为|去掉|删掉|正确做法|应该|兜底)", re.I
)
CMD_HINT = re.compile(
    r"^\s*(?:[A-Za-z_]\w*=\S*\s+)*"
    r"(npm|npx|yarn|pnpm|bun|git|python3?|pip3?|uv|curl|wget|cd|mkdir|touch|chmod|cat|tee|"
    r"docker|brew|make|grep|sed|awk|echo|export|source|bash|sh|rg|find|cp|mv|rm|pytest|"
    r"tsc|node|nproc|lsof|kill|ps|top)"
)
ASSET_PAT = re.compile(
    r"[\w./\-]+\.(py|sh|md|json|ts|tsx|js|mjs|cjs|yaml|yml|toml|sql|html|css)\b"
)

MAX_PER_KIND = 30


def _norm(s: str) -> str:
    return re.sub(r"[\s`'\"]+", "", s).lower()


SPEAKER_PAT = re.compile(
    r"^(user|assistant|human|ai|用户|助手|我)\*{0,2}\s*[:：]\s*", re.I
)


def _clean(line: str) -> str:
    line = re.sub(r"^[#>\-*\s]+", "", line.strip()).strip()
    return SPEAKER_PAT.sub("", line).strip()


def extract(transcript: str) -> dict:
    lines = transcript.splitlines()
    signals = {k: [] for k in SIGNAL_KINDS}

    in_code = False
    code_lang = ""
    prev_pitfall_idx = None

    for i, raw in enumerate(lines, 1):
        stripped = raw.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code, code_lang = True, stripped[3:].strip().lower()
            else:
                in_code, code_lang = False, ""
            continue

        if in_code:
            if code_lang in ("bash", "sh", "shell", "zsh", ""):
                if CMD_HINT.match(stripped) and not stripped.startswith("#"):
                    signals["actions"].append(
                        {"text": stripped, "confidence": 0.9, "line": i}
                    )
            for m in ASSET_PAT.finditer(stripped):
                signals["assets"].append({"text": m.group(0), "confidence": 0.6, "line": i})
            continue

        text = _clean(stripped)
        if not text or len(text) < 6:
            continue

        is_heading = stripped.startswith("#")

        if not is_heading and i <= 60 and GOAL_PAT.search(text) and len(text) < 120:
            signals["goal"].append({"text": text, "confidence": 0.7, "line": i})

        if not is_heading and TRIGGER_PAT.search(text) and len(text) < 120:
            signals["trigger"].append({"text": text, "confidence": 0.7, "line": i})
            continue

        if PITFALL_PAT.search(text) and len(text) < 200:
            signals["pitfalls"].append({"text": text, "confidence": 0.7, "line": i})
            prev_pitfall_idx = len(signals["pitfalls"]) - 1
            continue

        if DECISION_PAT.search(text) and len(text) < 160:
            signals["decisions"].append({"text": text, "confidence": 0.6, "line": i})

        if prev_pitfall_idx is not None and FIX_PAT.search(text) and len(text) < 200:
            merged = signals["pitfalls"][prev_pitfall_idx]
            if "fix" not in merged:
                merged["fix"] = text
                merged["confidence"] = min(0.95, merged["confidence"] + 0.15)
            prev_pitfall_idx = None
            continue

        for m in ASSET_PAT.finditer(text):
            signals["assets"].append({"text": m.group(0), "confidence": 0.5, "line": i})

    for kind in SIGNAL_KINDS:
        seen, kept = set(), []
        for item in sorted(signals[kind], key=lambda x: -x["confidence"]):
            key = _norm(item["text"])
            if key in seen:
                continue
            seen.add(key)
            kept.append(item)
        signals[kind] = kept[:MAX_PER_KIND]

    if len(signals["goal"]) > 3:
        signals["goal"] = sorted(signals["goal"], key=lambda x: -x["confidence"])[:3]

    return {
        "source": None,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {"lines": len(lines), "samples": 1},
        "signals": signals,
        "routing_hint": route(signals),
    }


def route(signals: dict) -> str:
    """闸门分流: skill | memory | skip"""
    n_actions = len(signals["actions"])
    has_trigger = bool(signals["trigger"])
    has_knowledge = bool(signals["goal"] or signals["pitfalls"])
    if has_trigger and n_actions >= 3:
        return "skill"
    if has_knowledge and n_actions >= 1:
        return "memory"
    return "skip"


def main() -> int:
    ap = argparse.ArgumentParser(description="轨迹 -> 六类信号")
    ap.add_argument("transcript", help="会话轨迹 markdown 文件")
    ap.add_argument("-o", "--out", help="输出 signals.json 路径（缺省打印到 stdout）")
    args = ap.parse_args()

    path = Path(args.transcript)
    if not path.is_file():
        print(f"error: 找不到 {path}", file=sys.stderr)
        return 1

    result = extract(path.read_text(encoding="utf-8"))
    result["source"] = str(path)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"signals -> {args.out} (routing: {result['routing_hint']})", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
