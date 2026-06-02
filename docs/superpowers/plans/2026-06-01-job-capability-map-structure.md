# 双岗位能力地图结构补齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不填充概念卡正文、不改动用户现有编辑内容的前提下，为高级 Agent 开发工程师和 ToB 企业 AI / Agent 产品经理建立可审计的能力地图结构，并使两个岗位的加权结构覆盖率均达到 `>= 95%`。

**Architecture:** 保留现有 `01` 至 `40` 分支和 Wiki 链接，追加 `41` 至 `44` 四个一级分支，并扩展 `12`、`15`、`20` 三个既有分支。以 `39.7 双岗位能力覆盖矩阵.md` 作为覆盖率单一事实来源，岗位模型作为面试入口，审计报告作为阶段验收产物。

**Tech Stack:** Markdown、Obsidian Wiki Links、Git、`rg`、Node.js 只读校验脚本。

---

## 执行约束

工作区已有用户未提交修改。不要创建隔离 worktree，不要覆盖用户当前状态。所有手工文件改动使用 `apply_patch`，所有提交使用精确路径暂存，不使用 `git add -A` 或 `git add .`。

禁止修改：

```text
.obsidian/**
*.canvas
05-Agent系统化落地层/**
39-岗位能力模型覆盖树/39.3 AI平台产品经理.md
39-岗位能力模型覆盖树/39.4 AI解决方案经理.md
39-岗位能力模型覆盖树/39.5 AI架构师.md
39-岗位能力模型覆盖树/39.6 AI Coding研发效能负责人.md
```

结构覆盖率与知识掌握率必须始终分开表述。本轮允许新增空白卡中的 `status: todo` 和 `- 待补充`，这是有意保留的内容状态。

## 文件结构

### 新增一级分支

```text
41-通用工程与系统设计底座/
├── _index.md
├── 41.1 编程语言与异步编程.md
├── 41.2 API与后端服务.md
├── 41.3 数据库缓存与消息队列.md
├── 41.4 分布式系统设计.md
├── 41.5 高并发高可用.md
├── 41.6 测试部署与故障排查.md
└── 41.7 系统设计面试关键词.md

42-Agent前沿能力深水区/
├── _index.md
├── 42.1 长期记忆系统.md
├── 42.2 Skills与可复用能力封装.md
├── 42.3 Browser与Computer Use Agent.md
├── 42.4 多模态Agent.md
├── 42.5 Tool Learning与Self-Improvement.md
├── 42.6 A2A与Agent协议生态.md
└── 42.7 前沿能力选型边界.md

43-ToB AI产品经理基本功深水区/
├── _index.md
├── 43.1 客户调研与用户研究.md
├── 43.2 需求分析与场景抽象.md
├── 43.3 PRD与产品方案.md
├── 43.4 Roadmap与版本规划.md
├── 43.5 埋点漏斗与数据分析.md
├── 43.6 A-B Test与灰度验证.md
├── 43.7 客户成功与规模化复制.md
└── 43.8 产品经理面试关键词.md

44-中国大陆AI合规落地深水区/
├── _index.md
├── 44.1 合规适用范围判断.md
├── 44.2 数据来源授权与个人信息保护.md
├── 44.3 生成合成内容标识.md
├── 44.4 算法备案与生成式AI服务管理.md
├── 44.5 企业内部AI使用规范.md
├── 44.6 审计留痕与责任边界.md
└── 44.7 合规面试关键词.md
```

### 既有分支新增叶子

```text
12-模型与推理层/
├── 12.7 Transformer与大模型基础.md
├── 12.8 Embedding与Rerank原理.md
├── 12.9 微调量化与模型部署.md
└── 12.10 推理加速与GPU基础.md

15-EvalOps反馈闭环层/
├── 15.9 评测产品设计.md
└── 15.10 可复现评测与实验管理.md

20-RAG深水区/
├── 20.11 BM25与倒排索引.md
├── 20.12 向量数据库与HNSW-IVF.md
└── 20.13 检索性能与延迟优化.md
```

### 岗位入口与审计

```text
39-岗位能力模型覆盖树/
├── 39.1 高级Agent开发.md
├── 39.2 高级AI产品经理.md
├── 39.7 双岗位能力覆盖矩阵.md
└── _index.md

99-附件/
├── 知识地图.md
└── 岗位能力覆盖审计-2026-05.md
```

## 空白概念卡合同

每个新增叶子节点都使用以下结构，只替换标题和所属分支链接。不要填写正文。

```markdown
---
type: concept
status: todo
tags:
  - AI-Agent面试
---

# <节点标题>

> 所属分支：[[<目录名>/_index|<目录名>]]

## 子节点 / 待填充要点
- 待补充

## 一句话定义

## 解决什么问题

## 如何实现

## 项目映射

## 高频追问

## 我的回答要点
```

## Task 1: 锁定用户改动基线

**Files:**
- Read only: `.obsidian/workspace.json`
- Read only: `05-Agent系统化落地层/**`
- Read only: `99-附件/知识地图.md`

- [ ] **Step 1: 记录受保护文件哈希**

Run:

```bash
git rev-parse HEAD > /tmp/capability-map-start.commit
find .obsidian 05-Agent系统化落地层 -type f -print0 | sort -z | xargs -0 shasum -a 256 > /tmp/capability-map-protected.before.sha256
```

Expected: 两条命令退出码均为 `0`。

- [ ] **Step 2: 记录工作区状态**

Run:

```bash
git status --short --untracked-files=all
```

Expected: 能看到执行开始前已经存在的用户或 Obsidian 改动。本任务不修改文件，不提交。

## Task 2: 建立岗位矩阵骨架和岗位入口

**Files:**
- Create: `39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md`
- Modify: `39-岗位能力模型覆盖树/39.1 高级Agent开发.md`
- Modify: `39-岗位能力模型覆盖树/39.2 高级AI产品经理.md`
- Modify: `39-岗位能力模型覆盖树/_index.md`

- [ ] **Step 1: 新建双岗位覆盖矩阵**

使用 `apply_patch` 新增矩阵文件。矩阵固定使用以下表头：

```markdown
# 39.7 双岗位能力覆盖矩阵

> 结构覆盖率统计的单一事实来源。结构覆盖不等于知识掌握或面试准备完成。

## 权重
- P0 = 3
- P1 = 2
- P2 = 1

## 能力矩阵
| 能力ID | 岗位 | 能力域 | 原子能力 | 优先级 | 权重 | 主知识节点 | 辅助节点 | 项目证据入口 | 结构状态 |
|---|---|---|---|---:|---:|---|---|---|---|
```

把附录 A 的 `137` 条能力逐行写入表格。初始状态规则：

1. 主知识节点文件已存在时，写 `已映射`。
2. 主知识节点属于本计划新增文件时，写 `缺口`。
3. `辅助节点` 固定写 `无`。后续内容填充阶段再按需补充。
4. 权重按 `P0=3`、`P1=2`、`P2=1` 写入。

Expected initial statistics:

```text
高级Agent开发: 127 / 180 = 70.6%
ToB企业AI-Agent产品经理: 125 / 160 = 78.1%
总体: 252 / 340 = 74.1%
```

- [ ] **Step 2: 重写高级 Agent 开发岗位入口**

使用 `apply_patch` 重写 `39.1 高级Agent开发.md`。保留 frontmatter，正文必须包含：

```markdown
# 39.1 高级Agent开发

## 岗位定位
面向中国大陆企业级 Agent 应用研发岗位，重点覆盖从模型接入、Agent 编排、RAG、Tool / MCP 到生产可靠性、安全治理和前沿能力选型。

## 能力域
| 能力域 | 能力数量 | P0 | P1 | P2 | 主要入口 |
|---|---:|---:|---:|---:|---|
| 通用工程与系统设计 | 10 | 6 | 4 | 0 | [[41-通用工程与系统设计底座/_index|41-通用工程与系统设计底座]] |
| 模型与推理 | 8 | 3 | 3 | 2 | [[12-模型与推理层/_index|12-模型与推理层]] |
| Agent 架构与编排 | 10 | 5 | 5 | 0 | [[05-Agent系统化落地层/5.2 Agent架构模式|5.2 Agent架构模式]] |
| Agent Runtime | 10 | 8 | 2 | 0 | [[13-Agent Runtime深水区/_index|13-Agent Runtime深水区]] |
| Tool / MCP | 7 | 5 | 2 | 0 | [[21-Tool-MCP深水区/_index|21-Tool-MCP深水区]] |
| RAG | 9 | 6 | 3 | 0 | [[20-RAG深水区/_index|20-RAG深水区]] |
| EvalOps | 6 | 4 | 2 | 0 | [[15-EvalOps反馈闭环层/_index|15-EvalOps反馈闭环层]] |
| 安全治理 | 5 | 4 | 1 | 0 | [[30-安全攻防与红队测试深水区/_index|30-安全攻防与红队测试深水区]] |
| Agent 前沿能力 | 7 | 0 | 4 | 3 | [[42-Agent前沿能力深水区/_index|42-Agent前沿能力深水区]] |
| 合计 | 72 | 41 | 26 | 5 | [[39.7 双岗位能力覆盖矩阵]] |

## P0：面试高频，必须覆盖
## P1：常见要求，应当覆盖
## P2：加分项，按方向选修
## 能力清单与知识节点映射
## 项目证据映射
## 高频追问入口
## 当前覆盖统计
```

在分级章节中按附录 A 的能力 ID 填写 ID 列表；在映射章节链接 `[[39.7 双岗位能力覆盖矩阵]]`；在项目证据章节链接四个已有项目快捷入口；在高频追问入口章节链接 `[[40-高频面试主题索引树/_index|40-高频面试主题索引树]]`。当前覆盖统计先写 `127 / 180 = 70.6%`。

- [ ] **Step 3: 重写 ToB 企业 AI / Agent 产品经理入口**

使用 `apply_patch` 重写 `39.2 高级AI产品经理.md`。保留 frontmatter，正文必须包含：

```markdown
# 39.2 高级AI产品经理

## 岗位定位
面向中国大陆 ToB 企业 AI / Agent 产品经理岗位，重点覆盖场景选择、产品方案、人机协同、技术理解、评测运营、交付规模化、平台化和合规治理。

## 能力域
| 能力域 | 能力数量 | P0 | P1 | P2 | 主要入口 |
|---|---:|---:|---:|---:|---|
| 场景判断与需求抽象 | 8 | 7 | 1 | 0 | [[01-业务场景层/1.0 总览|01-业务场景层]] |
| AI 产品方案 | 9 | 7 | 2 | 0 | [[02-产品方案层/_index|02-产品方案层]] |
| AI 技术理解 | 8 | 4 | 2 | 2 | [[04-系统架构层/_index|04-系统架构层]] |
| 评测与运营 | 7 | 3 | 4 | 0 | [[15-EvalOps反馈闭环层/_index|15-EvalOps反馈闭环层]] |
| 数据分析与知识运营 | 5 | 2 | 3 | 0 | [[32-数据工程与知识工程深水区/_index|32-数据工程与知识工程深水区]] |
| 交付与组织推进 | 7 | 4 | 3 | 0 | [[34-端到端交付方法论深水区/_index|34-端到端交付方法论深水区]] |
| 平台产品理解 | 6 | 0 | 6 | 0 | [[14-AI平台化与中台层/_index|14-AI平台化与中台层]] |
| 商业化与客户成功 | 6 | 3 | 2 | 1 | [[17-商业化与产品经营层/_index|17-商业化与产品经营层]] |
| 安全与中国大陆合规 | 9 | 3 | 6 | 0 | [[44-中国大陆AI合规落地深水区/_index|44-中国大陆AI合规落地深水区]] |
| 合计 | 65 | 33 | 29 | 3 | [[39.7 双岗位能力覆盖矩阵]] |

## P0：面试高频，必须覆盖
## P1：常见要求，应当覆盖
## P2：加分项，按方向选修
## 能力清单与知识节点映射
## 项目证据映射
## 高频追问入口
## 当前覆盖统计
```

在分级章节中按附录 A 的能力 ID 填写 ID 列表；在映射章节链接 `[[39.7 双岗位能力覆盖矩阵]]`；在项目证据章节链接四个已有项目快捷入口；在高频追问入口章节链接 `[[40-高频面试主题索引树/_index|40-高频面试主题索引树]]`。当前覆盖统计先写 `125 / 160 = 78.1%`。

- [ ] **Step 4: 更新岗位覆盖树索引**

在 `39-岗位能力模型覆盖树/_index.md` 的子节点末尾追加：

```markdown
- [[39.7 双岗位能力覆盖矩阵]]
```

- [ ] **Step 5: 校验矩阵骨架**

Run:

```bash
rg -n '^\| (DEV|PM)-[A-Z]+-[0-9]{2} \|' '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md' | wc -l
rg -o '(DEV|PM)-[A-Z]+-[0-9]{2}' '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md' | sort | uniq -d
```

Expected:

```text
137
```

第二条命令无输出。

- [ ] **Step 6: 提交岗位矩阵骨架**

Run:

```bash
git add -- \
  '39-岗位能力模型覆盖树/39.1 高级Agent开发.md' \
  '39-岗位能力模型覆盖树/39.2 高级AI产品经理.md' \
  '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md' \
  '39-岗位能力模型覆盖树/_index.md'
git commit -m 'docs: add dual-role capability coverage matrix'
```

Expected: 只提交上述四个文件。

## Task 3: 扩展模型、EvalOps 和 RAG 结构

**Files:**
- Create: `12-模型与推理层/12.7 Transformer与大模型基础.md`
- Create: `12-模型与推理层/12.8 Embedding与Rerank原理.md`
- Create: `12-模型与推理层/12.9 微调量化与模型部署.md`
- Create: `12-模型与推理层/12.10 推理加速与GPU基础.md`
- Modify: `12-模型与推理层/_index.md`
- Create: `15-EvalOps反馈闭环层/15.9 评测产品设计.md`
- Create: `15-EvalOps反馈闭环层/15.10 可复现评测与实验管理.md`
- Modify: `15-EvalOps反馈闭环层/_index.md`
- Create: `20-RAG深水区/20.11 BM25与倒排索引.md`
- Create: `20-RAG深水区/20.12 向量数据库与HNSW-IVF.md`
- Create: `20-RAG深水区/20.13 检索性能与延迟优化.md`
- Modify: `20-RAG深水区/_index.md`
- Modify: `39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md`

- [ ] **Step 1: 新增九张空白概念卡**

使用 `apply_patch`，按“空白概念卡合同”新增九个叶子节点文件。所属分支分别写：

```text
12-模型与推理层
15-EvalOps反馈闭环层
20-RAG深水区
```

- [ ] **Step 2: 更新三个既有索引**

使用 `apply_patch`，按文件编号顺序把新增节点追加到对应 `_index.md` 的 `## 子节点` 列表中。

- [ ] **Step 3: 更新矩阵状态**

把以下能力的结构状态从 `缺口` 改为 `已映射`：

```text
DEV-MODEL-01 DEV-MODEL-04 DEV-MODEL-06 DEV-MODEL-07
DEV-RAG-04 DEV-RAG-06 DEV-RAG-08
DEV-EVAL-03
PM-EVAL-05 PM-EVAL-06
```

- [ ] **Step 4: 校验新增叶子**

Run:

```bash
for f in \
  '12-模型与推理层/12.7 Transformer与大模型基础.md' \
  '12-模型与推理层/12.8 Embedding与Rerank原理.md' \
  '12-模型与推理层/12.9 微调量化与模型部署.md' \
  '12-模型与推理层/12.10 推理加速与GPU基础.md' \
  '15-EvalOps反馈闭环层/15.9 评测产品设计.md' \
  '15-EvalOps反馈闭环层/15.10 可复现评测与实验管理.md' \
  '20-RAG深水区/20.11 BM25与倒排索引.md' \
  '20-RAG深水区/20.12 向量数据库与HNSW-IVF.md' \
  '20-RAG深水区/20.13 检索性能与延迟优化.md'; do
  test -f "$f" || exit 1
done
```

Expected: 无输出，退出码为 `0`。

- [ ] **Step 5: 提交既有分支扩展**

Run:

```bash
git add -- \
  '12-模型与推理层/12.7 Transformer与大模型基础.md' \
  '12-模型与推理层/12.8 Embedding与Rerank原理.md' \
  '12-模型与推理层/12.9 微调量化与模型部署.md' \
  '12-模型与推理层/12.10 推理加速与GPU基础.md' \
  '12-模型与推理层/_index.md' \
  '15-EvalOps反馈闭环层/15.9 评测产品设计.md' \
  '15-EvalOps反馈闭环层/15.10 可复现评测与实验管理.md' \
  '15-EvalOps反馈闭环层/_index.md' \
  '20-RAG深水区/20.11 BM25与倒排索引.md' \
  '20-RAG深水区/20.12 向量数据库与HNSW-IVF.md' \
  '20-RAG深水区/20.13 检索性能与延迟优化.md' \
  '20-RAG深水区/_index.md' \
  '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md'
git commit -m 'docs: extend model evalops and rag capability structure'
```

Expected: 不暂存任何禁止修改文件。

## Task 4: 新增开发工程和 Agent 前沿分支

**Files:**
- Create: `41-通用工程与系统设计底座/**`
- Create: `42-Agent前沿能力深水区/**`
- Modify: `39-岗位能力模型覆盖树/39.1 高级Agent开发.md`
- Modify: `39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md`

- [ ] **Step 1: 新建 `41` 分支**

使用 `apply_patch` 新增 `41-通用工程与系统设计底座/_index.md`：

```markdown
# 41-通用工程与系统设计底座

## 子节点
- [[41.1 编程语言与异步编程]]
- [[41.2 API与后端服务]]
- [[41.3 数据库缓存与消息队列]]
- [[41.4 分布式系统设计]]
- [[41.5 高并发高可用]]
- [[41.6 测试部署与故障排查]]
- [[41.7 系统设计面试关键词✅]]

## 备注
- 这里作为高级 Agent 开发的通用工程底座入口。
```

按“空白概念卡合同”新增该分支的七个叶子节点。

- [ ] **Step 2: 新建 `42` 分支**

使用 `apply_patch` 新增 `42-Agent前沿能力深水区/_index.md`：

```markdown
# 42-Agent前沿能力深水区

## 子节点
- [[42.1 长期记忆系统]]
- [[42.2 Skills与可复用能力封装]]
- [[42.3 Browser与Computer Use Agent]]
- [[42.4 多模态Agent]]
- [[42.5 Tool Learning与Self-Improvement]]
- [[42.6 A2A与Agent协议生态]]
- [[42.7 前沿能力选型边界]]

## 备注
- 这里用于跟踪 2026 年 Agent 岗位中的前沿能力和选型边界。
```

按“空白概念卡合同”新增该分支的七个叶子节点。

- [ ] **Step 3: 更新开发岗位矩阵状态和覆盖统计**

把以下能力的结构状态从 `缺口` 改为 `已映射`：

```text
DEV-ENG-01 DEV-ENG-02 DEV-ENG-03 DEV-ENG-04 DEV-ENG-05
DEV-ENG-06 DEV-ENG-07 DEV-ENG-08 DEV-ENG-09 DEV-ENG-10
DEV-AGENT-09
DEV-FRONTIER-01 DEV-FRONTIER-02 DEV-FRONTIER-03 DEV-FRONTIER-04
DEV-FRONTIER-05 DEV-FRONTIER-06 DEV-FRONTIER-07
```

更新 `39.1 高级Agent开发.md` 的当前覆盖统计：

```text
180 / 180 = 100%
```

- [ ] **Step 4: 校验开发岗位覆盖率**

Run:

```bash
node <<'NODE'
const fs = require('fs');
const rows = fs.readFileSync('39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md', 'utf8')
  .split('\n')
  .filter(line => /^\| DEV-[A-Z]+-\d{2} \|/.test(line))
  .map(line => line.split('|').slice(1, -1).map(cell => cell.trim()));
const total = rows.reduce((sum, row) => sum + Number(row[5]), 0);
const mapped = rows.filter(row => row[9] === '已映射')
  .reduce((sum, row) => sum + Number(row[5]), 0);
console.log(`高级Agent开发: ${mapped}/${total} = ${(mapped / total * 100).toFixed(1)}%`);
if (mapped !== total) process.exit(1);
NODE
```

Expected:

```text
高级Agent开发: 180/180 = 100.0%
```

- [ ] **Step 5: 提交开发岗位结构**

Run:

```bash
git add -- \
  '41-通用工程与系统设计底座' \
  '42-Agent前沿能力深水区' \
  '39-岗位能力模型覆盖树/39.1 高级Agent开发.md' \
  '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md'
git commit -m 'docs: add agent engineering capability branches'
```

Expected: 只提交开发岗位相关结构。

## Task 5: 新增 ToB 产品基本功和中国大陆合规分支

**Files:**
- Create: `43-ToB AI产品经理基本功深水区/**`
- Create: `44-中国大陆AI合规落地深水区/**`
- Modify: `10-安全与治理层/_index.md`
- Modify: `39-岗位能力模型覆盖树/39.2 高级AI产品经理.md`
- Modify: `39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md`

- [ ] **Step 1: 新建 `43` 分支**

使用 `apply_patch` 新增 `43-ToB AI产品经理基本功深水区/_index.md`：

```markdown
# 43-ToB AI产品经理基本功深水区

## 子节点
- [[43.1 客户调研与用户研究]]
- [[43.2 需求分析与场景抽象]]
- [[43.3 PRD与产品方案]]
- [[43.4 Roadmap与版本规划]]
- [[43.5 埋点漏斗与数据分析]]
- [[43.6 A-B Test与灰度验证]]
- [[43.7 客户成功与规模化复制]]
- [[43.8 产品经理面试关键词]]

## 备注
- 这里作为 ToB 企业 AI / Agent 产品经理通用基本功入口。
```

按“空白概念卡合同”新增该分支的八个叶子节点。

- [ ] **Step 2: 新建 `44` 分支**

使用 `apply_patch` 新增 `44-中国大陆AI合规落地深水区/_index.md`：

```markdown
# 44-中国大陆AI合规落地深水区

## 子节点
- [[44.1 合规适用范围判断]]
- [[44.2 数据来源授权与个人信息保护]]
- [[44.3 生成合成内容标识]]
- [[44.4 算法备案与生成式AI服务管理]]
- [[44.5 企业内部AI使用规范]]
- [[44.6 审计留痕与责任边界]]
- [[44.7 合规面试关键词]]

## 备注
- 这里作为中国大陆 ToB AI 项目合规落地结构入口。
```

按“空白概念卡合同”新增该分支的七个叶子节点。

- [ ] **Step 3: 更新安全治理索引**

在 `10-安全与治理层/_index.md` 的备注中追加：

```markdown
- 中国大陆合规落地专项见 [[44-中国大陆AI合规落地深水区/_index|44-中国大陆AI合规落地深水区]]。
```

- [ ] **Step 4: 更新产品岗位矩阵状态和覆盖统计**

把以下能力的结构状态从 `缺口` 改为 `已映射`：

```text
PM-SCENE-06 PM-SCENE-07
PM-PRODUCT-07 PM-PRODUCT-08
PM-DATA-01 PM-DATA-02
PM-BIZ-05
PM-GOV-04 PM-GOV-05 PM-GOV-06 PM-GOV-07 PM-GOV-08 PM-GOV-09
```

更新 `39.2 高级AI产品经理.md` 的当前覆盖统计：

```text
160 / 160 = 100%
```

- [ ] **Step 5: 校验产品岗位覆盖率**

运行 Task 7 中的矩阵校验脚本。

Expected:

```text
ToB企业AI-Agent产品经理: 160/160 = 100.0%
```

- [ ] **Step 6: 提交产品岗位结构**

Run:

```bash
git add -- \
  '43-ToB AI产品经理基本功深水区' \
  '44-中国大陆AI合规落地深水区' \
  '10-安全与治理层/_index.md' \
  '39-岗位能力模型覆盖树/39.2 高级AI产品经理.md' \
  '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md'
git commit -m 'docs: add tob ai product and compliance branches'
```

Expected: 只提交产品岗位相关结构。

## Task 6: 同步总览和生成审计报告

**Files:**
- Modify: `00-总览/AI Agent 面试知识库首页.md`
- Modify: `00-总览/企业AI应用落地完整知识树.md`
- Modify: `99-附件/知识地图.md`
- Create: `99-附件/岗位能力覆盖审计-2026-05.md`

- [ ] **Step 1: 更新知识库首页**

使用 `apply_patch`：

1. 把 `## 40 个一级分支` 改为 `## 44 个一级分支`。
2. 在一级分支列表末尾追加：

```markdown
- [[41-通用工程与系统设计底座/_index|41-通用工程与系统设计底座]]
- [[42-Agent前沿能力深水区/_index|42-Agent前沿能力深水区]]
- [[43-ToB AI产品经理基本功深水区/_index|43-ToB AI产品经理基本功深水区]]
- [[44-中国大陆AI合规落地深水区/_index|44-中国大陆AI合规落地深水区]]
```

3. 在 `## 优先深挖` 末尾追加：

```markdown
- [[39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵|双岗位能力覆盖矩阵]]
```

- [ ] **Step 2: 更新完整知识树**

使用 `apply_patch`：

1. 在 `12-模型与推理层`、`15-EvalOps反馈闭环层` 和 `20-RAG深水区` 下追加本计划新增叶子。
2. 在文件末尾追加 `41` 至 `44` 四个一级分支及其全部叶子。

- [ ] **Step 3: 更新附件知识地图**

`99-附件/知识地图.md` 已存在。只使用 `apply_patch` 做以下定向修改：

1. 标题版本从 `v4` 更新为 `v5`。
2. 根节点说明从 `1 ～ 40` 更新为 `1 ～ 44`。
3. 在 `12`、`15` 和 `20` 分支中追加新增叶子。
4. 在现有 `40` 分支后追加 `41` 至 `44` 四个一级分支及其全部叶子。
5. 不改写原有 `01` 至 `40` 的其他内容。

- [ ] **Step 4: 新增覆盖审计报告**

使用 `apply_patch` 新增 `99-附件/岗位能力覆盖审计-2026-05.md`。报告必须包含：

```markdown
# 岗位能力覆盖审计：2026 年 5 月中国大陆

## 评估范围
- 高级 Agent 开发工程师
- ToB 企业 AI / Agent 产品经理
- 时间基线：截至 2026-05-31

## 口径说明
- 结构覆盖率表示原子能力存在可达的主知识节点。
- 结构覆盖率不等于知识掌握率，也不等于面试准备完成度。

## 改造前严格映射基线
| 岗位 | 已映射权重 | 总权重 | 结构覆盖率 |
|---|---:|---:|---:|
| 高级Agent开发 | 127 | 180 | 70.6% |
| ToB企业AI-Agent产品经理 | 125 | 160 | 78.1% |
| 总体 | 252 | 340 | 74.1% |

## 改造后结构覆盖率
| 岗位 | 已映射权重 | 总权重 | 结构覆盖率 |
|---|---:|---:|---:|
| 高级Agent开发 | 180 | 180 | 100.0% |
| ToB企业AI-Agent产品经理 | 160 | 160 | 100.0% |
| 总体 | 340 | 340 | 100.0% |

## 新增一级分支
## 既有分支扩展
## 未映射能力
- 无

## 下一阶段说明
- 后续按面试收益优先级填充知识卡正文。
```

在“新增一级分支”和“既有分支扩展”章节写入本计划文件结构中声明的完整清单。

- [ ] **Step 5: 提交总览和审计报告**

Run:

```bash
git add -- \
  '00-总览/AI Agent 面试知识库首页.md' \
  '00-总览/企业AI应用落地完整知识树.md' \
  '99-附件/知识地图.md' \
  '99-附件/岗位能力覆盖审计-2026-05.md'
git commit -m 'docs: sync capability map overview and audit'
```

Expected: `99-附件/知识地图.md` 被有意纳入提交，其余用户原有改动不进入提交。

## Task 7: 执行最终验收

**Files:**
- Read only: repository Markdown files
- Read only: `.obsidian/workspace.json`
- Read only: `05-Agent系统化落地层/**`

- [ ] **Step 1: 校验 Git diff 格式**

Run:

```bash
git diff --check "$(cat /tmp/capability-map-start.commit)"..HEAD
```

Expected: 无输出，退出码为 `0`。

- [ ] **Step 2: 校验矩阵 ID、主节点、P0 和覆盖率**

Run:

```bash
node <<'NODE'
const fs = require('fs');
const path = require('path');

const matrixPath = '39-岗位能力模型覆盖树/39.7 双岗位能力覆盖矩阵.md';
const matrix = fs.readFileSync(matrixPath, 'utf8');
const rows = matrix.split('\n')
  .filter(line => /^\| (DEV|PM)-[A-Z]+-\d{2} \|/.test(line))
  .map(line => line.split('|').slice(1, -1).map(cell => cell.trim()));

if (rows.length !== 137) throw new Error(`expected 137 rows, got ${rows.length}`);

const ids = rows.map(row => row[0]);
const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
if (duplicates.length) throw new Error(`duplicate ids: ${[...new Set(duplicates)].join(', ')}`);

const markdownFiles = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '.git') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    if (entry.isFile() && entry.name.endsWith('.md')) markdownFiles.push(full);
  }
}
walk('.');

const targets = new Set();
for (const file of markdownFiles) {
  targets.add(file.replace(/^\.\//, '').replace(/\.md$/, ''));
  targets.add(path.basename(file, '.md'));
}

const scores = new Map();
for (const row of rows) {
  const [id, role, domain, capability, priority, weightText, mainNode, auxiliary, evidence, status] = row;
  const weight = Number(weightText);
  const match = mainNode.match(/^\[\[([^\]|]+)(?:\|[^\]]+)?\]\]$/);
  if (!match) throw new Error(`${id}: invalid main node ${mainNode}`);
  if (!targets.has(match[1])) throw new Error(`${id}: missing main node ${match[1]}`);
  if (status !== '已映射') throw new Error(`${id}: status is ${status}`);
  if (priority === 'P0' && status !== '已映射') throw new Error(`${id}: P0 is not mapped`);
  if (!['1', '2', '3'].includes(weightText)) throw new Error(`${id}: invalid weight ${weightText}`);
  const current = scores.get(role) || { mapped: 0, total: 0 };
  current.total += weight;
  if (status === '已映射') current.mapped += weight;
  scores.set(role, current);
}

for (const [role, score] of scores.entries()) {
  const percent = (score.mapped / score.total * 100).toFixed(1);
  console.log(`${role}: ${score.mapped}/${score.total} = ${percent}%`);
  if (score.mapped / score.total < 0.95) throw new Error(`${role}: coverage below 95%`);
}
NODE
```

Expected:

```text
高级Agent开发: 180/180 = 100.0%
ToB企业AI-Agent产品经理: 160/160 = 100.0%
```

- [ ] **Step 3: 校验四个一级分支已同步到三份总览**

Run:

```bash
for f in \
  '00-总览/AI Agent 面试知识库首页.md' \
  '00-总览/企业AI应用落地完整知识树.md' \
  '99-附件/知识地图.md'; do
  for n in 41 42 43 44; do
    rg -q "$n" "$f" || exit 1
  done
done
```

Expected: 无输出，退出码为 `0`。

- [ ] **Step 4: 校验受保护文件没有新增变化**

Run:

```bash
find .obsidian 05-Agent系统化落地层 -type f -print0 | sort -z | xargs -0 shasum -a 256 > /tmp/capability-map-protected.after.sha256
diff -u /tmp/capability-map-protected.before.sha256 /tmp/capability-map-protected.after.sha256
```

Expected: 无输出，退出码为 `0`。

- [ ] **Step 5: 检查最终工作区**

Run:

```bash
git status --short --untracked-files=all
```

Expected: 只保留执行开始前已有的受保护文件或 Canvas 改动，不出现本计划遗漏的未提交文件。`99-附件/知识地图.md` 已有意进入提交。

## 附录 A：能力矩阵记录

下表是矩阵的规范性数据源。`主知识节点` 必须按 Wiki 链接写入矩阵。`项目证据入口` 必须按表填写。`辅助节点` 固定填写 `无`。

### A.1 高级 Agent 开发：72 项，180 权重

| 能力ID | 能力域 | 原子能力 | 优先级 | 主知识节点 | 项目证据入口 |
|---|---|---|---|---|---|
| DEV-ENG-01 | 通用工程与系统设计 | 使用主流后端语言实现可维护服务 | P0 | [[41.1 编程语言与异步编程]] | [[企业AI开发套件项目]] |
| DEV-ENG-02 | 通用工程与系统设计 | 处理异步任务、并发执行和资源控制 | P0 | [[41.1 编程语言与异步编程]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-ENG-03 | 通用工程与系统设计 | 设计 REST、RPC 和 Webhook API | P0 | [[41.2 API与后端服务]] | [[企业AI开发套件项目]] |
| DEV-ENG-04 | 通用工程与系统设计 | 使用数据库事务、索引和查询优化 | P1 | [[41.3 数据库缓存与消息队列]] | [[企业AI开发套件项目]] |
| DEV-ENG-05 | 通用工程与系统设计 | 使用缓存、消息队列和事件驱动机制 | P1 | [[41.3 数据库缓存与消息队列]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-ENG-06 | 通用工程与系统设计 | 设计分布式一致性和幂等边界 | P0 | [[41.4 分布式系统设计]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-ENG-07 | 通用工程与系统设计 | 设计限流、熔断、降级和高可用方案 | P0 | [[41.5 高并发高可用]] | [[企业AI开发套件项目]] |
| DEV-ENG-08 | 通用工程与系统设计 | 建立测试、容器化和 CI/CD 流程 | P1 | [[41.6 测试部署与故障排查]] | [[AI Coding工程化项目✅]] |
| DEV-ENG-09 | 通用工程与系统设计 | 定位日志、链路和生产故障 | P1 | [[41.6 测试部署与故障排查]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-ENG-10 | 通用工程与系统设计 | 完成系统设计取舍和容量分析 | P0 | [[41.7 系统设计面试关键词✅]] | [[企业AI开发套件项目]] |
| DEV-MODEL-01 | 模型与推理 | 理解 Transformer、Token 和上下文窗口 | P1 | [[12.7 Transformer与大模型基础]] | [[企业AI开发套件项目]] |
| DEV-MODEL-02 | 模型与推理 | 按任务效果、延迟和成本选择模型 | P0 | [[12.1 模型选型]] | [[企业AI开发套件项目]] |
| DEV-MODEL-03 | 模型与推理 | 设计上下文裁剪、压缩和注入策略 | P0 | [[12.4 Context Engineering]] | [[应用生成智能体项目✅]] |
| DEV-MODEL-04 | 模型与推理 | 理解 Embedding 和 Rerank 原理 | P1 | [[12.8 Embedding与Rerank原理]] | [[企业AI开发套件项目]] |
| DEV-MODEL-05 | 模型与推理 | 判断 SFT、DPO、LoRA、RAG 和规则边界 | P1 | [[12.5 微调与替代方案]] | [[企业AI开发套件项目]] |
| DEV-MODEL-06 | 模型与推理 | 理解量化和私有化模型部署 | P2 | [[12.9 微调量化与模型部署]] | [[企业AI开发套件项目]] |
| DEV-MODEL-07 | 模型与推理 | 理解推理加速、GPU 和 vLLM 基础 | P2 | [[12.10 推理加速与GPU基础]] | [[企业AI开发套件项目]] |
| DEV-MODEL-08 | 模型与推理 | 实现模型网关、路由、熔断和 fallback | P0 | [[12.6 推理服务]] | [[企业AI开发套件项目]] |
| DEV-AGENT-01 | Agent 架构与编排 | 判断 Agent、Workflow 和传统系统边界 | P0 | [[5.2 Agent架构模式]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-02 | Agent 架构与编排 | 设计 Router、Planner、Executor 和 Critic | P0 | [[5.4 Planning-Reasoning]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-03 | Agent 架构与编排 | 实现 Agent Orchestrator 调度 | P0 | [[13.9 Agent Orchestrator]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-04 | Agent 架构与编排 | 判断何时使用 Multi-Agent | P1 | [[22.1 是否需要Multi-Agent]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-05 | Agent 架构与编排 | 选择 DAG、Supervisor-Worker 和 Critic-Refine 编排模式 | P1 | [[22.3 编排模式]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-06 | Agent 架构与编排 | 设计多 Agent 通信和收敛条件 | P1 | [[22.4 多Agent通信]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-07 | Agent 架构与编排 | 设计 Human-in-the-loop 审批和接管 | P0 | [[5.7 Human-in-the-loop]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-AGENT-08 | Agent 架构与编排 | 设计复杂任务拆解和动态重规划 | P0 | [[13.9 Agent Orchestrator]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-09 | Agent 架构与编排 | 设计短期记忆和长期记忆边界 | P1 | [[42.1 长期记忆系统]] | [[应用生成智能体项目✅]] |
| DEV-AGENT-10 | Agent 架构与编排 | 按业务约束选择 Agent 框架 | P1 | [[37.1 Agent框架]] | [[企业AI开发套件项目]] |
| DEV-RUNTIME-01 | Agent Runtime | 建模任务状态机和生命周期 | P0 | [[13.5 任务生命周期]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-02 | Agent Runtime | 实现 Durable Execution | P0 | [[13.1 Durable Execution]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-03 | Agent Runtime | 实现 Checkpoint 和断点恢复 | P0 | [[13.1 Durable Execution]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-04 | Agent Runtime | 使用 Event Log 支撑 Replay 和 RCA | P0 | [[13.6 Replay-Time Travel]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-05 | Agent Runtime | 处理工具执行和状态保存一致性 | P0 | [[13.2 状态一致性]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-06 | Agent Runtime | 实现幂等、去重和重试安全 | P0 | [[13.3 幂等与去重]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-07 | Agent Runtime | 设计队列、Worker 和并发调度 | P0 | [[13.4 并发控制]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-08 | Agent Runtime | 处理取消、超时、失败和降级 | P1 | [[5.3 Agent Runtime]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-09 | Agent Runtime | 建立 Trace、指标和任务成本观测 | P0 | [[13.7 Runtime可观测性]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RUNTIME-10 | Agent Runtime | 支撑长任务暂停、审批后恢复和人工接管 | P1 | [[13.1 Durable Execution]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-TOOL-01 | Tool / MCP | 设计结构化 Tool Schema | P0 | [[21.2 Tool Schema]] | [[企业AI开发套件项目]] |
| DEV-TOOL-02 | Tool / MCP | 实现 Tool Executor 参数、权限和结果校验 | P0 | [[21.3 Tool Executor]] | [[企业AI开发套件项目]] |
| DEV-TOOL-03 | Tool / MCP | 使用 MCP Server 标准化工具封装 | P0 | [[21.4 MCP Server]] | [[企业AI开发套件项目]] |
| DEV-TOOL-04 | Tool / MCP | 设计工具风险分级和审批 | P0 | [[21.6 工具风险分级]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-TOOL-05 | Tool / MCP | 处理工具失败、重试和只读降级 | P0 | [[21.7 工具调用失败处理]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-TOOL-06 | Tool / MCP | 接入 REST、GraphQL、Webhook 和 SDK | P1 | [[7.3 API集成]] | [[企业AI开发套件项目]] |
| DEV-TOOL-07 | Tool / MCP | 记录工具调用审计链路 | P1 | [[31.5 审计]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-RAG-01 | RAG | 判断 RAG、Tool 和微调适用边界 | P0 | [[20.1 RAG适用场景判断]] | [[企业AI开发套件项目]] |
| DEV-RAG-02 | RAG | 设计文档接入、解析和 Chunk 策略 | P0 | [[20.3 文档解析]] | [[企业AI开发套件项目]] |
| DEV-RAG-03 | RAG | 设计 Metadata 和权限过滤 | P0 | [[20.5 Metadata设计]] | [[企业AI开发套件项目]] |
| DEV-RAG-04 | RAG | 理解 BM25 和倒排索引 | P1 | [[20.11 BM25与倒排索引]] | [[企业AI开发套件项目]] |
| DEV-RAG-05 | RAG | 实现关键词、向量和混合检索 | P0 | [[20.6 检索策略]] | [[企业AI开发套件项目]] |
| DEV-RAG-06 | RAG | 理解向量数据库、HNSW 和 IVF | P1 | [[20.12 向量数据库与HNSW-IVF]] | [[企业AI开发套件项目]] |
| DEV-RAG-07 | RAG | 设计 Rerank 和上下文预算 | P0 | [[20.7 Rerank策略]] | [[企业AI开发套件项目]] |
| DEV-RAG-08 | RAG | 优化检索延迟和召回性能 | P1 | [[20.13 检索性能与延迟优化]] | [[企业AI开发套件项目]] |
| DEV-RAG-09 | RAG | 评估和归因 RAG 失败类型 | P0 | [[20.9 RAG失败类型]] | [[企业AI开发套件项目]] |
| DEV-EVAL-01 | EvalOps | 构建 Golden Dataset 和 Bad Case Dataset | P0 | [[15.2 样本构建]] | [[AI Coding工程化项目✅]] |
| DEV-EVAL-02 | EvalOps | 实现规则评测、LLM-as-Judge 和轨迹评测 | P0 | [[15.3 自动评测]] | [[AI Coding工程化项目✅]] |
| DEV-EVAL-03 | EvalOps | 实现可复现评测和实验对比 | P1 | [[15.10 可复现评测与实验管理]] | [[AI Coding工程化项目✅]] |
| DEV-EVAL-04 | EvalOps | 建立变更回归和上线门禁 | P0 | [[15.5 回归体系]] | [[AI Coding工程化项目✅]] |
| DEV-EVAL-05 | EvalOps | 监控在线指标和质量看板 | P1 | [[15.7 指标看板]] | [[企业AI开发套件项目]] |
| DEV-EVAL-06 | EvalOps | 建立 Bad Case 闭环优化 | P0 | [[15.6 闭环优化]] | [[AI Coding工程化项目✅]] |
| DEV-SEC-01 | 安全治理 | 防护直接和间接 Prompt Injection | P0 | [[30.1 Prompt Injection]] | [[企业AI开发套件项目]] |
| DEV-SEC-02 | 安全治理 | 强制执行数据权限和多租户隔离 | P0 | [[31.4 数据权限✅]] | [[企业AI开发套件项目]] |
| DEV-SEC-03 | 安全治理 | 使用沙箱、审批和白名单控制工具滥用 | P0 | [[30.4 工具滥用风险]] | [[运维智能体项目-OpsPilot✅]] |
| DEV-SEC-04 | 安全治理 | 建立红队测试和安全回归集 | P1 | [[30.6 红队测试]] | [[企业AI开发套件项目]] |
| DEV-SEC-05 | 安全治理 | 建立模型、知识和工具审计 | P0 | [[31.5 审计]] | [[企业AI开发套件项目]] |
| DEV-FRONTIER-01 | Agent 前沿能力 | 设计长期记忆系统 | P1 | [[42.1 长期记忆系统]] | [[应用生成智能体项目✅]] |
| DEV-FRONTIER-02 | Agent 前沿能力 | 封装 Skills 和可复用能力 | P1 | [[42.2 Skills与可复用能力封装]] | [[AI Coding工程化项目✅]] |
| DEV-FRONTIER-03 | Agent 前沿能力 | 理解 Browser 和 Computer Use Agent | P2 | [[42.3 Browser与Computer Use Agent]] | [[应用生成智能体项目✅]] |
| DEV-FRONTIER-04 | Agent 前沿能力 | 设计多模态 Agent 输入和工具链 | P1 | [[42.4 多模态Agent]] | [[应用生成智能体项目✅]] |
| DEV-FRONTIER-05 | Agent 前沿能力 | 理解 Tool Learning 和 Self-Improvement | P2 | [[42.5 Tool Learning与Self-Improvement]] | [[AI Coding工程化项目✅]] |
| DEV-FRONTIER-06 | Agent 前沿能力 | 理解 A2A 和 Agent 协议生态 | P2 | [[42.6 A2A与Agent协议生态]] | [[企业AI开发套件项目]] |
| DEV-FRONTIER-07 | Agent 前沿能力 | 判断前沿能力的生产采用边界 | P1 | [[42.7 前沿能力选型边界]] | [[企业AI开发套件项目]] |

### A.2 ToB 企业 AI / Agent 产品经理：65 项，160 权重

| 能力ID | 能力域 | 原子能力 | 优先级 | 主知识节点 | 项目证据入口 |
|---|---|---|---|---|---|
| PM-SCENE-01 | 场景判断与需求抽象 | 识别企业业务痛点 | P0 | [[1.1 业务问题识别]] | [[运维智能体项目-OpsPilot✅]] |
| PM-SCENE-02 | 场景判断与需求抽象 | 识别知识、流程、决策和生成类场景 | P0 | [[1.2 场景类型识别]] | [[应用生成智能体项目✅]] |
| PM-SCENE-03 | 场景判断与需求抽象 | 量化提效、降本、增收、提质和风控价值 | P0 | [[1.3 业务价值判断]] | [[运维智能体项目-OpsPilot✅]] |
| PM-SCENE-04 | 场景判断与需求抽象 | 判断 AI 适用性 | P0 | [[1.4 AI适用性判断]] | [[企业AI开发套件项目]] |
| PM-SCENE-05 | 场景判断与需求抽象 | 识别不适合直接 AI 化的场景 | P1 | [[1.5 不适合直接AI化的场景]] | [[企业AI开发套件项目]] |
| PM-SCENE-06 | 场景判断与需求抽象 | 执行客户调研和用户研究 | P0 | [[43.1 客户调研与用户研究]] | [[运维智能体项目-OpsPilot✅]] |
| PM-SCENE-07 | 场景判断与需求抽象 | 抽象需求、流程节点和系统集成点 | P0 | [[43.2 需求分析与场景抽象]] | [[企业AI开发套件项目]] |
| PM-SCENE-08 | 场景判断与需求抽象 | 按客户价值、可行性和风险排序需求 | P0 | [[17.6 需求优先级]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-01 | AI 产品方案 | 选择 Assistant、Copilot、Agent、Workflow 或 Platform | P0 | [[2.1 产品定位]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-02 | AI 产品方案 | 定义用户角色和权限边界 | P0 | [[2.2 用户角色设计]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-03 | AI 产品方案 | 设计多模态输入和任务输出 | P1 | [[2.3 用户输入设计]] | [[应用生成智能体项目✅]] |
| PM-PRODUCT-04 | AI 产品方案 | 设计人机协同和审批节点 | P0 | [[2.6 人机协同设计]] | [[运维智能体项目-OpsPilot✅]] |
| PM-PRODUCT-05 | AI 产品方案 | 定义 AI 能力边界、失败兜底和责任边界 | P0 | [[2.7 产品边界设计]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-06 | AI 产品方案 | 设计高频低风险 MVP | P0 | [[2.8 MVP范围设计]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-07 | AI 产品方案 | 编写 PRD 和 AI 产品方案 | P0 | [[43.3 PRD与产品方案]] | [[应用生成智能体项目✅]] |
| PM-PRODUCT-08 | AI 产品方案 | 规划 Roadmap 和版本节奏 | P1 | [[43.4 Roadmap与版本规划]] | [[企业AI开发套件项目]] |
| PM-PRODUCT-09 | AI 产品方案 | 设计可解释、可控和可接管体验 | P0 | [[33.4 可控体验]] | [[运维智能体项目-OpsPilot✅]] |
| PM-TECH-01 | AI 技术理解 | 理解模型选型的效果、延迟和成本取舍 | P2 | [[12.1 模型选型]] | [[企业AI开发套件项目]] |
| PM-TECH-02 | AI 技术理解 | 理解 Prompt 和 Context Engineering | P1 | [[12.4 Context Engineering]] | [[企业AI开发套件项目]] |
| PM-TECH-03 | AI 技术理解 | 理解 RAG 适用场景和关键链路 | P0 | [[20.1 RAG适用场景判断]] | [[企业AI开发套件项目]] |
| PM-TECH-04 | AI 技术理解 | 理解 Tool / MCP 的行动边界 | P0 | [[21.1 Tool设计原则]] | [[企业AI开发套件项目]] |
| PM-TECH-05 | AI 技术理解 | 理解 Agent Runtime 生产风险 | P0 | [[5.3 Agent Runtime]] | [[运维智能体项目-OpsPilot✅]] |
| PM-TECH-06 | AI 技术理解 | 判断 Multi-Agent 是否必要 | P2 | [[22.1 是否需要Multi-Agent]] | [[应用生成智能体项目✅]] |
| PM-TECH-07 | AI 技术理解 | 理解平台化沉淀价值 | P1 | [[14.9 平台化价值]] | [[企业AI开发套件项目]] |
| PM-TECH-08 | AI 技术理解 | 使用评测门禁控制上线风险 | P0 | [[15.8 上线门禁]] | [[企业AI开发套件项目]] |
| PM-EVAL-01 | 评测与运营 | 定义业务结果指标 | P0 | [[9.1 业务指标]] | [[运维智能体项目-OpsPilot✅]] |
| PM-EVAL-02 | 评测与运营 | 定义 Agent 执行指标 | P0 | [[9.3 Agent执行指标]] | [[运维智能体项目-OpsPilot✅]] |
| PM-EVAL-03 | 评测与运营 | 理解 RAG 评测指标 | P1 | [[9.4 RAG指标]] | [[企业AI开发套件项目]] |
| PM-EVAL-04 | 评测与运营 | 建立 Bad Case 运营机制 | P0 | [[9.6 Bad Case运营]] | [[企业AI开发套件项目]] |
| PM-EVAL-05 | 评测与运营 | 设计评测产品和评分 Rubric | P1 | [[15.9 评测产品设计]] | [[企业AI开发套件项目]] |
| PM-EVAL-06 | 评测与运营 | 管理可复现评测和实验对比 | P1 | [[15.10 可复现评测与实验管理]] | [[企业AI开发套件项目]] |
| PM-EVAL-07 | 评测与运营 | 建立线上质量看板 | P1 | [[15.7 指标看板]] | [[企业AI开发套件项目]] |
| PM-DATA-01 | 数据分析与知识运营 | 设计埋点、漏斗、留存和分群指标 | P0 | [[43.5 埋点漏斗与数据分析]] | [[企业AI开发套件项目]] |
| PM-DATA-02 | 数据分析与知识运营 | 设计 A/B Test 和灰度验证 | P1 | [[43.6 A-B Test与灰度验证]] | [[企业AI开发套件项目]] |
| PM-DATA-03 | 数据分析与知识运营 | 识别数据质量风险 | P1 | [[32.4 数据质量]] | [[企业AI开发套件项目]] |
| PM-DATA-04 | 数据分析与知识运营 | 建立用户反馈和 Bad Case 数据闭环 | P0 | [[32.5 数据闭环]] | [[企业AI开发套件项目]] |
| PM-DATA-05 | 数据分析与知识运营 | 规划知识生命周期和知识运营 | P1 | [[32.3 知识工程]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-01 | 交付与组织推进 | 规划立项到规模化阶段 | P0 | [[34.1 立项阶段]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-02 | 交付与组织推进 | 使用 PoC 验证关键假设 | P0 | [[34.2 PoC阶段]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-03 | 交付与组织推进 | 设计 MVP 和试点闭环 | P0 | [[34.3 MVP阶段]] | [[运维智能体项目-OpsPilot✅]] |
| PM-DELIVERY-04 | 交付与组织推进 | 推动生产治理和正式上线 | P1 | [[34.5 生产阶段]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-05 | 交付与组织推进 | 推动模板化交付和规模复制 | P1 | [[34.6 规模化阶段]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-06 | 交付与组织推进 | 协同业务、研发、数据、安全和管理层 | P1 | [[11.2 角色协作]] | [[企业AI开发套件项目]] |
| PM-DELIVERY-07 | 交付与组织推进 | 完成客户需求调研和成功标准定义 | P0 | [[35.1 需求调研]] | [[运维智能体项目-OpsPilot✅]] |
| PM-PLATFORM-01 | 平台产品理解 | 理解模型网关平台 | P1 | [[14.1 模型网关平台]] | [[企业AI开发套件项目]] |
| PM-PLATFORM-02 | 平台产品理解 | 理解 Prompt 管理平台 | P1 | [[14.2 Prompt管理平台]] | [[企业AI开发套件项目]] |
| PM-PLATFORM-03 | 平台产品理解 | 理解 RAG 知识平台 | P1 | [[14.3 RAG知识平台]] | [[企业AI开发套件项目]] |
| PM-PLATFORM-04 | 平台产品理解 | 理解 Tool / MCP 平台 | P1 | [[14.4 Tool-MCP平台]] | [[企业AI开发套件项目]] |
| PM-PLATFORM-05 | 平台产品理解 | 理解 Agent 编排平台 | P1 | [[14.5 Agent编排平台]] | [[企业AI开发套件项目]] |
| PM-PLATFORM-06 | 平台产品理解 | 理解 Eval 平台 | P1 | [[14.6 Eval平台]] | [[企业AI开发套件项目]] |
| PM-BIZ-01 | 商业化与客户成功 | 量化客户价值和 ROI | P0 | [[17.3 客户价值证明]] | [[企业AI开发套件项目]] |
| PM-BIZ-02 | 商业化与客户成功 | 理解 SaaS、私有化和项目制商业模式 | P2 | [[17.1 商业模式]] | [[企业AI开发套件项目]] |
| PM-BIZ-03 | 商业化与客户成功 | 设计计费和定价维度 | P1 | [[17.2 定价维度]] | [[企业AI开发套件项目]] |
| PM-BIZ-04 | 商业化与客户成功 | 运营活跃、留存、采纳率和续费指标 | P1 | [[17.5 产品经营]] | [[企业AI开发套件项目]] |
| PM-BIZ-05 | 商业化与客户成功 | 推动客户成功和规模化复制 | P0 | [[43.7 客户成功与规模化复制]] | [[企业AI开发套件项目]] |
| PM-BIZ-06 | 商业化与客户成功 | 做出效果、成本、风险和平台化取舍 | P0 | [[17.7 高级产品取舍]] | [[企业AI开发套件项目]] |
| PM-GOV-01 | 安全与中国大陆合规 | 设计用户、角色、租户和工具权限 | P0 | [[10.1 权限控制]] | [[企业AI开发套件项目]] |
| PM-GOV-02 | 安全与中国大陆合规 | 控制敏感信息、脱敏和数据不出域 | P0 | [[10.2 数据安全]] | [[企业AI开发套件项目]] |
| PM-GOV-03 | 安全与中国大陆合规 | 设计 Agent 行为边界和高风险审批 | P0 | [[10.5 Agent行为治理✅]] | [[运维智能体项目-OpsPilot✅]] |
| PM-GOV-04 | 安全与中国大陆合规 | 判断中国大陆 AI 合规适用范围 | P1 | [[44.1 合规适用范围判断]] | [[企业AI开发套件项目]] |
| PM-GOV-05 | 安全与中国大陆合规 | 管理数据来源授权和个人信息保护 | P1 | [[44.2 数据来源授权与个人信息保护]] | [[企业AI开发套件项目]] |
| PM-GOV-06 | 安全与中国大陆合规 | 规划生成合成内容显式和隐式标识 | P1 | [[44.3 生成合成内容标识]] | [[企业AI开发套件项目]] |
| PM-GOV-07 | 安全与中国大陆合规 | 判断算法备案和生成式 AI 服务管理要求 | P1 | [[44.4 算法备案与生成式AI服务管理]] | [[企业AI开发套件项目]] |
| PM-GOV-08 | 安全与中国大陆合规 | 建立企业内部 AI 使用规范 | P1 | [[44.5 企业内部AI使用规范]] | [[企业AI开发套件项目]] |
| PM-GOV-09 | 安全与中国大陆合规 | 建立审计留痕和责任边界 | P1 | [[44.6 审计留痕与责任边界]] | [[企业AI开发套件项目]] |
