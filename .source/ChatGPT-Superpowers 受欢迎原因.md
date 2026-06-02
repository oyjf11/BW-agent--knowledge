# Superpowers 受欢迎原因

**User:** Anonymous  
**Created:** 5/30/2026 18:04:20  
**Updated:** 5/30/2026 18:05:25  
**Exported:** 6/3/2026 1:45:32  
**Link:** [https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813/c/6a1ab5fc-346c-83ec-b785-8e1ef372b1f9](https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813/c/6a1ab5fc-346c-83ec-b785-8e1ef372b1f9)  

## Prompt:
2026/5/30 18:04:19

Superpower 这个skill为什么那么受欢迎？它有哪些先进的能力和设计哲学

## Response:
2026/5/30 18:04:19

> **浏览当前超级能力技能及Claude代码**
>
> [AI Agents Plunged the Tech World Into Chaos. Here's Exactly How That Happened](https://www.wired.com/story/how-ai-agents-plunged-tech-world-into-chaos)
> [Claude Code creator says 22-year-old CS grads should found startups: 'It's the golden age'](https://www.businessinsider.com/claude-code-creator-advice-cs-grads-startup-2026-5)
> [Superpower](https://superpower.com/?srsltid=AfmBOoohowelkVNLX7kmRRS0yMuMw5ZnVMc3D05x5cRQT5ASNpUHZdGk)
> [obra/superpowers: An agentic skills framework ...](https://github.com/obra/superpowers)
> [Superpower](https://en.wikipedia.org/wiki/Superpower)
> [Superpowers: How I'm using coding agents in October 2025](https://blog.fsck.com/2025/10/09/superpowers/)
> [Superpower Wiki | Fandom](https://powerlisting.fandom.com/wiki/Superpower_Wiki)
> [List of 100 Superpowers (common and uncommon)](https://stephenhudler.com/list-of-100-superpowers-common-and-uncommon/)
> [Claude Code Skill for Workflow Discipline](https://mcpmarket.com/tools/skills/skill-orchestration-workflow-discipline)
> [What Is the Superpowers Plugin for Claude Code ...](https://www.mindstudio.ai/blog/what-is-superpowers-plugin-claude-code/)
> [Superpowers: How I'm using coding agents in October 2025](https://news.ycombinator.com/item?id=45547344)
> [Daniel Caesar - Superpowers (Official Audio)](https://www.youtube.com/watch?v=rScwLoES2bM)
> [Claude Code Got 100x Better With Superpowers Skill](https://medium.com/%40codeandbird/claude-code-got-100x-better-with-superpowers-skill-a36450f708b1)
> [Coding Beyond Your Training: Claude Code and the Technological Frontier of Software Developers](https://arxiv.org/abs/2605.25438)
>
> **查询关于引用文件和GitHub的问题**
>
> [GitHub - obra/superpowers: An agentic skills framework & software development methodology that works. · GitHub](https://github.com/obra/superpowers)
> [Superpowers: How I'm using coding agents in October 2025
 — Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/)
> [What Is the Superpowers Plugin for Claude Code? The Agentic Skills Framework Explained | MindStudio](https://www.mindstudio.ai/blog/what-is-superpowers-plugin-claude-code/)
>
> 已思考 7s

我先核一下你说的 Superpower 具体是哪套 skill/项目，避免把同名项目混在一起；然后按“为什么火、先进能力、设计哲学、对你项目的启发”来拆。

你说的应该是 **obra/superpowers** 这套 Agent Skills 框架，不是某一个单独 skill。它受欢迎的核心原因不是“能力特别神秘”，而是它把 AI Coding 从“每次靠模型临场发挥”推进到了“可复用、可约束、可组合的方法论系统”。

## 一句话判断

**Superpowers 火，是因为它抓住了 AI Coding 的真实痛点：模型本身已经很强，但缺的是稳定的工程流程、任务纪律、上下文组织、TDD、代码审查和可复用技能库。**

它不是让 Claude Code / Codex / OpenCode 获得新模型能力，而是把已有能力装进一套工程化 workflow。官方 README 也明确说，它是一个“完整的软件开发方法论”，由可组合 skills 和初始指令组成，并支持 Claude Code、Codex CLI、Gemini CLI、OpenCode、Cursor、GitHub Copilot CLI 等多个 coding agent。([GitHub](https://github.com/obra/superpowers))

---

# 1. 为什么 Superpowers 这么受欢迎？

## 1.1 它解决的是“AI 很聪明，但做事不稳定”的问题

普通 AI Coding 最大的问题不是不会写代码，而是：

- 有时不先理解需求，直接改代码；
- 有时不写测试，直接实现；
- 有时改着改着偏离目标；
- 有时一个复杂任务没有计划、没有拆解、没有审查；
- 不同 session、不同开发者得到的执行风格不一致；
- 长任务中容易上下文漂移。

Superpowers 的价值在于：**它把这些不稳定行为变成一套默认流程**。

它的工作流大致是：

```text
需求沟通
→ 提炼 spec
→ 分块展示给用户确认
→ 生成实现计划
→ 等用户确认 go
→ 子 agent 分任务执行
→ 每个任务实现后 review
→ TDD 红绿循环
→ 最后选择 PR / merge / stop
```

README 中也描述了类似流程：agent 不会一上来就写代码，而是先理解目标、提炼 spec、展示设计、再制定实现计划，并强调 red/green TDD、YAGNI、DRY。([GitHub](https://github.com/obra/superpowers))

这点非常符合真实工程场景。**工程里最怕的不是 AI 写不出来，而是 AI 写得太快、但没有边界。**

---

## 1.2 它让 skill “自动触发”，降低使用成本

很多人做 AI Coding 规范，会写一堆 prompt，比如：

```text
请先分析需求，再拆任务，再写测试，再实现，再检查。
```

问题是：每次都要提醒，模型也不一定稳定遵守。

Superpowers 的设计是通过 session hook / bootstrap prompt 告诉 agent：

1. 你有 skills；
2. 你要搜索 skills；
3. 如果有适用 skill，必须使用它。

作者在博客里展示了启动时注入的提示，并说明这会让 Claude 在任务开始时读取 getting-started skill，理解“搜索 skill、读取 skill、按 skill 做事”的机制。([Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/))

这就是它受欢迎的关键：**不是让用户记住流程，而是让 agent 自己记住流程。**

---

## 1.3 它把“经验”变成了可复用资产

Superpowers 的本质不是 prompt 包，而是 **工程经验的沉淀方式**。

比如一个资深工程师调 bug，不会每次从零思考。他会自然执行：

```text
复现问题
→ 定位最近变更
→ 缩小影响范围
→ 构造最小测试
→ 修复
→ 回归验证
```

Superpowers 把这种“资深工程师的隐性经验”写成可调用 skill。MindStudio 的文章也把 skills 解释为“可复用的认知模板”，让 Claude Code 不再每次重新发明调试、规划、重构、测试流程。([MindStudio](https://www.mindstudio.ai/blog/what-is-superpowers-plugin-claude-code/))

这点非常先进，因为它对应的是 **Agent 能力产品化**：

```text
一次性 prompt
↓
可复用 workflow
↓
团队级规范
↓
可版本化能力资产
```

---

# 2. 它有哪些先进能力？

## 2.1 Meta-skill：先学会“如何使用技能”

Superpowers 最先进的地方不是某个单点 skill，而是它有一个 **meta-skill 机制**。

普通 skill 是：

```text
当你要调试时，按这个流程做。
```

Superpowers 更进一步：

```text
当你开始任务时，先判断有没有适合的 skill；
如果有，必须读取并使用；
如果没有，可以创建或改进 skill。
```

这就类似你在做的 AI 开发套件里的：

```text
Router → Skill Selection → Agent Execution
```

只不过 Superpowers 是把这个能力做成了 Claude Code / Codex / OpenCode 可直接吃的技能体系。

---

## 2.2 Brainstorm → Plan → Implement 的强制工程节奏

它不是“直接代码生成器”，而是强制分阶段：

```text
Brainstorm：澄清目标、理解需求
Plan：形成可执行计划
Implement：按计划执行
Review：检查实现质量
Test：TDD / 回归验证
```

作者博客里也明确说，它 baked in 了 brainstorm → plan → implement workflow，并且如果 Claude 判断你在开始一个任务，会默认先与你讨论计划，而不是直接实现。([Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/))

这个能力很重要，因为它防止 AI Coding 里最常见的坏路径：

```text
用户一句话需求
→ AI 直接全量改代码
→ 跑不起来
→ 再修
→ 越修越乱
```

Superpowers 的路线是：

```text
先把任务说清楚
→ 再把执行路径说清楚
→ 再动代码
```

这就是你面试中可以讲的 **Spec Driven / Plan First / Controlled Execution**。

---

## 2.3 Worktree 并行隔离

Superpowers 会在 git repo 中自动创建 worktree，让并行任务互不污染。作者博客提到，完成 brainstorming 后，如果在 git 仓库中，它会自动为项目创建 worktree，这样可以并行启动任务而不会互相覆盖。([Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/))

这点非常工程化。

普通 AI Coding 的问题是：

```text
任务 A 正在改文件
任务 B 也在改同一批文件
最后 diff 混在一起，不知道谁引入了问题
```

worktree 方案是：

```text
main branch
├── worktree/task-a
├── worktree/task-b
└── worktree/task-c
```

好处：

- 每个 agent 有独立工作区；
- 方便并发；
- 方便回滚；
- 方便 review；
- 方便最终 merge；
- 避免多 agent 改同一份 working directory。

这对你做 **AI Coding 工程化体系** 很有启发。你现在讲“任务隔离、断点续传、可审计、MR 质量门禁”，可以把 worktree 作为一个具体落点。

---

## 2.4 Subagent-driven development

Superpowers 不只是一个 agent 从头做到尾，而是支持把任务分发给 subagents。README 提到，在用户确认后，会启动 subagent-driven-development，让 agents 逐个处理工程任务、检查和 review 工作，并继续前进。([GitHub](https://github.com/obra/superpowers))

这比单 agent 更先进的点在于：

```text
主 agent：负责规划、调度、验收
子 agent：负责具体任务实现
review agent：负责检查实现质量
```

对应真实团队就是：

```text
PM / Tech Lead / Engineer / Reviewer
```

这跟你之前做的 **Architect / Frontend / DBA / QA Agent** 是同一类思想。

区别是：Superpowers 更偏 coding methodology，你的应用生成智能体更偏业务应用生成平台。

---

## 2.5 真正强调 RED/GREEN TDD

作者博客明确提到，Claude 会执行 RED/GREEN TDD：先写失败测试，再实现刚好能通过的代码。([Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/))

这点很关键。很多 AI Coding 项目说自己有测试，但实际是：

```text
代码写完
→ 补一个能过的测试
```

Superpowers 更偏：

```text
先定义失败用例
→ 再实现最小代码
→ 再让测试变绿
```

这解决的是 AI Coding 的可靠性问题。

因为 AI 最容易犯的错是：**自以为完成，但没有客观验证。**

TDD 让任务有一个外部判定标准：

```text
不是 AI 说完成，而是测试通过才算完成。
```

---

## 2.6 Skills 可组合、可扩展、可自我改进

作者在博客里提到，他教给 Superpowers 的早期 skill 之一就是“如何创建 skills”，后来要加入 git worktree workflow 时，只需要描述想要的流程，Claude 就能把相关技能和说明补进去。([Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/))

这说明 Superpowers 的设计不是静态 prompt，而是：

```text
Skill 可以被新增
Skill 可以被修改
Skill 可以组合
Skill 可以沉淀新的工作流
```

这就是 Agent 系统里很重要的 **self-improving workflow memory**。

对你项目来说，可以翻译成：

```text
Bad Case → 归因 → 规则/Skill/Planner Prompt 更新 → 下一次复用
```

也就是你一直在做的 Bad Case 迭代。

---

# 3. 它的设计哲学是什么？

## 3.1 不是提升模型智商，而是提升执行纪律

Superpowers 的底层哲学是：

```text
LLM 已经足够聪明，但缺少纪律。
```

所以它不是在做更复杂的模型推理，而是在做：

- 流程约束；
- skill 选择；
- 计划先行；
- 测试驱动；
- 子任务隔离；
- 审查闭环；
- 可复用工程方法。

MindStudio 的文章也指出，Superpowers 不会给 Claude Code 增加它原本没有的新能力，而是提供结构化方法，让已有能力以更一致的方式执行。([MindStudio](https://www.mindstudio.ai/blog/what-is-superpowers-plugin-claude-code/))

这句话很重要：

> **Agent 产品化，不是让模型更聪明，而是让模型少犯工程错误。**

---

## 3.2 从 Prompt Engineering 转向 Skill Engineering

传统 Prompt Engineering 是：

```text
写一大段提示词，让模型这次表现好一点。
```

Superpowers 的思路是：

```text
把高频任务抽象成 skill，让模型每次都按稳定流程执行。
```

这是一种范式升级：

| 阶段 | 特征 | 问题 |
|---|---|---|
| Prompt | 一次性提示 | 难复用，难维护 |
| AGENTS.md / CLAUDE.md | 项目级规则 | 偏静态，容易膨胀 |
| Skills | 任务级方法论 | 可选择、可组合 |
| Subagents | 角色级执行单元 | 可分工、可并行 |
| Workflow Runtime | 状态机执行 | 可恢复、可审计 |

Superpowers 处在 **Skills + Subagents + Workflow Discipline** 这一层。

---

## 3.3 把 AI 当“初级工程师团队”，不是当“万能大神”

README 里有个很有意思的表述：计划要清晰到让“热情但没判断力、没项目上下文、不爱测试的初级工程师”也能照着做。([GitHub](https://github.com/obra/superpowers))

这背后的哲学是：

```text
不要假设 agent 天然可靠。
要把它当成需要明确任务书、边界、测试和 review 的执行者。
```

这非常贴近真实落地。

AI Coding 最危险的心智模型是：

```text
AI 是大神，我一句话它就该全懂。
```

更合理的心智模型是：

```text
AI 是高执行力但低稳定性的 junior engineer。
你需要给它 spec、plan、tests、review gate。
```

这个观点对你的 AI Coding 工程化表达非常有价值。

---

## 3.4 从“聊天式 AI”变成“流程化 Agent”

普通 Claude Code / Cursor / OpenCode 更像：

```text
用户输入
→ 模型响应
→ 工具调用
→ 继续响应
```

Superpowers 试图变成：

```text
任务进入
→ 选择 skill
→ 生成 spec
→ 用户确认
→ 生成 plan
→ 用户确认
→ 创建隔离工作区
→ 分配 subagent
→ TDD 实现
→ review
→ PR / merge
```

这就是从 **chat interface** 到 **agent workflow** 的转变。

这也是为什么它会火：它不是只优化“代码写得好不好”，而是优化“AI 如何像一个工程团队一样工作”。

---

# 4. 它和你当前项目的关系

你现在做的几个项目，其实都可以吸收 Superpowers 的思想。

## 4.1 对“AI Coding 工程化体系”的启发

你可以把你的开发套件表述为：

```text
我们不是简单封装一个 AI 编码工具，而是参考 Superpowers 这类 Skills-based Agent Framework 的思想，
把研发流程拆成可复用的 Commands、Agents、Skills 和 Rules。
```

然后强调你的差异点：

| Superpowers | 你的开发套件 |
|---|---|
| 偏通用 coding workflow | 偏企业内部研发流程 |
| 面向 Claude Code / Codex / OpenCode 等工具 | 面向公司内部 OpenCode / 工程规范 / CI/CD |
| 核心是 skills 方法论 | 核心是需求、开发、测试、MR、CI/CD 全流程 |
| 强调 TDD、worktree、subagent | 你强调 Spec、Runner、Playwright、质量门禁、Bad Case 数据闭环 |

你的表达可以是：

> 我们借鉴了 Superpowers 这类 Skills-based Agent Framework 的思想，但没有停留在个人 AI Coding 提效，而是把它产品化成团队级研发流程。我们把需求设计、任务拆解、代码生成、测试验证、代码审查、MR 创建和知识沉淀拆成可编排的 Commands、Agents、Skills 和 Rules，让 AI Coding 从“个人临场发挥”变成“团队可复用、可验证、可治理”的工程体系。

---

## 4.2 对“应用生成智能体”的启发

你的应用生成平台目前是：

```text
Router
→ UIPlanner
→ SupabasePlanner
→ RoutingPlanner
→ Codegen
→ Preview
→ QA
```

可以吸收 Superpowers 的几个点：

### 第一，引入 Skill Registry

不要让 Planner 什么都靠 prompt 临场判断，而是按任务类型调用 skill：

```text
add_page_skill
modify_form_skill
add_supabase_table_skill
fix_route_skill
debug_sandpack_skill
generate_crud_skill
```

### 第二，引入强制 Plan Gate

复杂需求不能直接生成代码：

```text
用户需求
→ Router 判断 intent
→ Planner 输出变更计划
→ 用户确认或自动低风险确认
→ Codegen 执行
```

### 第三，引入 Worktree / Version Sandbox

每次生成或修改应用，都应该有隔离版本：

```text
app_version_001
app_version_002
patch_attempt_001
patch_attempt_002
```

类似 git worktree，避免一次失败修改污染主版本。

### 第四，引入 QA Skill

比如：

```text
sandpack_runtime_error_skill
typescript_error_skill
supabase_rls_error_skill
schema_migration_error_skill
```

每种错误都有固定排查流程，而不是让模型每次自由发挥。

---

## 4.3 对“运维智能体”的启发

运维智能体也可以借鉴 Superpowers 的 skill 思想：

```text
k8s_pod_crashloop_skill
mysql_slow_query_skill
alb_5xx_skill
oss_permission_error_skill
deployment_rollback_skill
```

每个 skill 不是简单 prompt，而是一套标准排查 SOP：

```text
触发条件
→ 需要收集哪些证据
→ 禁止做哪些高风险动作
→ 如何判断根因
→ 如何输出建议
→ 如何验证修复
```

这和你运维智能体的 **证据链、审批、验证、RCA** 是一致的。

---

# 5. Superpowers 真正先进在哪里？

我认为先进点可以总结为 6 个关键词：

## 5.1 Skill-first

不是“模型先想”，而是“先找已有技能”。

这降低了随机性。

## 5.2 Spec-first

不是直接写代码，而是先把目标结构化。

这降低了误解需求的概率。

## 5.3 Plan-first

不是边写边想，而是先拆任务、定顺序、识别边界。

这降低了长任务失控概率。

## 5.4 Test-first

不是写完自夸完成，而是用测试定义完成标准。

这降低了幻觉交付概率。

## 5.5 Worktree isolation

不是所有任务都污染主目录，而是隔离执行、方便并发和回滚。

这提高了工程安全性。

## 5.6 Self-improving skills

不是一次性 prompt，而是把新的经验沉淀成 skill，下一次复用。

这形成了能力复利。

---

# 6. 但它也不是完美方案

需要客观看：

## 6.1 它仍然依赖模型遵守自然语言规则

Skills 本质上还是 Markdown / prompt 规则，不是强制状态机。  
如果模型不遵守，仍然可能跳步。

所以在企业级场景里，最好不要只靠 skill，要加：

```text
状态机
JSON Schema
工具权限
测试门禁
执行日志
人工审批
CI 校验
```

## 6.2 Skill 越多，选择和治理越难

skill 多了以后会出现：

- 什么时候触发哪个 skill？
- 多个 skill 冲突怎么办？
- skill 版本如何管理？
- malicious skill 如何防？
- skill 质量如何评估？

近期也有研究指出，SKILL.md 这类自然语言技能注册机制会带来语义供应链风险，因为技能描述会影响 agent 的发现、选择和信任过程。([arXiv](https://arxiv.org/abs/2605.11418?utm_source=chatgpt.com))

所以你做企业内部开发套件时，不能只讲“我们有很多 skills”，还要讲：

```text
Skill 准入
Skill 版本管理
Skill 权限边界
Skill 执行日志
Skill 效果评估
Skill 下线机制
```

这会比单纯模仿 Superpowers 更高级。

---

# 7. 你面试时可以怎么讲

可以这样表达：

> Superpowers 受欢迎的本质，不是它给模型增加了什么魔法能力，而是它把 AI Coding 从一次性 prompt 推进到了 Skills-based Workflow。它通过 session 启动注入、skill 自动检索、brainstorm-plan-implement 流程、TDD、subagent 执行、worktree 隔离和 review gate，让 AI 不再每次临场发挥，而是按稳定的软件工程方法做事。

再接你的项目：

> 我自己的 AI 开发套件也是类似思路，但更偏企业内部落地。我不会只把 AI 当代码生成器，而是把研发流程拆成 Commands、Agents、Skills 和 Rules，围绕需求解析、任务拆解、代码生成、测试验证、代码审查、MR 和 Bad Case 反馈形成闭环。这样做的目标是让 AI Coding 从个人提效工具变成团队可复用、可验证、可治理的工程体系。

---

## 最终结论

**Superpowers 的核心先进性 = Skills 工程化 + 流程纪律 + TDD 验证 + Subagent 分工 + 工作区隔离 + 经验可沉淀。**

它火的原因也很直接：

```text
模型能力已经足够强，
但真实工程需要的是稳定、可控、可复用、可验证。
Superpowers 正好补上了这层工程方法论。
```

---

**Sources:**

- [GitHub - obra/superpowers: An agentic skills framework & software development methodology that works. · GitHub](https://github.com/obra/superpowers)
- [Superpowers: How I'm using coding agents in October 2025
 — Massively Parallel Procrastination](https://blog.fsck.com/2025/10/09/superpowers/)
- [What Is the Superpowers Plugin for Claude Code? The Agentic Skills Framework Explained | MindStudio](https://www.mindstudio.ai/blog/what-is-superpowers-plugin-claude-code/)
- [Under the Hood of SKILL.md: Semantic Supply-chain Attacks on AI Agent Skill Registry](https://arxiv.org/abs/2605.11418?utm_source=chatgpt.com)



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)