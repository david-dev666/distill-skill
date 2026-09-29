#!/usr/bin/env python3
"""emit.py — 六类信号 -> skill 骨架（闸门分流 + delta 追加）

闸门分流:
  skill  多步可复用流程 -> 生成 SKILL.md（须过评估门: samples >= 2 或 --force）
  memory 偏好/事实      -> 输出 memory 建议，不生成 skill
  skip   一次性问答     -> 不沉淀

硬规则:
  - 特有值参数化: 绝对路径 / 长哈希 -> {{占位符}}
  - 评估门: 单样本只落 drafts/，不注册
  - 只做 delta 追加: 目标 SKILL.md 已存在时仅追加新条目，不改写既有内容

用法:
  python3 scripts/emit.py signals.json -o skills/ [--name <slug>] [--force]

退出码: 0 正常 / 1 出错 / 2 单样本仅生成草稿
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTION_OF = {
    "goal": "## 目标 / 成功判据",
    "trigger": "## 触发条件",
    "actions": "## SOP",
    "decisions": "## 决策点",
    "pitfalls": "## 硬约束（坑与修正）",
    "assets": "## 可复用资产",
}

BUILTIN_TEMPLATE = """---
name: {{name}}
description: {{description}}
---

# {{name}}

## 目标 / 成功判据
<!-- signals:goal -->

## 触发条件
<!-- signals:trigger -->

## SOP
<!-- signals:actions -->

## 决策点
<!-- signals:decisions -->

## 硬约束（坑与修正）
<!-- signals:pitfalls -->

## 可复用资产
<!-- signals:assets -->
"""

PARAM_RULES = [
    (re.compile(r"/(?:Users|home)/[\w.\-]+(?:/[\w.\-]+)*/"), "{{workdir}}/"),
    (re.compile(r"\b[0-9a-f]{8,}\b"), "{{hash}}"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent


def _norm(s: str) -> str:
    return re.sub(r"[\s`'\"]+", "", s).lower()


def parameterize(text: str) -> str:
    for pat, repl in PARAM_RULES:
        text = pat.sub(repl, text)
    return text


def load_template() -> str:
    t = REPO_ROOT / "assets" / "template" / "SKILL.md"
    if t.is_file():
        return t.read_text(encoding="utf-8")
    return BUILTIN_TEMPLATE


def slugify(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", text or "")
    return "-".join(w.lower() for w in words[:3]) or "distilled-skill"


def _first_sentence(text: str) -> str:
    return re.split(r"[。；;.!？?]", text, 1)[0].strip()


def build_description(signals: dict) -> str:
    trig = signals["trigger"][0]["text"] if signals["trigger"] else ""
    goal = signals["goal"][0]["text"] if signals["goal"] else ""
    if trig:
        t = _first_sentence(trig).rstrip("，, ")
        desc = t if t.startswith("当") else f"当{t}时"
        if goal and not desc.endswith("。"):
            desc += f"，{_first_sentence(goal)[:60]}"
        desc += "。"
    elif goal:
        desc = _first_sentence(goal)[:100]
    else:
        desc = "（待补充触发条件）"
    return re.sub(r"\s+", " ", desc)[:102]


def render_items(kind: str, items: list[dict]) -> str:
    out: list[str] = []
    if kind == "actions":
        for idx, it in enumerate(items, 1):
            out.append(f"{idx}. `{parameterize(it['text'])}`")
    elif kind == "pitfalls":
        for it in items:
            out.append(f"- {parameterize(it['text'])}")
            if it.get("fix"):
                out.append(f"  - 修正: {parameterize(it['fix'])}")
    elif kind == "assets":
        for it in items:
            out.append(f"- `{it['text']}`")
    else:
        for it in items:
            out.append(f"- {parameterize(it['text'])}")
    return "\n".join(out)


def render(name: str, signals: dict) -> str:
    body = (
        load_template()
        .replace("{{name}}", name)
        .replace("{{description}}", build_description(signals))
    )
    for kind in SECTION_OF:
        block = render_items(kind, signals.get(kind, []))
        body = body.replace(f"<!-- signals:{kind} -->", block or "（暂无）")
    return body if body.endswith("\n") else body + "\n"


def delta_append(existing: str, signals: dict) -> str:
    """只追加新条目，不改写既有内容"""
    result = existing.splitlines()
    for kind, title in SECTION_OF.items():
        header_idx = next(
            (i for i, l in enumerate(result) if l.strip() == title), None
        )
        if header_idx is None:
            continue
        end = len(result)
        for j in range(header_idx + 1, len(result)):
            if result[j].startswith("## "):
                end = j
                break
        existing_norm = {
            _norm(re.sub(r"^[\s\-\d.]*", "", l))
            for l in result[header_idx + 1 : end]
            if l.strip()
        }
        new_items = [
            it
            for it in signals.get(kind, [])
            if _norm(parameterize(it["text"])) not in existing_norm
        ]
        if not new_items:
            continue
        block = render_items(kind, new_items).splitlines()
        insert_at = end
        while insert_at > header_idx + 1 and not result[insert_at - 1].strip():
            insert_at -= 1
        result[insert_at:insert_at] = block + [""]
    return "\n".join(result) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="六类信号 -> skill 骨架")
    ap.add_argument("signals", help="extract.py 输出的 signals.json")
    ap.add_argument("-o", "--out", required=True, help="skill 输出目录")
    ap.add_argument("--name", help="skill 名（缺省从信号推断）")
    ap.add_argument("--force", action="store_true", help="跳过评估门（单样本也生成正式 skill）")
    args = ap.parse_args()

    src = Path(args.signals)
    if not src.is_file():
        print(f"error: 找不到 {src}", file=sys.stderr)
        return 1

    data = json.loads(src.read_text(encoding="utf-8"))
    signals, meta = data["signals"], data.get("meta", {})

    routing = data.get("routing_hint", "skip")
    if routing == "skip":
        print("一次性问答，不沉淀")
        return 0
    if routing == "memory":
        print("偏好/事实，建议写 memory（不生成 skill）：")
        for k in ("goal", "trigger", "pitfalls"):
            for it in signals.get(k, [])[:5]:
                print(f"  - [{k}] {it['text']}")
        return 0

    name = args.name or slugify(signals["goal"][0]["text"] if signals["goal"] else "")
    passed = meta.get("samples", 1) >= 2 or args.force
    out_dir = Path(args.out)
    target = (
        out_dir / name / "SKILL.md" if passed else out_dir / "drafts" / name / "SKILL.md"
    )

    if target.exists():
        content = delta_append(target.read_text(encoding="utf-8"), signals)
        action = "delta 追加"
    else:
        content = render(name, signals)
        action = "新建"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    if not passed:
        print(
            f"单样本不注册（评估门未过），草稿 -> {target}",
            file=sys.stderr,
        )
        return 2

    print(f"skill ({action}) -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
