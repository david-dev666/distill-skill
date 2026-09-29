#!/usr/bin/env bash
# validate.sh — 蒸馏管线自检
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*" >&2; exit 1; }

command -v python3 >/dev/null || fail "需要 python3"

echo "[1/6] 语法检查"
python3 -m py_compile scripts/extract.py scripts/emit.py

echo "[2/6] 抽取信号"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 scripts/extract.py examples/trace.md -o "$TMP/signals.json"

echo "[3/6] 评估门：单样本不注册"
if python3 scripts/emit.py "$TMP/signals.json" -o "$TMP/out" --name node-memory-leak 2>/dev/null; then
  fail "单样本不应直接注册为正式 skill"
fi
test -f "$TMP/out/drafts/node-memory-leak/SKILL.md" || fail "单样本应落 drafts/"

echo "[4/6] 生成（--force 过评估门）"
python3 scripts/emit.py "$TMP/signals.json" -o "$TMP/out" --name node-memory-leak --force >/dev/null
SKILL="$TMP/out/node-memory-leak/SKILL.md"
test -f "$SKILL" || fail "SKILL.md 未生成"

echo "[5/6] 结构检查"
grep -q '^name: node-memory-leak' "$SKILL" || fail "缺少 frontmatter name"
grep -q '^description:' "$SKILL" || fail "缺少 description"
for sec in "目标 / 成功判据" "触发条件" "## SOP" "决策点" "硬约束" "可复用资产"; do
  grep -q "$sec" "$SKILL" || fail "缺少章节: $sec"
done

echo "[6/6] 硬规则检查"
# 特有值参数化：不允许绝对路径硬编码
if grep -qE '/(Users|home)/' "$SKILL"; then
  fail "存在未参数化的绝对路径"
fi
# 只做 delta 追加：重复 emit 不得改写既有内容
md5_of() { md5 -q "$1" 2>/dev/null || md5sum "$1" | cut -d' ' -f1; }
a="$(md5_of "$SKILL")"
python3 scripts/emit.py "$TMP/signals.json" -o "$TMP/out" --name node-memory-leak --force >/dev/null
b="$(md5_of "$SKILL")"
[ "$a" = "$b" ] || fail "重复 emit 改写了既有内容（违反 delta 追加）"

echo "PASS: 全部检查通过"
