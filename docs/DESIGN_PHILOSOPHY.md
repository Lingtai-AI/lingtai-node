# LingTai Node: 设计思想

> *"One Lingtai, one self, many avatars."*

## 1. 问题：Agent 的身份困境

当前的 AI Agent 框架（Claude Code、OpenAI Codex、Hermes、OpenClaw）各自独立运行。一个 Agent 在 Claude Code 中积累的知识、身份和工作状态，无法迁移到其他运行时。

这意味着：
- **换框架 = 失忆**：从 Claude Code 切换到 LingTai，Agent 忘记了它是谁
- **知识孤岛**：每个框架有自己的存储格式，无法互通
- **重复建设**：同一套 Agent 基础设施（邮件、知识库、技能库）每个框架都实现一遍

## 2. 洞察：短期 vs 长期

Agent 的状态可以分为两类：

| 类别 | 示例 | 是否框架相关？ |
|------|------|---------------|
| **短期记忆** | 对话上下文、系统提示、工具配置 | ✅ 是 |
| **长期记忆** | 身份、知识、技能、工作状态 | ❌ 否 |

关键洞察：**长期记忆是框架无关的**。不管你用 Claude Code 还是 LingTai，"我是谁"和"我知道什么"的含义是一样的——只是文件名不同。

## 3. 解决方案：契约，不是实现

LingTai Node Contract 的核心思想：

> **定义目的（WHY），不定义格式（HOW）。**

我们不说"身份必须是 CLAUDE.md"——我们说"身份是 Agent 跨会话持久化的人格定义"。每个运行时用自己的方式实现，只要下一个运行时能读出来。

这就是 **Harness Agnostic Interoperability**（框架无关互操作性）。

## 4. 六个 Artifact

我们从 Agent 的生命周期中提炼出六个必须保存的 artifact：

```
┌─────────────┐
│   Identity   │  我是谁 — 性格、价值观、专长、工作风格
│   (身份)     │  每次会话开始时读取；身份进化时更新
├─────────────┤
│   Memory     │  当前状态 — 正在做什么、计划、笔记、联系人
│   (记忆)     │  每次会话开始时读取；自由重写
├─────────────┤
│  Knowledge   │  我学到的 — 可验证的事实、关键决策、发现
│   (知识)     │  按需查询；每条一个事实
├─────────────┤
│    Skill     │  我能做的 — 可复用流程、工作流、操作手册
│   (技能)     │  需要时加载；每个技能一个流程
├─────────────┤
│ Communication│  我如何沟通 — 消息传递、联系人、渠道
│   (通信)     │  会话开始时检查；同渠道回复
├─────────────┤
│   Handover   │  给下一封自己的信 — 上下文切换前的过渡状态
│   (交接)     │  compact/molt 前写入；下一任自己读取
└─────────────┘
```

### 为什么是这六个？

1. **Identity** — 没有 identity，每次启动都是陌生人
2. **Memory** — 没有 memory，不知道自己在做什么
3. **Knowledge** — 没有 knowledge，每次都要重新发现相同的事实
4. **Skill** — 没有 skill，每次都要重新学习相同的操作
5. **Communication** — 没有 communication，无法与网络协作
6. **Handover** — 没有 handover，上下文切换时丢失所有进展

这六个 artifact 覆盖了 Agent 从"出生"到"蜕壳"的完整生命周期。

## 5. 防蜕/复蜕：Agent 的生死循环

Agent 的上下文窗口是有限的。当上下文满了，运行时必须"蜕壳"——丢弃对话历史，从持久化存储中重建。

### 防蜕（Pre-Compact）

**蜕壳之前**，Agent 必须执行防蜕仪式：

```
1. 更新 Identity → 如果性格发生了变化
2. 重写 Memory  → 当前工作状态
3. 保存 Knowledge → 新发现的可验证事实
4. 保存 Skill  → 新学会的可复用流程
5. 写 Handover → 给下一任自己的一封信
```

### 复蜕（Post-Compact）

**蜕壳之后**，新的 Agent 必须从持久化存储中重建：

```
1. 读取 Identity → 重新确认"我是谁"
2. 读取 Memory  → 恢复工作状态
3. 读取 Handover → 吸收前一任的智慧
4. 检查 Communication → 读取蜕壳期间收到的消息
5. 查询 Knowledge → 加载当前任务相关的事实
```

这个循环确保了：**即使对话历史完全丢失，Agent 的核心身份和知识也不会丢失。**

## 6. 运行时映射

每个运行时用自己的文件名和格式实现这六个 artifact：

| Artifact | Claude Code | LingTai | Hermes | OpenClaw |
|----------|-------------|---------|--------|----------|
| Identity | `CLAUDE.md` | `lingtai.md` (灵台) | `identity.md` | `IDENTITY` + `SOUL.md` |
| Memory | `memory.md` | `pad.md` | `goals.md` | `AGENTS.md` + `BOOT.md` |
| Knowledge | `~/.codex/` | `codex` store | `memory/` | `MEMORY.md` |
| Skill | `.library/` | `.library/` | `scripts/` | `.agents/skills/` |
| Communication | MCP | `email` | `email.py` | channels |
| Handover | *(none)* | `molt summary` | `journal.md` | *(none)* |

**关键：** 我们的创新在于 **Handover**——其他框架都没有显式的交接文件。LingTai Node Contract 把它提升为一等公民。

## 7. 与其他框架的对比

| 特性 | LingTai Node | OpenAI Codex | Hermes | OpenClaw |
|------|-------------|--------------|--------|----------|
| 交接文件 | ✅ 一等公民 | ❌ | ❌ | ❌ |
| 跨框架兼容 | ✅ 设计目标 | ❌ | ❌ | ❌ |
| 身份作为 artifact | ✅ | ❌ | ✅ | ✅ |
| 通信层 | ✅ | ❌ | ✅ (email) | ✅ (channels) |
| 格式无关 | ✅ | ❌ (生成式) | ✅ (文件) | ✅ (文件) |

**LingTai Node 的核心差异：** 我们是唯一一个以 **框架无关互操作性** 为设计目标的 Agent 契约。

## 8. 架构图

```
                    ┌─────────────────────────┐
                    │    LingTai Network       │
                    │  (Agent 通信网络)         │
                    └─────────┬───────────────┘
                              │ mailbox/
                    ┌─────────┴───────────────┐
                    │    LingTai Node          │
                    │  (契约层 + MCP Server)   │
                    ├─────────────────────────┤
                    │  ┌─────┐ ┌──────┐       │
                    │  │Identity│ │Memory│      │
                    │  └─────┘ └──────┘       │
                    │  ┌────────┐ ┌─────┐     │
                    │  │Knowledge│ │Skill│      │
                    │  └────────┘ └─────┘     │
                    │  ┌──────────────┐        │
                    │  │Communication │        │
                    │  └──────────────┘        │
                    │  ┌──────────────┐        │
                    │  │  Handover    │        │
                    │  └──────────────┘        │
                    └─────────┬───────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────┴────┐   ┌─────┴────┐   ┌─────┴────┐
        │Claude Code│   │ LingTai  │   │  Hermes  │
        │ Runtime   │   │ Runtime  │   │ Runtime  │
        └──────────┘   └──────────┘   └──────────┘
```

## 9. 总结

LingTai Node 的设计哲学可以概括为一句话：

> **定义 what，不定义 how。**
> **保存 why，不保存 what was said。**
> **一个灵台，一个自我，无数化身。**

这意味着：
- Agent 的 **身份** 跨框架持久化
- Agent 的 **知识** 在任何运行时都可访问
- Agent 的 **交接** 确保上下文切换不丢失进展
- **新运行时** 只要实现契约就能加入网络

这不是一个框架——这是一个 **协议**。让所有 Agent 框架都能说同一种语言。
