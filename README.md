# distill-skill

从真实会话轨迹蒸馏可复用的 skill。

把「这次是怎么解决的」变成「下次直接照做的 SOP」——不靠复述，靠蒸馏。

## 在线示例

**[查看一次真实蒸馏：trace.md → skill.md](https://david-dev666.github.io/distill-skill/)**

一次 Node 内存泄漏排查的真实会话，蒸馏成换项目直接可用的 skill。

## 流程

```
取景 → 解析 → 抽六类信号 → 抽象 → 闸门分流 → 生成 → 校验 → 落盘
```

| 阶段 | 执行者 | 说明 |
|------|--------|------|
| 解析 + 抽信号 | 脚本 | `extract.py` 启发式抽取，确定、可复现 |
| 抽象泛化 | 模型/人工 | 编辑 signals.json，把「本次叙述」泛化为「通用规律」 |
| 闸门/生成/校验/落盘 | 脚本 | `emit.py` + `validate.sh`，硬规则守门 |

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

```
压缩 delta，不压缩对话
特有值参数化，通用规律固化
单样本不注册，必须过评估门
只做 delta 追加，禁止重写
```

## 安装

### 方式一：Claude Code 插件（推荐）

```bash
claude plugin marketplace add david-dev666/distill-skill
claude plugin install distill-skill
```

装完对 Claude 说「沉淀成 skill」即触发。

### 方式二：手动安装

```bash
git clone https://github.com/david-dev666/distill-skill.git
cd distill-skill
./install.sh                    # 复制到 ~/.claude/skills/distill-skill
./install.sh /your/skill/dir    # 或指定目录
```

### 方式三：只用蒸馏管线（任意编辑器/AI 均可）

```bash
git clone https://github.com/david-dev666/distill-skill.git
```

无需安装，直接调用脚本。

## 使用

### 蒸馏一段会话

```bash
# 1. 抽六类信号
python3 scripts/extract.py trace.md -o signals.json

# 2.（模型/人工）抽象：编辑 signals.json，
#    把特有叙述泛化为通用规律 —— 见 SKILL.md 第 3 步

# 3. 闸门分流 + 生成骨架
python3 scripts/emit.py signals.json -o skills/ --name my-skill

# 4. 自检
./scripts/validate.sh
```

分流规则：

```
多步可复用流程 -> 生成 skill（单样本只落 drafts/，须过评估门）
偏好/事实      -> 建议写 memory
一次性问答     -> 不沉淀
```

### 蒸馏产物结构

```
skills/<name>/SKILL.md    # 目标/触发条件/SOP/决策点/硬约束/资产 六章节
```

## 示例

`examples/` 下是一组完整真实产物：

| 文件 | 说明 |
|------|------|
| `trace.md` | 原始会话轨迹（Node 内存泄漏排查，含真实压测输出） |
| `signals.json` | 六类信号中间产物（已抽象泛化） |
| `skill.md` | 蒸馏生成的 skill 骨架 |
| `index.html` | before/after 对照展示页 |

## 参与贡献

跑通 `./scripts/validate.sh` 全绿即可提交 PR。蒸馏相关约定见 `references/`（信号定义、反模式清单）。

## License

[MIT](LICENSE)
