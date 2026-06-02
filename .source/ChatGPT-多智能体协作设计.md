# 多智能体协作设计

**User:** Anonymous  
**Created:** 6/1/2026 16:43:40  
**Updated:** 6/1/2026 17:22:51  
**Exported:** 6/3/2026 0:23:10  
**Link:** [https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813-aimian-shi/c/6a1d45ff-2ca8-83ec-a2ee-9973116046b8](https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813-aimian-shi/c/6a1d45ff-2ca8-83ec-a2ee-9973116046b8)  

## Prompt:
2026/6/1 16:43:39

针对 应用开发智能体和运维智能体，回答以下问题：1、多agent如何协作 2、数据库、redis、消息队列怎么设计，数据库都存什么 3、checkpoint都是怎么设计的

## Response:
2026/6/1 16:43:39

> **考虑引用格式和回应结构**
>
> Mclick工具显示的内容没有行号，这让我在引用时有些困惑。根据指示，引用格式要求精确匹配，但没有行号。可能需要省略行号，或者引用整个文件，而这是系统说不允许的。如果必须严格遵循，引用片段或图表可能是可行的。
>
> 已思考 42s

我会按“面试可讲 + 技术可落地”的口径来拆：先分别讲两个智能体的协作流，再统一抽象底层状态、存储、队列和 checkpoint 设计，避免空泛。

我已经把两个项目区分开了：应用开发智能体偏“生成与变更流水线”，运维智能体偏“诊断与受控执行流水线”。底层共同点是：Agent 本身不存状态，状态进数据库；短期运行态进 Redis；异步节点靠队列推进。

下面这套回答可以直接用于面试。核心口径是：

> **我的两个智能体不是“多个大模型互相聊天”，而是把复杂任务拆成多个有边界的 Agent 节点，由 Orchestrator 统一调度，每个 Agent 只负责一个确定环节，所有中间产物、状态、事件、审批、checkpoint 都结构化落库。**

---

# 1. 多 Agent 如何协作

## 一、应用开发智能体：生成型工作流

你的应用开发智能体本质是：

> **自然语言需求 → 意图识别 → 任务规划 → 页面生成 → Schema / SQL → 数据接入 → 预览验证 → 增量修改 → 部署交付**

这和你简历里的描述一致：基于 Router / Planner 分层，把自然语言需求、页面生成、Schema 生成、SQL 建表 / 迁移、数据接入、预览验证和增量修改拆成可编排、可验证、可迭代的流程。`欧阳锦峰-AI-7年.pdf`

### 多 Agent 分工

| Agent | 职责 | 输入 | 输出 |
|---|---|---|---|
| **Orchestrator** | 总调度器，不直接生成代码 | user_request、run_id、当前项目状态 | 任务依赖图 / 状态流转 / 下一步任务 |
| **Router Agent** | 判断需求类型 | 用户自然语言、轻量项目上下文 | intent：新建应用、改页面、改字段、改路由、改数据结构 |
| **Context / RAG Agent** | 检索相关上下文 | intent、app_id、page_id | 相关页面、Schema、历史变更、规范、样例 |
| **UI Planner** | 规划页面和组件变更 | 用户需求、页面上下文 | page_change_plan、component_plan |
| **Supabase / DBA Planner** | 规划数据结构 | 字段需求、旧 Schema | table_plan、field_plan、migration_plan |
| **Routing Planner** | 规划路由和导航 | 页面变化、routes manifest | route_change_plan |
| **Codegen Agent** | 生成 / 修改 React 代码 | UI plan、Schema、代码上下文 | 文件 patch、组件代码、数据绑定代码 |
| **SQL / Migration Agent** | 生成 SQL / 迁移脚本 | schema plan | create table / alter table SQL |
| **QA Agent** | 校验代码与运行结果 | 代码、SQL、预览日志 | lint / tsc / runtime / preview 结果 |
| **Deploy Agent** | 打包部署 | 通过 QA 的版本 | deployment_url、release_record |
| **Memory / Feedback Agent** | 沉淀 bad case | 运行日志、用户反馈 | 样例库、规则、知识库增量 |

### 协作方式

不是所有 Agent 串行执行。比较合理的是 **任务依赖图 + 状态机**：

```text
User Request
   ↓
Orchestrator
   ↓
Router Agent
   ↓
Context / RAG Agent
   ↓
┌───────────────┬────────────────────┬────────────────┐
│ UI Planner     │ Supabase Planner   │ Routing Planner │
└───────┬───────┴─────────┬──────────┴───────┬────────┘
        ↓                 ↓                  ↓
   Codegen Agent     SQL/Migration Agent    Route Codegen
        ↓                 ↓                  ↓
        └──────────────┬──┴──────────────────┘
                       ↓
                  QA Agent
                       ↓
                Preview / Deploy
                       ↓
              Memory / Bad Case
```

面试中可以这样说：

> 应用生成智能体里，我没有让一个大模型一次性完成所有事情，而是拆成 Router、Planner、Codegen、DBA、QA 等多个角色。Router 负责识别任务类型，Planner 负责生成结构化执行计划，Codegen 只根据计划修改指定文件，DBA Agent 只处理 Schema 和 SQL，QA Agent 负责验证。Orchestrator 根据任务依赖图调度这些节点，每个节点的输入输出都用 JSON Schema 约束，并且都会落库，方便失败恢复和审计。

---

## 二、运维智能体：诊断型工作流

运维智能体本质是：

> **工单接入 → 自动分诊 → 多源证据采集 → 根因假设 → 处置建议 → 人工审批 → 模拟 / 受控执行 → 结果验证 → RCA 复盘**

这和你项目中的端到端闭环一致：工单接入、自动分诊、多源证据采集、根因假设、处置建议、人工审批、模拟执行 / 受控执行、结果验证、RCA 复盘。`欧阳锦峰-AI-7年.pdf`

### 多 Agent 分工

| Agent | 职责 | 输入 | 输出 |
|---|---|---|---|
| **Ticket Intake Agent** | 解析工单 | 工单标题、描述、告警、服务名 | normalized_ticket |
| **Triage Agent** | 自动分诊 | 工单、历史规则、服务拓扑 | service、severity、incident_type |
| **Evidence Planner** | 判断要查哪些证据 | service、故障类型 | evidence_plan |
| **Evidence Collector Agents** | 并发采集证据 | MySQL、K8s、ALB、OSS、日志、监控 | evidence_items |
| **Diagnosis Agent** | 根因分析 | 证据链、历史 RCA、SOP | root_cause_hypotheses |
| **Critic / Risk Agent** | 反驳与风险评估 | 诊断结论、证据链 | confidence、risk_level、missing_evidence |
| **Remediation Planner** | 生成处置方案 | 根因、风险、SOP | remediation_plan、rollback_plan |
| **Approval Agent** | 人工审批卡点 | 处置方案、影响范围 | approved / rejected |
| **Executor Agent** | 执行动作 | 审批后的 action | execution_result |
| **Verifier Agent** | 验证恢复情况 | 指标、日志、服务状态 | verification_result |
| **RCA Writer Agent** | 复盘沉淀 | 全链路记录 | RCA 报告、改进建议 |

### 协作方式

运维场景更强调 **证据链 + 人工审批 + 安全边界**。

```text
Ticket / Alert
   ↓
Ticket Intake Agent
   ↓
Triage Agent
   ↓
Evidence Planner
   ↓
┌────────────┬────────────┬────────────┬────────────┐
│ MySQL Agent │ K8s Agent  │ ALB Agent  │ OSS Agent  │
└─────┬──────┴──────┬─────┴──────┬─────┴──────┬─────┘
      ↓             ↓            ↓            ↓
             Evidence Store
                   ↓
            Diagnosis Agent
                   ↓
              Critic Agent
                   ↓
          Remediation Planner
                   ↓
             Human Approval
                   ↓
          Executor / Mock Executor
                   ↓
              Verifier Agent
                   ↓
               RCA Agent
```

你的运维智能体里已经强调了 MySQL、K8s、ALB / SLB、OSS 等多源只读数据接入，支撑服务状态、资源信息、异常记录、告警上下文和历史工单分析。`欧阳锦峰-AI-7年.pdf`

面试中可以这样说：

> 运维智能体的多 Agent 协作不是为了炫技，而是为了控制风险。Triage Agent 负责判断工单归属和严重程度，Evidence Agent 并发采集 MySQL、K8s、ALB、OSS 等多源证据，Diagnosis Agent 只基于证据链给出根因假设，Risk Agent 会反向检查证据是否充分，Remediation Agent 生成处置和回滚方案，真正执行前必须经过人工审批，执行后再由 Verifier Agent 验证恢复情况，最后由 RCA Agent 结构化沉淀复盘。

---

# 2. 数据库、Redis、消息队列怎么设计

## 一句话总原则

> **数据库存长期事实和审计数据，Redis 存短期运行态和锁，消息队列负责异步任务解耦和失败重试。**

不要把所有东西都塞 Redis，也不要让消息队列承载业务状态。

---

# 2.1 数据库设计

## 通用数据库表

两个智能体都应该有一套通用运行表。

| 表 | 存什么 | 作用 |
|---|---|---|
| `agent_runs` | 一次完整任务运行 | 记录 run_id、用户、状态、入口参数 |
| `agent_steps` | 每个 Agent 节点执行记录 | 记录 Router / Planner / Codegen / QA 等节点状态 |
| `agent_events` | 事件流 | 用于前端展示过程、审计、回放 |
| `agent_checkpoints` | checkpoint 快照 | 失败恢复、断点续跑 |
| `agent_artifacts` | 中间产物引用 | 代码、SQL、报告、截图、日志、RCA |
| `agent_tool_calls` | 工具调用记录 | 调了什么工具、参数、结果、耗时 |
| `agent_approvals` | 人工审批 | 审批人、审批结果、审批意见 |
| `agent_errors` | 错误记录 | 错误类型、堆栈、失败节点、重试次数 |
| `prompt_versions` | Prompt 版本 | 支持回放和问题追踪 |
| `bad_cases` | bad case 沉淀 | 用于后续优化 Router / Planner / Prompt |

---

## 应用开发智能体数据库存什么

应用开发智能体要存 **应用元数据、版本、页面、路由、Schema、代码产物、部署产物**。

### 核心表设计

| 表 | 存什么 |
|---|---|
| `tenants` | 租户信息 |
| `tenant_members` | 租户成员、角色、权限 |
| `apps` | 应用基本信息：app_id、tenant_id、name、owner |
| `app_versions` | 每次生成 / 修改后的版本 |
| `pages` | 页面元数据：page_id、path、name、layout |
| `routes` | 路由表：path、component、auth_required |
| `page_schemas` | 页面 Schema、字段、组件配置 |
| `db_schemas` | 数据库 Schema：表、字段、类型、索引 |
| `migrations` | SQL 建表 / 改表脚本 |
| `code_files` | 生成的文件树、文件内容 hash、OSS 路径 |
| `deployments` | 部署记录、静态资源地址、部署状态 |
| `preview_sessions` | Sandpack 预览状态、错误日志 |
| `app_feedbacks` | 用户反馈、bad case、修复记录 |

你原项目里已经有“自然语言需求 → 页面代码 → Schema 结构 → SQL 生成 → 建表 / 迁移 → 页面渲染”的链路，而且把大模型输出拆成前端代码、字段 Schema、SQL 建表语句和数据绑定逻辑等中间产物，目的就是降低一次性生成完整应用的不可控风险。`欧阳锦峰-AI-7年.pdf`

### 关键点

应用开发智能体里有两类数据库：

| 类型 | 说明 |
|---|---|
| **平台数据库** | 存 app、version、page、schema、run、checkpoint、artifact |
| **生成应用业务数据库** | 存生成出来的业务表，比如客户表、订单表、工单表 |

如果用 Supabase / PostgreSQL，可以这样拆：

```text
平台侧 PostgreSQL
- apps
- app_versions
- pages
- schemas
- migrations
- agent_runs
- checkpoints
- artifacts

生成应用侧 Supabase PostgreSQL
- generated_customer_xxx
- generated_order_xxx
- generated_ticket_xxx
- 所有业务表带 tenant_id
- RLS 基于 tenant_id 做隔离
```

你的项目中已经规划过 Supabase、多租户和企业 SSO 鉴权，通过租户标识传递、数据隔离和统一身份校验，让生成应用支持多团队、多租户安全访问。`欧阳锦峰-AI-7年.pdf`

---

## 运维智能体数据库存什么

运维智能体要存 **工单、证据、诊断、审批、执行、验证、RCA、审计**。

### 核心表设计

| 表 | 存什么 |
|---|---|
| `tickets` | 工单原始信息 |
| `incidents` | 事件 / 故障实例 |
| `services` | 服务元数据、负责人、等级 |
| `service_dependencies` | 服务依赖关系 |
| `alerts` | 告警信息 |
| `evidence_plans` | 证据采集计划 |
| `evidence_items` | 采集到的证据 |
| `diagnosis_results` | 根因假设、置信度、依据 |
| `remediation_plans` | 修复方案、风险、回滚方案 |
| `approvals` | 人工审批记录 |
| `execution_records` | 执行动作、结果、日志 |
| `verification_results` | 验证结果 |
| `rca_reports` | RCA 报告 |
| `audit_logs` | 审计日志 |
| `runbooks` | SOP / 处置手册 |
| `historical_rcas` | 历史复盘案例 |

### `evidence_items` 示例

```json
{
  "id": "ev_001",
  "run_id": "run_123",
  "ticket_id": "ticket_456",
  "source_type": "k8s",
  "source_name": "prod-cluster",
  "service": "order-service",
  "query": "kubectl get pods -n prod -l app=order-service",
  "result_summary": "3 个 pod 中 2 个 CrashLoopBackOff",
  "raw_result_ref": "oss://agent-runs/run_123/evidence/k8s_pods.json",
  "confidence": 0.92,
  "collected_at": "2026-06-01T10:20:00+08:00"
}
```

运维场景里，证据原文可能很大，不建议全部塞数据库。数据库存摘要、结构化字段和对象存储引用，原始日志、截图、大 JSON 放 OSS / S3。

---

# 2.2 Redis 设计

Redis 不做最终事实源，只做运行态加速。

## Redis 存什么

| 类型 | Key 示例 | 作用 |
|---|---|---|
| 任务运行状态 | `agent:run:{run_id}:status` | 前端快速查询 |
| SSE 事件缓冲 | `agent:run:{run_id}:events` | 流式展示过程 |
| 分布式锁 | `lock:run:{run_id}` | 防止同一个 run 被重复执行 |
| 幂等锁 | `idempotency:{step_id}` | 防止重复执行副作用节点 |
| 队列消费游标 | `stream:agent-events` | 事件推送 |
| LLM 临时上下文 | `ctx:{run_id}` | 避免频繁查 DB |
| 工具结果缓存 | `tool_cache:{hash}` | 避免重复查相同证据 |
| 限流计数 | `rate:user:{user_id}` | 控制模型调用频率 |
| 心跳 | `heartbeat:{worker_id}` | 判断 worker 是否存活 |

---

## 应用开发智能体 Redis 示例

```text
agent:run:run_001:status = "CODEGEN_RUNNING"
agent:run:run_001:current_step = "codegen_home_page"
agent:run:run_001:stream_events = [...]
lock:app:app_123 = "run_001"
sandpack:preview:run_001 = latest preview error
```

作用：

- 前端实时显示“正在生成页面 / 正在建表 / 正在预览”
- 防止同一个应用被两个生成任务同时修改
- 缓存 RAG 检索结果和当前项目快照

---

## 运维智能体 Redis 示例

```text
agent:run:run_789:status = "WAITING_APPROVAL"
lock:incident:inc_001 = "run_789"
tool_cache:k8s:order-service:pods = {...}
approval:run_789:ttl = 1800
heartbeat:worker:evidence-collector-01 = alive
```

作用：

- 工单处置过程中快速展示进度
- 防止同一个故障被多个执行器重复修复
- 缓存短期证据，比如 30 秒内重复查询 K8s Pod 状态不必重复打到集群

---

# 2.3 消息队列设计

消息队列负责 **异步解耦、削峰、重试、并发执行**。

你可以用：

| 方案 | 适合场景 |
|---|---|
| Redis Queue / BullMQ | 轻量 MVP，Node 生态友好 |
| Kafka | 大规模事件流、审计、回放、吞吐高 |
| RabbitMQ | 传统任务分发、可靠投递 |
| Redis Stream | 中等规模事件流 + 消费组 |

如果是你当前项目，面试里建议说：

> MVP 阶段我会优先用 Redis Stream / BullMQ，复杂度低，和 Node Agent Runtime 结合方便；如果后续进入生产级大规模场景，再把事件流和任务队列迁移到 Kafka。

---

## 应用开发智能体队列

| Queue | 消费者 | 任务 |
|---|---|---|
| `router.queue` | Router Worker | 意图识别 |
| `planner.queue` | Planner Worker | 生成 UI / DB / Routing plan |
| `codegen.queue` | Codegen Worker | 生成代码 |
| `migration.queue` | Migration Worker | 执行 SQL |
| `qa.queue` | QA Worker | lint / tsc / preview |
| `deploy.queue` | Deploy Worker | 打包部署 |

消息体不要太大，只放引用：

```json
{
  "job_id": "job_001",
  "run_id": "run_123",
  "step_id": "step_codegen_home",
  "app_id": "app_456",
  "version_id": "ver_007",
  "payload_ref": "db://agent_steps/step_codegen_home/input"
}
```

---

## 运维智能体队列

| Queue | 消费者 | 任务 |
|---|---|---|
| `triage.queue` | Triage Worker | 工单分诊 |
| `evidence.queue` | Evidence Workers | 并发采集证据 |
| `diagnosis.queue` | Diagnosis Worker | 根因分析 |
| `approval.queue` | Approval Worker | 等待人工确认 |
| `execution.queue` | Executor Worker | 模拟 / 受控执行 |
| `verification.queue` | Verifier Worker | 验证恢复 |
| `rca.queue` | RCA Worker | 生成 RCA |

运维智能体尤其适合消息队列，因为证据采集可以并发：

```text
Evidence Planner
   ↓
发送 4 个 evidence jobs：
- 查 K8s Pod
- 查 MySQL 慢 SQL
- 查 ALB 5xx
- 查 OSS 访问错误
   ↓
所有 evidence jobs 完成
   ↓
Diagnosis Agent 开始分析
```

---

# 3. Checkpoint 怎么设计

## 一句话解释

> **Checkpoint 是每个关键节点执行后的持久化快照，用来支持失败恢复、断点续跑、人工审批暂停、过程回放和审计。**

你运维项目中已经明确提到：引入检查点持久化、事件流追踪、执行记录和审批节点，用来提升流程可恢复性、可追踪性和可审计性。`欧阳锦峰-AI-7年.pdf`

---

# 3.1 Checkpoint 存什么

核心表：

```sql
agent_checkpoints (
  id,
  run_id,
  step_id,
  checkpoint_no,
  node_key,
  status,
  state_json,
  artifact_refs,
  input_hash,
  output_hash,
  idempotency_key,
  retry_count,
  created_at
)
```

### 字段解释

| 字段 | 说明 |
|---|---|
| `run_id` | 一次完整任务 |
| `step_id` | 当前执行节点 |
| `checkpoint_no` | 第几个 checkpoint |
| `node_key` | 当前节点，比如 `UI_PLANNER`、`K8S_EVIDENCE` |
| `status` | `PENDING / RUNNING / SUCCESS / FAILED / WAITING_APPROVAL` |
| `state_json` | 当前状态快照 |
| `artifact_refs` | 代码、SQL、日志、证据、截图等产物引用 |
| `input_hash` | 输入摘要，用于幂等判断 |
| `output_hash` | 输出摘要，用于变更追踪 |
| `idempotency_key` | 防重复执行 |
| `retry_count` | 重试次数 |

---

# 3.2 应用开发智能体的 checkpoint

应用开发智能体的 checkpoint 应该围绕 **代码、Schema、SQL、版本** 设计。

## 关键 checkpoint 节点

| 节点 | checkpoint 内容 |
|---|---|
| `REQUEST_RECEIVED` | 用户原始需求、app_id、tenant_id |
| `ROUTER_DONE` | intent、任务类型、置信度 |
| `CONTEXT_READY` | 检索到的页面、Schema、路由、历史版本 |
| `UI_PLAN_DONE` | 页面变更计划 |
| `DB_PLAN_DONE` | 表结构变更计划 |
| `ROUTING_PLAN_DONE` | 路由变更计划 |
| `CODEGEN_DONE` | 生成的文件 patch、文件 hash |
| `SQL_GENERATED` | SQL 脚本、migration_id |
| `MIGRATION_APPLIED` | SQL 执行结果 |
| `PREVIEW_READY` | Sandpack 预览结果 |
| `QA_PASSED` | lint / tsc / runtime 结果 |
| `VERSION_SAVED` | app_version_id |
| `DEPLOYED` | 部署地址 |

## 示例

```json
{
  "run_id": "run_app_001",
  "node_key": "CODEGEN_DONE",
  "status": "SUCCESS",
  "state_json": {
    "app_id": "app_123",
    "version_id": "ver_008",
    "target_files": [
      "src/pages/CustomerList.tsx",
      "src/routes.tsx"
    ],
    "changed_pages": ["customer-list"],
    "changed_schema": ["customers"]
  },
  "artifact_refs": {
    "patch": "oss://agent-runs/run_app_001/patch.diff",
    "files_snapshot": "oss://apps/app_123/ver_008/files.json"
  },
  "input_hash": "hash_user_request_context",
  "output_hash": "hash_generated_patch"
}
```

## 恢复逻辑

假设 SQL 已经建表成功，但预览失败：

```text
SQL_GENERATED ✅
MIGRATION_APPLIED ✅
PREVIEW_READY ❌
```

系统恢复时不应该重新建表，而是：

```text
读取最近成功 checkpoint
   ↓
发现 migration 已 applied
   ↓
从 PREVIEW_READY 重新开始
   ↓
把 Sandpack 错误交给 QA / Patch Agent 修复
```

面试说法：

> 应用生成场景里，checkpoint 的核心价值是避免全链路重跑。比如 SQL 已经执行成功，后面预览失败，我不能重新执行建表脚本，否则会造成重复建表或字段冲突。所以每个有副作用的节点，比如 migration、文件写入、部署，都要有 checkpoint 和幂等 key。

---

# 3.3 运维智能体的 checkpoint

运维智能体的 checkpoint 更关键，因为它涉及生产安全。

## 关键 checkpoint 节点

| 节点 | checkpoint 内容 |
|---|---|
| `TICKET_RECEIVED` | 工单原文、告警、服务名 |
| `TRIAGE_DONE` | 服务、等级、故障类型 |
| `EVIDENCE_PLAN_DONE` | 要采集哪些证据 |
| `EVIDENCE_COLLECTED` | 证据列表、证据来源 |
| `DIAGNOSIS_DONE` | 根因假设、置信度 |
| `RISK_REVIEW_DONE` | 风险等级、缺失证据 |
| `REMEDIATION_PLAN_DONE` | 修复方案、回滚方案 |
| `WAITING_APPROVAL` | 等待谁审批、审批内容 |
| `APPROVED` | 审批人、审批结果 |
| `MOCK_EXECUTED` | 模拟执行结果 |
| `EXECUTED` | 实际执行结果 |
| `VERIFIED` | 指标是否恢复 |
| `RCA_GENERATED` | RCA 报告 |

## 示例

```json
{
  "run_id": "run_ops_001",
  "node_key": "WAITING_APPROVAL",
  "status": "WAITING_APPROVAL",
  "state_json": {
    "ticket_id": "ticket_9527",
    "service": "order-service",
    "severity": "P1",
    "root_cause": "order-service pod CrashLoopBackOff caused by config error",
    "confidence": 0.87,
    "risk_level": "HIGH",
    "remediation_action": "rollback deployment to previous stable version",
    "rollback_plan": "restore deployment image tag v1.2.7"
  },
  "artifact_refs": {
    "evidence": "oss://agent-runs/run_ops_001/evidence.json",
    "remediation_plan": "oss://agent-runs/run_ops_001/remediation.md"
  },
  "idempotency_key": "ticket_9527:rollback:v1.2.7"
}
```

## 运维 checkpoint 的特殊点

运维场景需要 **强制在高风险节点前打 checkpoint**：

```text
诊断完成
   ↓
生成修复方案
   ↓
checkpoint: WAITING_APPROVAL
   ↓
人工审批
   ↓
checkpoint: APPROVED
   ↓
模拟执行
   ↓
checkpoint: MOCK_EXECUTED
   ↓
真实执行
   ↓
checkpoint: EXECUTED
   ↓
验证
```

原因是：

- 人工审批可能隔很久才发生；
- Worker 可能中途重启；
- 执行动作不能重复触发；
- 出问题后要能审计是谁批准、执行了什么、结果如何。

你的运维项目也强调了高风险操作安全边界：Agent 输出根因、影响范围、置信度、风险等级、处置步骤和回滚建议，并通过“建议生成 + 人工确认 + 模拟执行 + 结果验证”的控制链路平衡效率与生产安全。`欧阳锦峰-AI-7年.pdf`

---

# 4. 面试时可以直接这么答

## 标准版回答

> 我这两个项目底层都是 Agent Workflow，不是简单 Chatbot。  
>   
> 应用开发智能体里，多 Agent 主要围绕生成链路协作：Router 识别需求类型，Context Agent 检索项目上下文，UI Planner 规划页面变更，Supabase / DBA Planner 规划 Schema 和 SQL，Routing Planner 处理路由，Codegen Agent 生成代码，QA Agent 负责验证，Deploy Agent 负责发布。Orchestrator 根据任务依赖图调度，每个 Agent 的输出都是结构化 JSON，并作为下一步输入。  
>   
> 运维智能体里，多 Agent 主要围绕诊断和处置协作：Triage Agent 做工单分诊，Evidence Agents 并发采集 MySQL、K8s、ALB、OSS 等证据，Diagnosis Agent 生成根因假设，Risk Agent 做风险审查，Remediation Agent 给出修复和回滚方案，Approval Agent 处理人工审批，Executor Agent 执行，Verifier Agent 验证恢复，最后 RCA Agent 输出复盘。  
>   
> 存储上，数据库是事实源，存 run、step、event、checkpoint、artifact、approval、tool_call、RCA 等结构化数据；Redis 存短期运行态、分布式锁、SSE 事件缓冲、工具结果缓存和限流；消息队列负责异步节点调度、并发证据采集、失败重试和削峰。  
>   
> Checkpoint 设计上，我会在每个关键节点完成后落一个快照，包含当前节点、状态、输入输出 hash、中间产物引用、重试次数和幂等 key。应用生成里重点防止 SQL、文件写入、部署这类副作用重复执行；运维智能体里重点在审批、执行、验证前后打 checkpoint，确保流程可恢复、可审计、可回放。

---

# 5. 你要特别强调的高级点

面试官如果继续追问，你重点讲这 5 句：

1. **Agent 不直接共享内存，而是通过数据库里的结构化中间产物协作。**
2. **Orchestrator 只负责任务流转，不负责具体智能判断。**
3. **Router / Planner / Codegen / QA 的输入输出都用 JSON Schema 约束。**
4. **Redis 只做运行态和锁，不做最终事实源。**
5. **Checkpoint 不只是保存日志，而是保存可恢复的状态快照，尤其要覆盖副作用节点和人工审批节点。**

## Prompt:
2026/6/1 16:46:37

DAG 不要写这种英文，换成中文

## Response:
2026/6/1 16:46:38

可以，后面统一不要写 **DAG**，改成下面这些中文说法：

| 原说法 | 替换成 |
|---|---|
| DAG | **任务依赖图** |
| DAG 调度 | **按任务依赖关系调度** |
| DAG + 状态机 | **任务依赖图 + 状态机** |
| 按 DAG 编排 | **按流程依赖关系编排** |
| 节点之间组成 DAG | **节点之间形成有前后依赖的任务流** |

最适合你面试表达的是：

> **任务依赖图 + 状态机**

因为它既不生硬，又能表达清楚两个关键点：

1. **任务依赖图**：说明哪些节点先执行、哪些节点后执行、哪些节点可以并行。
2. **状态机**：说明每个节点有明确状态，比如等待中、执行中、成功、失败、等待审批、已恢复。

---

## 修改后的标准表达

原来这句：

> Orchestrator 按任务依赖图调度这些节点。

改成：

> **Orchestrator 会根据任务依赖图调度这些节点。每个节点完成后都会更新状态，并把结构化产物传给下一个节点。**

或者更口语化一点：

> **我不是让所有 Agent 随机互相调用，而是先把任务拆成一张任务依赖图：哪些节点必须先做，哪些节点可以并行，哪些节点依赖前一步结果。Orchestrator 根据这张任务依赖图和当前状态，决定下一步该调哪个 Agent。**

---

## 应用开发智能体里怎么说

> 在应用开发智能体里，我会把一次生成任务拆成一张任务依赖图。比如先经过 Router 判断需求类型，再由 Context Agent 拉取项目上下文，然后 UI Planner、Supabase Planner、Routing Planner 分别规划页面、数据结构和路由变化。规划完成后，Codegen Agent 生成代码，SQL Agent 生成迁移脚本，最后由 QA Agent 做校验，Deploy Agent 负责部署。  
>   
> 这里不是所有节点串行执行，有些节点可以并行。比如 UI 规划、数据结构规划、路由规划在拿到上下文后可以并行跑。但 Codegen 一定要等规划结果出来，QA 一定要等代码和 SQL 都完成后再执行。

---

## 运维智能体里怎么说

> 在运维智能体里，我也会先把工单处理流程拆成任务依赖图。工单进来后，先由 Triage Agent 做分诊，然后 Evidence Planner 判断要查哪些证据。MySQL、K8s、ALB、OSS 这些证据采集节点可以并行执行。证据收集完成后，Diagnosis Agent 才能做根因分析，Risk Agent 再做风险审查，Remediation Agent 生成处置方案。到了高风险执行节点之前，必须进入人工审批状态，审批通过后才能执行和验证。  
>   
> 所以运维智能体的核心不是让模型直接执行命令，而是通过任务依赖图和状态机，把诊断、审批、执行、验证这些环节严格串起来。

---

## 最终统一口径

你后续可以统一这样讲：

> **我的 Agent 编排不是简单链式调用，而是“任务依赖图 + 状态机”。任务依赖图负责描述节点之间的前后依赖和并行关系，状态机负责记录每个节点当前处于等待、执行、成功、失败、等待审批还是已完成。Orchestrator 根据当前状态和依赖关系，决定下一步调哪个 Agent，并把每一步的输入、输出、事件和 checkpoint 都结构化落库。**

这句话比说专业英文缩写更适合面试，也更容易让非后端面试官听懂。

## Prompt:
2026/6/1 16:47:30

这份内容中不要写DAG这种专有英文名词

[Attachment: 粘贴的 markdown (1)。md]

## Response:
2026/6/1 16:47:33

> **检查用户要求修改内容**
>
> 用户可能要求修改“这份内容”，可能是之前的文本，而不是文件。文件似乎是之前的内容，可能要检查一下。如果需要修改，可以直接提供修订版。要确定用户是否希望我们重写全文，或者只是更新其中的术语。
>
> **读取并修改上传的Markdown文件内容**
>
>
> **修改文件内容并替换术语**
>
> 用户要求删除内容中的“DAG”并进行替换。鉴于上传的文件较长（634行），我可以替换“DAG”为“任务依赖图”，并且调整与“状态机”相关的术语。需要确保不改变文档结构并产生一个更新的、清洁的文件。
>
> **替换DAG术语并更新文件**
>
>
> **更新文件并替换DAG术语**
>
> 我需要创建一个更新的文件，其中替换掉所有的“DAG”。如果用户提到其他专有名词如“Agent”和“Router”，可以在不主动询问的情况下提供中文替代版本。我会编写文件并更新相关段落。
>
> **更新文件并替换DAG术语**
>
>
> 已思考 27s

已处理。后续这份内容里不再写 **DAG**，统一改成中文表达：

- **任务依赖图**
- **任务依赖关系**
- **按任务依赖关系调度**
- **任务依赖图 + 状态机**

我也生成了一份去掉该词的 Markdown 文件：  
[下载修改后的版本](sandbox:/mnt/data/应用开发智能体与运维智能体_去DAG版.md)

其中核心表述已改成：

> Orchestrator 会根据任务依赖关系调度这些节点，每个节点的输入输出都用 JSON Schema 约束，并且都会落库，方便失败恢复和审计。

## Prompt:
2026/6/1 17:20:20

增加一个问题：这两个项目的表的设计有哪些设计思维？为什么要这么设计？索引有设计吗？为什么这么设计索引？

## Response:
2026/6/1 17:20:24

> **考虑修改并更新文档**
>
> 用户要求“增加一个问题”，这可能意味着在现有内容中添加新部分。要添加的问题涉及设计思维和索引设计。我需要检查文件 `/mnt/data/应用开发智能体与运维智能体_去DAG版.md`，并考虑如何修改文档。更新后，可以提供包含新内容的文件。
>
> **更新Markdown文件并添加新问题**
>
>
> **修改并更新Markdown文件**
>
>
> **添加问题并更新Markdown文件**
>
>
> **修改和补充文档内容**
>
> 用户需要在文档中添加新的部分，我应该确保没有涉及“DAG”，可能用“工作流”替代。我打算插入关于表设计、设计思维、索引设计的内容，也许会需要包括Postgres的各种索引类型。我会插入一个新的Section #4，并更新其它部分的编号。
>
> **撰写文件内容**
>
> 我需要创建一个新的章节，避免使用“DAG”这个术语，改用“任务依赖图”更为合适。我会尽量避免过多英文术语，像“B 树索引”代替“B-tree”，“JSON 字段倒排索引”代替GIN。“Agent”可以保留。稍后会检查文件是否有“DAG”的存在。
>
> **插入表设计与索引思维**
>
>
> 已思考 2m 15s

我会把这个补成一个新的面试问题章节，重点不只列字段，而是讲清楚：表为什么这么拆、哪些是事实表/过程表/产物表、索引为什么围绕查询路径设计。

我会把这个作为新的“第 4 个问题”插入原文，并把原来的“面试标准回答”和“高级点”顺延。新增部分会避免只写表名，改成“表设计思维 + 索引设计思维 + 可直接回答的话术”。

已新增一个完整问题章节：

## 4. 表设计有哪些设计思维？为什么这么设计？索引怎么设计？

我补充了四块内容：

1. **通用运行表设计思维**
   - `agent_runs`
   - `agent_steps`
   - `agent_events`
   - `agent_checkpoints`
   - `agent_tool_calls`
   - `agent_artifacts`
   - `agent_approvals`
   - `agent_errors`

2. **应用开发智能体表设计**
   - 为什么按：应用、版本、页面、路由、Schema、代码、迁移、部署拆表
   - 为什么要有 `tenant_id`、`app_id`、`version_id`
   - 为什么代码文件和大产物不直接塞主表

3. **运维智能体表设计**
   - 为什么工单和故障要分开
   - 为什么证据、诊断、处置、审批、执行、验证、RCA 要分表
   - 为什么证据表和执行记录要追加写，不覆盖

4. **索引设计**
   - 应用开发智能体索引：`tenant_id + app_id + version_id + file_path + run_id`
   - 运维智能体索引：`service_id + 时间`、`incident_id + 时间`、`status + severity`、`approver_id + status`
   - 解释了联合索引、唯一索引、部分索引、JSON 字段查询、大文件存储引用等设计原因

更新后的文件在这里：  
[下载新增表设计与索引章节后的版本](sandbox:/mnt/data/应用开发智能体与运维智能体_去DAG版_增加表设计索引.md)

核心面试表达我也补进去了：

> 表设计不是按 Agent 名字简单建表，而是按业务对象和执行过程来拆。应用开发智能体围绕应用、版本、页面、路由、Schema、代码文件、迁移脚本和部署记录设计；运维智能体围绕工单、故障、服务、证据、诊断、处置、审批、执行、验证和 RCA 设计。索引不是看到字段就加，而是围绕高频查询路径设计。应用生成场景重点是 tenant_id、app_id、version_id、file_path、run_id；运维场景重点是 service_id、incident_id、status、severity、created_at、approver_id。



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)