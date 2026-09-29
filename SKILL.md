---
name: distill-skill
description: 当用户说「沉淀成 skill」或「distill-skill」时触发。从当前会话轨迹蒸馏可复用 skill：抽六类信号、闸门分流、生成骨架并校验。
---

# distill-skill

从真实会话轨迹蒸馏可复用的 skill。

## 流程

```
取景 → 解析 → 抽六类信号 → 抽象 → 闸门分流 → 生成 → 校验 → 落盘
```

## 步骤

1. **取景**：确认沉淀范围——当前会话，或用户指定的轨迹文件。范围外内容不进入蒸馏。
2. **解析 + 抽六类信号**：
   ```bash
   python3 scripts/extract.py <transcript.md> -o signals.json
   ```
   六类信号定义见 `references/signals.md`。
3. **抽象**（关键步骤，AI 职责，脚本不做语义泛化）：编辑 signals.json，把每条信号从「本次轨迹的叙述」泛化为「下次可直接执行的规律」：
   - 特有上下文 → 通用触发：「线上 Node 服务跑两天 OOM」→「Node 服务内存持续上涨/OOM/定时任务变慢」
   - 特有命令 → 方法论步骤：「MODE=load node server.js」→「构造最小复现+每秒打印 memoryUsage 与嫌疑结构长度」
   - 特有值 → 占位符：端口号写 `{{port}}`、目录写 `{{workdir}}`
   - 检验标准：读每条信号时，问「换一个项目这段还成立吗」——不成立就继续泛化
4. **闸门分流**（依据 signals.json 的 `routing_hint`）：
   - 多步可复用流程 → 生成 skill
   - 偏好/事实 → 建议写 memory（口头确认，不自动写）
   - 一次性问答 → 不沉淀，直接结束
5. **生成**：
   ```bash
   python3 scripts/emit.py signals.json -o skills/ --name <skill-name>
   ```
   单样本（samples < 2）只落 `skills/drafts/`，不注册。评估门：同类型问题出现 ≥ 2 次，或用户明确要求 `--force`。
6. **校验**：
   ```bash
   ./scripts/validate.sh
   ```
7. **落盘**：只做 delta 追加，禁止重写既有 skill。

## 六类信号（对应 skill 部件）

```text
目标/成功判据 -> 什么叫做完
触发条件     -> description
动作序列     -> SOP 主体
决策点       -> 分支判断
坑与修正     -> 硬约束
可复用资产   -> scripts/assets
```

## 四条硬规则

1. **压缩 delta，不压缩对话**——只沉淀新增的东西，不复述过程。
2. **特有值参数化，通用规律固化**——绝对路径、哈希等特有值写成 `{{占位符}}`。
3. **单样本不注册，必须过评估门**。
4. **只做 delta 追加，禁止重写**。

## 参考

- `references/signals.md` —— 六类信号定义
- `references/anti-patterns.md` —— 反模式清单
- `assets/template/SKILL.md` —— 输出模板
- `examples/` —— 真实会话示例：`trace.md → signals.json → skill.md`，`index.html` 为渲染展示页
