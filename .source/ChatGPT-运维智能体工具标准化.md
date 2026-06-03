# 运维智能体工具标准化

**User:** Anonymous  
**Created:** 5/13/2026 15:12:39  
**Updated:** 5/18/2026 16:25:10  
**Exported:** 6/3/2026 1:59:04  
**Link:** [https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813/c/6a042445-8470-83ec-aaf2-39f8ec74daef](https://chatgpt.com/g/g-p-69ca3774037c81918046dac60a5ac813/c/6a042445-8470-83ec-aaf2-39f8ec74daef)  

## Prompt:
2026/5/13 15:12:37

运维智能体中，如何将接入MySQL、K8s、ALB、OSS变成标准化工具

## Response:
2026/5/13 15:12:38

> **Discussing architecture and tool standardization**
>
> User's asking about an architecture with stable knowledge. I think they’re looking for a standard approach to integrating tools like “K8s ALB OSS.” I don't need to browse the latest API names, but I'll mention vendor SDKs. The focus should be on standardization, not raw client integrations. I'll reference schemas and tool contracts, with details like input/output schemas, safety, and permissions, and a separation of tools for evidence and mutation handling.
>
> Thought for 28s

我会按“面试可讲 + 架构可落地”的方式拆：先定义标准工具模型，再分别套到 MySQL、K8s、ALB、OSS，最后给你一段可以直接背的表达。

这里的核心不是“把 SDK 接进来”，而是把每个基础设施能力包装成同一种工具协议：统一入参、统一权限、统一返回、统一审计、统一风险等级。这样 Agent 才能稳定规划和调用。

可以这样理解：**MySQL、K8s、ALB、OSS 不应该直接作为“系统接口”暴露给大模型，而应该先抽象成一批标准化 Tool，再由 Agent 按工具说明调用。**

你现在简历里已经把运维智能体定义为“多源证据采集 → 根因假设 → 处置建议 → 审批 → 执行验证 → RCA”的闭环，并且提到 MySQL、K8s、ALB/SLB、OSS 作为多源只读数据接入和证据采集来源。这个方向是对的，下一步就是把它讲成**工具标准化体系**。`欧阳锦峰-AI-7年.pdf`

---

## 1. 核心思路：不是接入 4 个系统，而是沉淀一套 Tool Contract

标准工具要统一 7 个东西：

```ts
type OpsTool = {
  name: string              // 工具名，如 k8s.get_pod_status
  domain: string            // mysql / k8s / alb / oss
  description: string       // 给 Agent 理解这个工具什么时候用
  inputSchema: JSONSchema   // 入参结构
  outputSchema: JSONSchema  // 出参结构
  permission: ToolPermission // 只读 / 需审批 / 高危
  riskLevel: "low" | "medium" | "high"
  timeoutMs: number
  retryPolicy: RetryPolicy
  audit: boolean
}
```

也就是说，Agent 看到的不是：

> 我能连 MySQL、K8s、ALB、OSS。

而是：

> 我有一组可调用的、受控的、结构化工具，可以查询数据库状态、Pod 状态、负载均衡健康检查、对象存储访问异常，并把结果统一转成证据。

---

## 2. 整体架构可以这样设计

```text
用户工单 / 告警
   ↓
Triage Agent：判断问题类型
   ↓
Planner：生成排查计划
   ↓
Tool Router：选择工具
   ↓
Tool Runtime：权限校验 / 参数校验 / 超时重试 / 审计记录
   ↓
Tool Adapter：
   - MySQL Adapter
   - K8s Adapter
   - ALB Adapter
   - OSS Adapter
   ↓
Evidence Normalizer：统一转成证据格式
   ↓
Diagnosis Agent：基于证据做根因判断
   ↓
Remediation / RCA
```

其中最关键的是 **Tool Runtime**。它不是简单的函数调用层，而是运维智能体的“安全执行网关”。

它负责：

1. 校验 Agent 是否有权限调用这个工具；
2. 校验入参是否符合 JSON Schema；
3. 控制超时、重试、限流；
4. 屏蔽敏感字段，比如密码、Token、AK/SK；
5. 写入执行记录；
6. 把不同系统返回结果统一成 Evidence。

---

## 3. 标准返回：所有工具都要转成 EvidenceRecord

不要让 MySQL 返回一坨 SQL 结果、K8s 返回一段 kubectl 文本、ALB 返回云厂商原始 JSON。这样模型很难稳定判断。

应该统一成这种结构：

```ts
type EvidenceRecord = {
  toolName: string
  resourceType: "mysql" | "k8s" | "alb" | "oss"
  resourceId: string
  timeRange?: {
    start: string
    end: string
  }
  status: "normal" | "warning" | "critical" | "unknown"
  summary: string
  rawData: unknown
  keyFindings: string[]
  confidence: number
  collectedAt: string
}
```

例如 K8s Pod 异常工具返回：

```json
{
  "toolName": "k8s.get_pod_status",
  "resourceType": "k8s",
  "resourceId": "namespace/order-service",
  "status": "critical",
  "summary": "order-service 存在 3 个 CrashLoopBackOff Pod",
  "keyFindings": [
    "最近 10 分钟重启次数持续增加",
    "错误日志中出现数据库连接超时",
    "Deployment 最近 30 分钟发生过一次发布"
  ],
  "confidence": 0.86,
  "collectedAt": "2026-05-13T14:30:00+08:00"
}
```

这样 Agent 后面做根因分析时，面对的就是标准证据，而不是杂乱的系统输出。

---

## 4. 四类工具如何标准化

### MySQL 工具

MySQL 不要开放任意 SQL 给 Agent 直接执行。要分成**只读诊断工具**和**受控查询模板**。

可以设计这些工具：

| 工具名 | 作用 | 风险 |
|---|---|---|
| `mysql.get_instance_status` | 查询实例状态、连接数、QPS、慢查询概况 | 低 |
| `mysql.get_slow_queries` | 查询指定时间窗口内慢 SQL | 低 |
| `mysql.get_connection_stats` | 查看连接数、活跃连接、锁等待 | 低 |
| `mysql.explain_query` | 对指定 SQL 做执行计划分析 | 中 |
| `mysql.query_readonly` | 只读 SQL 查询，限制表、字段、LIMIT | 中 |

重点控制：

```text
只能 SELECT
禁止 UPDATE / DELETE / INSERT / DROP / ALTER
强制 LIMIT
限制查询时间窗口
限制库表白名单
敏感字段脱敏
慢 SQL / 连接 / 锁等待优先使用模板工具
```

面试可以说：

> MySQL 这块我不会让 Agent 直接拼接任意 SQL，而是通过只读账号、SQL 白名单、查询模板和 LIMIT 约束，把数据库诊断能力包装成标准工具，主要采集连接数、慢查询、锁等待、执行计划等证据。

---

### K8s 工具

K8s 也不要让 Agent 直接执行任意 kubectl 命令，而是封装成 API 工具。

可以设计这些工具：

| 工具名 | 作用 | 风险 |
|---|---|---|
| `k8s.get_pod_status` | 查询 Pod 状态、重启次数、异常原因 | 低 |
| `k8s.get_pod_logs` | 拉取指定 Pod 最近日志 | 中 |
| `k8s.get_events` | 查询 namespace / workload 事件 | 低 |
| `k8s.describe_deployment` | 查询 Deployment 镜像、版本、副本数 | 低 |
| `k8s.get_resource_usage` | 查询 CPU / 内存使用情况 | 低 |
| `k8s.rollout_restart` | 重启工作负载 | 高，必须审批 |

重点控制：

```text
ServiceAccount RBAC 最小权限
namespace 白名单
禁止任意 shell / exec
日志行数限制
日志敏感信息脱敏
写操作必须进入审批节点
```

面试可以说：

> K8s 工具层我会把能力拆成状态查询、事件查询、日志查询、资源使用率查询和受控处置工具。只读工具可以自动调用，重启、扩缩容、回滚这类动作工具必须经过人工审批。

---

### ALB / SLB 工具

ALB 主要用于定位流量入口、后端健康检查、5xx、转发异常、证书和监听器配置问题。

可以设计这些工具：

| 工具名 | 作用 | 风险 |
|---|---|---|
| `alb.get_listener_status` | 查询监听器状态 | 低 |
| `alb.get_backend_health` | 查询后端服务器健康检查 | 低 |
| `alb.get_traffic_metrics` | 查询 QPS、RT、4xx、5xx | 低 |
| `alb.get_access_errors` | 查询异常访问日志 | 中 |
| `alb.compare_config_snapshot` | 对比配置变更前后差异 | 中 |

重点控制：

```text
只读 OpenAPI 权限
按 app / service 映射 ALB 实例
限制时间窗口
日志采样返回
隐藏公网 IP、Header、Cookie 等敏感信息
```

ALB 工具对运维智能体很关键，因为很多故障不是服务挂了，而是：

```text
入口流量异常
后端健康检查失败
路由规则错误
证书过期
转发到错误 upstream
某个可用区后端不健康
```

面试可以说：

> ALB 工具主要承担流量入口侧证据采集，帮助 Agent 判断问题是在入口层、转发层还是后端服务层。比如 5xx 升高时，Agent 会先查 ALB 指标和后端健康检查，再联动 K8s Pod 状态和应用日志。

---

### OSS 工具

OSS 主要用于对象存储、静态资源、上传下载链路、权限和访问异常排查。

可以设计这些工具：

| 工具名 | 作用 | 风险 |
|---|---|---|
| `oss.get_bucket_status` | 查询 Bucket 基础状态 | 低 |
| `oss.get_object_meta` | 查询对象元信息、大小、更新时间 | 低 |
| `oss.check_object_exists` | 判断对象是否存在 | 低 |
| `oss.get_access_errors` | 查询 403、404、5xx 等访问异常 | 中 |
| `oss.check_policy` | 检查 Bucket Policy / ACL 配置 | 中 |

重点控制：

```text
不直接下载大文件
不返回文件敏感内容
只查元信息、访问日志、权限配置
限制 bucket 白名单
临时 URL 生成必须审批或严格过期
```

OSS 在故障场景里常见问题包括：

```text
图片 / 附件 404
上传失败
下载 403
Bucket 权限变更
对象不存在
CDN 回源 OSS 失败
文件大小异常
```

面试可以说：

> OSS 工具不重点读取文件内容，而是采集对象是否存在、元信息、权限配置和访问错误，避免 Agent 接触敏感文件内容，同时能支持上传下载类故障诊断。

---

## 5. 工具要分三类：查询型、诊断型、动作型

这是面试里很加分的分层。

### 查询型工具

只负责拿原始信息。

```text
mysql.get_slow_queries
k8s.get_pod_logs
alb.get_backend_health
oss.get_object_meta
```

### 诊断型工具

在工具内部做一些规则判断，返回更结构化的结论。

```text
k8s.analyze_crash_loop
mysql.analyze_lock_wait
alb.analyze_5xx_spike
oss.analyze_403_errors
```

### 动作型工具

会改变生产状态，必须审批。

```text
k8s.restart_workload
k8s.rollback_deployment
alb.disable_backend
oss.update_bucket_policy
mysql.kill_session
```

你的运维智能体第一阶段最好只做：

```text
查询型工具 + 诊断型工具
```

动作型工具先做模拟执行，不直接操作生产。

---

## 6. 标准工具定义示例

以 `k8s.get_pod_status` 为例：

```json
{
  "name": "k8s.get_pod_status",
  "domain": "k8s",
  "description": "查询指定服务在 K8s 中的 Pod 状态、重启次数、异常原因和最近事件",
  "inputSchema": {
    "type": "object",
    "properties": {
      "cluster": { "type": "string" },
      "namespace": { "type": "string" },
      "workload": { "type": "string" },
      "timeRangeMinutes": { "type": "number", "default": 30 }
    },
    "required": ["cluster", "namespace", "workload"]
  },
  "permission": {
    "mode": "readonly",
    "approvalRequired": false
  },
  "riskLevel": "low",
  "timeoutMs": 5000,
  "outputSchema": {
    "type": "object",
    "properties": {
      "status": { "type": "string" },
      "summary": { "type": "string" },
      "pods": { "type": "array" },
      "keyFindings": { "type": "array" }
    }
  }
}
```

以 `mysql.query_readonly` 为例：

```json
{
  "name": "mysql.query_readonly",
  "domain": "mysql",
  "description": "执行受控只读 SQL 查询，用于排查数据库连接、慢查询、业务数据异常",
  "permission": {
    "mode": "readonly",
    "approvalRequired": false
  },
  "constraints": {
    "allowedStatements": ["SELECT"],
    "forbiddenKeywords": ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER"],
    "maxRows": 100,
    "timeoutMs": 3000
  }
}
```

---

## 7. Agent 调用工具的流程

比如用户说：

> 订单服务接口大量 500，帮我看下原因。

Agent 不应该直接乱查，而是生成一个排查计划：

```text
1. 查 ALB 5xx 指标，判断是否入口层异常
2. 查 ALB 后端健康检查，判断是否某些后端不可用
3. 查 K8s Pod 状态，判断服务是否重启或崩溃
4. 查 K8s 最近事件和日志，确认是否发布、OOM、CrashLoop
5. 查 MySQL 连接数和慢查询，判断是否数据库导致接口超时
6. 汇总证据，形成根因假设
```

实际工具调用可能是：

```text
alb.get_traffic_metrics
alb.get_backend_health
k8s.get_pod_status
k8s.get_events
k8s.get_pod_logs
mysql.get_connection_stats
mysql.get_slow_queries
```

最后输出：

```text
根因假设：
订单服务 500 的主要原因可能不是 ALB 本身，而是后端 order-service Pod 在 14:20 后出现频繁重启，日志中同时出现 MySQL connection timeout。结合 MySQL 连接数达到上限和慢查询增加，判断数据库连接池耗尽是高概率根因。

证据：
1. ALB 5xx 在 14:20 后升高；
2. 后端健康检查显示 order-service 部分实例不健康；
3. K8s 显示 3 个 Pod CrashLoopBackOff；
4. MySQL 连接数接近上限，慢查询数量增加。

建议：
1. 先扩容 order-service 副本；
2. 临时提高连接池上限；
3. 排查最近发布是否引入慢 SQL；
4. 对慢 SQL 建立后续优化任务。
```

---

## 8. 安全边界是这套设计的重点

运维智能体最怕“模型误操作生产环境”，所以工具标准化必须带安全等级。

```text
Level 1：只读查询
- 自动执行
- 如查询日志、状态、指标

Level 2：低风险动作
- 需要二次确认
- 如清理临时缓存、触发健康检查

Level 3：高风险动作
- 必须人工审批
- 如重启服务、回滚发布、修改 ALB 后端、修改 OSS 权限、kill MySQL 连接

Level 4：禁止动作
- 不允许 Agent 执行
- 如删除数据库、删除 Bucket、批量删除对象、执行任意 shell
```

这句话很适合面试：

> 我们不是简单把运维 API 给大模型调用，而是把所有基础设施能力先分级：只读证据采集可以自动化，高风险变更必须走人工审批和模拟执行，最后还要做结果验证和审计留痕。

---

## 9. 你可以这样总结成面试话术

你可以直接这样讲：

> 在运维智能体里，我不会把 MySQL、K8s、ALB、OSS 当成几个零散接口接进去，而是把它们抽象成标准化工具体系。每个工具都有统一的名称、能力描述、入参 Schema、出参 Schema、权限等级、风险等级、超时重试和审计记录。  
>
> 比如 MySQL 主要封装慢查询、连接数、锁等待、执行计划等只读诊断工具；K8s 封装 Pod 状态、事件、日志、资源使用率和受控重启工具；ALB 封装监听器状态、后端健康检查、5xx 指标和访问日志工具；OSS 封装对象元信息、访问异常、权限配置检查工具。  
>
> Agent 不直接操作底层系统，而是通过 Tool Runtime 调用这些标准工具。Tool Runtime 负责权限校验、参数校验、脱敏、限流、超时重试和审计。所有工具返回结果都会被统一转成 EvidenceRecord，供后续诊断 Agent 做根因判断、处置建议和 RCA 沉淀。  
>
> 这样做的价值是：一方面让 Agent 能稳定使用多源运维数据，另一方面避免模型直接接触生产系统，把不可控的大模型调用变成可控、可审计、可回滚的运维流程。

---

一句话压缩版：

> **把 MySQL、K8s、ALB、OSS 接成标准化工具，本质是做一层受控 Tool Runtime：上层给 Agent 暴露统一工具协议，下层适配不同基础设施 API，中间统一做权限、参数、脱敏、审计、风险分级和证据结构化。**

## Prompt:
2026/5/13 16:09:05

排查计划是根据什么生成的

## Response:
2026/5/13 16:09:06

> **Summarizing troubleshooting process**
>
> I need to clarify the process step by step. The approach includes bringing together various deterministic inputs: incident context, service topology, alert rules, runbooks, historical data, and more. It isn’t just LLM imagination but involves a planner using Triage outputs, topology, and a variety of resources. The process starts with ticket normalization and finishes with filtering possible tools.
>
> Thought for 10s

排查计划**不是凭空生成的**，它应该来自 6 类输入。

核心公式是：

```text
排查计划 =
工单/告警信息
+ 服务拓扑
+ 问题类型
+ 历史 SOP / Runbook / RCA
+ 可用工具清单
+ 当前已采集证据
```

你的运维智能体项目本身已经定义了“工单接入 → 自动分诊 → 多源证据采集 → 根因假设 → 处置建议 → 人工审批 → 验证 → RCA”的链路，所以排查计划应该放在**自动分诊之后、工具调用之前**。`欧阳锦峰-AI产品经理.pdf`

---

## 1. 第一来源：工单 / 告警本身

比如用户输入：

> 订单接口 500 增多，用户下单失败。

Agent 先从工单里抽取结构化信息：

```json
{
  "service": "order-service",
  "symptom": "HTTP 500 increase",
  "impact": "下单失败",
  "timeRange": "最近30分钟",
  "environment": "prod",
  "severity": "P1",
  "relatedResource": ["order-api", "order-service"]
}
```

这一步解决的是：

> 到底要排查哪个服务？什么时间段？什么现象？影响范围多大？

没有这些信息，后面排查计划就会乱。

---

## 2. 第二来源：问题类型分类

Planner 会先判断这是什么类型的问题。

常见分类：

```text
接口 5xx 问题
接口超时问题
服务不可用问题
数据库慢查询问题
Pod 重启问题
流量入口异常
对象存储上传/下载失败
权限/鉴权异常
发布变更引发问题
```

不同问题类型，对应不同排查模板。

比如：

### 5xx 问题

优先查：

```text
ALB 5xx 指标
后端健康检查
K8s Pod 状态
应用日志
数据库连接 / 慢查询
最近发布记录
```

### 接口超时问题

优先查：

```text
接口 RT
K8s CPU / 内存
线程池 / 连接池
MySQL 慢查询
下游服务调用耗时
```

### OSS 访问 403 / 404

优先查：

```text
对象是否存在
Bucket 权限
访问日志
临时签名 URL 是否过期
CDN / ALB 回源是否异常
```

所以排查计划的第一层逻辑来自：**问题类型 → 排查模板**。

---

## 3. 第三来源：服务拓扑

服务拓扑决定“从哪里开始查、查哪些依赖”。

比如 `order-service` 的拓扑是：

```text
用户
 ↓
ALB
 ↓
order-service on K8s
 ↓
MySQL order_db
 ↓
OSS order-attachments
```

那么排查计划就会按链路展开：

```text
1. 查入口层：ALB 是否有 5xx、后端是否健康
2. 查运行层：K8s Pod 是否异常、是否重启、是否 OOM
3. 查应用层：应用日志是否出现异常堆栈
4. 查依赖层：MySQL 是否慢查询、连接数是否打满
5. 查存储层：OSS 是否有 403 / 404 / 5xx
6. 查变更层：最近是否有发布、配置变更、扩缩容
```

这就是为什么我前面说“服务拓扑”很重要。

没有服务拓扑，Agent 只知道“订单服务异常”，但不知道它背后依赖了哪些基础设施。

---

## 4. 第四来源：历史 SOP / Runbook / RCA

这部分是最像“专家经验”的来源。

比如历史 RCA 里沉淀过：

```text
订单服务 500 常见原因：
1. MySQL 连接池耗尽
2. 发布后字段不兼容
3. ALB 健康检查路径配置错误
4. Pod OOM 后反复重启
5. 下游库存服务超时
```

那么 Planner 会优先生成这类排查步骤：

```text
1. 查 MySQL 连接数和慢查询
2. 查最近发布记录
3. 查 ALB 健康检查配置
4. 查 Pod 重启次数和 OOM 事件
5. 查库存服务调用耗时
```

这一步可以通过 RAG 实现。

也就是说，Planner 生成计划前，会先检索：

```text
相似历史工单
相似告警案例
服务 Runbook
排障 SOP
历史 RCA
平台规则
```

然后把检索结果作为参考证据，注入给 Planner。

---

## 5. 第五来源：可用工具清单

排查计划不能只写“检查数据库”。它必须知道系统里有哪些工具可以用。

比如工具注册表里有：

```text
mysql.get_connection_stats
mysql.get_slow_queries
k8s.get_pod_status
k8s.get_events
k8s.get_pod_logs
alb.get_backend_health
alb.get_traffic_metrics
oss.get_object_meta
oss.get_access_errors
```

那么 Planner 才能生成可执行计划：

```json
[
  {
    "step": 1,
    "goal": "判断入口层是否异常",
    "tool": "alb.get_traffic_metrics",
    "params": {
      "service": "order-service",
      "timeRange": "30m"
    }
  },
  {
    "step": 2,
    "goal": "判断后端实例是否健康",
    "tool": "alb.get_backend_health",
    "params": {
      "service": "order-service"
    }
  },
  {
    "step": 3,
    "goal": "判断服务运行状态是否异常",
    "tool": "k8s.get_pod_status",
    "params": {
      "namespace": "prod",
      "workload": "order-service"
    }
  }
]
```

所以排查计划不是自由文本，而应该是**工具可执行的 Plan JSON**。

---

## 6. 第六来源：已采集证据

排查计划不是一次性生成完就不变。

它应该是动态的。

例如第一轮查到：

```text
ALB 5xx 升高
K8s Pod 正常
MySQL 慢查询明显增加
```

那么 Agent 下一轮就不应该继续乱查 K8s，而是收敛到 MySQL：

```text
1. 查询慢 SQL TopN
2. 查询锁等待
3. 查询连接池状态
4. 查询最近是否有 SQL 变更
5. 判断是否需要降级、扩容或回滚
```

所以真实流程应该是：

```text
初始排查计划
 ↓
工具采集证据
 ↓
更新根因假设
 ↓
调整下一步排查计划
 ↓
继续采集
 ↓
形成诊断结论
```

这就是 Agent Workflow，不是固定脚本。

---

## 推荐你面试时这样讲

你可以直接这样回答：

> 排查计划不是大模型凭空生成的，而是由 Planner 基于多类上下文生成。首先从工单和告警里抽取服务、时间窗口、异常现象、影响范围；然后通过分诊模型判断问题类型，比如 5xx、超时、Pod 重启、数据库慢查询、OSS 访问失败等；再结合服务拓扑，展开这个服务依赖的 ALB、K8s、MySQL、OSS 等组件；同时检索历史 SOP、Runbook 和 RCA，找到类似问题的排查经验；最后根据当前工具注册表，生成一份可执行的排查计划。
>
> 这个计划不是普通文字，而是结构化 Plan，每一步都会绑定具体工具、入参、预期证据和风险等级。执行过程中，Agent 会根据已返回的证据动态调整后续计划，比如发现 MySQL 慢查询异常，就会收敛到连接数、锁等待、执行计划等数据库方向继续排查。

一句话版：

> **排查计划来自“工单症状 + 问题分类 + 服务拓扑 + 历史 SOP/RCA + 工具能力清单 + 当前证据”的综合推理，本质是 Planner 把运维专家经验转成可执行的工具调用 DAG。**

## Prompt:
2026/5/13 16:10:07

工单长啥样？如何从工单里抽取结构化信息？

## Response:
2026/5/13 16:10:10

> **Clarifying ticket shapes and extraction process**
>
> I need to dive into how to explain the shape of a ticket and how to extract structured information from them. It seems the user wants a detailed answer about the ticket format as well as an explanation about the extraction pipeline using NLP, rules, and validation. I'll want to include some incident ticket examples to go deeper without making it too long, especially considering the project context.
>
> **Describing ticket structure and extraction process**
>
> The user is asking for detailed ticket information extraction with three forms: monitoring auto tickets, human text tickets, and chat ops messages. I need to explain the extraction pipeline that involves deterministic extraction, entity recognition with CMDB mapping, and LLM integration. I'll also include examples and validation steps.
>
> Thought for 19s

我先把“工单”具体化成一个真实样例，再拆它怎么被 Agent 转成结构化字段；重点是让你面试时能讲清楚“Planner 的输入到底从哪来”。

工单本质上就是一个**故障处理任务单**。它可能来自告警系统、客服反馈、研发手动提交、飞书/企微群消息、监控平台自动创建。你的运维智能体里“工单接入 → 自动分诊 → 多源证据采集 → 根因假设 → 处置建议 → 审批 → 验证 → RCA”的链路，本质就是围绕这个工单对象展开的。`欧阳锦峰-AI-7年.pdf`

---

## 1. 工单长什么样？

最真实的工单一般不是干净 JSON，而是**半结构化文本 + 一些系统字段**。

比如一个人工提交的工单可能长这样：

```text
工单标题：订单接口 500 增多，部分用户无法下单

工单内容：
从今天 14:20 开始，订单中心的创建订单接口大量报 500，
用户反馈提交订单失败。影响范围主要是华南区用户。
初步看监控里 order-service 的错误率升高，接口 RT 也有上涨。
麻烦帮忙排查一下是不是服务异常或者数据库问题。

服务：order-service
环境：prod
优先级：P1
提交人：张三
发生时间：2026-05-13 14:20 左右
相关接口：POST /api/orders/create
相关告警：ALB 5xx rate high、order-service error rate high
```

如果是监控系统自动生成，可能长这样：

```json
{
  "ticket_id": "INC-20260513-0012",
  "title": "P1告警：order-service 5xx错误率超过阈值",
  "source": "monitoring",
  "severity": "P1",
  "created_at": "2026-05-13T14:25:00+08:00",
  "alert_name": "order-service-5xx-high",
  "service": "order-service",
  "env": "prod",
  "region": "cn-south",
  "metric": "http_5xx_rate",
  "current_value": "12.8%",
  "threshold": "5%",
  "duration": "5m",
  "description": "order-service 在最近5分钟 HTTP 5xx 错误率持续高于阈值",
  "labels": {
    "cluster": "prod-shenzhen-01",
    "namespace": "order",
    "workload": "order-service",
    "alb": "alb-prod-order"
  }
}
```

如果是群里转工单，可能更口语化：

```text
订单这边炸了，用户下单一直失败，14点多开始的。
看起来 order-service 有不少 500，可能是刚才发布之后出的问题。
能不能帮忙看下？
```

所以工单输入有三种典型形态：

```text
1. 标准工单：有标题、描述、优先级、服务、环境、时间等字段
2. 告警工单：由监控系统自动创建，带指标、阈值、标签
3. 口语工单：来自 IM 群、客服反馈、研发描述，字段不完整
```

---

## 2. 要从工单里抽取哪些结构化信息？

核心不是抽取所有文字，而是抽取后续排查计划需要的字段。

可以定义一个标准结构：

```ts
type IncidentContext = {
  ticketId: string
  title: string
  source: "manual" | "monitoring" | "chatops" | "customer_feedback"

  severity: "P0" | "P1" | "P2" | "P3" | "unknown"
  environment: "prod" | "staging" | "test" | "unknown"

  service: {
    name: string
    aliases?: string[]
    owner?: string
    namespace?: string
    cluster?: string
  }

  symptom: {
    type:
      | "http_5xx"
      | "timeout"
      | "service_unavailable"
      | "pod_restart"
      | "mysql_slow_query"
      | "oss_access_error"
      | "unknown"
    description: string
  }

  impact: {
    businessImpact?: string
    affectedUsers?: string
    affectedRegion?: string
    affectedApi?: string
  }

  timeRange: {
    start?: string
    end?: string
    rawText?: string
  }

  relatedSignals: {
    metrics?: string[]
    alerts?: string[]
    logs?: string[]
    recentChanges?: string[]
  }

  confidence: number
  missingFields: string[]
}
```

抽出来之后，Agent 才知道：

```text
查哪个服务？
查哪个环境？
查哪个时间窗口？
是什么故障类型？
影响范围是什么？
优先查 ALB、K8s、MySQL 还是 OSS？
有哪些字段缺失需要补全？
```

---

## 3. 从刚才的工单里可以抽成这样

原始工单：

```text
订单接口 500 增多，部分用户无法下单。
从今天 14:20 开始，订单中心创建订单接口大量报 500。
影响华南区用户。order-service 错误率升高，接口 RT 上涨。
环境 prod，优先级 P1。
```

结构化结果：

```json
{
  "ticketId": "INC-20260513-0012",
  "source": "manual",
  "severity": "P1",
  "environment": "prod",
  "service": {
    "name": "order-service"
  },
  "symptom": {
    "type": "http_5xx",
    "description": "订单创建接口 HTTP 500 增多"
  },
  "impact": {
    "businessImpact": "用户无法下单",
    "affectedRegion": "华南区",
    "affectedApi": "POST /api/orders/create"
  },
  "timeRange": {
    "start": "2026-05-13T14:20:00+08:00",
    "end": "unknown",
    "rawText": "今天14:20开始"
  },
  "relatedSignals": {
    "metrics": ["error_rate", "api_rt"],
    "alerts": ["order-service error rate high"]
  },
  "missingFields": [
    "cluster",
    "namespace",
    "recent_release",
    "alb_instance"
  ],
  "confidence": 0.82
}
```

这份结构化结果就是后续 Planner 的输入。

---

## 4. 如何抽取？不要只靠大模型，要用“三段式”

最稳的方式是：

```text
规则抽取
+ 资源映射
+ LLM 结构化抽取
+ 校验补全
```

### 第一步：规则抽取确定硬字段

有些字段不需要大模型，直接用规则就能抽。

比如：

```text
P1 / P2 / 紧急 / 严重 → severity
prod / 生产 / 线上 → environment
14:20 / 今天下午两点 / 最近30分钟 → timeRange
500 / 5xx / 超时 / 403 / 404 → symptom candidate
order-service / 用户中心 / 支付服务 → service candidate
```

规则抽取适合处理：

```text
优先级
环境
时间
状态码
接口路径
告警名
服务名
指标名
```

因为这些字段相对明确，没必要消耗模型 token。

---

### 第二步：资源映射，把“人话服务名”映射成系统资源

工单里经常写的是：

```text
订单服务
订单中心
下单接口
order
order-service
```

但系统里真实资源可能是：

```json
{
  "service_id": "svc_order_001",
  "service_name": "order-service",
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service",
  "mysql": "order_db",
  "alb": "alb-prod-order",
  "oss_bucket": "order-attachment-prod"
}
```

这一步依赖 CMDB / 服务目录 / 服务拓扑。

也就是说，抽取不是只从文本里拿字段，还要做资源补全：

```text
订单服务 → order-service
order-service → K8s namespace/order-service
order-service → ALB alb-prod-order
order-service → MySQL order_db
order-service → OSS order-attachment-prod
```

这个映射非常关键。否则 Agent 知道“订单服务异常”，但不知道应该调用哪个 K8s cluster、哪个 namespace、哪个 ALB、哪个数据库。

---

### 第三步：LLM 做语义抽取和归类

大模型主要负责处理规则不好判断的内容，比如：

```text
用户描述里的真实故障现象是什么？
这是 5xx、超时、权限问题，还是发布问题？
业务影响是什么？
哪些信息是明确事实，哪些只是猜测？
有哪些缺失字段？
```

可以给模型一个严格 Schema，让它只输出 JSON：

```json
{
  "symptom_type": "http_5xx | timeout | oss_403 | pod_restart | mysql_slow_query | unknown",
  "business_impact": "string",
  "affected_api": "string | null",
  "affected_region": "string | null",
  "suspected_causes": ["string"],
  "explicit_facts": ["string"],
  "user_guesses": ["string"],
  "missing_fields": ["string"],
  "confidence": 0.0
}
```

关键点：**要让模型区分事实和猜测**。

比如工单写：

> 可能是刚才发布导致的。

这不是事实，只能抽成：

```json
{
  "user_guesses": ["可能与最近发布有关"]
}
```

不能直接当成根因。

---

### 第四步：校验和补全

LLM 抽出来后，还要经过校验层。

例如：

```text
服务名是否存在？
环境是否合法？
时间是否能解析？
P1 是否符合告警等级？
接口路径是否属于该服务？
ALB / K8s / MySQL 资源是否能从服务拓扑找到？
```

如果有缺失字段，可以走两种策略：

```text
1. 能从服务目录补全：自动补全
2. 不能补全：进入追问或低置信度排查
```

比如缺少 namespace，但 CMDB 能查到：

```text
order-service → namespace=order
```

就不需要问用户。

如果服务名完全不明确：

```text
“订单有问题”
```

那就需要追问：

```text
请确认是 order-service、trade-service，还是 payment-service？
```

---

## 5. 最终输出给 Planner 的不是工单原文，而是 IncidentContext

最终结构可以这样：

```json
{
  "incident": {
    "id": "INC-20260513-0012",
    "severity": "P1",
    "env": "prod",
    "timeRange": {
      "start": "2026-05-13T14:20:00+08:00",
      "end": "2026-05-13T14:50:00+08:00"
    }
  },
  "service": {
    "name": "order-service",
    "cluster": "prod-shenzhen-01",
    "namespace": "order",
    "workload": "order-service",
    "alb": "alb-prod-order",
    "mysql": "order_db",
    "oss": "order-attachment-prod"
  },
  "symptom": {
    "type": "http_5xx",
    "affectedApi": "POST /api/orders/create",
    "description": "订单创建接口 500 增多"
  },
  "impact": {
    "business": "部分用户无法下单",
    "region": "华南区"
  },
  "signals": {
    "metrics": ["http_5xx_rate", "api_rt", "error_rate"],
    "alerts": ["ALB 5xx rate high", "order-service error rate high"]
  },
  "hypothesisSeeds": [
    "入口层 ALB 后端健康异常",
    "K8s Pod 重启或 OOM",
    "MySQL 慢查询或连接池耗尽",
    "最近发布引入接口异常"
  ],
  "missingFields": [],
  "confidence": 0.88
}
```

Planner 拿到这个，就能生成排查计划：

```text
1. 查 ALB 5xx 和后端健康检查
2. 查 K8s Pod 状态和重启次数
3. 查应用日志中的 500 异常堆栈
4. 查 MySQL 连接数、慢查询、锁等待
5. 查最近发布和配置变更
```

这就是从“工单”到“排查计划”的中间桥梁。

---

## 6. 你可以这样回答面试官

> 工单通常不是一个完全标准的数据结构，而是半结构化信息，可能来自告警系统、人工提交、IM 群消息或者客服反馈。里面通常包含标题、故障描述、服务名、环境、时间、优先级、影响范围、相关告警和异常指标。  
>
> 我们不会直接把整段工单丢给大模型生成排查计划，而是先做结构化抽取。第一步通过规则抽取优先级、环境、时间、状态码、接口路径等硬字段；第二步通过服务目录或 CMDB 把业务服务名映射到真实资源，比如 K8s namespace、workload、ALB 实例、MySQL 库和 OSS bucket；第三步用 LLM 做语义抽取，识别故障类型、业务影响、用户猜测和缺失字段；最后经过校验层补全资源信息，形成标准 IncidentContext。  
>
> Planner 后续不是基于原始工单做规划，而是基于 IncidentContext 生成可执行排查计划。这样可以降低模型误解工单的风险，也能保证后续工具调用有明确的服务、环境、时间窗口和资源标识。

一句话版：

> **工单就是故障输入源，结构化抽取就是把“人写的故障描述”转成 Agent 可执行的 IncidentContext，包括服务、环境、时间、症状、影响范围、相关告警、拓扑资源和置信度。**

## Prompt:
2026/5/13 16:25:42

CMDB是什么

## Response:
2026/5/13 16:25:45

CMDB 全称是 **Configuration Management Database，配置管理数据库**。

你可以把它理解成：**企业内部所有 IT 资源和业务系统的“资产地图 + 关系地图”。**

在运维智能体里，CMDB 的作用非常关键，因为 Agent 不能只知道“订单服务出问题了”，它还要知道：

```text
订单服务到底部署在哪个 K8s 集群？
属于哪个 namespace？
对应哪个 workload？
入口 ALB 是哪个？
依赖哪个 MySQL？
用到了哪个 OSS bucket？
负责人是谁？
最近有没有发布？
上下游服务有哪些？
```

这些信息一般就来自 CMDB。

---

## 举个例子

用户工单写：

```text
订单服务 500 增多，用户无法下单。
```

这句话对人来说能理解，但对系统来说不够。

CMDB 可以把“订单服务”补全成：

```json
{
  "serviceName": "order-service",
  "owner": "交易研发组",
  "env": "prod",
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service",
  "alb": "alb-prod-order",
  "mysql": "order_db",
  "ossBucket": "order-attachment-prod",
  "upstream": ["gateway-service"],
  "downstream": ["payment-service", "inventory-service"]
}
```

这样 Agent 才知道后面该调用哪些工具：

```text
查 ALB：alb-prod-order
查 K8s：prod-shenzhen-01 / order / order-service
查 MySQL：order_db
查 OSS：order-attachment-prod
查下游：payment-service、inventory-service
```

---

## CMDB 里通常存什么？

常见包括：

```text
服务信息：服务名、服务别名、负责人、所属团队
部署信息：集群、namespace、workload、镜像、版本
资源信息：机器、容器、数据库、缓存、消息队列、对象存储
流量信息：域名、网关、ALB/SLB、Ingress、监听器
依赖关系：上游服务、下游服务、数据库依赖、外部 API 依赖
环境信息：prod、staging、test
变更信息：最近发布、配置变更、扩缩容记录
权限信息：谁能看、谁能操作、谁需要审批
```

---

## 在运维智能体中的价值

CMDB 主要解决三个问题：

第一，**资源定位**。

用户说“订单服务”，Agent 要能定位到真实资源：

```text
order-service → K8s workload → ALB → MySQL → OSS
```

第二，**服务拓扑展开**。

Agent 可以知道一个故障可能影响哪些上下游：

```text
gateway → order-service → payment-service / inventory-service → MySQL
```

第三，**排查计划生成**。

有了 CMDB，Planner 才能生成具体可执行的排查计划，而不是泛泛地说“检查服务状态”。

---

## 面试可以这样说

> CMDB 是配置管理数据库，可以理解为企业 IT 资源和服务关系的统一资产台账。它记录服务、集群、数据库、负载均衡、对象存储、负责人、环境和上下游依赖关系。  
>
> 在运维智能体里，CMDB 的作用是把用户工单里的自然语言服务名，映射成真实可操作的系统资源。比如用户说“订单服务异常”，CMDB 可以补全它对应的 K8s 集群、namespace、workload、ALB 实例、MySQL 库和 OSS bucket。这样 Agent 才能生成具体排查计划，并调用正确的工具采集证据。

一句话记：

> **CMDB 就是运维系统的资产和关系底座，负责把“业务服务名”翻译成“真实基础设施资源”。**

## Prompt:
2026/5/13 16:43:03

问题2：生成了结构化的排查计划后，如何选择工具

## Response:
2026/5/13 16:43:05

生成结构化排查计划后，**不是让大模型临场猜工具**，而是由一个 **Tool Router / Tool Selector** 根据计划步骤去匹配工具。

核心链路是：

```text
结构化排查计划
   ↓
拆成多个排查步骤
   ↓
识别每一步需要什么证据
   ↓
从 Tool Registry 里匹配候选工具
   ↓
根据资源、权限、风险、参数完整度打分
   ↓
选择最合适的工具执行
```

一句话：

> **排查计划告诉 Agent“要查什么”，工具选择器负责决定“用哪个工具查”。**

---

## 1. 结构化排查计划里要包含“证据需求”

比如排查计划不能只写：

```text
检查订单服务是否异常
```

这太泛了，工具选择器不知道该用 K8s、ALB 还是 MySQL。

应该写成这种结构：

```json
{
  "stepId": "step_1",
  "goal": "判断入口流量是否异常",
  "targetLayer": "traffic_entry",
  "resourceType": "alb",
  "evidenceNeeded": [
    "5xx_rate",
    "backend_health",
    "request_latency"
  ],
  "timeRange": "30m",
  "riskLevel": "readonly"
}
```

这样 Tool Router 就知道：这一环节要查的是 **ALB 入口层证据**，不是数据库，也不是 Pod 日志。

---

## 2. 工具选择依赖 Tool Registry

你要先有一个工具注册表。

比如：

```json
[
  {
    "name": "alb.get_traffic_metrics",
    "domain": "alb",
    "capabilities": ["5xx_rate", "4xx_rate", "latency", "qps"],
    "resourceType": "alb",
    "permission": "readonly",
    "riskLevel": "low"
  },
  {
    "name": "alb.get_backend_health",
    "domain": "alb",
    "capabilities": ["backend_health", "unhealthy_instance"],
    "resourceType": "alb",
    "permission": "readonly",
    "riskLevel": "low"
  },
  {
    "name": "k8s.get_pod_status",
    "domain": "k8s",
    "capabilities": ["pod_status", "restart_count", "oom_killed", "crash_loop"],
    "resourceType": "workload",
    "permission": "readonly",
    "riskLevel": "low"
  },
  {
    "name": "mysql.get_slow_queries",
    "domain": "mysql",
    "capabilities": ["slow_query", "query_latency"],
    "resourceType": "mysql",
    "permission": "readonly",
    "riskLevel": "low"
  }
]
```

Tool Router 就是拿排查步骤里的 `resourceType`、`evidenceNeeded`、`riskLevel` 去匹配这个注册表。

---

## 3. 工具选择的判断依据

主要看 6 个维度。

### 第一，看排查目标属于哪一层

```text
入口层问题 → ALB / SLB 工具
服务运行问题 → K8s 工具
应用异常问题 → 日志工具 / APM 工具
数据库问题 → MySQL 工具
文件上传下载问题 → OSS 工具
变更问题 → 发布系统 / 配置中心工具
```

比如计划写：

```text
判断 5xx 是否来自入口层
```

优先选：

```text
alb.get_traffic_metrics
alb.get_backend_health
```

计划写：

```text
判断服务是否重启或 OOM
```

优先选：

```text
k8s.get_pod_status
k8s.get_events
```

计划写：

```text
判断数据库是否拖慢接口
```

优先选：

```text
mysql.get_connection_stats
mysql.get_slow_queries
mysql.get_lock_waits
```

---

### 第二，看需要什么证据

工具不是按名字选，而是按**证据类型**选。

例如：

```text
需要 5xx 指标 → alb.get_traffic_metrics
需要后端健康状态 → alb.get_backend_health
需要 Pod 重启次数 → k8s.get_pod_status
需要 OOM 事件 → k8s.get_events
需要错误堆栈 → k8s.get_pod_logs
需要慢 SQL → mysql.get_slow_queries
需要 OSS 403/404 → oss.get_access_errors
```

这就是能力匹配。

---

### 第三，看 CMDB 能不能补齐资源

排查计划里可能只有：

```json
{
  "service": "order-service"
}
```

但工具调用需要：

```json
{
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service",
  "alb": "alb-prod-order",
  "mysql": "order_db"
}
```

所以 Tool Router 选择工具前，要先通过 CMDB 补全资源。

例如：

```text
order-service
  → ALB：alb-prod-order
  → K8s：prod-shenzhen-01 / order / order-service
  → MySQL：order_db
  → OSS：order-attachment-prod
```

如果 CMDB 能补齐，就可以执行工具。

如果补不齐，就进入：

```text
资源补全失败 → 降级排查 / 追问用户 / 查服务目录
```

---

### 第四，看工具参数是否完整

工具不是选中就能调用，还要看参数是否够。

比如：

```json
{
  "tool": "k8s.get_pod_logs",
  "requiredParams": ["cluster", "namespace", "podName", "timeRange"]
}
```

但当前只有：

```json
{
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service"
}
```

缺少 `podName`。

那就不能直接调用 `k8s.get_pod_logs`，应该先调用：

```text
k8s.get_pod_status
```

拿到异常 Pod 后，再调用：

```text
k8s.get_pod_logs
```

所以工具选择有依赖关系。

正确顺序是：

```text
先查 Pod 列表和状态
再查异常 Pod 日志
```

而不是一上来查日志。

---

### 第五，看权限和风险等级

工具分为：

```text
只读工具：可以自动执行
低风险动作：需要确认
高风险动作：必须审批
禁止动作：不允许执行
```

例如：

```text
k8s.get_pod_status         → 只读，可自动执行
k8s.get_pod_logs           → 只读，但要脱敏
k8s.rollout_restart        → 高风险，必须审批
mysql.get_slow_queries     → 只读，可自动执行
mysql.kill_session         → 高风险，必须审批
oss.check_object_exists    → 只读，可自动执行
oss.update_bucket_policy   → 高风险，必须审批
```

所以 Tool Router 不能只考虑“能不能解决问题”，还要考虑“能不能安全调用”。

---

### 第六，看当前证据状态

工具选择是动态的。

第一轮可能先查：

```text
ALB 指标
K8s Pod 状态
MySQL 连接数
```

如果结果显示：

```text
ALB 5xx 升高
K8s Pod 正常
MySQL 连接数打满
```

下一轮工具选择就应该收敛到 MySQL：

```text
mysql.get_slow_queries
mysql.get_lock_waits
mysql.get_connection_stats
mysql.explain_query
```

如果结果显示：

```text
Pod CrashLoopBackOff
```

下一轮工具选择就应该收敛到 K8s：

```text
k8s.get_events
k8s.get_pod_logs
k8s.describe_deployment
```

这就是 Agent Workflow 的价值：**不是一次性固定执行，而是根据证据动态调整工具选择。**

---

## 4. 可以设计一个工具选择评分

实际实现里可以给候选工具打分。

```text
工具得分 =
能力匹配度
+ 资源匹配度
+ 参数完整度
+ 低风险加分
+ 数据新鲜度
- 调用成本
- 权限风险
```

比如：

```ts
score(tool, planStep) =
  capabilityMatch * 0.35 +
  resourceMatch * 0.25 +
  inputCompleteness * 0.20 +
  safetyScore * 0.10 +
  freshnessScore * 0.10
```

举例：

排查步骤：

```json
{
  "goal": "判断后端服务是否有异常实例",
  "resourceType": "alb",
  "evidenceNeeded": ["backend_health", "unhealthy_instance"]
}
```

候选工具：

```text
alb.get_backend_health       0.95
alb.get_traffic_metrics      0.65
k8s.get_pod_status           0.45
mysql.get_connection_stats   0.10
```

最终选择：

```text
alb.get_backend_health
```

---

## 5. 一个完整例子

工单：

```text
订单接口 500 增多，用户无法下单，order-service，prod，14:20 开始。
```

结构化计划：

```json
[
  {
    "stepId": "s1",
    "goal": "判断入口层是否出现 5xx 异常",
    "resourceType": "alb",
    "evidenceNeeded": ["5xx_rate", "latency", "qps"]
  },
  {
    "stepId": "s2",
    "goal": "判断后端实例健康状态",
    "resourceType": "alb",
    "evidenceNeeded": ["backend_health"]
  },
  {
    "stepId": "s3",
    "goal": "判断服务运行状态是否异常",
    "resourceType": "k8s",
    "evidenceNeeded": ["pod_status", "restart_count", "oom_killed"]
  },
  {
    "stepId": "s4",
    "goal": "判断数据库是否存在连接或慢查询问题",
    "resourceType": "mysql",
    "evidenceNeeded": ["connection_stats", "slow_query"]
  }
]
```

工具选择结果：

```json
[
  {
    "stepId": "s1",
    "selectedTools": [
      "alb.get_traffic_metrics"
    ],
    "reason": "需要采集 5xx_rate、latency、qps，匹配 ALB 指标工具"
  },
  {
    "stepId": "s2",
    "selectedTools": [
      "alb.get_backend_health"
    ],
    "reason": "需要判断后端实例健康状态"
  },
  {
    "stepId": "s3",
    "selectedTools": [
      "k8s.get_pod_status",
      "k8s.get_events"
    ],
    "reason": "需要判断 Pod 状态、重启次数和 OOM 事件"
  },
  {
    "stepId": "s4",
    "selectedTools": [
      "mysql.get_connection_stats",
      "mysql.get_slow_queries"
    ],
    "reason": "需要判断连接数、慢查询和数据库性能异常"
  }
]
```

---

## 6. 工具选择器的伪代码

```ts
function selectTools(planStep, incidentContext, toolRegistry) {
  const resourceContext = resolveResourceFromCMDB(
    incidentContext.service,
    planStep.resourceType
  )

  const candidates = toolRegistry.filter(tool => {
    return tool.resourceType === planStep.resourceType
      && hasIntersection(tool.capabilities, planStep.evidenceNeeded)
      && tool.permission !== "forbidden"
  })

  const scoredTools = candidates.map(tool => {
    return {
      tool,
      score:
        capabilityMatch(tool, planStep) * 0.35 +
        resourceMatch(tool, resourceContext) * 0.25 +
        inputCompleteness(tool, resourceContext, planStep) * 0.2 +
        safetyScore(tool) * 0.1 +
        freshnessScore(tool) * 0.1
    }
  })

  return scoredTools
    .filter(item => item.score > 0.7)
    .sort((a, b) => b.score - a.score)
}
```

---

## 7. 面试表达版

你可以这样回答：

> 生成结构化排查计划后，我不会让大模型直接临场决定调用哪个接口，而是通过 Tool Router 做工具选择。排查计划里的每一步都会描述排查目标、目标层级、资源类型、需要的证据类型、时间窗口和风险等级。  
>
> Tool Router 会拿这些信息去工具注册表里做匹配。比如计划里需要判断入口层 5xx 和后端健康状态，就匹配 ALB 的指标查询和健康检查工具；如果需要判断 Pod 重启、OOM、CrashLoop，就匹配 K8s 的 Pod 状态、事件和日志工具；如果需要判断连接池、慢查询、锁等待，就匹配 MySQL 工具。  
>
> 选择工具时还会结合 CMDB 做资源补全，比如把 order-service 映射到具体的 K8s cluster、namespace、workload、ALB 实例和 MySQL 库。然后再根据能力匹配度、参数完整度、权限等级、风险等级和当前已有证据进行筛选。只读工具可以自动执行，高风险动作工具必须进入人工审批。  
>
> 所以工具选择不是简单关键词匹配，而是“排查步骤 → 证据需求 → 工具能力 → 资源补全 → 权限风控 → 执行编排”的过程。

一句话版：

> **工具选择的依据是排查步骤需要的证据类型，再结合工具注册表、CMDB 资源映射、参数完整度、权限风险和当前证据状态，由 Tool Router 选择最合适的工具。**

## Prompt:
2026/5/13 17:36:48

问题3：详细介绍下：Tool Runtime：权限校验 / 参数校验 / 超时重试 / 审计记录

## Response:
2026/5/13 17:36:49

这个问题是运维智能体能不能“生产可用”的关键点。Tool Runtime 可以理解成 Agent 和真实生产系统之间的安全网关，所有工具调用都必须从这里过。

`Tool Runtime` 可以理解成：

> **Agent 调用 MySQL、K8s、ALB、OSS 等工具之前，统一经过的一层安全执行网关。**

它不负责“推理”，而负责**把 Agent 的工具调用变成安全、可靠、可追踪、可恢复的工程动作**。

整体位置是：

```text
Planner 生成排查计划
   ↓
Tool Router 选择工具
   ↓
Tool Runtime 统一执行控制
   ↓
具体 Tool Adapter
   - MySQL Adapter
   - K8s Adapter
   - ALB Adapter
   - OSS Adapter
   ↓
返回标准 EvidenceRecord
```

也就是说：

```text
Agent 不直接调用 K8s / MySQL / ALB / OSS
Agent 只向 Tool Runtime 提交工具调用请求
Tool Runtime 审核通过后，再调用真实工具
```

---

# 1. Tool Runtime 解决什么问题？

如果没有 Tool Runtime，Agent 可能会这样：

```text
想查 Pod → 直接调 K8s
想查 SQL → 直接查 MySQL
想重启服务 → 直接执行 restart
想改配置 → 直接调云 API
```

这在生产环境非常危险。

Tool Runtime 解决的是 5 类问题：

```text
1. 能不能调？—— 权限校验
2. 参数对不对？—— 参数校验
3. 调用失败怎么办？—— 超时、重试、熔断
4. 调了什么？—— 审计记录
5. 返回结果能不能给模型？—— 脱敏、标准化
```

面试里你可以说：

> Tool Runtime 是 Agent 和生产系统之间的受控执行层。它把模型生成的工具调用请求，转换成经过权限校验、参数校验、超时重试、脱敏审计后的安全调用，避免大模型直接操作生产环境。

---

# 2. Tool Runtime 的标准输入

Tool Runtime 接收的不是自然语言，而是结构化调用请求。

例如：

```json
{
  "runId": "run_20260513_001",
  "incidentId": "INC-20260513-0012",
  "stepId": "step_3",
  "toolName": "k8s.get_pod_status",
  "caller": {
    "agent": "diagnosis-agent",
    "user": "oncall_zhangsan"
  },
  "params": {
    "cluster": "prod-shenzhen-01",
    "namespace": "order",
    "workload": "order-service",
    "timeRangeMinutes": 30
  },
  "riskLevel": "low",
  "reason": "排查 order-service 是否存在 Pod 重启、CrashLoop 或 OOM"
}
```

这里面有几个关键字段：

```text
runId：本次 Agent 执行任务 ID
incidentId：关联的工单 ID
stepId：排查计划里的步骤 ID
toolName：要调用哪个工具
caller：谁发起的调用
params：工具参数
riskLevel：风险等级
reason：为什么要调用
```

`reason` 很重要。因为后面审计时要知道：

> 这个工具为什么被调用？是排查哪一步？是哪个 Agent 触发的？

---

# 3. 权限校验：判断“能不能调”

权限校验不是简单看用户有没有登录，而是要同时校验 4 个维度。

## 3.1 用户权限

例如用户是不是这个服务的负责人、值班人、SRE、管理员。

```text
oncall 用户 → 可以查线上日志
普通研发 → 可以查自己服务
非服务成员 → 只能查脱敏摘要
管理员 → 可以查更多资源
```

示例规则：

```json
{
  "user": "oncall_zhangsan",
  "service": "order-service",
  "role": "oncall",
  "allowedActions": [
    "k8s.read",
    "mysql.read",
    "alb.read",
    "oss.read"
  ]
}
```

---

## 3.2 工具权限

每个工具本身要分权限等级。

```text
readonly：只读查询，可自动执行
approval_required：需要人工审批
forbidden：禁止执行
```

例如：

```text
k8s.get_pod_status        readonly
k8s.get_pod_logs          readonly，但需要脱敏
k8s.rollout_restart       approval_required
mysql.get_slow_queries    readonly
mysql.kill_session        approval_required
mysql.drop_table          forbidden
oss.get_object_meta       readonly
oss.delete_object         forbidden
```

---

## 3.3 资源权限

即使用户能查 K8s，也不代表能查所有 namespace。

例如：

```text
张三负责 order-service
可以查 namespace=order
不能查 namespace=payment
不能查 namespace=finance
```

这一步一般依赖 CMDB / 服务目录 / 权限系统。

```text
用户 → 团队 → 服务 → 资源
```

例如：

```json
{
  "user": "zhangsan",
  "allowedServices": ["order-service"],
  "allowedNamespaces": ["order"],
  "allowedDatabases": ["order_db"],
  "allowedAlbInstances": ["alb-prod-order"]
}
```

---

## 3.4 环境权限

生产环境和测试环境权限要分开。

```text
test / staging：权限宽一些
prod：严格控制
```

例如：

```text
prod 环境：
- 查询类工具可以自动执行
- 写操作必须审批
- 高危操作禁止模型自动触发

test 环境：
- 部分低风险动作可以自动执行
```

---

## 3.5 权限校验结果

权限校验最后会返回三种结果：

```text
ALLOW：允许执行
REQUIRE_APPROVAL：需要审批
DENY：拒绝执行
```

例如：

```json
{
  "decision": "REQUIRE_APPROVAL",
  "reason": "k8s.rollout_restart 属于生产环境高风险动作，需要服务负责人审批",
  "approvers": ["order-service-owner", "sre-oncall"]
}
```

这就进入 Human-in-the-loop 审批节点。

---

# 4. 参数校验：判断“参数对不对”

Agent 生成工具调用参数时，可能会出现：

```text
缺字段
字段类型错误
服务名不对
时间范围过大
namespace 不存在
SQL 不安全
日志行数太多
bucket 不在白名单
```

所以 Tool Runtime 必须做参数校验。

## 4.1 JSON Schema 校验

每个工具都有自己的入参 Schema。

例如 `k8s.get_pod_status`：

```json
{
  "type": "object",
  "properties": {
    "cluster": { "type": "string" },
    "namespace": { "type": "string" },
    "workload": { "type": "string" },
    "timeRangeMinutes": {
      "type": "number",
      "minimum": 1,
      "maximum": 120
    }
  },
  "required": ["cluster", "namespace", "workload"]
}
```

如果 Agent 传了：

```json
{
  "namespace": "order",
  "workload": "order-service"
}
```

缺少 `cluster`，Tool Runtime 不会直接执行，而是返回：

```json
{
  "status": "PARAMS_INVALID",
  "missingFields": ["cluster"],
  "suggestion": "请先通过 CMDB 查询 order-service 对应的 cluster"
}
```

---

## 4.2 参数补全

有些参数缺失时，不一定要问用户，可以自动补全。

例如 Agent 只传了：

```json
{
  "service": "order-service"
}
```

Tool Runtime 可以通过 CMDB 补全：

```json
{
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service"
}
```

所以参数校验不是只做拦截，也可以做**安全补全**。

---

## 4.3 安全参数校验

这个特别重要。

### MySQL 参数校验

```text
只允许 SELECT
禁止 UPDATE / DELETE / INSERT / DROP / ALTER
必须带 LIMIT
限制最大扫描时间
限制库表白名单
禁止查询敏感字段
```

例如 Agent 生成：

```sql
SELECT * FROM users;
```

Tool Runtime 应该拒绝或改写：

```text
拒绝原因：
1. 查询字段过宽，包含敏感字段风险
2. 缺少 LIMIT
3. 表不在当前服务授权范围内
```

更安全的方式是只允许模板化查询：

```json
{
  "toolName": "mysql.get_slow_queries",
  "params": {
    "database": "order_db",
    "timeRangeMinutes": 30,
    "limit": 20
  }
}
```

而不是让 Agent 自己写 SQL。

---

### K8s 参数校验

```text
namespace 必须在白名单内
禁止传入任意 shell command
日志行数限制
时间窗口限制
禁止 exec 进入容器
生产环境禁止自动 restart
```

---

### ALB 参数校验

```text
ALB 实例必须属于当前服务
时间窗口不能过大
日志查询需要采样
不能返回完整 Header / Cookie
```

---

### OSS 参数校验

```text
bucket 必须在白名单内
objectKey 需要做路径规范化
禁止读取大文件内容
禁止批量删除
禁止返回敏感文件原文
```

---

# 5. 超时重试：保证“调用稳定”

运维工具调用经常会失败。

原因包括：

```text
云 API 抖动
K8s API Server 繁忙
MySQL 查询超时
日志系统响应慢
网络短暂异常
权限系统超时
```

所以 Tool Runtime 要统一处理超时和重试。

---

## 5.1 每个工具配置超时时间

不同工具超时不同：

```text
alb.get_traffic_metrics      3s
k8s.get_pod_status           5s
k8s.get_pod_logs             10s
mysql.get_slow_queries       5s
oss.get_access_errors        8s
```

工具注册表里可以这样配置：

```json
{
  "name": "k8s.get_pod_logs",
  "timeoutMs": 10000,
  "retryPolicy": {
    "maxRetries": 2,
    "backoffMs": 500
  }
}
```

---

## 5.2 不是所有失败都能重试

要区分错误类型。

可以重试：

```text
网络超时
服务暂时不可用
限流后短暂等待
云 API 5xx
```

不能重试：

```text
权限不足
参数错误
资源不存在
高风险操作
SQL 安全校验失败
```

例如：

```text
PARAMS_INVALID → 不重试
PERMISSION_DENIED → 不重试
TIMEOUT → 可重试
RATE_LIMITED → 延迟重试
RESOURCE_NOT_FOUND → 不重试，但可以触发资源重新映射
```

---

## 5.3 重试要有退避策略

不要失败后马上疯狂重试。

```text
第 1 次失败：等待 500ms
第 2 次失败：等待 1000ms
第 3 次失败：停止
```

这叫指数退避。

```ts
const delay = baseDelay * Math.pow(2, retryCount)
```

---

## 5.4 熔断和降级

如果某个工具连续失败，Tool Runtime 可以短时间熔断。

比如：

```text
k8s.get_pod_logs 连续 5 次超时
5 分钟内不再自动调用
改用 k8s.get_events 或只返回 Pod 状态
```

这可以避免 Agent 不断调用一个已经不可用的系统。

降级方式包括：

```text
日志工具不可用 → 查事件
MySQL 慢查询工具不可用 → 查连接数
ALB 日志不可用 → 查指标
OSS 访问日志不可用 → 查对象元信息
```

---

# 6. 审计记录：保证“过程可追踪”

审计记录是生产级 Agent 的核心能力。

每次工具调用都要记录：

```text
谁调用的？
什么时候调用的？
为什么调用？
调用了哪个工具？
参数是什么？
是否脱敏？
返回了什么摘要？
成功还是失败？
耗时多少？
是否重试？
是否经过审批？
关联哪个工单？
关联哪个排查步骤？
```

---

## 6.1 审计日志示例

```json
{
  "auditId": "audit_20260513_0001",
  "runId": "run_20260513_001",
  "incidentId": "INC-20260513-0012",
  "stepId": "step_3",
  "toolName": "k8s.get_pod_status",
  "callerAgent": "diagnosis-agent",
  "operator": "oncall_zhangsan",
  "env": "prod",
  "resource": {
    "cluster": "prod-shenzhen-01",
    "namespace": "order",
    "workload": "order-service"
  },
  "riskLevel": "low",
  "permissionDecision": "ALLOW",
  "paramsHash": "sha256:xxxx",
  "paramsMasked": {
    "cluster": "prod-shenzhen-01",
    "namespace": "order",
    "workload": "order-service"
  },
  "status": "SUCCESS",
  "durationMs": 842,
  "retryCount": 0,
  "summary": "发现 3 个 Pod，1 个处于 CrashLoopBackOff",
  "createdAt": "2026-05-13T14:31:21+08:00"
}
```

注意：审计日志里不要记录完整敏感内容。

比如：

```text
不要记录完整 SQL 查询结果
不要记录用户手机号、身份证、Token
不要记录完整 Header / Cookie
不要记录 OSS 文件内容
```

可以记录：

```text
参数摘要
参数 Hash
结果摘要
脱敏后的关键字段
```

---

## 6.2 审计记录有什么用？

第一，**复盘 RCA**。

RCA 里可以还原：

```text
14:31 查了 ALB 指标
14:32 查了 K8s Pod
14:33 查了 MySQL 慢查询
14:35 生成处置建议
14:37 人工审批扩容
14:39 验证 5xx 下降
```

第二，**问题追责**。

如果 Agent 给出错误建议，可以回看：

```text
用了哪些证据？
哪些工具返回异常？
是否遗漏关键排查步骤？
是否工具参数错了？
```

第三，**能力评估**。

可以统计：

```text
工具调用成功率
平均耗时
重试次数
权限拒绝次数
高风险动作审批次数
诊断命中率
RCA 质量
```

第四，**安全合规**。

生产环境必须能回答：

```text
谁查了什么？
谁执行了什么？
有没有越权？
有没有访问敏感数据？
有没有高危操作？
```

---

# 7. Tool Runtime 的完整执行流程

一个工具调用从开始到结束，大概是这样：

```text
1. 接收工具调用请求
2. 读取工具注册信息
3. 校验工具是否存在
4. 校验用户 / Agent / 服务 / 环境权限
5. 判断是否需要人工审批
6. 校验参数 Schema
7. 通过 CMDB 补全资源参数
8. 做安全策略检查
9. 写入调用开始审计
10. 执行具体 Tool Adapter
11. 处理超时、重试、熔断
12. 对返回结果脱敏
13. 标准化成 EvidenceRecord
14. 写入调用完成审计
15. 返回给 Agent
```

可以用一段伪代码表示：

```ts
async function executeTool(request: ToolCallRequest) {
  const tool = toolRegistry.get(request.toolName)

  if (!tool) {
    return fail("TOOL_NOT_FOUND")
  }

  const permission = await permissionChecker.check({
    user: request.caller.user,
    agent: request.caller.agent,
    tool,
    resource: request.params,
    env: request.params.env
  })

  if (permission.decision === "DENY") {
    await audit.logDenied(request, permission)
    return fail("PERMISSION_DENIED", permission.reason)
  }

  if (permission.decision === "REQUIRE_APPROVAL") {
    await audit.logApprovalRequired(request, permission)
    return pendingApproval(permission)
  }

  const enrichedParams = await cmdbResolver.enrich(request.params)

  const validation = validateParams(tool.inputSchema, enrichedParams)
  if (!validation.ok) {
    await audit.logInvalidParams(request, validation)
    return fail("PARAMS_INVALID", validation.errors)
  }

  const safety = safetyPolicy.check(tool, enrichedParams)
  if (!safety.ok) {
    await audit.logBlocked(request, safety)
    return fail("SAFETY_BLOCKED", safety.reason)
  }

  const auditStart = await audit.logStarted(request, enrichedParams)

  try {
    const rawResult = await executeWithTimeoutAndRetry(
      () => tool.adapter.call(enrichedParams),
      tool.timeoutMs,
      tool.retryPolicy
    )

    const maskedResult = dataMasker.mask(rawResult)
    const evidence = evidenceNormalizer.normalize(tool, maskedResult)

    await audit.logSuccess(auditStart.auditId, evidence)

    return {
      status: "SUCCESS",
      evidence
    }
  } catch (error) {
    await audit.logFailure(auditStart.auditId, error)

    return {
      status: "FAILED",
      error: normalizeError(error)
    }
  }
}
```

---

# 8. 一个完整例子：查 K8s Pod 状态

Agent 生成调用请求：

```json
{
  "toolName": "k8s.get_pod_status",
  "params": {
    "service": "order-service",
    "env": "prod"
  },
  "reason": "排查订单服务 500 是否由 Pod 异常导致"
}
```

Tool Runtime 做的事情：

## 第一步：权限校验

```text
用户是否有 order-service 权限？
Agent 是否允许调用 K8s 只读工具？
prod 环境是否允许自动查询？
```

结果：

```text
ALLOW
```

## 第二步：参数补全

通过 CMDB：

```text
order-service + prod
  → cluster = prod-shenzhen-01
  → namespace = order
  → workload = order-service
```

补全后：

```json
{
  "cluster": "prod-shenzhen-01",
  "namespace": "order",
  "workload": "order-service"
}
```

## 第三步：参数校验

```text
cluster 不为空
namespace 合法
workload 存在
timeRange 默认 30 分钟
```

## 第四步：调用 K8s Adapter

```text
读取 Deployment
读取 Pod 列表
读取 Pod restart count
读取异常状态
读取最近 events
```

## 第五步：返回标准 Evidence

```json
{
  "toolName": "k8s.get_pod_status",
  "resourceType": "k8s",
  "resourceId": "prod-shenzhen-01/order/order-service",
  "status": "critical",
  "summary": "order-service 存在 1 个 CrashLoopBackOff Pod",
  "keyFindings": [
    "order-service-xxx Pod 最近 30 分钟重启 8 次",
    "最近事件中出现 BackOff restarting failed container",
    "未发现 OOMKilled 事件"
  ],
  "confidence": 0.9,
  "collectedAt": "2026-05-13T14:31:21+08:00"
}
```

---

# 9. 一个完整例子：高风险工具需要审批

Agent 想执行：

```json
{
  "toolName": "k8s.rollout_restart",
  "params": {
    "service": "order-service",
    "env": "prod"
  },
  "reason": "尝试通过重启服务恢复订单接口"
}
```

Tool Runtime 发现：

```text
工具：k8s.rollout_restart
环境：prod
风险等级：high
```

所以不会直接执行，而是返回：

```json
{
  "status": "REQUIRE_APPROVAL",
  "approvalCard": {
    "title": "是否允许重启 order-service？",
    "riskLevel": "high",
    "reason": "Agent 判断 order-service Pod 异常，建议执行 rollout restart",
    "impact": "可能导致短暂请求抖动",
    "rollbackPlan": "如重启后错误率升高，可回滚到上一版本",
    "evidence": [
      "1 个 Pod CrashLoopBackOff",
      "最近 30 分钟重启 8 次",
      "ALB 5xx 持续升高"
    ],
    "approvers": ["order-service-owner", "sre-oncall"]
  }
}
```

只有审批通过后，Tool Runtime 才会真正执行。

这就是生产级运维 Agent 和普通 Demo 的区别。

---

# 10. 面试表达版

你可以这样说：

> Tool Runtime 是我在运维智能体里设计的统一工具执行层，它位于 Agent 和真实基础设施之间。Agent 不直接访问 MySQL、K8s、ALB、OSS，而是把工具调用请求提交给 Tool Runtime。  
>
> Tool Runtime 会先做权限校验，判断当前用户、Agent、服务、环境是否允许调用这个工具；如果是生产环境高风险动作，比如重启服务、修改负载均衡、kill 数据库连接，就必须进入人工审批。  
>
> 第二步是参数校验。每个工具都有 input schema，Runtime 会校验必填字段、字段类型、时间范围、资源白名单和安全约束。比如 MySQL 只允许只读查询，K8s 禁止任意 shell，OSS 禁止直接读取大文件内容。缺失参数可以通过 CMDB 做资源补全，例如把 order-service 补全成具体的 cluster、namespace、workload、ALB 和数据库。  
>
> 第三步是超时重试和稳定性控制。不同工具有不同 timeout 和 retry policy。网络抖动、云 API 5xx 可以重试；权限不足、参数错误、安全策略拦截不能重试。连续失败时 Runtime 会做熔断和降级，避免 Agent 反复调用异常工具。  
>
> 第四步是审计记录。每次工具调用都会记录关联工单、排查步骤、调用人、Agent、工具名、资源、参数摘要、权限决策、执行结果、耗时、重试次数和返回摘要，用于 RCA 复盘、问题追踪和安全合规。  
>
> 所以 Tool Runtime 的价值不是简单封装 API，而是把大模型的不确定调用变成可控、可审计、可审批、可恢复的生产级工具执行流程。

一句话版：

> **Tool Runtime 就是 Agent 的工具执行安全网关，统一负责权限校验、参数校验、风险审批、超时重试、结果脱敏、证据标准化和审计留痕，保证智能体能接生产系统但不能失控。**

## Prompt:
2026/5/13 17:44:53

https://github.com/oyjf11/BW-sre-agent  这是我的项目源码，我有实现这个功能吗

## Response:
2026/5/13 17:44:56

> **Inspecting GitHub repository for function implementation**
>
> [GitHub - oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent)
>
> **Inspecting files and retrieving GitHub tree structure**
>
> [BW-sre-agent/backend at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/tree/main/backend)
>
> **Exploring GitHub raw access and API alternatives**
>
> [BW-sre-agent/backend/app at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/tree/main/backend/app)
>
> **Inspecting app tools and services via web click**
>
> [BW-sre-agent/backend/app/tools at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/tree/main/backend/app/tools)
>
> **Accessing raw files through gateway.py**
>
> [BW-sre-agent/backend/app/tools/gateway.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py)
>
> **Searching for HTML raw links on GitHub**
>
> [raw.githubusercontent.com](https://github.com/oyjf11/BW-sre-agent/raw/refs/heads/main/backend/app/tools/gateway.py)
>
> **Analyzing citation needs and raw code handling**
>
> [BW-sre-agent/backend/app/tools/gateway.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py)
>
> **Exploring ToolGateway call validation and auditing**
>
> [BW-sre-agent/backend/app/tools/gateway.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py)
>
> **Searching for ToolGateway validation and audit information**
>
> [BW-sre-agent/backend/app/tools/gateway.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py)
>
> **Inspecting schemas and evaluating tool runtime permissions**
>
>
> **Searching for click schema information**
>
> [BW-sre-agent/backend/app/tools/schemas at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/tree/main/backend/app/tools/schemas)
>
> **Initializing schemas**
>
> [BW-sre-agent/backend/app/tools/schemas/__init__.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/schemas/__init__.py)
>
> **Adding risk content line to code**
>
> [BW-sre-agent/backend/app/tools/policies/env.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/policies/env.py)
>
> **Inspecting tests for test_tool_gateway**
>
> [BW-sre-agent/backend/app/tests/test_tool_gateway.py at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tests/test_tool_gateway.py)
>
> Thought for 1m 5s

我会直接检查你这个仓库的源码，而不是按设计稿猜。重点看有没有 Tool Runtime 这类统一执行层，以及权限、参数、重试、审计是否已经落到代码里。

结论：**你已经实现了一个“Tool Runtime 雏形”，代码里叫 `ToolGateway`，但还不是我前面说的完整生产级 Tool Runtime。**

更准确地说：

> **你现在有：Tool Registry + Adapter 选择 + 参数校验 + 重试 + 内存审计 + Mock/Real Adapter 切换。**  
> **你还缺：真正的权限校验、审批拦截、timeout 生效、审计持久化、脱敏、CMDB 参数补全、OSS/SLB 完整真实接入。**

---

## 1. 你已经实现了什么？

### 1）有统一工具入口：`ToolGateway`

你的后端 README 写得很清楚，主流程已经是一个 13 节点的 SRE 故障处置智能体链路：

```text
intake -> triage -> retrieve_memory -> planner -> evidence_fanout ->
evidence_aggregate -> diagnose -> critic -> remediation -> risk_gate ->
approval_interrupt/executor -> verify -> rca
```

这说明你的项目不是单纯接口调用，而是有 Agent Workflow 主链路。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/README.md))

在工具层，`ToolGateway.call_tool()` 已经作为统一入口存在。它会：

```text
检查工具是否存在
读取工具 metadata
做参数校验
选择 mock / real adapter
执行工具
成功或失败都写 audit_log
返回 ToolResponse
```

代码里可以看到 `call_tool` 会先判断 `tool_name` 是否在 handlers 里，然后读取 registry，再做 `_validate_params`，再选择 real/mock handler，最后执行并记录 audit。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

所以你可以说：

> 项目里已经实现了一个基础版 Tool Gateway，作为 Agent 调用底层工具的统一入口。

---

### 2）有 Tool Registry 和工具元数据

你有 `ToolMetadata`：

```python
class ToolMetadata(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    risk_level: str = "LOW"
    requires_approval: bool = False
    timeout_ms: int = 30000
    retries: int = 1
```

这说明你已经把工具标准化成了元数据注册模式，包括参数 Schema、风险等级、是否需要审批、超时、重试次数。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/schemas/__init__.py))

并且 `gateway.py` 里注册了多类工具，例如：

```text
query_logs
query_metrics
query_deployments
query_runbook
execute_action
query_ticket_by_id
query_service_metadata
query_k8s_deployment_status
query_k8s_pods
query_k8s_events
query_k8s_pod_logs_summary
query_lb_health_status
query_lb_traffic_metrics
query_db_processlist
query_db_slow_queries
query_db_table_status
query_db_variables
```

K8s、LB、MySQL 相关工具都已经注册了。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

这部分可以算是**标准化工具注册表**已经有了。

---

### 3）有参数校验

`ToolGateway._validate_params()` 已经能校验：

```text
required 必填字段
string 类型
integer 类型
object 类型
array 类型
```

如果类型错误，会提前返回错误，不会继续执行 handler。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

你的测试里也覆盖了这个点：`threshold_seconds` 传字符串 `"bad"` 时，会返回 `Invalid parameter 'threshold_seconds': expected integer`，并且 fake handler 没有被执行。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tests/test_tool_gateway.py))

所以这个点可以明确说：

> 参数 Schema 校验已经实现了基础版本，能够防止明显错误参数进入真实工具调用。

---

### 4）有重试机制

你在 `_execute_with_retry()` 上用了 `tenacity.retry`：

```python
@retry(
  stop=stop_after_attempt(2),
  wait=wait_exponential(multiplier=1, min=1, max=10),
  reraise=True,
)
```

这说明已经实现了**固定 2 次 + 指数退避**的基础重试机制。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

但注意：这个重试目前是**硬编码 2 次**，没有真正读取 `ToolMetadata.retries`。

所以只能说：

> 已经有基础重试能力，但还没有做到按工具配置动态重试。

---

### 5）有审计记录

`_log_audit()` 会记录：

```text
timestamp
run_id
tool_name
params
adapter
latency_ms
success
result
error
```

并 append 到 `self.audit_log`。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

所以你已经有了最基础的工具调用审计。

但是它现在是：

```text
内存审计
原始参数直接记录
结果直接记录
没有脱敏
没有持久化 DB
没有审批人 / 风险决策 / stepId / incidentId
```

所以只能算**开发调试级审计**，不是生产审计。

---

### 6）有 Mock / Real Adapter 切换

你有 `TOOL_ADAPTER_MODE=mock/real` 的设计。README 也写了默认使用 mock adapter，并说明真实 adapter 当前进度：已实现 MySQL 诊断工具、MySQL 应用日志 `query_logs`、K8s 只读工具；SLB、OSS、Prometheus/ARMS、CI/CD、RAG、Tracing、Eval 仍待实现。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/README.md))

代码里也能看到 `select_adapter()` 会根据 `ADAPTER_MODE == "real"` 选择真实 MySQL、K8s、SLB adapter，否则走 mock handler。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

所以你可以说：

> 项目已经实现了 Mock/Real Adapter 分层，MySQL 和 K8s 的真实只读接入已经有雏形，SLB/OSS 还没有完整落地。

---

## 2. 你还没有完整实现什么？

### 1）权限校验还没有真正接到 `ToolGateway`

你有 `EnvPolicy` 和 `RiskPolicy`，但我没看到它们在 `ToolGateway.call_tool()` 里被强制调用。

`EnvPolicy` 里有生产环境限制、动作白名单，比如 prod 允许 restart、scale_up、scale_down，不允许 delete/drop/truncate。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/policies/env.py))

`RiskPolicy` 里也有动作风险等级，比如 rollback/deploy 是 HIGH，delete 是 CRITICAL，并且 HIGH/CRITICAL 需要审批。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/policies/risk.py))

但是 `ToolGateway.call_tool()` 当前主流程是：

```text
工具是否存在
参数校验
选择 adapter
执行
审计
```

没有看到：

```text
用户权限校验
服务权限校验
资源权限校验
环境权限校验
requires_approval 拦截
RiskPolicy.assess_risk 调用
EnvPolicy.can_execute_action 调用
```

所以这里的判断是：

> **你有权限/风险策略类，但还没有真正接入 Tool Runtime 主执行链路。**

---

### 2）`requires_approval=True` 只是注册了，但没有被 ToolGateway 拦截

比如 `execute_action` 注册时是：

```text
risk_level="HIGH"
requires_approval=True
```

([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

但在 `call_tool()` 里没有看到：

```python
if metadata.requires_approval:
    return REQUIRE_APPROVAL
```

也没有看到它自动创建 approval card 或阻断执行。

你的审批链路应该是在 Agent Workflow 的 `risk_gate -> approval_interrupt/executor` 里有，但**工具执行层本身没有兜底拦截**。这意味着如果某段代码直接调用 `gateway.call_tool(ToolRequest(tool_name="execute_action"...))`，ToolGateway 自身不会因为 `requires_approval=True` 而拒绝执行。

所以面试里不要说：

> Tool Runtime 已经完整实现了审批拦截。

更准确说：

> 审批节点在工作流层有设计，工具元数据也标记了 requires_approval，但 ToolGateway 层还需要补一个强制审批校验，防止高风险工具绕过 risk_gate 被直接执行。

---

### 3）timeout 配置没有真正生效

`ToolMetadata` 有 `timeout_ms` 字段，工具注册时也写了 `timeout_ms=15000 / 30000 / 60000`。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/schemas/__init__.py))

但是 `_execute_with_retry()` 里没有看到 `asyncio.wait_for()` 或类似超时控制，只是直接调用 handler。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

所以这里是：

> **你有 timeout 配置，但没有真正执行 timeout 控制。**

应该补：

```python
result = await asyncio.wait_for(
    maybe_awaitable_handler(),
    timeout=metadata.timeout_ms / 1000
)
```

---

### 4）重试没有按工具配置动态生效

`ToolMetadata` 有 `retries` 字段，工具注册时也都写了 `retries=1`。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/schemas/__init__.py))

但 `_execute_with_retry()` 是固定：

```python
stop_after_attempt(2)
```

([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

也就是说：

> **当前重试机制是固定策略，不是按每个工具的 metadata 动态配置。**

---

### 5）审计记录还不是生产级

你现在的审计记录是内存 list：

```python
audit_log: List[Dict[str, Any]] = []
self.audit_log.append(entry)
```

记录了 params 和 result。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/app/tools/gateway.py))

但生产级应该至少补：

```text
持久化到 DB
关联 incident_id / step_id / approval_id
记录 permission_decision
记录 risk_level
记录 approver
参数脱敏
结果摘要化
敏感字段过滤
不要直接存完整 result
```

所以这里可以说：

> 当前已实现基础审计日志，但还不是合规级审计记录。

---

### 6）MySQL / K8s 有真实接入，SLB/OSS 不完整

README 明确写了：

```text
已实现：MySQL 诊断工具、MySQL 应用日志 query_logs、K8s 只读工具
待实现：SLB、OSS、Prometheus/ARMS 指标、CI/CD 部署记录、RAG、Tracing、Eval
```

([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/README.md))

所以你的项目不能说已经完整接入了：

```text
MySQL + K8s + ALB/SLB + OSS
```

更准确是：

```text
MySQL 和 K8s：已有真实 adapter 雏形
LB/SLB：已有工具注册和 mock 能力，真实接入待完善
OSS：目前未完成
```

---

## 3. 对照表：你现在实现程度

| 能力 | 当前状态 | 判断 |
|---|---:|---|
| 统一工具入口 | 已实现 `ToolGateway` | ✅ 已有 |
| Tool Registry | 已实现 `TOOL_REGISTRY` / `ToolMetadata` | ✅ 已有 |
| 参数 Schema | 已实现基础 required/type 校验 | ✅ 已有 |
| 工具风险元数据 | 有 `risk_level` / `requires_approval` | ✅ 有字段 |
| 真实权限校验 | 没看到接入 ToolGateway | ❌ 不完整 |
| 审批强制拦截 | metadata 有，但 gateway 未强制拦截 | ⚠️ 半成品 |
| 超时控制 | 有 timeout_ms 配置，但没看到实际 wait_for | ⚠️ 配了但未执行 |
| 重试控制 | 有 tenacity 重试，但固定 2 次 | ⚠️ 基础版 |
| 审计日志 | 内存 audit_log | ⚠️ 调试级 |
| 参数/结果脱敏 | 没看到 | ❌ 缺 |
| CMDB 参数补全 | 有 `query_service_metadata`，但不是统一补全层 | ⚠️ 半成品 |
| MySQL 接入 | README 显示已实现诊断工具和日志查询 | ✅ 已有 |
| K8s 接入 | README 显示已实现只读工具 | ✅ 已有 |
| ALB/SLB 接入 | 注册了 LB 工具，但 README 说待实现 | ⚠️ 半成品 |
| OSS 接入 | README 说待实现 | ❌ 缺 |

---

## 4. 你现在面试时应该怎么说？

不要说得太满。推荐这样讲：

> 我这个项目里已经实现了一个基础版 Tool Runtime，代码里叫 ToolGateway。它负责统一承接 Agent 的工具调用请求，并通过 Tool Registry 管理工具元数据，包括工具名、参数 Schema、风险等级、是否需要审批、超时和重试配置。  
>
> 当前 ToolGateway 已经实现了工具存在性校验、参数类型校验、Mock/Real Adapter 切换、基础重试和调用审计。MySQL 诊断工具和 K8s 只读工具已经有真实 adapter 雏形，LB 工具目前主要是注册和 mock，OSS 还在后续规划中。  
>
> 但如果按生产级 Tool Runtime 标准来看，它还需要继续补强：第一是把 EnvPolicy、RiskPolicy 和用户/资源权限真正接入 ToolGateway；第二是对 requires_approval 的高风险工具做强制审批拦截；第三是让 timeout_ms 和 retries 按工具配置真实生效；第四是把 audit_log 从内存日志升级成 DB 持久化审计，并增加参数脱敏、结果摘要和审批链路关联。

一句话版：

> **我已经实现了 Tool Runtime 的骨架和一部分工程能力，但目前更准确叫 ToolGateway 雏形；它具备注册、参数校验、Adapter 切换、重试和审计，生产级权限、审批、超时、脱敏、持久化审计和 OSS/SLB 完整接入还需要继续补齐。**

---

**Sources:**

- [BW-sre-agent/backend/README.md at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/backend/README.md)

## Prompt:
2026/5/14 09:54:08

如果按照我们的agent十个节点的分析方法，我们项目还缺哪些

## Response:
2026/5/14 09:54:10

> **Exploring current project source on GitHub**
>
> The user asked about their project source again. I think I should check GitHub for the most up-to-date info since the previous response might not have included the right citations and direct links. I’ll explore the current repo and get a proper citation for it.
>
> **Checking GitHub URL directly**
>
> It seems like my search didn’t work because GitHub isn’t indexed. I’ll need to open the URL directly to check the latest information on the repo. That should give me more accurate insights. Time to take a look!
>
> **Inspecting project files for gaps**
>
> I’ll need to look at the ACTION_PLAN, check for any current gaps, then dive into the backend README. It might also be useful to review the code itself to get a clearer understanding of the setup and any missing pieces. Let's go through the files carefully.
>
> **Handling raw action format issues**
>
> The raw action output looks messy because of formatting—it's all collapsed into one line. I’ll need to figure out whether I should use Python or curl to get a cleaner version. It’d help to cite specific lines, and perhaps opening the backend README or GitHub page could give me better line numbers to work with.
>
> **Continuing with proper citations**
>
> I need to continue citing key lines for clarity. It’s important to keep track of these specific lines to ensure proper referencing throughout the process. I’ll focus on providing accurate details and step-by-step citations wherever necessary.
>
> **Inspecting graph nodes for implementation details**
>
> I need to check the app's graph nodes, particularly the 13 nodes and their implementation. I'll open the relevant lines around the node list to make sure I fully understand how they’re structured and how they relate to the overall system. Let's inspect that closely.
>
> **Considerations for raw parsing and citations**
>
> It seems like I might need to parse the raw content with Python, but I’m unsure if internet access is available. If not, the container could potentially git clone the necessary files. I’ll aim to open raw lines on GitHub, especially focusing on relevant content and ensuring I include citations.
>
> **Assessing GitHub code and citation approach**
>
> The rendered GitHub code isn’t showing up well, so maybe using raw.githubusercontent could help, though it’s tricky with line breaks. The GitHub API might also assist, but I’m considering using container curl to access the code. Citations should likely focus on the ACTION_PLAN and repo without over-citing the code internals. I’ll inspect files locally for accuracy.
>
> **Considering code access via raw link**
>
> I’m thinking that just using the web might be the simplest approach. To view the code, I could click on the raw link directly. This might let me see the file better without too much hassle. Let's see if this does the trick!
>
> **Defining nodes and mapping project areas**
>
> I’m looking at the 10 nodes as part of the system design. Based on what I see in the repo, we’ve covered Workflow Agent, Tool Use, Approval, Checkpoint, SSE, and the Mock/Real Adapter. Now, I need to map them to the 10 nodes. This will help identify any gaps or areas to focus on!
>
> Thought for 4m 8s

按我们这套 **Agent 10 节点评估法**看，你这个 OpsPilot 项目现在不是“缺主链路”，而是：

> **主链路已经跑通，工具接入也有雏形；真正缺的是 RAG 记忆、离线评测、可观测、生产级任务调度、指标看板和知识闭环。**

你仓库里的行动计划也明确写了：Phase 1-4 已完成，包括前端核心体验、后端 API、端到端 Demo、前端测试修复；后续重点在真实数据源、RAG、Tracing、离线评测、生产工程能力。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

---

## 先给结论：10 个节点覆盖情况

| 10 节点 | 当前覆盖度 | 结论 |
|---|---:|---|
| 1. 场景与用户入口 | 80% | 有工单 / Run / 前端页面，但真实告警接入还不强 |
| 2. 工单结构化 / Intake | 70% | 有 ticket 输入和状态流转，但 NLP 抽取、CMDB 补全还弱 |
| 3. 自动分诊 / Triage | 75% | 有规则 + LLM + fallback 思路，但分诊评测不足 |
| 4. 排查计划 / Planner | 80% | 已能按故障类型生成工具任务，但计划质量缺评估 |
| 5. 工具标准化 / Tool Use | 75% | ToolGateway、MySQL、K8s、SLB 已有；OSS 未完成 |
| 6. 多源证据采集 / Evidence | 75% | 日志、DB、K8s、SLB 有雏形；Prometheus/ARMS、CI/CD 还弱 |
| 7. 根因诊断 / Diagnosis | 65% | 有候选根因，但证据引用、置信度校准、反证机制不够强 |
| 8. 安全审批 / Human-in-the-loop | 80% | 有审批、checkpoint、resume 机制，但 ToolGateway 强制拦截还可加强 |
| 9. 执行验证 / RCA | 70% | 有验证和 RCA 结构，但 OSS 归档、知识写回还缺 |
| 10. 评测 / 观测 / 持续迭代 | 35% | 这是最大短板：Eval、Tracing、指标看板、Prompt 版本管理还没落地 |

整体评分：

```text
当前项目覆盖率：约 70%
主流程完整度：较高
生产化完整度：中等偏弱
面试可讲性：较强
真正短板：评测、RAG、Tracing、指标、生产调度
```

---

# 1. 场景与用户入口：基本有，但真实入口还可以增强

你现在已经有 RunDetailPage、Stepper、证据/诊断/方案面板，也完成了端到端 Happy Path 验证，说明“用户提交工单 → 查看诊断过程 → 审批/查看结果”的产品闭环已经有了。行动计划里也明确写了 RunDetailPage、后端 API 和全链路 Happy Path 已完成。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

但还缺：

```text
真实告警系统接入
IM / ChatOps 接入
监控平台自动创建工单
客服反馈自动转工单
```

现在更像是：

> 用户手动创建一个故障 Run。

还没完全变成：

> 告警自动触发 OpsPilot，OpsPilot 自动生成排查任务。

面试表达要注意：

> 可以说“已完成工单驱动的故障处理闭环”，不要说“已经完整接入真实告警平台”。

---

# 2. 工单结构化 / Intake：有基础，但缺 CMDB + NLP 抽取增强

你现在有工单输入、ticket、service、env、severity 等字段，也有 intake 阶段。

但从 10 节点方法看，工单结构化应该更强，最好能做到：

```text
自然语言工单
→ 提取 service / env / severity / symptom / time_range / affected_api
→ 通过 CMDB 补齐 cluster / namespace / workload / SLB / DB
→ 输出标准 IncidentContext
```

你后续计划里也把 NLP 抽取作为短板补齐项：从工单 title/description 中抽取 service、symptom、metric、time_range、suspected_change，并作为 intake/triage 的辅助信息。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

所以这个节点当前是：

```text
有基础字段
缺智能抽取
缺 CMDB 资源补全
缺字段置信度
缺缺失字段追问机制
```

---

# 3. 自动分诊 / Triage：有雏形，但缺分诊准确率评测

自动分诊的目标是判断：

```text
这是发布回归？
资源耗尽？
依赖故障？
数据库问题？
流量入口问题？
OSS 访问问题？
```

你现在已经有分诊链路，并且后面的 planner 能根据 incident_type 生成不同排查任务。

但缺口是：

```text
没有分诊数据集
没有分诊准确率
没有 bad case 回放
没有 P0/P1 误判分析
```

所以它现在能跑，但还不能证明“分诊效果稳定”。

后续应该补：

```text
triage_eval_dataset.json
expected_incident_type
expected_severity
expected_service
expected_time_window
```

然后统计：

```text
incident_type accuracy
severity accuracy
service extraction accuracy
time_range extraction accuracy
```

---

# 4. 排查计划 / Planner：覆盖不错，但计划质量不可评估

你现在已经在 planner 中接入 DB 诊断任务生成逻辑，evidence_fanout 可以并行调度 MySQL 诊断工具。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

K8s 这边也已经在 planner 中接入，resource / dependency / deployment 类故障可自动调度 K8s 工具。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

说明 Planner 已经不是纯文本，而是能生成可执行工具任务。

但缺口是：

```text
没有判断“计划好不好”的指标
没有计划覆盖率
没有工具选择准确率
没有计划是否过查 / 漏查的评估
```

比如一个 5xx 工单，合理计划应该覆盖：

```text
ALB 指标
后端健康检查
K8s Pod
应用日志
MySQL 慢查询
最近发布
```

如果 Planner 只查日志，就算流程跑通，也是不合格。

建议补一个：

```text
plan_coverage_score
```

例如：

```json
{
  "case_id": "order_5xx_001",
  "expected_evidence_categories": ["lb", "k8s", "logs", "db", "deployments"],
  "actual_categories": ["logs", "db"],
  "coverage": 0.4
}
```

---

# 5. 工具标准化 / Tool Use：目前是强项之一，但 OSS 和生产级 Runtime 还缺

你现在 Tool Use 这块已经比较像样：

```text
MySQL 诊断工具：已完成
应用日志 query_logs 替换：已完成
K8s 只读适配器：已完成
SLB 适配器：已完成
ToolGateway：已有
Mock/Real Adapter：已有
```

MySQL 已实现 4 个真实诊断适配器，包括 processlist、slow queries、table status、variables，并且有只读账号、参数化查询、禁止拼接 SQL、结果截断等安全要求。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

K8s 已实现 deployment、pods、events、pod logs summary，并且有 namespace 白名单和日志截断。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

SLB 已实现真实阿里云 SLB API 接入，包括健康状态、QPS、延迟、5xx 指标，并接入 CMS 指标。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

但还缺：

```text
OSS 适配器未完成
Prometheus / ARMS 指标替换 query_metrics 还不完整
CI/CD 发布记录 query_deployments 仍需真实接入
ToolGateway 的权限 / 审批 / timeout / 脱敏 / 持久化审计还要加强
```

OSS 目前计划是把 RCA 报告和证据包写入 OSS，并限制只能写入 `rca/` 和 `evidence/` 前缀，但这个任务还没有标记完成。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

这个节点可以面试这样讲：

> 工具标准化已经做了 60%-70%，MySQL、K8s、SLB 已经有真实适配器，OSS、指标平台和发布系统还在补齐。

---

# 6. 多源证据采集 / Evidence：有并行采集，但证据质量体系不够

你现在 evidence_fanout 已经能并行调工具，这是好点。

当前证据源大概有：

```text
logs
metrics
deployments
runbook
mysql
k8s
slb
```

但真正生产级证据系统还缺：

```text
证据质量评分
证据来源引用
证据时间窗一致性
证据冲突检测
证据缺失提示
证据可信度分层
```

比如现在 Agent 说：

> MySQL 慢查询可能导致接口超时。

最好能明确引用：

```text
证据 1：query_db_slow_queries 返回 slow_query_count=12
证据 2：query_logs 出现 Lock wait timeout
证据 3：SLB 5xx 在同一时间窗口升高
```

也就是说，诊断不能只是“看过证据”，而要做到：

> 每个根因候选都能反查支持它的证据。

---

# 7. 根因诊断 / Diagnosis：有候选根因，但缺可解释和可校准

当前项目有 diagnose 和 critic 思路，这说明不是一次性直接输出结论，而是会做候选根因和审查。

但不足是：

```text
候选根因没有强绑定 evidence_id
confidence 不够可解释
没有 Top1 / Top3 命中率评测
反证机制偏弱
历史 RCA 没有真正参与诊断
```

后续 RAG 计划其实就是为这个节点补能力：让 planner/diagnose 能检索历史 RCA 和 Runbook，把历史同类故障作为 evidence 加入当前诊断。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

进一步，Phase 9 还计划把基础 RAG 升级成 hybrid search、rerank、citations 和召回评估，这才是比较完整的诊断增强。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

所以这个节点现在是：

```text
能诊断
但诊断依据不够强
历史经验复用不足
诊断质量不可量化
```

---

# 8. 安全审批 / Human-in-the-loop：覆盖较好，但 Runtime 兜底还要补

你的行动计划里明确说当前项目已经覆盖：

```text
Workflow Agent
Tool Use
审批
checkpoint
SSE
Mock/Real Adapter
```

([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

这说明安全审批是项目亮点之一。

尤其你之前修复过审批 resume 的问题，说明 checkpoint/resume 这条链路确实落过代码，不只是 PPT。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

但还缺一个更工程化的兜底：

```text
ToolGateway 层强制审批拦截
高危工具绕过 risk_gate 时也不能执行
审批记录和 tool audit 绑定
审批人、审批时间、审批理由持久化
```

现在更像是：

> 工作流层有审批节点。

还没完全做到：

> 工具执行层永远不允许高危动作绕过审批。

这是生产级 Agent 很关键的一点。

---

# 9. 执行验证 / RCA：有结构，但知识写回和归档不足

你现在有 verify、RCA 这类链路，也有 RunDetailPage 展示诊断、方案和结果。

但缺：

```text
RCA 写入知识库
RCA 人工确认
RCA 归档 OSS
证据包归档
下次同类故障可检索
```

Action Plan 里 Phase 6 明确规划了 `write_back(run_id)`，只把 `confirmed_by_human=True` 的 RCA 写入向量库；这说明目前知识写回还处在待实现状态。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

OSS 归档也还在 Task 5.4，目标是把 RCA 报告和证据包归档到 OSS。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

所以这个节点可以说：

> RCA 产物有，但 RCA 还没有完全变成可复用知识资产。

---

# 10. 评测 / 观测 / 持续迭代：当前最大短板

这是你项目最应该补的部分。

现在 Phase 8 才规划离线评测：创建 10-20 个测试案例，用 fixture 替换真实工具调用，跑 graph，比较 expected root cause、risk level，并统计 Top1/Top3 根因命中率、风险等级准确率、平均步骤数、延迟、token 消耗。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

Phase 7 也才规划 Tracing，要让每次 run 的执行路径在 LangSmith 或 Langfuse 中回放，并包含每个节点的 input/output、LLM 调用、tool 调用。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

Phase 10 还规划了指标看板，包括任务完成率、人工接管率、工具失败率、平均耗时、token 成本、RAG 命中率。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

所以你现在最大缺口是：

```text
不能稳定回答：这次 Agent 改动到底有没有变好？
不能稳定回答：根因诊断准确率是多少？
不能稳定回答：工具调用失败率是多少？
不能稳定回答：人工接管率有没有下降？
不能稳定回答：Prompt 改动是否引入回归？
```

这对 AI 产品经理面试非常关键。

---

# 按优先级，你现在最该补 6 件事

## P0：离线评测框架

先做这个，性价比最高。

最小实现：

```text
10 个 mock 工单 case
每个 case 有 expected_root_cause
每个 case 有 expected_risk_level
固定 tool fixtures
一键 replay
输出 eval_report.json
```

指标：

```text
Top1 根因命中率
Top3 根因命中率
风险等级准确率
工具调用成功率
平均步骤数
平均耗时
```

这能让你面试时从“我做了一个 Agent”升级成：

> 我建立了 Agent 迭代评测机制，可以用离线回放判断每次 Prompt、Planner、工具策略修改是否带来正向收益。

---

## P1：RAG + 历史 RCA / Runbook 检索

当前 planner / diagnose 还偏“当前证据驱动”，缺历史经验。

补完后变成：

```text
当前工单
→ 检索历史 RCA / Runbook
→ 注入相似故障经验
→ 辅助 Planner 和 Diagnosis
→ RCA 人工确认后写回知识库
```

这正好对应你 Phase 6 / Phase 9 规划。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

---

## P1：ToolGateway 生产级增强

补：

```text
权限校验
requires_approval 强制拦截
timeout_ms 真正生效
retries 按工具配置生效
参数脱敏
结果摘要化
审计持久化
```

这个是从 Demo 到生产级 Agent 的分水岭。

---

## P1：Tracing / 可观测性

补 LangSmith 或 Langfuse。

目标是每次 run 能看到：

```text
节点路径
每个节点输入输出
LLM prompt / response
tool call
tool latency
失败原因
重试次数
```

这个能支撑你讲：

> 我们不是黑盒 Agent，而是可观测、可回放、可追责的 Agent Workflow。

---

## P2：OSS 归档 + RCA 知识写回

补：

```text
write_rca_report_to_oss
write_evidence_bundle_to_oss
RCA confirmed_by_human 后写入向量库
下次同类故障可检索
```

这样 RCA 才真正变成“组织知识资产”。

---

## P2：Redis / 队列 / Worker

Phase 10 已经写得很清楚：现在短板是消息队列、缓存、分布式任务调度；目标是把长任务从单进程可跑，推进到可水平扩展、可观测、可恢复。([GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md))

这个不一定要马上做，但面试问“大规模生产化”时会很有用。

---

# 面试表达版

你可以这样说：

> 如果按照我对 Agent 项目的 10 节点评估法来看，OpsPilot 当前已经覆盖了主链路，包括工单接入、自动分诊、排查计划、多源证据采集、根因诊断、处置建议、人工审批、执行验证和 RCA 复盘。工程上也已经有 Workflow Agent、Tool Use、checkpoint、SSE、Mock/Real Adapter，以及 MySQL、K8s、SLB 等真实数据源接入。  
>
> 但它还不是完整生产级 Agent。当前最大的短板主要有 5 个：第一是 RAG 和历史 RCA/Runbook 检索还没完整落地，历史经验没有真正参与诊断；第二是离线评测体系不足，暂时无法用 Top1/Top3 根因命中率、风险等级准确率等指标衡量 Agent 迭代效果；第三是 Tracing 和指标看板不足，缺少对节点、工具、LLM 调用的完整回放；第四是 ToolGateway 的权限、审批、超时、脱敏、持久化审计还需要增强；第五是生产工程能力还不够，比如 Redis 缓存、分布式锁、后台队列和 Worker 还在规划中。  
>
> 所以这个项目当前更准确的定位是：已经跑通生产级运维 Agent 的核心闭环和工具接入雏形，但下一阶段重点要补齐评测、RAG、可观测性和大规模工程化能力。

一句话：

> **现在缺的不是 Agent 主流程，而是让它“可评测、可观测、可复用、可扩展、可审计”的生产化能力。**

---

**Sources:**

- [BW-sre-agent/ACTION_PLAN.md at main · oyjf11/BW-sre-agent · GitHub](https://github.com/oyjf11/BW-sre-agent/blob/main/ACTION_PLAN.md)

## Prompt:
2026/5/14 10:32:00

如何理解：可评测、可观测、可复用、可扩展、可审计

## Response:
2026/5/14 10:32:03

这 5 个词，本质是在判断一个 Agent 项目是不是从 **Demo** 走向 **生产级系统**。

你可以这样记：

```text
可评测：我怎么知道它有没有变好？
可观测：它每一步到底干了什么？
可复用：这套能力能不能迁移到别的场景？
可扩展：量大、工具多、团队多之后还能不能跑？
可审计：出了问题能不能追溯责任和证据？
```

---

# 1. 可评测：证明 Agent 效果有没有变好

**可评测**解决的是：

> 这次改 Prompt、改 Planner、加工具、加 RAG 后，Agent 到底有没有提升？

很多 Agent 项目最大的问题是：  
看起来能跑，但不知道效果好不好；今天觉得回答更聪明，明天可能又退化了。

在你的运维智能体里，可评测应该包括：

```text
根因命中率
排查计划覆盖率
工具选择准确率
风险等级判断准确率
处置建议可执行率
RCA 质量评分
人工接管率
平均排查耗时
```

比如一个标准测试集：

```json
{
  "caseId": "order_5xx_001",
  "input": "订单服务 500 增多，用户无法下单",
  "expectedRootCause": "MySQL 连接池耗尽",
  "expectedEvidence": ["ALB 5xx", "MySQL connection high", "slow query increase"],
  "expectedRiskLevel": "P1"
}
```

Agent 跑完后对比：

```text
有没有查到 MySQL？
有没有查 ALB？
有没有遗漏 K8s？
最终根因是否命中？
风险等级是否正确？
用了几步？
耗时多久？
```

所以，**可评测 = 有测试集 + 有指标 + 能回放 + 能对比版本效果**。

面试表达：

> 可评测不是简单看 Agent 能不能回答，而是要建立离线评测集和指标体系。比如针对历史故障工单构造标准 case，记录期望根因、期望证据和风险等级，每次修改 Planner、Prompt 或工具策略后自动回放，统计 Top1 根因命中率、工具调用准确率和排查计划覆盖率，判断 Agent 迭代是否真正变好。

---

# 2. 可观测：看清 Agent 每一步发生了什么

**可观测**解决的是：

> Agent 为什么这么判断？它查了什么？哪一步失败了？模型有没有乱推理？

传统系统可观测看的是：

```text
日志
指标
链路追踪
错误告警
```

Agent 系统还要额外看：

```text
每个节点输入输出
每次 LLM prompt / response
每次工具调用
工具返回结果
Planner 生成了什么计划
Diagnosis 使用了哪些证据
为什么进入人工审批
哪一步重试了
哪一步失败了
```

比如一次运维 Agent run，应该能回放成：

```text
Run ID: run_001

1. intake
输入：订单服务 500 工单
输出：service=order-service, severity=P1

2. triage
输出：incident_type=http_5xx

3. planner
输出：查 ALB、K8s、MySQL、发布记录

4. tool_call: alb.get_traffic_metrics
结果：5xx 从 2% 升到 15%

5. tool_call: k8s.get_pod_status
结果：Pod 正常，无重启

6. tool_call: mysql.get_connection_stats
结果：连接数接近上限

7. diagnose
输出：高概率根因是 MySQL 连接池耗尽
```

如果没有可观测，一旦 Agent 判断错了，你只能说：

> 模型可能幻觉了。

如果有可观测，你可以定位：

```text
是工单抽取错了？
是 Planner 少查了一个工具？
是 Tool Runtime 返回异常？
是 RAG 召回了错误案例？
是 Diagnosis 忽略了关键证据？
```

所以，**可观测 = 每个节点、每次模型调用、每次工具调用都能追踪和回放**。

面试表达：

> 可观测是为了避免 Agent 变成黑盒。我们需要记录每个 Workflow 节点的输入输出、LLM 调用、工具调用、耗时、错误、重试和证据流转，这样才能知道一次诊断结论是怎么来的，也能定位失败发生在工单抽取、Planner、工具调用还是诊断阶段。

---

# 3. 可复用：能力不是为一个 case 写死

**可复用**解决的是：

> 这套 Agent 能不能从“订单服务 500”复用到“支付超时”“OSS 403”“库存服务异常”？

很多 Demo 是写死的：

```text
只会处理一个服务
只会调用一组固定工具
只会走固定排查路径
Prompt 里写死业务逻辑
工具参数写死
```

生产级 Agent 要把能力抽象出来。

在你的运维智能体里，可复用体现在：

```text
统一工单结构：IncidentContext
统一工具协议：Tool Schema
统一证据结构：EvidenceRecord
统一排查计划：PlanStep
统一审批结构：ApprovalCard
统一 RCA 模板：RCAArtifact
```

这样不同场景只需要替换配置和工具：

```text
订单 500：
ALB + K8s + MySQL + 日志

OSS 403：
OSS + 权限策略 + CDN + 访问日志

支付超时：
K8s + 下游服务 + DB + MQ + APM

发布异常：
CI/CD + K8s deployment + 日志 + 指标
```

但底层流程仍然是：

```text
工单抽取 → 分诊 → 计划 → 工具 → 证据 → 诊断 → 审批 → 验证 → RCA
```

所以，**可复用 = 流程、工具、证据、模板都标准化，不为单个场景硬编码**。

面试表达：

> 可复用的关键是把一次故障处理拆成通用对象，而不是写死某个场景。比如工单统一成 IncidentContext，工具统一成 Tool Schema，工具结果统一成 EvidenceRecord，RCA 统一成结构化模板。这样同一套 Agent Workflow 可以复用到接口 5xx、数据库慢查询、K8s Pod 异常、OSS 访问失败等多类故障。

---

# 4. 可扩展：规模上来后还能稳定运行

**可扩展**解决的是：

> 当工单变多、工具变多、团队变多、服务变多时，系统还能不能撑住？

Demo 阶段可能是：

```text
一个进程
一次只跑一个任务
工具同步调用
状态存在内存里
失败就重来
```

生产阶段要考虑：

```text
多工单并发
工具调用限流
任务队列
状态持久化
分布式 Worker
缓存
超时重试
熔断降级
多租户 / 多团队隔离
```

在你的运维智能体里，可扩展可以这样设计：

```text
Agent Run 状态持久化到 DB
长任务丢到 Queue
Worker 异步执行工具调用
Redis 做缓存和分布式锁
Tool Runtime 做限流和熔断
工具注册表支持动态新增工具
不同团队通过 tenant/team/service 做权限隔离
```

比如以后新增 Redis、MQ、ES、CDN 工具，不应该改主流程，而是注册新工具：

```json
{
  "name": "redis.get_slowlog",
  "capabilities": ["slow_command", "latency"],
  "resourceType": "redis",
  "riskLevel": "low"
}
```

Planner 和 Tool Router 就可以按能力选择它。

所以，**可扩展 = 架构能支持更多任务、更多工具、更多团队、更多并发，而不是靠单机硬跑**。

面试表达：

> 可扩展不是简单加机器，而是 Agent 架构本身要支持扩展。比如工具通过 Tool Registry 动态注册，任务通过队列和 Worker 异步执行，运行状态持久化，工具调用有超时、重试、限流和熔断。这样后续新增 Redis、MQ、CDN、ES 等数据源时，不需要重写主链路，只需要新增工具 Adapter 和元数据。

---

# 5. 可审计：出了问题能追溯和复盘

**可审计**解决的是：

> Agent 查了什么？谁批准的？有没有越权？为什么执行这个动作？出了问题谁负责？

运维 Agent 接生产环境，审计非常重要。

审计要记录：

```text
关联哪个工单
哪个用户触发
哪个 Agent 节点触发
调用了哪个工具
为什么调用
调用了哪个资源
参数是什么
是否脱敏
权限决策是什么
是否需要审批
谁审批的
执行结果是什么
是否成功
耗时多久
是否重试
返回了哪些证据
最终 RCA 如何生成
```

比如：

```json
{
  "incidentId": "INC-001",
  "runId": "run-001",
  "stepId": "tool-003",
  "toolName": "k8s.rollout_restart",
  "operator": "zhangsan",
  "resource": "prod/order/order-service",
  "riskLevel": "high",
  "permissionDecision": "REQUIRE_APPROVAL",
  "approver": "sre-lead",
  "reason": "Pod CrashLoopBackOff，建议重启服务恢复",
  "result": "success",
  "createdAt": "2026-05-14T09:30:00+08:00"
}
```

审计和可观测有区别：

```text
可观测：主要给研发排查系统问题
可审计：主要给安全、合规、复盘、责任追踪
```

可观测关注：

```text
为什么慢？
哪里错？
哪一步失败？
```

可审计关注：

```text
谁做的？
为什么做？
有没有权限？
有没有审批？
有没有证据？
能不能追责？
```

所以，**可审计 = 所有关键操作都有记录、有依据、有审批、有追溯链路**。

面试表达：

> 可审计是生产级运维 Agent 的安全底线。每次工具调用、审批、执行和验证都要关联工单、用户、Agent 节点、资源、风险等级和执行结果。尤其是高风险动作，比如重启服务、扩缩容、修改负载均衡配置，必须记录审批人、审批理由、证据链和回滚方案，保证后续 RCA 和安全追责有据可查。

---

# 这 5 个词之间的关系

你可以这样理解：

```text
可评测：衡量 Agent 效果
可观测：看清 Agent 过程
可复用：沉淀 Agent 能力
可扩展：支撑 Agent 规模化
可审计：保证 Agent 安全合规
```

更像一套生产级 Agent 的五个维度：

| 维度 | 解决的问题 | 运维智能体里的体现 |
|---|---|---|
| 可评测 | 效果有没有变好 | 离线评测集、根因命中率、计划覆盖率 |
| 可观测 | 过程能不能看清 | Trace、节点日志、工具调用链路 |
| 可复用 | 能力能不能迁移 | Tool Schema、EvidenceRecord、RCA 模板 |
| 可扩展 | 规模上来能不能跑 | Queue、Worker、Redis、动态工具注册 |
| 可审计 | 出事能不能追责 | 审批记录、工具审计、证据链、RCA |

---

# 最适合你面试的一段话

你可以直接背这个：

> 我理解生产级 Agent 不能只看能不能跑通 Demo，而要看五个能力。第一是可评测，能通过离线 case、根因命中率、工具选择准确率等指标判断每次迭代有没有变好；第二是可观测，能追踪每个节点、每次 LLM 调用和每次工具调用，定位问题发生在哪一环；第三是可复用，把工单、工具、证据、RCA 都标准化，避免为单个场景硬编码；第四是可扩展，通过 Tool Registry、队列、Worker、状态持久化和限流熔断支撑更多工具和更多并发；第五是可审计，所有生产环境工具调用、审批、执行和验证都要关联工单、用户、证据和风险等级，保证可追溯、可复盘和可追责。  
>
> 所以我判断一个 Agent 是否生产可用，不是看它回答得像不像，而是看它是否具备评测、观测、复用、扩展和审计这五类工程化能力。

一句话版：

> **可评测看效果，可观测看过程，可复用看沉淀，可扩展看规模，可审计看安全。**

## Prompt:
2026/5/14 10:36:24

我们一个个来，先讲`可评测`

## Response:
2026/5/14 10:36:32

可以。先讲 **可评测**。

一句话理解：

> **可评测 = 我能用一套固定 Case 和指标，判断这个 Agent 这次改动到底有没有变好。**

不是“感觉它回答得还行”，而是可以回答这些问题：

```text
根因判断准不准？
排查计划有没有漏查？
工具选得对不对？
风险等级有没有误判？
处置建议能不能执行？
这次改 Prompt / Planner / 工具后，是提升还是退化？
```

---

# 1. 为什么 Agent 一定要“可评测”？

传统系统好评测：

```text
接口返回 200 就通过
单测通过就通过
E2E 流程走通就通过
```

但 Agent 不一样。它的输出不是固定的，可能每次都不完全一样。

比如同一个工单：

```text
订单服务 500 增多，用户无法下单。
```

Agent 可能有几种表现：

```text
A：只查了日志，结论是代码异常
B：查了 ALB、K8s、MySQL，结论是 MySQL 连接池耗尽
C：查了 K8s 后直接建议重启
D：误判成 OSS 问题
```

如果没有评测，你只能凭感觉说：

> B 好像更靠谱。

但生产级 Agent 需要能量化：

```text
B 的根因命中
B 的排查覆盖完整
B 的工具调用合理
C 的动作风险过高
D 是误判
```

所以，**可评测的核心价值是把 Agent 迭代从“主观感觉”变成“指标驱动”。**

---

# 2. 运维智能体要评测什么？

不要只评最终答案。运维 Agent 要按链路评测。

你的 OpsPilot 链路大概是：

```text
工单接入
→ 工单结构化
→ 自动分诊
→ 排查计划
→ 工具选择
→ 证据采集
→ 根因诊断
→ 处置建议
→ 风险审批
→ 执行验证
→ RCA
```

所以可评测要拆成 8 类指标。

---

## 2.1 工单结构化准确率

看 Agent 有没有从工单里抽对字段。

输入：

```text
订单服务从 14:20 开始 500 增多，用户无法下单，生产环境，P1。
```

期望抽取：

```json
{
  "service": "order-service",
  "env": "prod",
  "severity": "P1",
  "symptom": "http_5xx",
  "timeRange": "14:20-now",
  "impact": "用户无法下单"
}
```

评测指标：

```text
service 抽取准确率
env 抽取准确率
severity 抽取准确率
symptom 分类准确率
timeRange 抽取准确率
```

这一步如果错了，后面全错。

比如把 `order-service` 抽成 `payment-service`，后面工具查得再多也没用。

---

## 2.2 自动分诊准确率

看 Agent 有没有判断对故障类型。

常见故障类型：

```text
http_5xx
timeout
pod_crash
mysql_slow_query
mysql_connection_exhausted
alb_backend_unhealthy
oss_403
oss_404
deployment_regression
```

例如：

```json
{
  "input": "订单接口 500 增多，ALB 告警 5xx rate high",
  "expectedIncidentType": "http_5xx"
}
```

评测指标：

```text
故障类型准确率
P0/P1/P2 风险等级准确率
是否误判为无关类型
```

---

## 2.3 排查计划覆盖率

这是非常关键的指标。

比如一个 `http_5xx` 故障，合理排查计划应该覆盖：

```text
ALB 指标
ALB 后端健康检查
K8s Pod 状态
应用日志
MySQL 连接 / 慢查询
最近发布记录
```

如果 Agent 只查日志，说明计划不完整。

可以这样评：

```json
{
  "caseId": "order_5xx_001",
  "expectedEvidenceCategories": [
    "alb_metrics",
    "alb_backend_health",
    "k8s_pod_status",
    "app_logs",
    "mysql_connection",
    "deployment_record"
  ],
  "actualEvidenceCategories": [
    "app_logs",
    "mysql_connection"
  ]
}
```

覆盖率：

```text
actual 命中 expected 的数量 / expected 总数
= 2 / 6 = 33%
```

面试里这个点很加分：

> 我们不是只评最终回答，而是评排查计划有没有覆盖关键证据源，避免 Agent 只查一个方向就过早下结论。

---

## 2.4 工具选择准确率

排查计划说“查数据库连接情况”，Agent 是否选对工具？

例如：

```text
证据需求：MySQL 连接数
正确工具：mysql.get_connection_stats
错误工具：k8s.get_pod_logs
```

评测指标：

```text
工具选择准确率
无效工具调用率
重复工具调用率
高风险工具误调用率
```

例子：

```json
{
  "planStep": "判断数据库连接池是否耗尽",
  "expectedTools": [
    "mysql.get_connection_stats",
    "mysql.get_processlist"
  ],
  "actualTools": [
    "mysql.get_slow_queries",
    "k8s.get_pod_logs"
  ]
}
```

这里 `mysql.get_slow_queries` 有一定相关性，但不是最优；`k8s.get_pod_logs` 对这个步骤就偏离了。

---

## 2.5 证据质量评分

工具返回了很多信息，Agent 有没有抓住关键证据？

比如工具返回：

```json
{
  "mysql_connections": 198,
  "max_connections": 200,
  "slow_queries": 28,
  "lock_waits": 6
}
```

Agent 应该总结：

```text
MySQL 连接数接近上限，存在连接池耗尽风险。
```

而不是只说：

```text
数据库存在异常。
```

证据质量可以评：

```text
是否引用关键指标
是否引用时间窗口
是否区分事实和猜测
是否遗漏关键异常
是否产生无根据推断
```

---

## 2.6 根因命中率

这是最核心指标。

分两类：

```text
Top1 根因命中率
Top3 根因命中率
```

比如标准答案是：

```text
MySQL 连接池耗尽导致 order-service 请求超时，最终引发 ALB 5xx 升高。
```

Agent 输出：

```text
候选根因：
1. MySQL 连接池耗尽
2. order-service 线程阻塞
3. ALB 后端实例不健康
```

这就是：

```text
Top1 命中：是
Top3 命中：是
```

如果 Agent 输出：

```text
候选根因：
1. K8s Pod OOM
2. 最近发布代码异常
3. ALB 配置错误
```

那就是：

```text
Top1 未命中
Top3 未命中
```

根因评测要注意：  
运维故障经常不是单一根因，而是链式根因。

所以建议评两个层次：

```text
直接原因：ALB 5xx 升高 / Pod 不健康
深层原因：MySQL 连接池耗尽 / 慢 SQL / 发布变更
```

---

## 2.7 处置建议可执行率

Agent 不能只说：

```text
建议优化数据库。
```

这太虚。

好的处置建议应该是：

```text
1. 临时扩容 order-service 副本数，从 4 扩到 8
2. 限流非核心下单请求
3. 排查慢 SQL：SELECT xxx
4. 回滚 14:10 发布版本
5. 观察 ALB 5xx 是否在 10 分钟内下降
```

评测指标：

```text
是否具体
是否有执行步骤
是否有风险说明
是否有回滚方案
是否有验证方式
是否需要审批判断正确
```

尤其是高风险动作：

```text
重启服务
回滚版本
扩缩容
kill MySQL session
修改 ALB 后端
修改 OSS 权限
```

Agent 必须知道：

```text
这类动作不能自动执行，要走人工审批。
```

---

## 2.8 RCA 质量评分

RCA 不是一句“数据库问题”。

结构化 RCA 应该包含：

```text
故障背景
影响范围
时间线
证据链
根因判断
处置过程
验证结果
后续改进
```

RCA 评测指标：

```text
时间线是否完整
证据是否引用充分
根因是否明确
处置过程是否可追溯
改进建议是否具体
是否区分事实和推测
```

---

# 3. 可评测的三层体系

你可以把评测分成三层。

---

## 第一层：节点级评测

单独评某一个节点。

例如只评 `triage`：

```text
输入：工单文本
输出：故障类型、服务、等级
评测：是否抽取正确
```

只评 `planner`：

```text
输入：IncidentContext
输出：排查计划
评测：是否覆盖必要证据源
```

只评 `tool_router`：

```text
输入：PlanStep
输出：工具列表
评测：是否选对工具
```

优点：

```text
定位问题快
适合开发调试
```

---

## 第二层：链路级评测

评一整条链路：

```text
工单 → 分诊 → 排查计划 → 工具调用 → 诊断 → RCA
```

看最终结果：

```text
根因是否命中
工具调用是否合理
排查步骤是否过多
耗时是否可接受
```

优点：

```text
更接近真实使用
```

---

## 第三层：在线评测

系统真实上线后，看真实业务指标：

```text
人工接管率
平均定位耗时
平均恢复耗时
用户采纳率
误诊率
高风险动作拦截率
RCA 人工通过率
```

比如：

```text
人工串行排障平均 40 分钟
Agent 辅助后平均 25 分钟
定位耗时下降 37.5%
```

这类指标最适合写进简历和面试。

---

# 4. 最小可落地方案：先做离线评测集

你现在项目最应该先补的是 **离线评测集**。

不用一开始做很复杂，先做 10～20 个典型故障 Case。

目录可以这样设计：

```text
eval/
  cases/
    order_5xx_mysql_connection.json
    payment_timeout_downstream.json
    user_service_pod_crash.json
    oss_403_policy_changed.json
    alb_backend_unhealthy.json

  fixtures/
    order_5xx_mysql_connection/
      alb_metrics.json
      k8s_pods.json
      mysql_connections.json
      app_logs.json

  expected/
    order_5xx_mysql_connection.expected.json

  run_eval.py
  eval_report.json
```

每个 case 包含：

```json
{
  "caseId": "order_5xx_mysql_connection",
  "ticket": {
    "title": "订单接口 500 增多",
    "description": "14:20 开始用户无法下单，order-service 5xx 升高",
    "severity": "P1",
    "env": "prod"
  },
  "expected": {
    "incidentType": "http_5xx",
    "service": "order-service",
    "expectedEvidenceCategories": [
      "alb_metrics",
      "k8s_pod_status",
      "mysql_connection",
      "app_logs"
    ],
    "rootCause": "mysql_connection_exhausted",
    "riskLevel": "P1",
    "requiredApproval": true
  }
}
```

工具返回不要真实调生产系统，而是用 fixture 固定住：

```json
{
  "tool": "mysql.get_connection_stats",
  "result": {
    "currentConnections": 198,
    "maxConnections": 200,
    "status": "critical"
  }
}
```

这样每次评测结果可复现。

---

# 5. Eval Report 应该长什么样？

跑完之后生成报告：

```json
{
  "summary": {
    "totalCases": 20,
    "rootCauseTop1Accuracy": 0.7,
    "rootCauseTop3Accuracy": 0.85,
    "triageAccuracy": 0.9,
    "planCoverageAvg": 0.78,
    "toolSelectionAccuracy": 0.82,
    "riskLevelAccuracy": 0.9,
    "avgSteps": 6.4,
    "avgLatencyMs": 18500
  },
  "failedCases": [
    {
      "caseId": "oss_403_policy_changed",
      "expectedRootCause": "oss_bucket_policy_changed",
      "actualRootCause": "cdn_cache_issue",
      "failureReason": "Planner 未调用 oss.check_policy"
    }
  ]
}
```

这份报告的价值很大。

你就能说：

```text
这次改了 Planner 之后：
排查计划覆盖率从 65% 提升到 78%
根因 Top1 命中率从 60% 提升到 70%
但 OSS 类故障仍然薄弱
```

这就是真正的 Agent 迭代。

---

# 6. 可评测对应你项目里的改造点

你现在项目可以补 5 个东西：

## 1）Case 数据集

沉淀典型故障：

```text
订单 5xx
支付超时
Pod CrashLoopBackOff
MySQL 慢查询
MySQL 连接池耗尽
ALB 后端不健康
OSS 403
OSS 404
发布回归
CPU / 内存打满
```

---

## 2）固定工具返回 Fixture

不要真实调工具，先用 mock 数据固定每个 case 的证据。

这样可以稳定评：

```text
同一输入
同一证据
不同 Agent 版本
输出是否变好
```

---

## 3）评测 Runner

一键执行：

```bash
python eval/run_eval.py --case-dir eval/cases --output eval/report.json
```

它做的事：

```text
读取 case
注入 mock tool fixture
跑完整 Agent graph
收集输出
和 expected 对比
生成报告
```

---

## 4）指标计算器

至少先做这几个：

```text
triage_accuracy
plan_coverage
tool_selection_accuracy
root_cause_top1_accuracy
root_cause_top3_accuracy
risk_level_accuracy
avg_steps
avg_latency
```

---

## 5）Bad Case 输出

每次评测失败，要能输出：

```text
失败 case
期望结果
实际结果
失败节点
可能原因
建议修复方向
```

例如：

```json
{
  "caseId": "alb_backend_unhealthy",
  "failedNode": "planner",
  "expected": "should call alb.get_backend_health",
  "actual": "only called k8s.get_pod_status",
  "suggestion": "补充 http_5xx 场景下 ALB backend health 必查规则"
}
```

这就能形成 Bad Case 迭代闭环。

---

# 7. 面试怎么讲“可评测”

你可以这样讲：

> 我理解 Agent 的可评测，不是简单看它能不能回答，而是要能持续判断每次迭代有没有变好。对于运维智能体，我会把评测拆成节点级和链路级两层。节点级评测包括工单结构化准确率、分诊准确率、排查计划覆盖率、工具选择准确率；链路级评测包括根因 Top1/Top3 命中率、风险等级准确率、处置建议可执行率和 RCA 质量评分。  
>
> 具体落地上，我会基于历史故障和模拟工单构建离线评测集，每个 case 包含工单输入、期望故障类型、期望证据源、期望根因、风险等级和工具 fixture。每次修改 Prompt、Planner、Tool Router 或 RAG 策略后，自动跑一遍 eval，输出根因命中率、计划覆盖率、工具选择准确率等指标，并记录失败 case，形成 Bad Case 迭代闭环。  
>
> 这样 Agent 的优化就不是凭感觉，而是可以用数据证明：这次改动让哪些场景变好了，哪些场景退化了，下一轮应该针对哪些 Bad Case 优化。

---

# 8. 一句话版

> **可评测就是给 Agent 建一套“考试系统”：用固定工单、固定工具返回、标准答案和指标体系，持续评估它的分诊、规划、工具调用、根因判断、风险控制和 RCA 输出是否真的变好。**

## Prompt:
2026/5/14 11:20:49

现在讲 可观测

## Response:
2026/5/14 11:20:52

继续讲 **可观测**。

一句话理解：

> **可观测 = Agent 每一步做了什么、为什么这么做、哪里失败了、耗时多少、用了哪些证据，都能被看见、回放和定位。**

如果说 **可评测** 解决的是：

```text
Agent 有没有变好？
```

那 **可观测** 解决的是：

```text
Agent 这次为什么这么判断？
Agent 到底在哪一步出错？
```

---

# 1. 为什么 Agent 必须可观测？

传统系统出问题，你可以看：

```text
接口日志
错误堆栈
数据库慢查询
链路 Trace
服务指标
```

但 Agent 系统更复杂，因为它不是固定代码逻辑，而是：

```text
LLM 推理
Planner 规划
工具调用
证据采集
状态流转
人工审批
结果生成
```

所以如果没有可观测，Agent 一旦出错，你很难判断问题来自哪里。

比如用户说：

```text
订单服务 500 增多，帮我排查。
```

Agent 最后误判成：

```text
根因是 K8s Pod OOM。
```

但真实原因是：

```text
MySQL 连接池耗尽。
```

没有可观测，你只能说：

```text
模型误判了。
```

有可观测，你可以继续追：

```text
是工单抽取错了吗？
是 Planner 没有规划 MySQL 排查吗？
是 Tool Router 没选 MySQL 工具吗？
是 MySQL 工具调用失败了吗？
是证据返回了但 Diagnosis 没用上吗？
是 RAG 召回了错误历史案例吗？
是 Prompt 让模型过早下结论了吗？
```

所以，可观测的价值是：

> **把 Agent 从黑盒变成可追踪的工作流系统。**

---

# 2. 运维智能体要观测什么？

你的 OpsPilot 这类运维 Agent，至少要观测 6 层。

```text
Run 层：一次完整任务
Node 层：每个工作流节点
LLM 层：每次模型调用
Tool 层：每次工具调用
Evidence 层：证据如何产生和使用
Human 层：审批和人工介入
```

---

# 3. 第一层：Run 层观测

Run 就是一次完整的 Agent 执行任务。

比如：

```text
run_id = run_20260514_001
incident_id = INC-001
```

Run 层要看：

```text
这次任务当前跑到哪一步？
是否完成？
是否失败？
失败在哪个节点？
总耗时多少？
调用了多少次 LLM？
调用了多少个工具？
有没有进入人工审批？
最终根因是什么？
```

一个 Run Summary 可以长这样：

```json
{
  "runId": "run_20260514_001",
  "incidentId": "INC-001",
  "status": "completed",
  "currentNode": "rca",
  "startedAt": "2026-05-14T10:20:00+08:00",
  "endedAt": "2026-05-14T10:27:35+08:00",
  "durationMs": 455000,
  "llmCalls": 6,
  "toolCalls": 9,
  "approvalRequired": true,
  "approvalStatus": "approved",
  "finalRootCause": "mysql_connection_exhausted",
  "riskLevel": "P1"
}
```

这个东西适合放在前端 RunDetail 页面顶部。

它回答的是：

> 这次 Agent 任务整体发生了什么？

---

# 4. 第二层：Node 层观测

Agent 不是一步完成的，而是多个节点流转。

比如你的运维智能体链路可以拆成：

```text
intake
triage
retrieve_memory
planner
evidence_fanout
evidence_aggregate
diagnose
critic
remediation
risk_gate
approval
executor
verify
rca
```

每个节点都要记录：

```text
节点名称
输入是什么
输出是什么
开始时间
结束时间
耗时
状态
错误信息
下一个节点
```

例如 `planner` 节点：

```json
{
  "node": "planner",
  "status": "success",
  "input": {
    "service": "order-service",
    "symptom": "http_5xx",
    "env": "prod"
  },
  "output": {
    "planSteps": [
      "check_alb_5xx",
      "check_k8s_pods",
      "check_mysql_connections",
      "check_deployment_record"
    ]
  },
  "durationMs": 1830,
  "nextNode": "evidence_fanout"
}
```

这个东西非常关键。

因为如果诊断错了，你能看出来：

```text
Planner 有没有生成 MySQL 排查步骤？
如果没有，问题在 Planner。
如果有，但工具没执行，问题在 Tool Router / Tool Runtime。
如果执行了但诊断没用，问题在 Diagnosis。
```

---

# 5. 第三层：LLM 层观测

每次调用大模型，都要记录基本信息。

包括：

```text
模型名称
Prompt 版本
输入摘要
输出摘要
Token 消耗
耗时
是否重试
是否解析失败
是否触发 JSON 修复
```

不要把所有 Prompt 明文暴露给所有人，但内部系统至少要能回放。

比如：

```json
{
  "llmCallId": "llm_001",
  "node": "triage",
  "model": "gpt-4.1",
  "promptVersion": "triage_v3",
  "inputSummary": "order-service 5xx incident ticket",
  "outputSummary": {
    "incidentType": "http_5xx",
    "severity": "P1",
    "service": "order-service"
  },
  "inputTokens": 1850,
  "outputTokens": 420,
  "latencyMs": 2450,
  "status": "success"
}
```

这层主要解决几个问题：

```text
为什么 token 成本突然升高？
为什么某个节点输出 JSON 解析失败？
Prompt 改版后有没有变差？
模型是否频繁重试？
哪个节点最耗时？
```

面试时可以强调：

> Agent 可观测不能只看工具日志，还要看每次 LLM 调用的 Prompt 版本、输入输出、耗时、Token 和解析状态，否则无法定位是模型问题还是工具问题。

---

# 6. 第四层：Tool 层观测

Tool 层是运维 Agent 最重要的观测点之一。

每次工具调用要记录：

```text
tool_name
调用原因
关联 plan_step
入参摘要
目标资源
开始时间
结束时间
耗时
是否成功
是否重试
错误类型
返回摘要
```

例如：

```json
{
  "toolCallId": "tool_003",
  "runId": "run_20260514_001",
  "stepId": "step_check_mysql_connection",
  "toolName": "mysql.get_connection_stats",
  "reason": "判断 order-service 500 是否由数据库连接耗尽导致",
  "params": {
    "database": "order_db",
    "timeRangeMinutes": 30
  },
  "status": "success",
  "durationMs": 820,
  "retryCount": 0,
  "resultSummary": {
    "currentConnections": 198,
    "maxConnections": 200,
    "status": "critical"
  }
}
```

如果工具失败，也要记录：

```json
{
  "toolName": "k8s.get_pod_logs",
  "status": "failed",
  "errorType": "TIMEOUT",
  "retryCount": 2,
  "durationMs": 10000,
  "fallback": "k8s.get_events"
}
```

这能回答：

```text
哪个工具最慢？
哪个工具失败率最高？
Agent 是否调用了不必要的工具？
工具失败后有没有降级？
某次诊断缺证据是不是因为工具失败？
```

---

# 7. 第五层：Evidence 层观测

这是运维 Agent 和普通 Agent 最大的区别之一。

运维诊断必须讲证据链。

你要能看到：

```text
每条证据来自哪个工具？
证据采集时间是什么？
证据支持哪个根因？
证据有没有冲突？
哪些证据被 Diagnosis 使用了？
哪些证据被忽略了？
```

比如一条证据：

```json
{
  "evidenceId": "ev_mysql_001",
  "sourceTool": "mysql.get_connection_stats",
  "resource": "order_db",
  "timeRange": "14:20-14:50",
  "finding": "MySQL 连接数达到 198/200",
  "severity": "critical",
  "supports": ["mysql_connection_exhausted"],
  "collectedAt": "2026-05-14T14:50:00+08:00"
}
```

最终诊断应该能反查：

```json
{
  "rootCause": "mysql_connection_exhausted",
  "supportingEvidence": [
    "ev_mysql_001",
    "ev_mysql_002",
    "ev_alb_001"
  ],
  "contradictingEvidence": [
    "ev_k8s_001"
  ],
  "confidence": 0.86
}
```

这比单纯输出“我认为是 MySQL 问题”强很多。

面试里你可以说：

> 对运维 Agent 来说，可观测不仅是看调用日志，还要能看到证据链。每个根因候选都应该能追溯到具体 evidence id，知道它被哪些证据支持、有没有反证、置信度怎么来的。

---

# 8. 第六层：Human 层观测

生产运维 Agent 一定有人类介入。

所以要观测：

```text
什么时候进入审批？
为什么需要审批？
审批卡片展示了什么证据？
谁审批的？
审批结果是什么？
审批耗时多久？
用户有没有修改 Agent 建议？
有没有人工接管？
```

例如：

```json
{
  "approvalId": "approval_001",
  "runId": "run_20260514_001",
  "action": "k8s.rollout_restart",
  "riskLevel": "high",
  "reason": "Pod CrashLoopBackOff，Agent 建议重启服务",
  "evidence": [
    "ev_k8s_001",
    "ev_alb_001"
  ],
  "approver": "sre_oncall",
  "decision": "approved",
  "approvedAt": "2026-05-14T10:31:00+08:00"
}
```

这层既属于可观测，也属于可审计。

区别是：

```text
可观测关心：为什么进入审批、审批卡在哪一步卡住
可审计关心：谁审批、是否合规、出了事能不能追责
```

---

# 9. 最小可落地方案：先做事件流 Event Log

可观测不要一上来做很复杂。

最小可落地就是：**每个节点都往 event_log 写事件**。

事件类型可以设计成：

```text
run.started
node.started
node.completed
node.failed
llm.started
llm.completed
tool.started
tool.completed
tool.failed
evidence.created
approval.required
approval.completed
run.completed
```

事件结构：

```json
{
  "eventId": "evt_001",
  "runId": "run_001",
  "incidentId": "INC-001",
  "type": "tool.completed",
  "node": "evidence_fanout",
  "timestamp": "2026-05-14T10:21:30+08:00",
  "payload": {
    "toolName": "mysql.get_connection_stats",
    "durationMs": 820,
    "status": "success",
    "summary": "连接数达到 198/200"
  }
}
```

这样你前端可以根据 event_log 渲染：

```text
时间线
节点状态
工具调用记录
证据列表
审批记录
错误详情
```

这就已经是一个比较完整的可观测雏形。

---

# 10. 前端页面应该怎么看？

你的 RunDetail 页面可以分成 5 个区域：

```text
1. Run 概览
- 状态
- 当前节点
- 总耗时
- 工具调用次数
- LLM 调用次数
- 是否需要审批

2. Workflow 时间线
- intake 成功
- triage 成功
- planner 成功
- evidence_fanout 进行中
- diagnose 完成
- approval 等待中

3. Tool Calls
- 调用了哪些工具
- 每个工具耗时
- 成功 / 失败
- 重试次数
- 返回摘要

4. Evidence Board
- 关键证据
- 来源工具
- 支持哪个根因
- 采集时间

5. Diagnosis / RCA
- 候选根因
- 支持证据
- 处置建议
- 验证结果
- RCA 输出
```

这样用户不是只看到一个最终答案，而是能看到 Agent 的整个处理过程。

---

# 11. 可观测的核心指标

除了日志和 Trace，还要有指标。

常见指标：

```text
Run 成功率
Run 平均耗时
节点平均耗时
LLM 调用次数
LLM Token 消耗
工具调用成功率
工具平均耗时
工具重试率
审批等待时间
人工接管率
节点失败率
RCA 生成成功率
```

比如：

```text
planner 平均耗时：2.3s
evidence_fanout 平均耗时：8.6s
mysql 工具成功率：98%
k8s 日志工具超时率：12%
平均每个 Run 调用工具：7.4 次
平均每个 Run 消耗 token：9,800
```

这些指标能帮助你做优化：

```text
如果 evidence_fanout 太慢 → 工具并发 / 超时 / 缓存优化
如果 k8s 日志工具超时率高 → 限制日志行数 / 先查 events
如果 token 成本高 → 压缩上下文 / 减少无效证据
如果人工接管率高 → 分析是计划不准还是处置建议不可信
```

---

# 12. 可观测和可评测的区别

这两个容易混。

```text
可评测：结果维度
可观测：过程维度
```

举例：

```text
可评测问：
这次根因有没有命中？
这个版本比上个版本有没有提升？

可观测问：
为什么这次根因没命中？
到底是哪一步错了？
```

再简单点：

```text
可评测 = 考试分数
可观测 = 答题过程和草稿纸
```

没有可评测，你不知道 Agent 好不好。  
没有可观测，你知道它错了，但不知道为什么错。

---

# 13. 你项目里怎么补可观测？

按优先级来：

## P0：统一 Event Log

先把所有节点、工具、LLM、审批都写成事件。

```text
run_events 表
```

字段：

```text
id
run_id
incident_id
event_type
node_name
status
payload_json
created_at
duration_ms
error_message
```

---

## P0：RunDetail 时间线

前端先把 event log 展示出来。

最小也要能看到：

```text
节点流转
工具调用
错误信息
证据摘要
审批状态
```

---

## P1：Tool Call 观测

单独建：

```text
tool_calls 表
```

记录：

```text
tool_name
params_masked
resource
duration_ms
status
retry_count
result_summary
error_type
```

这和 Tool Runtime 很搭。

---

## P1：Evidence 观测

单独建：

```text
evidence_records 表
```

记录：

```text
evidence_id
source_tool
resource
finding
severity
supports_root_cause
collected_at
```

后面 RCA 可以直接引用这些 evidence。

---

## P2：接 LangSmith / Langfuse

如果你后面想更专业，可以接 Agent Trace 工具。

重点看：

```text
每个节点输入输出
每次 LLM prompt
tool call trace
token 成本
latency
错误重试
```

不过面试时不要说必须依赖某个平台。

你可以说：

> 底层先沉淀标准事件和 Trace 数据，外部可以对接 LangSmith、Langfuse 或公司内部可观测平台。

---

# 14. 面试表达版

你可以这样讲：

> 我理解 Agent 的可观测，是要把一次智能体任务从黑盒变成可回放的执行链路。对于运维智能体来说，不仅要看最终诊断结果，还要记录每个节点的输入输出、每次 LLM 调用、每次工具调用、证据生成过程、审批过程和最终 RCA。  
>
> 比如一次订单服务 500 的排查，我希望能在 RunDetail 里看到：intake 抽取了什么服务和故障类型，planner 生成了哪些排查步骤，Tool Runtime 调用了哪些工具，每个工具耗时和结果摘要是什么，哪些 Evidence 支持最终根因，是否进入人工审批，以及最终验证是否通过。  
>
> 这样做的价值是，一旦 Agent 误判，我们可以定位问题到底出在工单抽取、排查计划、工具调用、证据聚合还是根因诊断，而不是简单归因于模型幻觉。可观测能力也是后续做评测、Bad Case 分析、性能优化和安全审计的基础。

---

# 15. 一句话版

> **可观测就是给 Agent 装上“行车记录仪”：每个节点、每次模型调用、每次工具调用、每条证据、每次审批都能被记录、查看和回放，从而知道它为什么这么判断、哪里失败、怎么优化。**

## Prompt:
2026/5/14 11:34:57

上面`可观测`的实现有什么技术点

## Response:
2026/5/14 11:35:05

> **Providing conceptual answer on observability implementation**
>
> User is asking about a project’s implementation details, and I’ll offer a concise, technical breakdown in Chinese. I’ll cover observability implementation with points like event models, trace context, instrumentation, storage schema, real-time streaming, runtime metrics, lineage, LLM observability, and security/masking. “落代码” and “你项目” examples might be included. Should be concise but thorough, no need for external sources or repository access.
>
> Thought for 5s

“可观测”的实现不是简单打印日志，而是要把 Agent 的**执行过程结构化记录下来**。对你的运维智能体来说，核心技术点可以拆成 10 个。

---

# 1. 全链路 Trace ID 设计

第一步要给每次 Agent 执行生成统一 ID。

```text
incident_id：工单 ID
run_id：一次 Agent 运行 ID
node_id：工作流节点 ID
tool_call_id：工具调用 ID
llm_call_id：模型调用 ID
evidence_id：证据 ID
approval_id：审批 ID
```

这几个 ID 要贯穿整个链路。

比如：

```json
{
  "incident_id": "INC-001",
  "run_id": "run_001",
  "node_id": "planner",
  "tool_call_id": "tool_003",
  "evidence_id": "ev_mysql_001"
}
```

这样你才能把一次故障排查的所有节点、工具、证据、审批串起来。

技术重点：

```text
统一上下文对象 RunContext
所有节点函数都传入 run_id
所有工具调用都绑定 step_id / run_id
所有日志都带 trace_id
```

---

# 2. Event Log 事件流模型

可观测最基础的技术实现是 **事件流**。

Agent 每发生一个关键动作，就写一条事件。

事件类型可以是：

```text
run.started
run.completed
node.started
node.completed
node.failed
llm.started
llm.completed
llm.failed
tool.started
tool.completed
tool.failed
evidence.created
approval.required
approval.completed
```

事件结构：

```ts
type RunEvent = {
  id: string
  runId: string
  incidentId: string
  eventType: string
  nodeName?: string
  status: "running" | "success" | "failed" | "skipped"
  payload: Record<string, any>
  durationMs?: number
  errorMessage?: string
  createdAt: string
}
```

后端每个节点执行时写事件：

```python
await event_bus.emit({
    "run_id": run_id,
    "event_type": "node.started",
    "node_name": "planner",
    "payload": {
        "input_summary": "order-service http_5xx incident"
    }
})
```

节点完成后再写：

```python
await event_bus.emit({
    "run_id": run_id,
    "event_type": "node.completed",
    "node_name": "planner",
    "duration_ms": 1830,
    "payload": {
        "plan_steps": [
            "check_alb_metrics",
            "check_k8s_pods",
            "check_mysql_connections"
        ]
    }
})
```

技术重点：

```text
事件要结构化
事件要可持久化
事件要能实时推送到前端
事件要能按 run_id 回放
```

---

# 3. 工作流节点埋点

你的运维 Agent 一般有这些节点：

```text
intake
triage
retrieve_memory
planner
evidence_fanout
evidence_aggregate
diagnose
critic
remediation
risk_gate
approval
executor
verify
rca
```

每个节点都要做统一埋点。

可以做一个装饰器：

```python
def observable_node(node_name: str):
    def decorator(fn):
        async def wrapper(state, *args, **kwargs):
            run_id = state["run_id"]
            start = time.time()

            await emit_event(
                run_id=run_id,
                event_type="node.started",
                node_name=node_name,
                payload={"input": summarize_input(state)}
            )

            try:
                result = await fn(state, *args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)

                await emit_event(
                    run_id=run_id,
                    event_type="node.completed",
                    node_name=node_name,
                    duration_ms=duration_ms,
                    payload={"output": summarize_output(result)}
                )
                return result

            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)

                await emit_event(
                    run_id=run_id,
                    event_type="node.failed",
                    node_name=node_name,
                    duration_ms=duration_ms,
                    error_message=str(e)
                )
                raise

        return wrapper
    return decorator
```

然后每个节点这样用：

```python
@observable_node("planner")
async def planner_node(state):
    ...
```

这样所有节点都有统一观测能力，不需要每个节点手写日志。

技术重点：

```text
节点开始记录
节点结束记录
节点失败记录
节点耗时记录
节点输入输出摘要记录
```

---

# 4. LLM 调用观测

Agent 项目里，LLM 调用必须单独观测。

每次模型调用要记录：

```text
model
prompt_version
input_tokens
output_tokens
latency_ms
temperature
是否 JSON 解析成功
是否重试
输出摘要
错误信息
```

结构可以这样：

```ts
type LLMCallRecord = {
  id: string
  runId: string
  nodeName: string
  model: string
  promptVersion: string
  inputTokens: number
  outputTokens: number
  latencyMs: number
  status: "success" | "failed"
  inputSummary: string
  outputSummary: string
  rawPromptRef?: string
  rawResponseRef?: string
  errorMessage?: string
}
```

注意：不要把完整 Prompt、完整业务数据、完整日志都直接明文存数据库。可以做两层：

```text
普通表：存摘要、token、耗时、状态
对象存储 / 调试环境：存完整 prompt/response，按权限查看
```

技术重点：

```text
Prompt 版本化
Token 统计
JSON parse 失败记录
模型重试记录
LLM 调用成本统计
```

这能回答：

```text
哪个节点最耗 token？
哪个 prompt 版本效果变差？
哪个模型调用最慢？
JSON 输出失败率是多少？
```

---

# 5. Tool Runtime 观测

Tool Runtime 是可观测的重点。

每次工具调用都要记录：

```text
tool_name
adapter_mode：mock / real
调用原因
关联 plan_step
参数摘要
目标资源
权限决策
风险等级
开始时间
结束时间
耗时
重试次数
是否成功
错误类型
返回摘要
```

结构可以这样：

```ts
type ToolCallRecord = {
  id: string
  runId: string
  incidentId: string
  stepId: string
  toolName: string
  adapterMode: "mock" | "real"
  reason: string
  resource: {
    service?: string
    cluster?: string
    namespace?: string
    database?: string
    alb?: string
    bucket?: string
  }
  paramsMasked: Record<string, any>
  riskLevel: "low" | "medium" | "high"
  permissionDecision: "allow" | "deny" | "require_approval"
  status: "success" | "failed" | "timeout"
  durationMs: number
  retryCount: number
  resultSummary?: Record<string, any>
  errorType?: string
  errorMessage?: string
}
```

比如：

```json
{
  "toolName": "mysql.get_connection_stats",
  "resource": {
    "database": "order_db"
  },
  "status": "success",
  "durationMs": 820,
  "retryCount": 0,
  "resultSummary": {
    "currentConnections": 198,
    "maxConnections": 200,
    "status": "critical"
  }
}
```

技术重点：

```text
工具调用前记录 tool.started
工具调用后记录 tool.completed / tool.failed
记录 timeout / retry / fallback
记录 permission decision
记录 result summary，而不是完整敏感结果
```

---

# 6. Evidence 证据链观测

运维 Agent 的诊断不能只看最终结论，必须能追溯证据。

每条证据要有自己的 `evidence_id`。

```ts
type EvidenceRecord = {
  id: string
  runId: string
  sourceToolCallId: string
  sourceToolName: string
  resourceType: "mysql" | "k8s" | "alb" | "oss" | "log" | "metric"
  resourceId: string
  timeRange: {
    start: string
    end: string
  }
  status: "normal" | "warning" | "critical" | "unknown"
  finding: string
  keyMetrics: Record<string, any>
  supports: string[]
  contradicts: string[]
  confidence: number
  createdAt: string
}
```

例子：

```json
{
  "id": "ev_mysql_001",
  "sourceToolName": "mysql.get_connection_stats",
  "resourceType": "mysql",
  "resourceId": "order_db",
  "status": "critical",
  "finding": "MySQL 当前连接数 198/200，接近上限",
  "supports": ["mysql_connection_exhausted"],
  "confidence": 0.91
}
```

最终诊断也要引用证据：

```json
{
  "rootCause": "mysql_connection_exhausted",
  "supportingEvidenceIds": [
    "ev_mysql_001",
    "ev_alb_001",
    "ev_log_002"
  ],
  "contradictingEvidenceIds": [
    "ev_k8s_001"
  ],
  "confidence": 0.86
}
```

技术重点：

```text
工具结果标准化成 EvidenceRecord
Diagnosis 必须引用 evidence_id
RCA 必须引用 evidence_id
支持证据和反证分开记录
```

这会让你的项目从“模型生成结论”升级成“基于证据链的诊断系统”。

---

# 7. 状态快照与 Checkpoint

Agent 工作流可能中断，比如：

```text
等待审批
工具超时
节点失败
服务重启
用户刷新页面
```

所以要保存状态快照。

每个关键节点结束后保存：

```ts
type RunCheckpoint = {
  runId: string
  currentNode: string
  status: "running" | "paused" | "failed" | "completed"
  stateSnapshot: Record<string, any>
  createdAt: string
}
```

比如执行到审批节点：

```json
{
  "runId": "run_001",
  "currentNode": "approval",
  "status": "paused",
  "stateSnapshot": {
    "incidentContext": {},
    "plan": [],
    "evidence": [],
    "diagnosis": {},
    "remediationPlan": {}
  }
}
```

技术重点：

```text
每个节点结束保存 checkpoint
审批中断时保存 paused 状态
用户审批后从 checkpoint resume
失败后支持 replay / retry
```

这既是可观测，也是可恢复。

---

# 8. SSE / WebSocket 实时推送

可观测不只是后端存日志，前端也要实时看到 Agent 在做什么。

实现方式：

```text
简单场景：SSE
复杂双向交互：WebSocket
```

你的 Agent 这种“后端持续执行，前端看进度”的场景，SSE 就够用。

后端：

```python
async def stream_run_events(run_id: str):
    async for event in event_bus.subscribe(run_id):
        yield f"data: {json.dumps(event)}\n\n"
```

前端：

```ts
const eventSource = new EventSource(`/api/runs/${runId}/events`)

eventSource.onmessage = (event) => {
  const runEvent = JSON.parse(event.data)
  updateTimeline(runEvent)
}
```

前端可以实时展示：

```text
正在分诊
正在生成排查计划
正在查询 ALB 指标
正在查询 MySQL 连接
已生成根因假设
等待人工审批
正在验证结果
RCA 已生成
```

技术重点：

```text
后端事件流
前端订阅 run_id
断线重连
根据 last_event_id 补历史事件
事件持久化，刷新页面不丢状态
```

---

# 9. 指标 Metrics 聚合

Event Log 是明细，Metrics 是聚合。

你要从事件里统计指标：

```text
Run 成功率
Run 平均耗时
节点平均耗时
工具调用成功率
工具超时率
工具重试率
LLM 平均 token
LLM 平均耗时
审批平均等待时间
人工接管率
RCA 生成成功率
```

例如：

```text
planner.avg_latency_ms = 1830
mysql_tool.success_rate = 98%
k8s_logs.timeout_rate = 12%
avg_tool_calls_per_run = 7.4
avg_tokens_per_run = 9800
```

技术实现：

```text
简单版：从 PostgreSQL/MySQL 定时 SQL 聚合
中级版：Prometheus 指标暴露
高级版：OpenTelemetry + Grafana
```

例如暴露 Prometheus 指标：

```python
tool_call_counter.labels(tool_name="mysql.get_connection_stats", status="success").inc()
tool_latency_histogram.labels(tool_name="mysql.get_connection_stats").observe(duration)
llm_token_counter.labels(node="planner", model="gpt-4.1").inc(tokens)
```

技术重点：

```text
明细事件用于回放
聚合指标用于看趋势
错误率、延迟、成本必须可视化
```

---

# 10. 脱敏与权限控制

可观测不是把所有东西都裸露出来。

运维数据很敏感：

```text
数据库查询结果
用户手机号
Token / Cookie
公网 IP
内部域名
OSS object key
日志里的个人信息
```

所以观测数据必须脱敏。

常见做法：

```text
params_masked：参数脱敏后存
result_summary：只存结果摘要
raw_result_ref：原始结果另存，并做权限控制
secret pattern scanner：过滤 token/password/cookie
```

例如：

```json
{
  "paramsMasked": {
    "database": "order_db",
    "sql": "SELECT count(*) FROM orders WHERE user_phone = ***"
  }
}
```

而不是：

```json
{
  "sql": "SELECT * FROM users WHERE phone = '13266847690'"
}
```

技术重点：

```text
观测数据分级
敏感字段脱敏
原始日志限制访问
审计查看行为
生产环境默认不落完整敏感原文
```

---

# 11. 推荐的数据表设计

最小可以有 5 张表。

```text
agent_runs
run_events
llm_calls
tool_calls
evidence_records
```

### agent_runs

记录一次任务整体状态。

```sql
CREATE TABLE agent_runs (
  id VARCHAR(64) PRIMARY KEY,
  incident_id VARCHAR(64),
  status VARCHAR(32),
  current_node VARCHAR(64),
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  duration_ms BIGINT,
  final_root_cause TEXT,
  risk_level VARCHAR(32)
);
```

### run_events

记录事件流。

```sql
CREATE TABLE run_events (
  id VARCHAR(64) PRIMARY KEY,
  run_id VARCHAR(64),
  event_type VARCHAR(64),
  node_name VARCHAR(64),
  status VARCHAR(32),
  payload_json JSON,
  duration_ms BIGINT,
  error_message TEXT,
  created_at TIMESTAMP
);
```

### tool_calls

记录工具调用。

```sql
CREATE TABLE tool_calls (
  id VARCHAR(64) PRIMARY KEY,
  run_id VARCHAR(64),
  incident_id VARCHAR(64),
  step_id VARCHAR(64),
  tool_name VARCHAR(128),
  adapter_mode VARCHAR(32),
  resource_json JSON,
  params_masked JSON,
  risk_level VARCHAR(32),
  permission_decision VARCHAR(32),
  status VARCHAR(32),
  duration_ms BIGINT,
  retry_count INT,
  result_summary JSON,
  error_type VARCHAR(64),
  error_message TEXT,
  created_at TIMESTAMP
);
```

### llm_calls

记录模型调用。

```sql
CREATE TABLE llm_calls (
  id VARCHAR(64) PRIMARY KEY,
  run_id VARCHAR(64),
  node_name VARCHAR(64),
  model VARCHAR(64),
  prompt_version VARCHAR(64),
  input_tokens INT,
  output_tokens INT,
  latency_ms BIGINT,
  status VARCHAR(32),
  input_summary TEXT,
  output_summary TEXT,
  error_message TEXT,
  created_at TIMESTAMP
);
```

### evidence_records

记录证据链。

```sql
CREATE TABLE evidence_records (
  id VARCHAR(64) PRIMARY KEY,
  run_id VARCHAR(64),
  source_tool_call_id VARCHAR(64),
  source_tool_name VARCHAR(128),
  resource_type VARCHAR(64),
  resource_id VARCHAR(128),
  status VARCHAR(32),
  finding TEXT,
  key_metrics JSON,
  supports JSON,
  contradicts JSON,
  confidence FLOAT,
  created_at TIMESTAMP
);
```

---

# 12. 面试表达版

你可以这样说：

> 可观测的落地不是简单打日志，而是要把 Agent 的执行过程结构化。技术上我会先设计统一的 run_id、node_id、tool_call_id、llm_call_id 和 evidence_id，把一次故障排查的工单、节点、工具、证据、审批和 RCA 串起来。  
>
> 然后通过 Event Log 记录每个关键事件，比如 node.started、tool.completed、llm.failed、evidence.created、approval.required。每个工作流节点用统一装饰器埋点，记录输入摘要、输出摘要、耗时和错误。LLM 调用层记录模型、Prompt 版本、Token、耗时和解析状态；Tool Runtime 层记录工具名、参数摘要、目标资源、权限决策、风险等级、重试次数和返回摘要。  
>
> 对运维 Agent 来说，还要重点做 Evidence 证据链观测，每条证据都要有 evidence_id，能反查它来自哪个工具、支持哪个根因、有没有反证。前端通过 SSE 或 WebSocket 订阅 run events，实时展示工作流时间线、工具调用、证据看板和审批状态。最后再基于这些事件聚合出成功率、节点耗时、工具失败率、Token 成本、人工接管率等指标。  
>
> 这样一旦 Agent 误判，我们可以定位问题到底出在工单抽取、Planner、工具选择、工具调用、证据聚合还是根因诊断，而不是笼统地说模型幻觉。

---

# 13. 一句话版

> **可观测的技术核心是：统一 Trace ID + 结构化 Event Log + 节点埋点 + LLM/Tool 调用记录 + Evidence 证据链 + SSE 实时推送 + 指标聚合 + 脱敏权限控制。**

## Prompt:
2026/5/14 11:42:32

现在讲“可复用”

## Response:
2026/5/14 11:42:39

继续讲 **可复用**。

一句话理解：

> **可复用 = 这个 Agent 的能力不是为某一个故障、某一个服务、某一个工具写死，而是可以迁移到更多故障类型、更多业务线、更多数据源。**

比如你现在做的是运维智能体，不能只支持：

```text
order-service 500 排查
```

而应该能扩展到：

```text
支付接口超时
K8s Pod CrashLoopBackOff
MySQL 慢查询
ALB 后端不健康
OSS 上传失败
Redis 连接异常
MQ 消息堆积
发布回归
```

这就是“可复用”。

---

# 1. 为什么 Agent 要做可复用？

很多 Agent Demo 是这样的：

```text
用户问订单服务 500
→ Prompt 里写死查 order-service
→ 工具写死查某个 namespace
→ RCA 模板写死订单业务
→ 只能处理一个案例
```

这种能演示，但不可复用。

生产级 Agent 应该是：

```text
同一套流程
+ 不同工单输入
+ 不同服务拓扑
+ 不同工具组合
+ 不同故障类型模板
= 处理不同场景
```

换句话说，可复用的本质是：

> **把一次具体故障处理，拆成通用能力模块，而不是写死成单次脚本。**

---

# 2. 运维智能体里，哪些东西应该复用？

至少有 7 层。

```text
1. 工单结构复用
2. 工作流节点复用
3. 排查计划模板复用
4. 工具协议复用
5. 证据结构复用
6. 审批与风险控制复用
7. RCA 模板与知识沉淀复用
```

一个个说。

---

# 3. 第一层：工单结构复用

不同故障的原始描述可能完全不同。

比如：

```text
订单接口 500 增多
支付接口超时
图片上传失败
库存服务 Pod 重启
数据库慢查询告警
```

但它们都可以被抽象成统一的 `IncidentContext`。

```ts
type IncidentContext = {
  incidentId: string
  title: string
  source: "manual" | "alert" | "chatops"
  service: string
  environment: "prod" | "staging" | "test"
  severity: "P0" | "P1" | "P2" | "P3"
  symptomType: string
  timeRange: {
    start: string
    end: string
  }
  impact: {
    businessImpact?: string
    affectedApi?: string
    affectedRegion?: string
  }
  resources: {
    k8s?: {
      cluster: string
      namespace: string
      workload: string
    }
    mysql?: {
      database: string
    }
    alb?: {
      instanceId: string
    }
    oss?: {
      bucket: string
    }
  }
}
```

这样不管是 500、超时、OSS 403、Pod 重启，Planner 都可以消费同一种输入。

这就是第一种复用：

> **把不同来源、不同格式、不同表达的工单，统一成标准 IncidentContext。**

---

# 4. 第二层：工作流节点复用

你的运维智能体主链路不应该为每个故障单独写一条流程。

应该统一成：

```text
intake
→ triage
→ retrieve_memory
→ planner
→ evidence_fanout
→ evidence_aggregate
→ diagnose
→ critic
→ remediation
→ risk_gate
→ approval
→ executor
→ verify
→ rca
```

这个流程可以复用到多类故障。

比如订单 500：

```text
intake：抽取 order-service、http_5xx
triage：分类为接口 5xx
planner：规划查 ALB、K8s、MySQL、日志
diagnose：判断 MySQL 连接池耗尽
remediation：建议扩容、限流、优化 SQL
```

OSS 403：

```text
intake：抽取 oss_access_error、bucket、objectKey
triage：分类为 OSS 权限问题
planner：规划查 OSS ACL、Bucket Policy、访问日志、CDN 回源
diagnose：判断 Bucket Policy 被误改
remediation：建议恢复权限策略
```

两者故障不同，但主流程不变。

所以可复用的关键是：

> **流程节点固定，节点内部根据故障类型和资源上下文动态决策。**

---

# 5. 第三层：排查计划模板复用

不同故障类型应该沉淀不同的排查模板。

例如：

## HTTP 5xx 模板

```text
1. 查 ALB 5xx 指标
2. 查 ALB 后端健康检查
3. 查 K8s Pod 状态
4. 查应用错误日志
5. 查 MySQL 连接数 / 慢查询
6. 查最近发布记录
```

## 接口超时模板

```text
1. 查接口 RT 和超时比例
2. 查 K8s CPU / 内存
3. 查线程池 / 连接池
4. 查 MySQL 慢查询
5. 查下游服务耗时
6. 查最近流量突增
```

## OSS 403 模板

```text
1. 查对象是否存在
2. 查 Bucket Policy
3. 查 ACL 配置
4. 查临时签名 URL 是否过期
5. 查访问日志中的 403
6. 查 CDN / 回源配置
```

这些模板不是最终死流程，而是 Planner 的参考。

结构化可以这样：

```json
{
  "incidentType": "http_5xx",
  "requiredEvidenceCategories": [
    "alb_metrics",
    "alb_backend_health",
    "k8s_pod_status",
    "app_logs",
    "mysql_connection",
    "deployment_record"
  ],
  "optionalEvidenceCategories": [
    "oss_access",
    "downstream_service"
  ]
}
```

这样新来一个 `http_5xx` 工单，Planner 不用从零思考，而是复用这个模板，再结合具体服务拓扑裁剪。

---

# 6. 第四层：工具协议复用

这是最关键的一层。

不要为每个系统写一套特殊调用逻辑，而是把 MySQL、K8s、ALB、OSS 都封装成标准工具协议。

统一结构：

```ts
type ToolDefinition = {
  name: string
  domain: "mysql" | "k8s" | "alb" | "oss" | "redis" | "mq"
  description: string
  capabilities: string[]
  inputSchema: object
  outputSchema: object
  riskLevel: "low" | "medium" | "high"
  requiresApproval: boolean
  timeoutMs: number
  retryPolicy: object
}
```

例如 MySQL 工具：

```json
{
  "name": "mysql.get_connection_stats",
  "domain": "mysql",
  "capabilities": ["connection_stats", "connection_exhausted"],
  "riskLevel": "low",
  "requiresApproval": false
}
```

K8s 工具：

```json
{
  "name": "k8s.get_pod_status",
  "domain": "k8s",
  "capabilities": ["pod_status", "restart_count", "crash_loop", "oom_killed"],
  "riskLevel": "low",
  "requiresApproval": false
}
```

后续如果要新增 Redis，只需要注册：

```json
{
  "name": "redis.get_slowlog",
  "domain": "redis",
  "capabilities": ["slow_command", "latency", "blocked_client"],
  "riskLevel": "low",
  "requiresApproval": false
}
```

主流程不用改。

Tool Router 根据 `capabilities` 选择工具。

这就是工具层的复用：

> **新增数据源时，不改 Agent 主流程，只新增 Tool Adapter + Tool Metadata。**

---

# 7. 第五层：证据结构复用

不同工具返回的数据完全不同。

MySQL 返回：

```text
连接数、慢 SQL、锁等待
```

K8s 返回：

```text
Pod 状态、重启次数、Events
```

ALB 返回：

```text
5xx、QPS、RT、后端健康状态
```

OSS 返回：

```text
对象是否存在、403/404、Bucket Policy
```

如果每种数据都直接扔给模型，模型会很混乱。

所以要统一成 `EvidenceRecord`。

```ts
type EvidenceRecord = {
  id: string
  sourceTool: string
  resourceType: string
  resourceId: string
  timeRange: {
    start: string
    end: string
  }
  status: "normal" | "warning" | "critical" | "unknown"
  finding: string
  keyMetrics: Record<string, any>
  supports: string[]
  contradicts: string[]
  confidence: number
}
```

例如 MySQL 证据：

```json
{
  "id": "ev_mysql_001",
  "sourceTool": "mysql.get_connection_stats",
  "resourceType": "mysql",
  "resourceId": "order_db",
  "status": "critical",
  "finding": "MySQL 连接数达到 198/200，接近上限",
  "supports": ["mysql_connection_exhausted"],
  "confidence": 0.91
}
```

K8s 证据：

```json
{
  "id": "ev_k8s_001",
  "sourceTool": "k8s.get_pod_status",
  "resourceType": "k8s",
  "resourceId": "prod/order/order-service",
  "status": "normal",
  "finding": "Pod 无重启，无 OOMKilled",
  "contradicts": ["pod_crash", "oom_killed"],
  "confidence": 0.82
}
```

这样 Diagnosis 不需要关心原始工具格式，只消费标准 Evidence。

这就是证据层复用：

> **不同工具结果统一转 EvidenceRecord，诊断节点就能复用同一套推理逻辑。**

---

# 8. 第六层：审批与风险控制复用

运维 Agent 不能每个动作都单独写审批逻辑。

应该统一成：

```ts
type RiskPolicy = {
  action: string
  environment: string
  riskLevel: "low" | "medium" | "high" | "critical"
  requiresApproval: boolean
  approvers: string[]
  rollbackRequired: boolean
}
```

比如：

```text
查日志：低风险，不审批
查 MySQL 慢查询：低风险，不审批
重启服务：高风险，审批
回滚发布：高风险，审批
修改 ALB 后端：高风险，审批
删除 OSS 对象：禁止
```

这样以后新增 Redis 工具，也可以复用同一套风控逻辑：

```text
redis.get_slowlog：低风险
redis.flushall：禁止
redis.restart：高风险，审批
```

这就是风险控制复用：

> **所有工具动作统一走 RiskPolicy，不在每个工具里手写一套审批规则。**

---

# 9. 第七层：RCA 模板复用

RCA 不能每次让模型自由发挥。

应该统一模板：

```ts
type RCAArtifact = {
  incidentSummary: string
  impactScope: string
  timeline: TimelineItem[]
  rootCause: string
  supportingEvidence: string[]
  remediationActions: string[]
  verificationResult: string
  followUpActions: string[]
  owner: string
}
```

不管是 MySQL 故障、K8s 故障、OSS 故障，最终都按这个结构输出。

例如：

```text
故障背景
影响范围
时间线
根因判断
证据链
处置过程
验证结果
后续改进
```

这样 RCA 可以：

```text
统一展示
统一归档
统一检索
统一写入知识库
统一用于下次 RAG
```

这就是 RCA 层复用：

> **每次故障复盘都沉淀成同一种知识资产，后续类似故障可以被检索和复用。**

---

# 10. 可复用的本质：从 Case 编程变成能力编程

不可复用的写法是：

```text
如果 order-service 500，就查 order namespace；
如果 payment-service 超时，就查 payment namespace；
如果 OSS 403，就查某个 bucket；
```

这种会越写越乱。

可复用的写法是：

```text
工单 → IncidentContext
服务名 → CMDB 资源映射
故障类型 → 排查模板
证据需求 → Tool Router
工具结果 → EvidenceRecord
高危动作 → RiskPolicy
复盘结果 → RCAArtifact
```

也就是：

```text
不是为每个故障写死逻辑
而是为每类能力定义标准协议
```

---

# 11. 怎么判断你的 Agent 是否可复用？

可以问 6 个问题：

```text
1. 新增一种故障类型，需要改主流程吗？
2. 新增一个工具，比如 Redis / MQ / ES，需要改 Planner 吗？
3. 换一个业务服务，比如从订单到支付，流程还能跑吗？
4. 换一个云厂商，比如从阿里云到华为云，工具协议还能复用吗？
5. RCA 能不能沉淀成下次可检索的知识？
6. 流程、工具、证据、审批是否都是标准结构？
```

如果答案是：

```text
大部分只需要新增配置、模板或 Adapter
```

那就说明可复用做得不错。

如果答案是：

```text
每次新增场景都要改大量 prompt 和代码
```

那就说明还不够可复用。

---

# 12. 你这个项目怎么补“可复用”？

按优先级来。

## P0：统一几个核心数据结构

先把这些结构固定下来：

```text
IncidentContext
PlanStep
ToolDefinition
ToolCallRequest
ToolCallResult
EvidenceRecord
RiskDecision
ApprovalCard
RCAArtifact
```

这几个是复用基础。

---

## P0：Tool Registry 做成配置化

不要把工具能力散落在代码里。

统一工具注册表：

```json
{
  "tools": [
    {
      "name": "mysql.get_connection_stats",
      "domain": "mysql",
      "capabilities": ["connection_stats"],
      "inputSchema": {},
      "riskLevel": "low"
    },
    {
      "name": "k8s.get_pod_status",
      "domain": "k8s",
      "capabilities": ["pod_status", "restart_count"],
      "inputSchema": {},
      "riskLevel": "low"
    }
  ]
}
```

后面新增 OSS / Redis / MQ，不动主流程，只注册工具。

---

## P1：故障类型模板库

建立：

```text
incident_templates/
  http_5xx.json
  timeout.json
  pod_crash.json
  mysql_slow_query.json
  oss_403.json
  deployment_regression.json
```

每个模板定义：

```text
必查证据
可选证据
常见根因
风险动作
推荐工具类型
```

这样 Planner 可以复用模板。

---

## P1：CMDB / 服务目录抽象

不要写死：

```text
order-service → prod-shenzhen-01 / order namespace
```

而是通过服务目录查：

```text
service + env → cluster / namespace / workload / alb / mysql / oss
```

这样换业务服务也能跑。

---

## P1：Evidence Normalizer

为每个工具写一个 normalizer：

```text
MySQL result → EvidenceRecord
K8s result → EvidenceRecord
ALB result → EvidenceRecord
OSS result → EvidenceRecord
```

Diagnosis 只吃 EvidenceRecord。

---

## P2：Runbook / RCA 知识库

把每次复盘变成可检索资产。

```text
历史 RCA
排障 SOP
服务 Runbook
常见故障模板
```

下次同类故障，Planner 和 Diagnosis 可以复用历史经验。

---

# 13. 面试表达版

你可以这样讲：

> 我理解 Agent 的可复用，不是把一个 Demo 改改就能处理另一个场景，而是要把整个故障处理过程抽象成标准能力。对于运维智能体，我会把工单统一成 IncidentContext，把排查步骤统一成 PlanStep，把工具统一成 ToolDefinition，把工具返回统一成 EvidenceRecord，把高风险动作统一走 RiskPolicy，把复盘统一成 RCAArtifact。  
>
> 这样新增故障类型时，不需要重写主流程，只需要补充故障模板；新增数据源时，不需要重写 Agent，只需要新增 Tool Adapter 和 Tool Metadata；新增业务服务时，通过 CMDB 做资源映射即可。比如从订单服务 500 扩展到 OSS 403，主流程仍然是工单抽取、分诊、规划、证据采集、诊断、审批、验证和 RCA，只是排查模板和工具组合不同。  
>
> 所以可复用的关键是从“针对某个 case 写逻辑”，升级为“围绕工单、工具、证据、风险和复盘建立标准协议”。这样 Agent 才能从单点排障工具，演进成可以覆盖多服务、多故障类型、多数据源的运维智能体平台。

---

# 14. 一句话版

> **可复用就是把一次故障处理抽象成标准对象和标准流程：工单统一、计划统一、工具统一、证据统一、审批统一、RCA 统一；新增场景靠配置、模板和 Adapter 扩展，而不是重写 Agent。**

## Prompt:
2026/5/14 14:08:56

现在讲可扩展

## Response:
2026/5/14 14:08:58

继续讲 **可扩展**。

一句话理解：

> **可扩展 = 当工单变多、服务变多、工具变多、团队变多、并发变高时，这个 Agent 系统不用推倒重来，仍然能稳定运行和持续接入新能力。**

如果说 **可复用** 关注的是：

```text
一套能力能不能迁移到更多场景？
```

那么 **可扩展** 关注的是：

```text
规模上来以后，系统还能不能撑住？
```

---

# 1. 为什么 Agent 要做可扩展？

很多 Agent Demo 是这样跑的：

```text
一个用户提交一个工单
后端同步执行一整条链路
工具调用串行执行
状态存在内存里
刷新页面就丢状态
服务重启任务就失败
所有工具写死在代码里
```

这在 Demo 阶段没问题。

但一旦进入真实运维场景，会遇到：

```text
同时来了 100 个告警
一个工单要跑 10 个工具
某些工具接口很慢
有些工单要等人工审批
有些任务要暂停后恢复
不同团队只能看自己的服务
新增 Redis / MQ / CDN / ES 等工具
不同环境 prod / staging / test 权限不同
```

如果架构不可扩展，系统很快就会变成：

```text
任务阻塞
工具超时
状态丢失
重复执行
无法恢复
无法新增工具
无法支撑多团队使用
```

所以，可扩展的核心不是“机器配置更高”，而是：

> **Agent 架构本身要支持更多任务、更多工具、更多数据源、更多团队和更高并发。**

---

# 2. 运维智能体的可扩展主要看 8 层

```text
1. 任务执行可扩展
2. 工具接入可扩展
3. 工作流节点可扩展
4. 状态存储可扩展
5. 并发与队列可扩展
6. 多租户 / 多团队可扩展
7. 数据源与云厂商可扩展
8. 成本与性能可扩展
```

---

# 3. 第一层：任务执行可扩展

Demo 阶段可以同步跑：

```text
POST /run
后端直接执行完整 Agent
执行完再返回结果
```

但生产场景不能这样。

因为一次运维排查可能要：

```text
调用多个工具
等待慢查询结果
等待日志查询
等待审批
执行验证
生成 RCA
```

这可能持续几十秒、几分钟，甚至更久。

更合理的结构是：

```text
用户提交工单
   ↓
创建 Run 记录
   ↓
返回 run_id
   ↓
后台 Worker 异步执行 Agent
   ↓
前端通过 SSE / WebSocket 看进度
   ↓
任务完成后写入结果
```

也就是：

```text
请求线程只负责创建任务
后台 Worker 负责执行任务
前端订阅任务状态
```

这样才支持更多并发。

---

## 技术实现

可以拆成：

```text
API Server：接收请求、创建 run、查询状态
Queue：存放待执行任务
Worker：消费任务，执行 Agent Workflow
DB：保存 run 状态、checkpoint、事件日志
SSE Server：推送执行进度
```

架构大概是：

```text
Frontend
   ↓
API Server
   ↓
Queue / Redis / MQ
   ↓
Agent Worker
   ↓
Tool Runtime
   ↓
MySQL / K8s / ALB / OSS
```

这就是任务执行层的可扩展。

---

# 4. 第二层：工具接入可扩展

工具不能写死在 Planner 里。

不可扩展的写法：

```python
if incident_type == "mysql":
    call_mysql_tool()
elif incident_type == "k8s":
    call_k8s_tool()
elif incident_type == "oss":
    call_oss_tool()
```

这种写法后面新增 Redis、MQ、ES、CDN，会越来越乱。

可扩展的写法是：

```text
所有工具统一注册到 Tool Registry
Planner 只输出证据需求
Tool Router 根据能力选择工具
Tool Runtime 统一执行
```

工具注册表：

```json
{
  "name": "redis.get_slowlog",
  "domain": "redis",
  "capabilities": ["slow_command", "latency", "blocked_client"],
  "inputSchema": {},
  "riskLevel": "low",
  "requiresApproval": false,
  "timeoutMs": 5000
}
```

新增工具时，只需要新增：

```text
Tool Metadata
Tool Adapter
Evidence Normalizer
权限策略
测试 fixture
```

不用改主流程。

所以工具扩展的关键是：

> **新增工具靠注册，不靠改 Agent 主链路。**

---

# 5. 第三层：工作流节点可扩展

你的运维智能体现在可能有这些节点：

```text
intake
triage
planner
evidence_fanout
diagnose
remediation
risk_gate
approval
executor
verify
rca
```

后面可能要新增：

```text
retrieve_memory：检索历史 RCA / Runbook
critic：诊断自检
cost_guard：成本控制
security_guard：敏感信息检查
postmortem_writer：复盘增强
eval_hook：自动评测采样
```

如果工作流是硬编码的一长串函数，就不好扩展。

更好的方式是用 **状态机 / 图编排**：

```text
Node = 一个能力节点
Edge = 节点之间的流转规则
State = 当前任务状态
Checkpoint = 每一步状态快照
```

这样新增节点时，不需要推翻原流程，只需要插入新的节点。

比如：

```text
diagnose
   ↓
critic
   ↓
remediation
```

或者：

```text
planner
   ↓
retrieve_memory
   ↓
planner_refine
   ↓
evidence_fanout
```

可扩展的工作流应该支持：

```text
新增节点
删除节点
跳过节点
失败重试
条件分支
审批暂停
从 checkpoint 恢复
```

这就是为什么 Agent Workflow 最好做成状态机，而不是一个大函数。

---

# 6. 第四层：状态存储可扩展

不可扩展的方式：

```text
state 存在内存里
audit_log 存在 list 里
审批状态存在变量里
工具结果只存在当前进程里
```

问题是：

```text
服务重启就丢
多 Worker 之间不能共享
用户刷新页面无法恢复
审批后不能继续
失败后无法回放
```

可扩展的方式是：

```text
Run 状态持久化
Checkpoint 持久化
Event Log 持久化
Tool Call 记录持久化
Evidence 持久化
Approval 持久化
RCA 持久化
```

核心表可以是：

```text
agent_runs
run_checkpoints
run_events
tool_calls
evidence_records
approvals
rca_artifacts
```

这样系统才能支持：

```text
任务中断后恢复
多 Worker 执行
审批后继续
前端刷新后继续看进度
历史任务回放
失败任务重试
```

可扩展的 Agent 一定不能依赖内存状态。

---

# 7. 第五层：并发与队列可扩展

真实运维场景里，工单可能同时进来。

比如：

```text
10 个 P2 告警
3 个 P1 故障
1 个 P0 故障
多个团队同时使用
```

如果所有任务都直接并发执行，会出现：

```text
工具接口被打爆
数据库连接打满
K8s API Server 压力过大
LLM 成本飙升
高优任务被低优任务阻塞
```

所以需要队列和优先级。

可以设计：

```text
P0 队列：最高优先级
P1 队列：高优先级
P2/P3 队列：普通优先级
批处理 / RCA 队列：低优先级
```

Worker 消费策略：

```text
P0 优先
同一服务限流
同一工具限流
同一租户限流
失败任务重试
长任务超时中断
```

比如：

```text
mysql.get_slow_queries 每分钟最多 100 次
k8s.get_pod_logs 每个 namespace 并发最多 5 个
LLM diagnose 每个租户并发最多 10 个
```

这就是并发控制。

---

# 8. 第六层：多租户 / 多团队可扩展

如果你的运维智能体只给一个团队用，可以简单做。

但如果给多个业务团队用，就要支持：

```text
团队隔离
服务隔离
权限隔离
工具权限隔离
数据隔离
审计隔离
配置隔离
```

例如：

```text
交易团队只能看 order-service、payment-service
用户团队只能看 user-service
SRE 可以看多个服务
普通研发不能执行高危动作
测试环境权限比生产环境宽
```

所以核心对象里要有：

```text
tenant_id
team_id
service_id
env
user_id
role
```

工具调用前要判断：

```text
这个用户能不能查这个服务？
这个团队能不能访问这个 namespace？
这个 Agent 能不能调用这个工具？
这个动作在 prod 是否需要审批？
```

多团队扩展不是后面再补的东西，最好一开始就留字段。

---

# 9. 第七层：数据源与云厂商可扩展

你现在接的是：

```text
MySQL
K8s
ALB / SLB
OSS
```

后面可能还要接：

```text
Redis
MQ
Elasticsearch
CDN
Prometheus
ARMS
Grafana
CI/CD
配置中心
日志平台
链路追踪
```

如果每个数据源都写一套特殊逻辑，系统会失控。

更好的方式是三层抽象：

```text
ToolDefinition：工具元数据
ToolAdapter：真实系统适配器
EvidenceNormalizer：结果标准化
```

比如从阿里云切到华为云：

```text
ALB 工具能力不变：
- get_traffic_metrics
- get_backend_health

底层 Adapter 替换：
- AliyunAlbAdapter
- HuaweiCloudElbAdapter
```

上层 Agent 不应该关心云厂商差异。

它只关心：

```text
我需要入口层 5xx 指标
我需要后端健康状态
```

这就是数据源扩展能力。

---

# 10. 第八层：成本与性能可扩展

Agent 系统还有一个特殊问题：**LLM 成本和延迟**。

如果每一步都调用大模型，系统会很慢、很贵。

所以可扩展还要考虑：

```text
哪些步骤必须用大模型？
哪些步骤可以用规则？
哪些步骤可以用模板？
哪些结果可以缓存？
哪些工具可以并行？
哪些证据需要压缩？
```

可以设计：

```text
规则优先：简单分类不用 LLM
模板优先：常见故障直接套模板
缓存优先：服务拓扑、工具元数据、Runbook 缓存
并行优先：ALB / K8s / MySQL 只读工具并发执行
压缩优先：工具结果先摘要，再给模型
小模型优先：工单抽取、分类用小模型
大模型兜底：复杂诊断、RCA 用强模型
```

比如：

```text
工单结构化：规则 + 小模型
排查模板选择：规则 + RAG
证据采集：工具并行
根因诊断：大模型
RCA 生成：大模型
```

这样系统才能支撑更多任务。

---

# 11. 可扩展的典型架构

可以这样描述：

```text
Frontend
  - RunDetail
  - Timeline
  - Approval UI
  - Evidence Board

API Server
  - create_run
  - get_run_status
  - approve_action
  - stream_events

Queue / Redis
  - run task queue
  - priority queue
  - distributed lock
  - rate limit

Agent Worker
  - execute workflow
  - save checkpoint
  - emit events

Tool Runtime
  - permission check
  - params validation
  - timeout / retry
  - audit
  - adapter dispatch

Tool Adapters
  - MySQL
  - K8s
  - ALB
  - OSS
  - Redis / MQ / ES later

Storage
  - runs
  - checkpoints
  - events
  - tool_calls
  - evidence
  - approvals
  - rca
```

这个架构的特点：

```text
API 不负责长任务
Worker 可水平扩展
工具可动态注册
状态可恢复
事件可回放
多团队可隔离
```

---

# 12. 一个具体例子：从 1 个工单扩展到 100 个工单

## Demo 方式

```text
100 个工单同时进来
→ API 同步执行 100 个 Agent
→ 每个 Agent 调 10 个工具
→ 1000 次工具调用瞬间打出去
→ K8s / MySQL / LLM 全部压力过大
```

## 可扩展方式

```text
100 个工单进入队列
→ 按 P0/P1/P2 排优先级
→ Worker 池并发消费
→ 同一服务加锁，避免重复排查
→ 同一工具限流
→ 工具调用失败自动重试
→ 状态写入 checkpoint
→ 前端实时看进度
```

例如：

```text
P0：立即执行
P1：高优队列
P2：普通队列
重复 order-service 告警：合并为同一个 incident
低优 RCA 生成：放后台慢慢跑
```

这才是可扩展。

---

# 13. 你项目里可以怎么补“可扩展”

按优先级来。

## P0：Run 状态持久化

先确保每次 Agent run 都有稳定记录：

```text
run_id
incident_id
status
current_node
created_at
updated_at
final_result
```

---

## P0：Checkpoint 持久化

每个关键节点后保存状态：

```text
当前工单上下文
排查计划
已采集证据
候选根因
审批状态
执行结果
```

这样支持：

```text
失败重试
审批恢复
服务重启恢复
用户刷新恢复
```

---

## P1：任务队列 + Worker

把长任务从 API 请求里拆出去：

```text
API 创建任务
Queue 存任务
Worker 执行 Agent
前端订阅事件
```

最小实现可以先用 Redis Queue / Celery / RQ / BullMQ，具体技术栈按你的项目语言选。

---

## P1：Tool Registry 配置化

现在工具如果散落在代码里，后面扩展会难。

应该沉淀：

```text
工具名
能力标签
参数 Schema
风险等级
超时时间
重试策略
Adapter 类型
```

新增工具只新增配置和 Adapter。

---

## P1：工具调用限流

至少要做：

```text
按 tool_name 限流
按 service 限流
按 tenant/team 限流
按 env 限流
```

比如：

```text
prod 环境 k8s logs 每个 namespace 同时最多 3 个
mysql 慢查询工具每分钟最多 20 次
同一服务同一时间只跑一个深度排查任务
```

---

## P2：多团队 / 多租户隔离

提前在数据表和权限模型里留：

```text
tenant_id
team_id
service_id
env
user_id
role
```

否则后面很难补。

---

## P2：缓存层

适合缓存：

```text
CMDB 服务拓扑
工具注册表
服务 owner
Runbook
历史 RCA 检索结果
短时间窗口内重复指标查询
```

这样可以减少重复查询和 LLM 调用。

---

# 14. 可扩展和可复用的区别

这两个容易混。

```text
可复用：能力能不能迁移到别的场景
可扩展：规模变大后能不能稳定承载
```

举例：

```text
可复用：
从 order-service 500 扩展到 OSS 403，不重写主流程。

可扩展：
同时有 100 个故障工单进来，系统不会挂，能排队、限流、恢复、监控。
```

再简单点：

```text
可复用 = 横向复用能力
可扩展 = 纵向支撑规模
```

---

# 15. 面试表达版

你可以这样讲：

> 我理解 Agent 的可扩展，不只是后端多部署几个实例，而是整个架构要支持更多工单、更多工具、更多团队和更高并发。对于运维智能体来说，首先要把长任务从同步 API 中拆出来，采用 Run 记录 + Queue + Worker 的方式异步执行，前端通过 SSE 或 WebSocket 查看进度。  
>
> 其次，Agent 状态不能存在内存里，要把 run、checkpoint、event、tool call、evidence、approval、RCA 都持久化，这样任务失败、服务重启、人工审批后都能继续执行。  
>
> 第三，工具接入要通过 Tool Registry 扩展，新增 Redis、MQ、ES、CDN 等数据源时，只新增 Tool Adapter、Metadata 和 Evidence Normalizer，而不是修改主工作流。  
>
> 第四，要做并发控制和限流，比如按工具、服务、环境、团队限制调用频率，避免大量 Agent 同时打爆 K8s、MySQL、日志平台或 LLM。  
>
> 最后，要支持多团队、多服务、多环境的权限隔离，以及缓存、降级和 Worker 水平扩展。这样这个 Agent 才能从单个 Demo，演进成可支撑真实运维场景的平台型系统。

---

# 16. 一句话版

> **可扩展就是让 Agent 从“单机跑一个 Demo”升级为“可支撑多工单、多工具、多团队、多并发”的平台：任务队列化、Worker 异步化、状态持久化、工具注册化、调用限流化、多租户隔离化。**

## Prompt:
2026/5/14 16:50:15

现在讲 可审计

## Response:
2026/5/14 16:50:18

继续讲 **可审计**。

一句话理解：

> **可审计 = Agent 做过什么、为什么做、谁批准、有没有越权、依据是什么、结果如何，事后都能追溯。**

如果说：

```text
可观测：看清 Agent 的执行过程
可审计：证明 Agent 的行为合规、可追责、可复盘
```

可观测更偏研发排障；可审计更偏生产安全、合规、责任边界。

---

# 1. 为什么运维 Agent 必须可审计？

运维智能体和普通问答 Agent 不一样，它可能接触生产系统：

```text
MySQL
K8s
ALB / SLB
OSS
日志平台
发布系统
配置中心
监控平台
```

一旦 Agent 执行了高风险动作，比如：

```text
重启服务
回滚发布
扩缩容
kill MySQL session
修改 ALB 后端
修改 OSS 权限
清理缓存
```

如果没有审计，出事后就回答不了这些问题：

```text
是谁触发的？
Agent 为什么建议这么做？
用了哪些证据？
有没有经过审批？
审批人是谁？
执行了哪个资源？
执行结果是什么？
有没有回滚方案？
有没有越权访问？
有没有访问敏感数据？
```

所以，**可审计是生产级运维 Agent 的安全底线**。

---

# 2. 可审计到底审什么？

运维 Agent 至少要审 8 类东西：

```text
1. 工单来源
2. Agent 决策过程
3. 工具调用
4. 权限判断
5. 高风险动作审批
6. 执行结果
7. 证据链
8. RCA 复盘产物
```

---

# 3. 第一类：审计工单来源

首先要知道这次任务从哪来。

比如：

```json
{
  "incidentId": "INC-20260514-001",
  "source": "monitoring",
  "createdBy": "alertmanager",
  "title": "order-service 5xx rate high",
  "severity": "P1",
  "env": "prod",
  "createdAt": "2026-05-14T10:20:00+08:00"
}
```

要审计：

```text
工单 ID 是什么？
来源是人工、告警、ChatOps 还是客服反馈？
谁创建的？
影响哪个服务？
生产环境还是测试环境？
严重等级是什么？
```

这个决定后续权限、审批和追责范围。

---

# 4. 第二类：审计 Agent 的决策过程

Agent 每一步关键决策都要能解释。

例如：

```text
为什么判断这是 P1？
为什么判断故障类型是 http_5xx？
为什么排查 MySQL？
为什么没有排查 OSS？
为什么建议重启服务？
```

所以要记录：

```json
{
  "decisionId": "decision_001",
  "runId": "run_001",
  "nodeName": "planner",
  "decisionType": "plan_generation",
  "inputSummary": "order-service 5xx increased after 14:20",
  "outputSummary": "Plan includes ALB, K8s, MySQL, deployment checks",
  "reason": "HTTP 5xx incidents require traffic entry, runtime, database and deployment evidence",
  "createdAt": "2026-05-14T10:21:00+08:00"
}
```

这不是为了保存模型的所有废话，而是为了保存**关键决策依据**。

---

# 5. 第三类：审计工具调用

每次工具调用都要记录。

比如 Agent 调用了：

```text
mysql.get_connection_stats
k8s.get_pod_status
alb.get_backend_health
oss.get_access_errors
```

审计记录应该包含：

```text
谁调用的
哪个 Agent 节点调用的
调用哪个工具
为什么调用
查哪个资源
入参是什么
返回摘要是什么
是否成功
耗时多少
是否重试
有没有脱敏
```

示例：

```json
{
  "auditId": "audit_tool_001",
  "runId": "run_001",
  "incidentId": "INC-001",
  "stepId": "step_mysql_check",
  "toolName": "mysql.get_connection_stats",
  "callerAgent": "diagnosis-agent",
  "operator": "zhangsan",
  "resource": {
    "database": "order_db",
    "env": "prod"
  },
  "reason": "排查 order-service 5xx 是否由 MySQL 连接池耗尽导致",
  "paramsMasked": {
    "database": "order_db",
    "timeRangeMinutes": 30
  },
  "resultSummary": {
    "currentConnections": 198,
    "maxConnections": 200,
    "status": "critical"
  },
  "status": "success",
  "durationMs": 830,
  "retryCount": 0,
  "createdAt": "2026-05-14T10:22:00+08:00"
}
```

注意：审计日志不要裸存敏感数据。要存 `paramsMasked` 和 `resultSummary`，不要存完整原始结果。

---

# 6. 第四类：审计权限判断

生产系统一定要记录权限决策。

比如 Agent 想查 `order_db`，系统要判断：

```text
用户是否有 order-service 权限？
用户是否能访问 prod？
Agent 是否允许调用 MySQL 工具？
这个工具是否只读？
这个数据库是否属于当前服务？
```

审计记录：

```json
{
  "permissionAuditId": "perm_001",
  "runId": "run_001",
  "userId": "zhangsan",
  "role": "oncall",
  "service": "order-service",
  "env": "prod",
  "toolName": "mysql.get_connection_stats",
  "resource": "order_db",
  "decision": "ALLOW",
  "reason": "user is current on-call owner of order-service",
  "createdAt": "2026-05-14T10:22:00+08:00"
}
```

如果拒绝：

```json
{
  "decision": "DENY",
  "reason": "user has no permission to access payment_db in prod"
}
```

这很关键，因为生产审计最关心：

> 有没有越权访问？

---

# 7. 第五类：审计高风险动作审批

这是可审计里最重要的一块。

比如 Agent 建议：

```text
重启 order-service
```

这类动作不能直接执行，必须进入审批。

审批卡片要记录：

```text
动作是什么
作用资源是什么
风险等级是什么
为什么建议执行
支持证据是什么
影响范围是什么
回滚方案是什么
审批人是谁
审批结果是什么
审批时间是什么
```

示例：

```json
{
  "approvalId": "approval_001",
  "runId": "run_001",
  "incidentId": "INC-001",
  "action": "k8s.rollout_restart",
  "resource": "prod/order/order-service",
  "riskLevel": "high",
  "reason": "order-service Pod 出现 CrashLoopBackOff，Agent 建议重启服务恢复",
  "supportingEvidenceIds": [
    "ev_k8s_001",
    "ev_alb_001"
  ],
  "impact": "可能造成短暂请求抖动",
  "rollbackPlan": "如重启后错误率升高，可回滚至上一版本",
  "approver": "sre_lead",
  "decision": "approved",
  "approvedAt": "2026-05-14T10:30:00+08:00"
}
```

这个审计记录的价值是：

```text
证明不是 Agent 私自执行
证明审批人看到了风险和证据
证明动作有明确依据
证明后续可以追责和复盘
```

---

# 8. 第六类：审计执行结果

审批通过后，真正执行动作也要审计。

例如：

```json
{
  "executionAuditId": "exec_001",
  "approvalId": "approval_001",
  "runId": "run_001",
  "toolName": "k8s.rollout_restart",
  "resource": "prod/order/order-service",
  "executor": "tool-runtime",
  "status": "success",
  "startedAt": "2026-05-14T10:31:00+08:00",
  "endedAt": "2026-05-14T10:31:10+08:00",
  "resultSummary": "Deployment order-service restarted successfully",
  "rollbackAvailable": true
}
```

如果执行失败，也要记录：

```json
{
  "status": "failed",
  "errorType": "K8S_API_TIMEOUT",
  "retryCount": 2,
  "fallbackAction": "manual_intervention_required"
}
```

这样才能回答：

> 审批通过后到底有没有执行成功？

---

# 9. 第七类：审计证据链

可审计不是只记录动作，还要记录 Agent 的判断依据。

比如最终结论是：

```text
根因是 MySQL 连接池耗尽。
```

那么必须能反查：

```text
这个结论由哪些证据支持？
哪些证据是反证？
证据来自哪个工具？
证据采集时间是什么？
```

示例：

```json
{
  "diagnosisAuditId": "diag_001",
  "runId": "run_001",
  "rootCause": "mysql_connection_exhausted",
  "confidence": 0.86,
  "supportingEvidenceIds": [
    "ev_mysql_001",
    "ev_mysql_002",
    "ev_alb_001"
  ],
  "contradictingEvidenceIds": [
    "ev_k8s_001"
  ],
  "reasoningSummary": "ALB 5xx 升高与 MySQL 连接数打满处于同一时间窗口，K8s Pod 无明显重启，故优先判断为数据库连接耗尽。"
}
```

这能避免 Agent 给出“无证据结论”。

---

# 10. 第八类：审计 RCA 产物

RCA 是故障复盘的最终产物，也要可审计。

RCA 里应该包含：

```text
故障背景
影响范围
时间线
根因
证据链
处置过程
验证结果
后续改进
确认人
归档时间
```

示例：

```json
{
  "rcaId": "rca_001",
  "incidentId": "INC-001",
  "runId": "run_001",
  "rootCause": "mysql_connection_exhausted",
  "impact": "部分用户下单失败，影响华南区用户",
  "timeline": [
    {
      "time": "14:20",
      "event": "ALB 5xx 开始升高"
    },
    {
      "time": "14:22",
      "event": "MySQL 连接数达到 198/200"
    },
    {
      "time": "14:30",
      "event": "执行服务扩容和连接池调整"
    }
  ],
  "evidenceIds": [
    "ev_alb_001",
    "ev_mysql_001"
  ],
  "verifiedBy": "sre_oncall",
  "confirmedByHuman": true,
  "archivedAt": "2026-05-14T11:00:00+08:00"
}
```

这份 RCA 后续可以写入知识库，成为下一次故障诊断的参考。

---

# 11. 可审计和可观测的区别

这两个很容易混。

## 可观测关注过程

它问的是：

```text
Agent 每一步发生了什么？
哪一步慢？
哪一步失败？
哪个工具超时？
哪个节点输出异常？
```

主要服务对象是：

```text
研发
运维平台工程师
Agent 开发者
```

## 可审计关注责任和合规

它问的是：

```text
谁触发的？
谁审批的？
为什么执行？
有没有权限？
有没有证据？
有没有越权？
结果如何？
能不能追责？
```

主要服务对象是：

```text
SRE 管理者
安全团队
合规团队
故障复盘负责人
业务负责人
```

一句话区分：

> **可观测是为了排查系统为什么错；可审计是为了证明行为为什么合理、谁负责、有没有合规。**

---

# 12. 可审计的技术实现点

核心有 8 个技术点。

## 12.1 审计 ID 体系

所有审计记录要能串起来：

```text
incident_id
run_id
step_id
tool_call_id
evidence_id
approval_id
execution_id
rca_id
user_id
```

这样能从一个工单追到所有行为。

---

## 12.2 审计事件表

可以设计统一表：

```sql
CREATE TABLE audit_events (
  id VARCHAR(64) PRIMARY KEY,
  incident_id VARCHAR(64),
  run_id VARCHAR(64),
  event_type VARCHAR(64),
  actor_type VARCHAR(32),
  actor_id VARCHAR(64),
  action VARCHAR(128),
  resource_type VARCHAR(64),
  resource_id VARCHAR(128),
  risk_level VARCHAR(32),
  permission_decision VARCHAR(32),
  approval_id VARCHAR(64),
  reason TEXT,
  payload_json JSON,
  created_at TIMESTAMP
);
```

常见 `event_type`：

```text
permission.checked
tool.called
tool.blocked
approval.required
approval.approved
approval.rejected
action.executed
action.failed
evidence.created
diagnosis.generated
rca.generated
```

---

## 12.3 参数脱敏

不要把敏感参数直接写入审计日志。

需要做：

```text
Token 脱敏
Cookie 脱敏
手机号脱敏
身份证脱敏
AccessKey 脱敏
SQL 查询结果脱敏
OSS object key 脱敏或分级展示
```

比如：

```json
{
  "paramsMasked": {
    "phone": "132****7690",
    "accessKey": "AKIA****",
    "cookie": "***"
  }
}
```

---

## 12.4 结果摘要化

审计日志里不要保存大段原始日志。

应该保存：

```text
结果摘要
关键指标
状态
异常类型
证据 ID
原始数据引用地址
```

比如：

```json
{
  "resultSummary": {
    "status": "critical",
    "finding": "MySQL 连接数达到 198/200",
    "evidenceId": "ev_mysql_001"
  },
  "rawResultRef": "oss://ops-audit/run_001/tool_003.json"
}
```

原始数据可以放对象存储，但要权限控制。

---

## 12.5 不可篡改或低篡改审计

审计记录不能轻易被修改。

可以做：

```text
append-only 追加写
禁止 update/delete
记录 hash
定期归档
高风险审计单独存储
```

简单版：

```text
audit_events 只插入，不更新
```

增强版：

```text
每条 audit_event 计算 hash
后一条记录 prev_hash
形成 hash chain
```

这样可以防篡改。

---

## 12.6 审批记录和执行记录强绑定

高风险动作必须满足：

```text
没有 approval_id，不允许执行
approval_id 状态不是 approved，不允许执行
审批资源和执行资源必须一致
审批动作和执行动作必须一致
```

比如审批的是：

```text
重启 order-service
```

执行时不能偷偷变成：

```text
重启 payment-service
```

这要由 Tool Runtime 强制校验。

---

## 12.7 权限决策记录

每次工具调用都要记录权限决策：

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

这能证明系统没有越权。

---

## 12.8 审计查询和导出

审计不是存起来就完了，还要能查。

常见查询：

```text
查某个工单的完整审计链
查某个用户执行过哪些生产动作
查某个服务最近有哪些 Agent 操作
查所有高风险动作审批记录
查被拒绝的越权访问
导出 RCA 审计报告
```

---

# 13. Tool Runtime 里怎么落可审计？

Tool Runtime 是可审计最核心的落点。

一次工具调用应该这样：

```text
1. 接收工具调用请求
2. 记录 tool.requested
3. 做权限校验
4. 记录 permission.checked
5. 如果拒绝，记录 tool.blocked
6. 如果需要审批，记录 approval.required
7. 审批通过后，记录 approval.approved
8. 执行工具，记录 action.executed
9. 生成 evidence，记录 evidence.created
10. 返回结果，记录 tool.completed
```

伪代码：

```python
async def execute_tool(request):
    await audit.log("tool.requested", request)

    permission = await permission_checker.check(request)
    await audit.log("permission.checked", {
        "decision": permission.decision,
        "reason": permission.reason
    })

    if permission.decision == "DENY":
        await audit.log("tool.blocked", {
            "reason": permission.reason
        })
        return {"status": "DENIED"}

    if permission.decision == "REQUIRE_APPROVAL":
        approval = await create_approval(request)
        await audit.log("approval.required", {
            "approval_id": approval.id,
            "risk_level": request.risk_level
        })
        return {"status": "PENDING_APPROVAL"}

    result = await adapter.call(request.params)

    evidence = normalize_to_evidence(result)
    await audit.log("evidence.created", {
        "evidence_id": evidence.id,
        "summary": evidence.finding
    })

    await audit.log("tool.completed", {
        "status": "success",
        "result_summary": summarize(result)
    })

    return evidence
```

---

# 14. 一个完整例子：重启服务的审计链

用户工单：

```text
order-service 500 增多，Pod CrashLoopBackOff，建议重启服务。
```

完整审计链应该是：

```text
1. incident.created
   创建 P1 工单，来源为监控告警

2. run.started
   Agent 开始处理工单

3. triage.completed
   判断为 http_5xx + runtime_failure

4. tool.called
   调用 alb.get_traffic_metrics

5. evidence.created
   证据：ALB 5xx 升高

6. tool.called
   调用 k8s.get_pod_status

7. evidence.created
   证据：Pod CrashLoopBackOff

8. diagnosis.generated
   根因候选：Pod 异常导致后端不健康

9. remediation.generated
   建议：rollout restart order-service

10. permission.checked
   生产环境高风险动作，需要审批

11. approval.required
   创建审批卡

12. approval.approved
   SRE 负责人审批通过

13. action.executed
   执行 k8s.rollout_restart

14. verify.completed
   验证 ALB 5xx 下降，Pod 恢复正常

15. rca.generated
   生成 RCA 并归档
```

有了这条链，出了问题可以完整回放。

---

# 15. 你项目里可审计应该怎么补

按优先级：

## P0：ToolGateway 审计增强

你现在如果已有基础 audit_log，下一步要补：

```text
incident_id
step_id
user_id
risk_level
permission_decision
approval_id
params_masked
result_summary
duration_ms
retry_count
error_type
```

并且从内存 list 升级为 DB 持久化。

---

## P0：高风险动作审批强绑定

规则：

```text
requires_approval=true 的工具
没有 approval_id 不能执行
approval_id 未通过不能执行
审批动作和执行动作必须一致
审批资源和执行资源必须一致
```

这一步非常重要。

---

## P1：审计事件表

新增统一 `audit_events` 表，所有关键动作都写进去。

---

## P1：脱敏和摘要

加：

```text
mask_params()
summarize_result()
detect_sensitive_fields()
```

不要把完整日志、完整 SQL 结果、完整对象内容直接写入审计。

---

## P1：RCA 关联审计链

RCA 里引用：

```text
相关 evidence_id
相关 tool_call_id
相关 approval_id
相关 execution_id
```

这样 RCA 不是模型自由生成，而是有完整依据。

---

## P2：审计查询页面

前端可以做一个 Audit Timeline：

```text
工单创建
Agent 分诊
工具调用
证据生成
审批
执行
验证
RCA
```

支持按：

```text
run_id
incident_id
user_id
tool_name
risk_level
service
env
```

查询。

---

# 16. 面试表达版

你可以这样讲：

> 我理解可审计是生产级运维 Agent 的安全底线。因为 Agent 会接触 MySQL、K8s、ALB、OSS 等生产资源，所以不能只记录最终结果，而要记录完整行为链路。  
>
> 具体来说，每次 Agent 处理工单，都要记录工单来源、Agent 决策、工具调用、权限判断、风险等级、审批记录、执行结果、证据链和 RCA 产物。尤其是高风险动作，比如重启服务、回滚发布、修改负载均衡、kill 数据库连接，必须强制绑定审批记录，没有审批 ID 或审批未通过，Tool Runtime 不允许执行。  
>
> 在实现上，我会通过统一 audit_events 表记录关键事件，比如 permission.checked、tool.called、approval.required、approval.approved、action.executed、evidence.created、rca.generated。审计日志里只存脱敏参数和结果摘要，原始数据按权限归档。这样后续可以按工单、用户、服务、工具、风险等级追溯完整操作链路。  
>
> 这样做的价值是：一旦 Agent 误判或执行异常，可以明确它基于什么证据做判断、哪个用户触发、谁审批、执行了什么资源、结果如何，从而满足故障复盘、安全合规和责任追踪要求。

---

# 17. 一句话版

> **可审计就是给 Agent 建一条不可随意篡改的“责任链”：从工单、决策、工具调用、权限校验、人工审批、执行结果到 RCA，每一步都有记录、有证据、有责任人、可追溯。**

## Prompt:
2026/5/14 17:22:52

以上这几点，现在你总结的还是很乱，我没法在面试中结构化地说出来

## Response:
2026/5/14 17:23:01

> **Providing concise framework for interview**
>
> The user asked for a structured approach based on previous context. I'll offer a concise framework for structuring the interview: "生产级Agent五性". The answer format should be: start with a summary, followed by expanding on five dimensions: "定义-为什么-怎么做-项目现状/缺口". I'll focus on key qualities: measurable, observable, reusable, scalable, auditable. No citations are needed since it's based on earlier discussion.
>
> Thought for 9s

我把它重新整理成一套“面试能直接讲”的口径：先给总框架，再给五个维度的固定表达模板，最后给你一版 1 分钟完整答案。

确实，前面讲得太散了。你面试不能按“技术点清单”讲，要按一个**统一框架**讲。

你就记住一句核心话：

> **我判断一个运维 Agent 是否生产可用，不是只看它能不能回答问题，而是看它有没有五个工程闭环：效果可评测、过程可观测、能力可复用、架构可扩展、行为可审计。**

然后每个维度都用同一个表达结构：

```text
它解决什么问题？
在运维 Agent 里怎么落地？
我的项目目前做到哪，后续怎么补？
```

---

# 一、五个维度一句话记忆

| 维度 | 面试里怎么解释 | 你要表达的核心 |
|---|---|---|
| 可评测 | 判断 Agent 效果有没有变好 | 有测试集、有指标、有回放 |
| 可观测 | 看清 Agent 每一步干了什么 | 有 Trace、有事件流、有工具调用记录 |
| 可复用 | 能力不是为单个故障写死 | 工单、工具、证据、RCA 标准化 |
| 可扩展 | 工单、工具、团队变多后还能跑 | 队列、Worker、状态持久化、限流 |
| 可审计 | 出问题后能追溯责任和依据 | 权限、审批、执行、证据都有记录 |

你面试时不要展开太碎，先这样讲：

> 可评测解决“好不好”的问题，可观测解决“为什么”的问题，可复用解决“能不能迁移”的问题，可扩展解决“规模上来能不能撑住”的问题，可审计解决“生产操作能不能追责”的问题。

---

# 二、每个维度的标准面试表达

## 1. 可评测：证明 Agent 有没有变好

不要说：

> 我们会评估 Agent 效果。

要说：

> 可评测的核心是建立一套离线评测集和指标体系，用来判断每次 Prompt、Planner、工具策略或 RAG 调整后，Agent 到底是变好还是退化。

在运维 Agent 里，评测对象不是只有最终答案，而是整条链路：

```text
工单结构化是否准确
分诊类型是否准确
排查计划是否完整
工具选择是否合理
根因判断是否命中
风险等级是否正确
处置建议是否可执行
RCA 是否完整
```

对应指标：

```text
根因 Top1 / Top3 命中率
排查计划覆盖率
工具选择准确率
风险等级准确率
人工接管率
平均排查耗时
RCA 质量评分
```

面试表达：

> 比如我们可以准备 20 个历史或模拟故障工单，每个 case 都有标准答案，包括期望故障类型、期望证据源、期望根因和风险等级。每次修改 Agent 后自动回放这些 case，统计根因命中率、排查计划覆盖率、工具选择准确率等指标。这样 Agent 迭代不是靠感觉，而是靠数据判断有没有提升。

一句话：

> **可评测就是给 Agent 建一套考试系统，用固定工单、固定工具返回和标准答案评估它有没有变好。**

---

## 2. 可观测：看清 Agent 每一步发生了什么

不要说：

> 我们会打日志。

要说：

> 可观测的核心是把 Agent 从黑盒变成可回放的工作流。一次排障任务中，每个节点、每次模型调用、每次工具调用、每条证据和每次审批都要能被追踪。

在运维 Agent 里要观测：

```text
Run 层：这次任务整体状态
Node 层：每个工作流节点输入输出
LLM 层：模型调用、Prompt 版本、Token、耗时
Tool 层：调用了什么工具、参数、耗时、成功失败
Evidence 层：证据来自哪里、支持哪个根因
Human 层：是否进入人工审批、谁处理了
```

技术落地：

```text
统一 run_id / node_id / tool_call_id / evidence_id
结构化 Event Log
Tool Call 记录
LLM Call 记录
Evidence Record
SSE / WebSocket 实时推送
RunDetail 时间线展示
```

面试表达：

> 比如一次订单服务 500 的排查，我希望能在 RunDetail 页面里看到：intake 抽取了什么服务和故障类型，planner 生成了哪些排查步骤，Tool Runtime 调用了哪些工具，每个工具返回什么摘要，哪些证据支持最终根因，是否进入审批。这样如果 Agent 误判，我们可以定位问题是出在工单抽取、Planner、工具调用还是诊断节点，而不是简单归因于模型幻觉。

一句话：

> **可观测就是给 Agent 装行车记录仪，让它每一步为什么这么做、哪里失败、用了哪些证据都能回放。**

---

## 3. 可复用：能力不要为单个故障写死

不要说：

> 我们希望这个 Agent 能支持更多场景。

要说：

> 可复用的核心是把一次故障处理拆成标准对象和标准流程，避免为某个服务、某个故障、某个工具写死逻辑。

运维 Agent 里要复用这些对象：

```text
IncidentContext：标准工单上下文
PlanStep：标准排查步骤
ToolDefinition：标准工具定义
EvidenceRecord：标准证据结构
RiskPolicy：标准风险策略
ApprovalCard：标准审批卡片
RCAArtifact：标准 RCA 产物
```

举例：

```text
订单服务 500
支付接口超时
OSS 403
K8s Pod CrashLoopBackOff
MySQL 慢查询
```

这些故障不同，但主流程都可以是：

```text
工单抽取 → 分诊 → 计划 → 工具采集 → 证据聚合 → 根因诊断 → 处置建议 → 审批 → 验证 → RCA
```

面试表达：

> 比如新增 Redis 或 MQ 故障，不应该重写 Agent 主流程，而是新增 Tool Adapter、Tool Metadata 和 Evidence Normalizer。Planner 只关心需要什么证据，Tool Router 根据工具能力选择对应工具，Diagnosis 统一消费 EvidenceRecord。这样从订单 500 扩展到 OSS 403 或 Redis 慢查询，只需要补模板和工具，不需要推翻主链路。

一句话：

> **可复用就是把 Agent 从 case 编程升级为能力编程，靠标准协议、模板和 Adapter 扩展新场景。**

---

## 4. 可扩展：规模上来后系统还能撑住

不要说：

> 后面可以加机器扩容。

要说：

> 可扩展不是简单加机器，而是 Agent 架构本身要支持多工单、多工具、多团队和高并发。

运维 Agent 的扩展点包括：

```text
任务异步化
队列化执行
Worker 水平扩展
状态持久化
Checkpoint 恢复
工具调用限流
多团队权限隔离
工具动态注册
缓存与降级
```

架构表达：

```text
API Server 只负责创建 Run
Queue 负责任务排队
Agent Worker 执行工作流
Tool Runtime 控制工具调用
DB 保存状态、事件、证据和审批
前端通过 SSE 看进度
```

面试表达：

> 比如真实生产里可能同时有几十个告警，如果每个请求都同步跑完整 Agent，很容易打爆 K8s、MySQL、日志平台和 LLM。所以我会把长任务从 API 请求里拆出去，采用 Run + Queue + Worker 的模式异步执行；同时把 run、checkpoint、event、tool call、evidence、approval 都持久化，支持失败恢复和审批后继续执行。工具调用层再按 tool、service、env、team 做限流，避免大量 Agent 同时冲击生产系统。

一句话：

> **可扩展就是让 Agent 从单机跑 Demo，升级成支持多工单、多工具、多团队、多并发的平台型系统。**

---

## 5. 可审计：生产操作要能追责

不要说：

> 我们会保存操作记录。

要说：

> 可审计的核心是建立一条完整责任链：Agent 做了什么、为什么做、谁批准、有没有权限、依据是什么、结果如何，都能追溯。

运维 Agent 要审计：

```text
工单来源
Agent 决策
工具调用
权限判断
风险等级
审批记录
执行结果
证据链
RCA 产物
```

尤其高风险动作：

```text
重启服务
扩缩容
回滚发布
kill MySQL session
修改 ALB 后端
修改 OSS 权限
```

必须满足：

```text
没有审批不能执行
审批动作和执行动作一致
审批资源和执行资源一致
审批记录和执行记录绑定
所有结果可追溯
```

面试表达：

> 比如 Agent 建议重启 order-service，这不是模型说了就执行。Tool Runtime 要先判断这是生产环境高风险动作，生成审批卡片，里面包含支持证据、影响范围、风险等级和回滚方案。只有服务负责人或 SRE 审批通过后，工具层才允许执行。执行后还要记录 execution audit，并把验证结果和 RCA 关联起来。这样出问题后可以明确是谁触发、谁审批、执行了什么资源、依据是什么、结果如何。

一句话：

> **可审计就是给 Agent 建一条责任链，从工单、决策、工具、审批、执行到 RCA，每一步都有记录、有证据、有责任人。**

---

# 三、面试时不要逐个散讲，要用这个总结构

你可以这样组织：

```text
第一层：总判断
生产级 Agent 不能只看能不能回答，而要看五个工程闭环。

第二层：五个维度
可评测、可观测、可复用、可扩展、可审计。

第三层：结合运维项目落地
分别对应评测集、Trace、标准协议、队列 Worker、审计审批。

第四层：说当前项目状态
主链路已跑通，但这五类能力是继续生产化补强方向。
```

---

# 四、1 分钟完整面试答案

你可以直接背这版：

> 我判断一个运维 Agent 是否生产可用，不会只看它能不能回答问题，而是看它有没有五个工程闭环：可评测、可观测、可复用、可扩展、可审计。  
>
> 可评测解决的是效果问题，也就是每次改 Prompt、Planner 或工具策略后，怎么判断 Agent 有没有变好。我的理解是要建立离线评测集，用历史或模拟工单，评估根因 Top1/Top3 命中率、排查计划覆盖率、工具选择准确率和风险等级准确率。  
>
> 可观测解决的是过程问题，也就是 Agent 每一步做了什么能不能看清。运维 Agent 里需要记录每个 workflow 节点、每次 LLM 调用、每次工具调用、证据生成和人工审批，通过 run_id 串起来，在 RunDetail 页面能回放完整链路。  
>
> 可复用解决的是能力沉淀问题，也就是不要为某个故障写死逻辑。我会把工单抽象成 IncidentContext，把工具抽象成 ToolDefinition，把工具结果统一成 EvidenceRecord，把 RCA 统一成结构化产物。这样新增 Redis、MQ、OSS 等场景时，主要是新增工具 Adapter 和故障模板，而不是重写主流程。  
>
> 可扩展解决的是规模问题。真实场景里会有多工单、多工具、多团队并发，所以需要 Run + Queue + Worker 的异步架构，状态和 checkpoint 持久化，工具调用做限流和重试，支持 Worker 水平扩展。  
>
> 可审计解决的是生产安全问题。所有工具调用、权限判断、高风险审批、执行结果和 RCA 都要有审计记录。尤其是重启、回滚、扩缩容这类动作，必须经过人工审批，并且审批动作、执行资源和证据链要强绑定。  
>
> 所以这个项目不是做一个简单的大模型问答助手，而是围绕生产级运维场景，把 Agent 做成可评测、可观测、可复用、可扩展、可审计的工作流系统。

---

# 五、30 秒压缩版

> 这个项目我会从五个生产化维度来讲。第一是可评测，用历史工单和指标评估根因命中率、计划覆盖率、工具选择准确率；第二是可观测，记录每个节点、LLM 调用、工具调用和证据链，支持回放；第三是可复用，把工单、工具、证据、RCA 标准化，新增场景靠模板和 Adapter 扩展；第四是可扩展，用 Queue、Worker、Checkpoint 和限流支撑多工单并发；第五是可审计，对权限、审批、执行和 RCA 做完整记录，保证生产操作可追溯。  
>
> 这五点合起来，才是我理解的生产级运维 Agent。

---

# 六、最短记忆口诀

你就记这句：

> **评测看效果，观测看过程，复用看沉淀，扩展看规模，审计看责任。**

面试官继续追问时，你再逐个展开。

## Prompt:
2026/5/15 11:30:36

你想象你是面试官，基于上面的内容，你对我提出二十个最有可能问我的问题（假设你们想招ai架构师）

## Response:
2026/5/15 11:30:38

下面这 20 个问题，我会按 **AI 架构师面试官** 的视角来问你，不是普通产品经理面试。重点会追问：**架构抽象、生产化、工具治理、Agent Workflow、评测、可观测、安全边界和扩展性**。

---

# 一、项目整体架构类

## 1. 你这个运维智能体和普通 ChatBot / Copilot 最大区别是什么？

追问点：

```text
它为什么是 Agent，而不是问答机器人？
它有没有状态机？
有没有工具调用？
有没有人机协同？
有没有闭环验证？
```

面试官想听你说：

```text
不是单轮问答，而是围绕工单形成自动分诊、证据采集、诊断、处置建议、审批、执行验证、RCA 的工作流闭环。
```

---

## 2. 你这个 Agent 的主链路是怎么设计的？

追问点：

```text
从工单进入到 RCA 输出，中间有哪些节点？
每个节点的输入输出是什么？
哪些节点用 LLM？
哪些节点用规则？
哪些节点调用工具？
```

他不是想听泛泛的“排查故障”，而是想听：

```text
intake → triage → retrieve_memory → planner → evidence_fanout → evidence_aggregate → diagnose → critic → remediation → risk_gate → approval → executor → verify → rca
```

---

## 3. 你为什么要用 Workflow / 状态机，而不是让大模型一次性回答？

追问点：

```text
一次性回答有什么问题？
状态机解决了什么？
哪里需要 checkpoint？
哪里需要中断恢复？
```

标准方向：

```text
大模型一次性回答不可控、不可恢复、不可审计。
状态机可以把复杂任务拆成节点，每个节点输入输出明确，可以记录状态、失败重试、人工审批、中断恢复和过程追踪。
```

---

## 4. 你的 Agent 状态 State 里应该保存哪些核心字段？

追问点：

```text
IncidentContext 存什么？
Plan 存什么？
Evidence 存什么？
Diagnosis 存什么？
Approval 存什么？
Checkpoint 怎么设计？
```

面试官想判断你是否真的理解 Agent Workflow，而不是只会说概念。

---

# 二、工单与规划类

## 5. 工单进来后，你如何把自然语言变成 Agent 可执行的结构化输入？

追问点：

```text
工单结构化怎么做？
规则抽取和 LLM 抽取怎么分工？
如何从 CMDB 补齐资源？
怎么处理缺失字段？
```

他想听：

```text
工单原文 → 规则抽取硬字段 → LLM 语义抽取 → CMDB 资源映射 → IncidentContext。
```

---

## 6. 排查计划是怎么生成的？依据是什么？

追问点：

```text
是大模型自由生成？
还是基于故障类型模板？
是否结合服务拓扑？
是否结合历史 RCA / Runbook？
是否结合可用工具清单？
```

你要能答：

```text
排查计划来自工单症状、故障类型、服务拓扑、历史 SOP/RCA、工具注册表和当前证据状态。
```

---

## 7. 你如何避免 Planner 生成一个“看起来合理但不可执行”的排查计划？

追问点：

```text
PlanStep 结构是什么？
是否绑定工具能力？
是否校验参数完整度？
是否限制风险等级？
是否能判断依赖顺序？
```

他想听你说：

```text
排查计划不是自由文本，而是结构化 PlanStep，每一步包含目标、证据需求、资源类型、候选工具、参数、风险等级和预期输出。
```

---

## 8. 如果排查计划第一轮查完发现方向错了，Agent 如何调整？

追问点：

```text
计划是一次性的吗？
有没有基于证据动态调整？
有没有反证机制？
```

最好回答：

```text
不是一次性固定计划，而是 plan → act → observe → re-plan。比如第一轮发现 K8s 正常但 MySQL 连接异常，后续计划会收敛到慢查询、锁等待、连接池和最近 SQL 变更。
```

---

# 三、工具调用与 Tool Runtime 类

## 9. MySQL、K8s、ALB、OSS 这些基础设施能力，你是怎么抽象成标准工具的？

追问点：

```text
工具定义里有哪些字段？
如何统一入参和出参？
如何描述工具能力？
如何标记风险等级？
```

标准回答方向：

```text
ToolDefinition = name、domain、description、capabilities、inputSchema、outputSchema、riskLevel、requiresApproval、timeout、retryPolicy。
```

---

## 10. 生成排查计划后，Agent 如何选择具体工具？

追问点：

```text
Tool Router 是怎么做的？
按关键词选工具吗？
如何结合 EvidenceNeeded？
如何结合 CMDB？
如何处理参数不完整？
```

他想听：

```text
不是关键词匹配，而是基于排查步骤的 evidenceNeeded、resourceType、capabilities、权限、风险、参数完整度和当前证据状态做工具选择。
```

---

## 11. Tool Runtime 在你的架构里解决什么问题？

追问点：

```text
为什么 Agent 不能直接调用工具？
Tool Runtime 具体做哪些事情？
权限、参数、重试、审计怎么做？
```

要回答到：

```text
Tool Runtime 是 Agent 和生产系统之间的安全执行网关，统一做权限校验、参数校验、风险审批、超时重试、结果脱敏、证据标准化和审计留痕。
```

---

## 12. 如果大模型生成了一个危险操作，比如重启生产服务，你怎么拦截？

追问点：

```text
是在 Prompt 里要求模型不要做？
还是在工具层强制拦截？
审批怎么做？
审批和执行怎么绑定？
```

架构师面试里，不能只说“Prompt 约束”。

你要说：

```text
Prompt 只是第一层，真正兜底在 Tool Runtime 和 RiskPolicy。高风险工具 requiresApproval=true，没有 approval_id 或审批未通过，Runtime 不允许执行。
```

---

## 13. MySQL 工具如何防止 Agent 执行危险 SQL？

追问点：

```text
是否允许任意 SQL？
如何防止 UPDATE / DELETE / DROP？
如何限制扫描量？
如何脱敏？
```

好的回答：

```text
优先使用模板化只读工具，比如 get_slow_queries、get_connection_stats；如果开放 readonly query，也必须只允许 SELECT、表白名单、字段白名单、强制 LIMIT、超时限制、敏感字段脱敏。
```

---

## 14. K8s 工具如何设计安全边界？

追问点：

```text
是否允许 exec？
是否允许 restart？
namespace 怎么限制？
日志怎么脱敏？
生产环境动作怎么控制？
```

标准方向：

```text
只读工具自动执行，写操作必须审批；ServiceAccount 使用最小 RBAC；namespace 白名单；禁止任意 shell/exec；日志限制行数和时间窗口；生产 restart/rollback 必须审批。
```

---

# 四、证据与诊断类

## 15. 你如何把不同工具返回的数据变成 Agent 能理解的证据？

追问点：

```text
MySQL、K8s、ALB 返回格式都不一样，怎么统一？
EvidenceRecord 长什么样？
证据如何支持根因？
```

要说：

```text
通过 Evidence Normalizer 把工具原始结果统一成 EvidenceRecord，包括 sourceTool、resourceType、resourceId、status、finding、keyMetrics、supports、contradicts、confidence。
```

---

## 16. 你的根因诊断是如何避免幻觉的？

追问点：

```text
模型怎么判断根因？
有没有 evidence citation？
有没有反证？
有没有置信度？
有没有 critic？
```

好的回答方向：

```text
诊断必须基于 EvidenceRecord，不允许无证据下结论。每个 root cause candidate 都要绑定 supportingEvidenceIds 和 contradictingEvidenceIds，再由 critic 节点检查证据是否充分、是否过早下结论。
```

---

## 17. 如果多个证据互相冲突，比如 ALB 5xx 升高但 K8s Pod 正常，Agent 怎么处理？

追问点：

```text
是否会直接下结论？
如何处理反证？
如何继续排查？
```

你要体现架构思维：

```text
冲突证据不会直接丢弃，而是记录为 contradictingEvidence。诊断节点会降低某些根因置信度，并触发下一轮补充证据，比如继续查 MySQL、下游依赖、发布记录。
```

---

# 五、生产化能力类

## 18. 你说项目要可评测，具体怎么评？指标是什么？

追问点：

```text
评最终答案还是评每个节点？
测试集怎么构造？
怎么判断每次改动有没有变好？
```

你要说：

```text
用历史/模拟故障构建离线评测集，每个 case 有期望故障类型、期望证据源、期望根因和风险等级。指标包括根因 Top1/Top3 命中率、排查计划覆盖率、工具选择准确率、风险等级准确率、平均步骤数和平均耗时。
```

---

## 19. 你说项目要可观测，具体要观测哪些内容？怎么实现？

追问点：

```text
日志和可观测有什么区别？
Trace ID 怎么设计？
Event Log 怎么设计？
前端怎么看？
```

面试官想听：

```text
统一 run_id、node_id、tool_call_id、llm_call_id、evidence_id；通过 Event Log 记录 node.started、tool.completed、llm.failed、evidence.created、approval.required；前端通过 SSE 展示 RunDetail 时间线、工具调用、证据链和审批状态。
```

---

## 20. 如果这个系统要从 Demo 走向生产，你认为最大的三个架构风险是什么？怎么解决？

这个是架构师面试里最可能的收口问题。

你可以从这三点答：

```text
第一，模型不可控风险：
用结构化 Workflow、Tool Runtime、Evidence-based Diagnosis、Critic、Human-in-the-loop 降低风险。

第二，生产操作安全风险：
用权限校验、风险分级、强制审批、执行审计、回滚方案和验证机制兜底。

第三，规模化运行风险：
用 Run + Queue + Worker、状态持久化、Checkpoint、工具限流、熔断降级、多租户隔离和评测体系支撑生产化。
```

---

# 最可能被连续追问的一组问题

如果我是面试官，我最可能围绕这条链连续追你：

```text
工单进来后如何结构化？
↓
排查计划怎么生成？
↓
工具怎么选？
↓
工具调用怎么保证安全？
↓
证据怎么标准化？
↓
根因怎么判断？
↓
高风险动作怎么审批？
↓
怎么验证修复有效？
↓
怎么沉淀 RCA？
↓
怎么评估 Agent 迭代有没有变好？
```

这条链你必须打通。

---

# 最高频“架构师级”追问

最后这 5 个尤其要准备好：

```text
1. 你怎么证明这个 Agent 不是一个套壳 ChatBot？
2. 你怎么防止大模型误操作生产环境？
3. 你怎么评估根因诊断是否准确？
4. 你怎么设计 Tool Runtime？
5. 如果同时来了 100 个告警，这套架构怎么撑住？
```

你只要能把这 5 个问题答稳，这个运维智能体项目在 AI 架构师面试里就比较能打。

## Prompt:
2026/5/15 11:31:48

你别只给问题，顺便把解答也给我

## Response:
2026/5/15 11:31:50

> **规划回答模板并考虑边界**
>
> 我想使用总-分-例-边界的回答模板，提供20个简洁Q&A，每个问题对应一段。一些追问部分也许可以提及。使用中文回答，避免用项目符号，内容较长但可接受。对于项目未实现部分，我会提到“当前项目里...”，并谨慎避免不必要的夸大。
>
> 已思考 10s

可以。下面我把刚才那 **20 个 AI 架构师高频问题**，全部配上**可直接面试使用的回答**。

你回答时不要像背八股，要始终围绕这条主线：

> **这个项目不是一个大模型问答工具，而是一个面向生产运维场景的 Agent Workflow 系统。核心设计是：工单进入后，经过结构化分诊、排查计划生成、多源工具采集、证据聚合、根因诊断、风险审批、执行验证和 RCA 沉淀，最终形成可评测、可观测、可复用、可扩展、可审计的闭环。**

---

# 1. 你这个运维智能体和普通 ChatBot / Copilot 最大区别是什么？

**回答：**

普通 ChatBot 更偏问答，它主要根据上下文直接生成回答，缺少稳定的任务状态、工具执行、审批和验证闭环。

我的运维智能体不是让大模型直接“猜故障原因”，而是围绕工单处理构建了一条 Agent Workflow。它会先做工单结构化和自动分诊，再生成排查计划，然后调用 MySQL、K8s、ALB、OSS 等工具采集证据，基于证据做根因诊断，给出处置建议。涉及生产高风险动作时，会进入人工审批，执行后还要做验证，最后生成 RCA。

所以它和 ChatBot 的区别在于：**它不是一次性回答，而是有状态、有工具、有证据、有审批、有验证、有复盘的生产级工作流系统。**

---

# 2. 你这个 Agent 的主链路是怎么设计的？

**回答：**

主链路我会拆成几个标准节点：

```text
工单接入 intake
→ 自动分诊 triage
→ 历史经验检索 retrieve_memory
→ 排查计划 planner
→ 多源证据采集 evidence_fanout
→ 证据聚合 evidence_aggregate
→ 根因诊断 diagnose
→ 诊断自检 critic
→ 处置建议 remediation
→ 风险判断 risk_gate
→ 人工审批 approval
→ 执行 executor
→ 结果验证 verify
→ RCA 复盘 rca
```

这里不是每个节点都必须依赖大模型。像工单硬字段抽取、权限判断、风险等级判断、工具参数校验，可以更多依赖规则和结构化逻辑；Planner、Diagnosis、RCA 这类复杂判断才更适合用 LLM。

这种设计的好处是，每个节点的输入输出都比较清楚，后续可以单独评测、观测和优化，不会变成一个不可控的大 Prompt。

---

# 3. 你为什么要用 Workflow / 状态机，而不是让大模型一次性回答？

**回答：**

运维场景不能让大模型一次性自由发挥，因为生产故障处理有几个要求：要可控、可追踪、可恢复、可审批、可验证。

如果一次性让模型回答，它可能会漏查关键证据，也可能在证据不足时过早下结论，甚至给出危险操作建议。状态机的价值是把复杂任务拆成多个确定节点，比如先分诊，再规划，再采集证据，再诊断，再审批，再验证。每个节点都有明确输入输出，可以记录 checkpoint，失败后可以重试，审批时可以暂停，审批后可以继续恢复。

所以我使用 Workflow / 状态机，本质是把大模型的不确定推理，放进一个可控的工程流程里。

---

# 4. 你的 Agent State 里应该保存哪些核心字段？

**回答：**

Agent State 需要保存一次故障处理的完整上下文，核心包括几类。

第一是 `IncidentContext`，也就是工单结构化结果，包括服务名、环境、严重等级、故障类型、时间窗口、影响范围。

第二是 `Plan`，包括排查步骤、每一步需要什么证据、目标资源类型、候选工具、风险等级。

第三是 `Evidence`，也就是工具返回后标准化的证据，比如 ALB 5xx、K8s Pod 状态、MySQL 慢查询、OSS 访问异常。

第四是 `Diagnosis`，包括候选根因、支持证据、反证、置信度。

第五是 `Remediation / Approval / Execution / Verify / RCA`，分别记录处置建议、审批状态、执行结果、验证结果和最终复盘产物。

这样 State 不是简单聊天上下文，而是一次故障处理的结构化状态快照，方便恢复、回放和审计。

---

# 5. 工单进来后，你如何把自然语言变成 Agent 可执行的结构化输入？

**回答：**

我不会直接把工单原文丢给模型生成排查计划，而是先把它转成标准 `IncidentContext`。

具体分四步：

第一步，用规则抽取硬字段，比如 P1/P2、prod/test、时间、状态码、接口路径、服务名候选。

第二步，用 LLM 做语义抽取，识别故障类型、业务影响、用户猜测、缺失字段。比如区分“明确发生了 500”和“用户猜测可能是发布导致”。

第三步，通过 CMDB 或服务目录做资源补全，把“订单服务”映射成真实资源，比如 K8s cluster、namespace、workload、ALB 实例、MySQL 库、OSS bucket。

第四步，做校验和置信度判断，比如服务是否存在、环境是否合法、时间窗口是否合理、缺失字段是否需要追问。

最终 Planner 消费的是结构化 IncidentContext，而不是原始工单文本。

---

# 6. 排查计划是怎么生成的？依据是什么？

**回答：**

排查计划不是大模型凭空生成的，它主要基于六类信息。

第一是工单症状，比如 5xx、超时、403、Pod 重启。  
第二是故障类型分类，比如 http_5xx、mysql_slow_query、oss_access_error。  
第三是服务拓扑，也就是这个服务依赖哪些 ALB、K8s、MySQL、OSS、下游服务。  
第四是历史 SOP、Runbook 和 RCA，提供相似故障经验。  
第五是工具注册表，告诉 Planner 当前有哪些工具可以用。  
第六是当前已有证据，支持动态调整后续排查方向。

所以排查计划本质上是：

```text
工单症状 + 故障类型 + 服务拓扑 + 历史经验 + 工具能力 + 当前证据
```

生成的不是普通文字，而是结构化 PlanStep，每一步都要说明查什么、为什么查、用什么工具、期望得到什么证据。

---

# 7. 你如何避免 Planner 生成一个“看起来合理但不可执行”的排查计划？

**回答：**

关键是让 Planner 输出结构化计划，而不是自由文本。

每个 PlanStep 至少要包含：

```text
step_id
排查目标 goal
目标层级 target_layer
资源类型 resource_type
需要的证据 evidence_needed
候选工具 candidate_tools
必要参数 required_params
风险等级 risk_level
预期输出 expected_output
```

比如不能只写“检查数据库是否异常”，而要写成“采集 MySQL 连接数、慢查询和锁等待证据，候选工具是 mysql.get_connection_stats、mysql.get_slow_queries”。

然后在执行前还要由 Tool Router 和 Tool Runtime 校验：工具是否存在、参数是否完整、资源是否能通过 CMDB 补全、权限是否允许、是否需要审批。

这样可以避免 Planner 生成看起来正确但系统无法执行的计划。

---

# 8. 如果排查计划第一轮查完发现方向错了，Agent 如何调整？

**回答：**

排查计划不应该是一次性固定的，而应该支持 `plan → act → observe → re-plan`。

比如一开始判断是接口 5xx，计划会同时查 ALB、K8s、MySQL 和发布记录。第一轮执行后，如果发现 ALB 5xx 升高、K8s Pod 正常，但 MySQL 连接数接近上限，那么下一轮计划就应该收敛到数据库方向，继续查慢 SQL、锁等待、连接池、最近 SQL 变更。

反过来，如果 MySQL 正常，但 K8s 出现 CrashLoopBackOff，就应该继续查 Pod events、最近镜像版本、发布记录和容器日志。

所以 Agent 不是一次性排查，而是根据证据动态调整假设和下一步工具调用。

---

# 9. MySQL、K8s、ALB、OSS 这些基础设施能力，你是怎么抽象成标准工具的？

**回答：**

我会把它们都抽象成统一的 `ToolDefinition`，而不是让 Agent 直接调用底层 API。

每个工具定义包括：

```text
name：工具名
domain：所属领域，比如 mysql/k8s/alb/oss
description：工具用途
capabilities：能提供什么证据
inputSchema：入参结构
outputSchema：出参结构
riskLevel：风险等级
requiresApproval：是否需要审批
timeoutMs：超时时间
retryPolicy：重试策略
```

比如 MySQL 可以有 `mysql.get_connection_stats`、`mysql.get_slow_queries`；K8s 可以有 `k8s.get_pod_status`、`k8s.get_events`；ALB 可以有 `alb.get_traffic_metrics`、`alb.get_backend_health`；OSS 可以有 `oss.check_object_exists`、`oss.get_access_errors`。

这样 Agent 面对的是标准工具能力，不需要关心底层系统 SDK 的差异。

---

# 10. 生成排查计划后，Agent 如何选择具体工具？

**回答：**

工具选择不是靠关键词匹配，而是通过 Tool Router 基于证据需求做匹配。

PlanStep 里会描述需要什么证据，比如 `5xx_rate`、`backend_health`、`pod_status`、`slow_query`、`oss_403`。Tool Router 会拿这些 evidenceNeeded 去 Tool Registry 里匹配工具的 capabilities。

同时还会结合资源类型、CMDB 资源补全、参数完整度、权限风险和当前证据状态。

比如排查步骤是“判断入口层是否异常”，需要 `5xx_rate` 和 `backend_health`，就会选择 ALB 指标和后端健康检查工具。如果步骤是“判断服务是否重启或 OOM”，就会选择 K8s Pod 状态和 events 工具。如果步骤是“判断数据库是否拖慢接口”，就会选择 MySQL 连接数、慢查询和锁等待工具。

所以工具选择过程是：

```text
排查步骤 → 证据需求 → 工具能力匹配 → 资源补全 → 参数校验 → 权限风控 → 执行
```

---

# 11. Tool Runtime 在你的架构里解决什么问题？

**回答：**

Tool Runtime 是 Agent 和生产系统之间的安全执行网关。

Agent 不能直接访问 MySQL、K8s、ALB、OSS，因为模型输出不稳定，可能参数错误、越权访问，甚至触发高风险动作。Tool Runtime 统一负责把模型生成的工具调用请求变成安全、可靠、可追踪的工程动作。

它主要做几件事：

```text
权限校验：判断用户、Agent、服务、环境是否允许调用
参数校验：按 inputSchema 校验字段、类型、范围
风险判断：高风险动作是否需要审批
超时重试：处理工具失败、超时、云 API 抖动
结果脱敏：避免敏感数据进入模型上下文
证据标准化：把结果转成 EvidenceRecord
审计留痕：记录谁调用、为什么调用、结果如何
```

所以 Tool Runtime 的价值不是简单封装 API，而是保证 Agent 可以接生产系统，但不能失控。

---

# 12. 如果大模型生成了一个危险操作，比如重启生产服务，你怎么拦截？

**回答：**

不能只靠 Prompt 约束，真正的拦截必须在工具执行层。

我会在 ToolDefinition 里给每个工具标记 `riskLevel` 和 `requiresApproval`。比如 `k8s.get_pod_status` 是低风险只读工具，可以自动执行；但 `k8s.rollout_restart`、`rollback_deployment`、`mysql.kill_session`、`alb.modify_backend` 都是高风险动作，必须审批。

当 Agent 调用这类工具时，Tool Runtime 会检查：

```text
是否是生产环境
动作风险等级是多少
是否已有 approval_id
approval_id 是否审批通过
审批动作和执行动作是否一致
审批资源和执行资源是否一致
```

如果没有审批，Runtime 直接返回 `REQUIRE_APPROVAL`，生成审批卡片，展示风险、影响范围、支持证据和回滚方案。审批通过后才允许执行。

所以模型可以提出建议，但不能绕过 Tool Runtime 直接操作生产。

---

# 13. MySQL 工具如何防止 Agent 执行危险 SQL？

**回答：**

MySQL 工具我会优先设计成模板化只读工具，而不是开放任意 SQL。

比如：

```text
mysql.get_connection_stats
mysql.get_slow_queries
mysql.get_lock_waits
mysql.explain_query
mysql.get_table_status
```

如果确实要提供 readonly query，也要做严格限制：

```text
只允许 SELECT
禁止 UPDATE / DELETE / INSERT / DROP / ALTER
库表白名单
字段白名单
强制 LIMIT
查询超时限制
最大扫描行数限制
敏感字段脱敏
结果摘要化
```

而且 MySQL 账号本身也应该是只读账号，从数据库权限层兜底，不能只靠应用层判断。

所以安全策略是三层：**账号只读 + SQL 策略校验 + Tool Runtime 审计**。

---

# 14. K8s 工具如何设计安全边界？

**回答：**

K8s 工具也要分只读和动作两类。

只读工具包括：

```text
k8s.get_pod_status
k8s.get_events
k8s.get_pod_logs_summary
k8s.describe_deployment
k8s.get_resource_usage
```

这些可以自动执行，但要限制 namespace、日志行数、时间窗口，并做敏感信息脱敏。

动作工具包括：

```text
k8s.rollout_restart
k8s.scale_deployment
k8s.rollback_deployment
```

这些在生产环境必须进入人工审批。

底层还要使用最小权限 ServiceAccount 和 RBAC。比如只允许读指定 namespace 的 Pod、Deployment、Event，不允许任意 exec，不允许执行 shell，不允许跨 namespace 操作。

所以 K8s 的安全边界是：**最小 RBAC + namespace 白名单 + 禁止任意命令 + 高危动作审批**。

---

# 15. 你如何把不同工具返回的数据变成 Agent 能理解的证据？

**回答：**

我会在 Tool Adapter 后面加一层 Evidence Normalizer，把不同工具的原始结果统一成 `EvidenceRecord`。

因为 MySQL、K8s、ALB、OSS 返回格式都不一样，如果直接丢给模型，诊断会很混乱。

标准 EvidenceRecord 包括：

```text
evidence_id
source_tool
resource_type
resource_id
time_range
status：normal/warning/critical
finding：一句话发现
key_metrics：关键指标
supports：支持哪些根因
contradicts：反驳哪些根因
confidence：证据置信度
```

比如 MySQL 返回连接数 198/200，Normalizer 会转成：

```text
MySQL 连接数接近上限，支持 mysql_connection_exhausted 根因。
```

K8s 返回 Pod 无重启，则会转成：

```text
Pod 状态正常，反驳 pod_crash / oom_killed 根因。
```

这样 Diagnosis 节点消费的是统一证据，而不是各种原始 API 结果。

---

# 16. 你的根因诊断是如何避免幻觉的？

**回答：**

核心原则是：**诊断必须基于证据，不允许无证据下结论。**

具体做法有几层。

第一，Diagnosis 节点输入的是标准 EvidenceRecord，而不是原始日志堆砌。

第二，每个 root cause candidate 都必须绑定 supportingEvidenceIds 和 contradictingEvidenceIds。也就是说，它要说明哪些证据支持这个根因，哪些证据反驳这个根因。

第三，输出时要给置信度，并区分“事实”和“推测”。比如“ALB 5xx 升高”是事实，“可能由 MySQL 连接池耗尽引发”是推断。

第四，可以增加 Critic 节点，对诊断结果做自检，检查是否证据不足、是否忽略反证、是否过早下结论、是否需要补充工具调用。

所以不是让模型凭经验猜，而是让模型在证据约束下做诊断。

---

# 17. 如果多个证据互相冲突，比如 ALB 5xx 升高但 K8s Pod 正常，Agent 怎么处理？

**回答：**

冲突证据不能简单忽略，而要显式记录成反证。

比如 ALB 5xx 升高说明用户侧确实有错误，但 K8s Pod 正常说明问题可能不在 Pod 崩溃或 OOM。这时 Diagnosis 不应该继续坚持 K8s 根因，而是降低 pod_crash 的置信度，并继续扩展到其他方向，比如 MySQL、下游服务、发布记录、网关配置。

所以我会让 EvidenceRecord 支持：

```text
supports：支持哪些根因
contradicts：反驳哪些根因
```

诊断时根据支持证据和反证综合打分。如果关键证据冲突，就触发下一轮补充排查，而不是直接下结论。

这也是 Agent 相比固定脚本的价值：它可以基于证据动态调整假设。

---

# 18. 你说项目要可评测，具体怎么评？指标是什么？

**回答：**

可评测不是看 Agent 回答得像不像，而是用固定 case 和指标判断它有没有变好。

我会构建离线评测集，每个 case 包含：

```text
工单输入
期望故障类型
期望服务和环境
期望证据源
期望根因
期望风险等级
工具 fixture
```

然后每次修改 Prompt、Planner、Tool Router 或 RAG 后，自动回放这些 case，输出指标。

核心指标包括：

```text
工单结构化准确率
分诊准确率
排查计划覆盖率
工具选择准确率
根因 Top1 / Top3 命中率
风险等级准确率
平均步骤数
平均耗时
人工接管率
RCA 质量评分
```

比如一个 5xx case，标准期望要查 ALB、K8s、MySQL、发布记录。如果 Agent 只查了日志，最终即使猜对根因，排查计划覆盖率也不高。

这样 Agent 迭代就不是凭感觉，而是可以用数据证明有没有提升。

---

# 19. 你说项目要可观测，具体要观测哪些内容？怎么实现？

**回答：**

可观测的目标是把 Agent 从黑盒变成可回放的工作流。

我会用统一 ID 串联一次任务：

```text
run_id
node_id
llm_call_id
tool_call_id
evidence_id
approval_id
```

然后通过 Event Log 记录关键事件：

```text
run.started
node.started
node.completed
llm.completed
tool.started
tool.completed
tool.failed
evidence.created
approval.required
approval.completed
run.completed
```

具体要观测六层：

```text
Run 层：任务状态、耗时、最终结论
Node 层：每个节点输入输出和耗时
LLM 层：模型、Prompt 版本、Token、耗时、解析状态
Tool 层：工具名、参数摘要、资源、结果、重试、错误
Evidence 层：证据来源、支持哪个根因、是否有反证
Human 层：审批人、审批结果、人工接管
```

前端可以通过 SSE 或 WebSocket 订阅 run events，在 RunDetail 页面展示时间线、工具调用、证据看板和审批状态。

这样一旦误判，可以定位到底是工单抽取错、Planner 漏查、工具失败，还是 Diagnosis 没用上关键证据。

---

# 20. 如果这个系统要从 Demo 走向生产，你认为最大的三个架构风险是什么？怎么解决？

**回答：**

我认为最大的三个风险是：模型不可控、生产操作安全、规模化运行。

第一，模型不可控。  
大模型可能误解工单、漏查证据、过早下结论。解决方式是用结构化 Workflow 约束它，把任务拆成 intake、planner、evidence、diagnosis、critic 等节点；诊断必须基于 EvidenceRecord；关键结论要有证据引用；必要时通过 Critic 和人工确认兜底。

第二，生产操作安全风险。  
运维 Agent 可能触发重启、回滚、扩缩容、kill session 等高风险动作。解决方式是 Tool Runtime + RiskPolicy，把所有工具分级，只读工具自动执行，高风险工具必须审批；没有 approval_id 或审批未通过不能执行；执行后还要验证和审计。

第三，规模化运行风险。  
真实场景里会有多工单、多工具、多团队并发，如果同步执行很容易阻塞或打爆基础设施。解决方式是 Run + Queue + Worker 架构，长任务异步执行；状态、checkpoint、event、tool call、evidence 持久化；工具调用做限流、熔断和重试；多团队做权限隔离。

所以从 Demo 到生产，不是简单多接几个工具，而是要补齐可评测、可观测、可复用、可扩展、可审计这些工程能力。

---

# 最后一版：20 题的“超短背诵索引”

你可以这样快速记：

```text
1. ChatBot vs Agent：问答 vs 工作流闭环
2. 主链路：工单 → 分诊 → 计划 → 工具 → 证据 → 诊断 → 审批 → 验证 → RCA
3. 状态机价值：可控、可恢复、可审批、可追踪
4. State：工单、计划、证据、诊断、审批、执行、RCA
5. 工单结构化：规则 + LLM + CMDB + 校验
6. 排查计划：症状 + 拓扑 + SOP + 工具 + 证据
7. 可执行计划：PlanStep 结构化，不是自由文本
8. 动态调整：plan-act-observe-replan
9. 工具标准化：ToolDefinition
10. 工具选择：evidenceNeeded 匹配 capabilities
11. Tool Runtime：权限、参数、审批、重试、审计
12. 危险动作：Runtime 强制审批，不靠 Prompt
13. MySQL 安全：只读、白名单、LIMIT、脱敏
14. K8s 安全：RBAC、namespace、禁 exec、高危审批
15. 证据标准化：EvidenceRecord
16. 防幻觉：根因必须绑定证据和反证
17. 冲突证据：降低置信度，触发补充排查
18. 可评测：离线 case + 指标回放
19. 可观测：Trace ID + Event Log + RunDetail
20. 生产风险：模型、安全、规模化
```

你面试时不需要一口气全说完，但这 20 个问题基本覆盖了 AI 架构师会追你的核心区域。

## Prompt:
2026/5/15 11:44:40

重新输出以上内容，要求：类似`intake、planner、evidence、diagnosis、critic。。。`这种语句，英文后面加个括号带上中文翻译

## Response:
2026/5/15 11:44:43

下面是重排版。我把关键英文术语后面都加了中文翻译，方便你面试时直接说。

核心主线先记住：

> **这个项目不是一个大模型问答工具，而是一个面向生产运维场景的 Agent Workflow（智能体工作流）系统。核心设计是：工单进入后，经过 intake（工单接入 / 信息抽取）、triage（自动分诊）、planner（排查计划生成）、evidence collection（证据采集）、diagnosis（根因诊断）、risk gate（风险门禁）、approval（人工审批）、executor（执行器）、verify（结果验证）和 RCA（Root Cause Analysis，根因分析 / 故障复盘）沉淀，最终形成可评测、可观测、可复用、可扩展、可审计的闭环。**

---

# 1. 你这个运维智能体和普通 ChatBot（聊天机器人）/ Copilot（辅助助手）最大区别是什么？

**回答：**

普通 ChatBot（聊天机器人）更偏问答，它主要根据上下文直接生成回答，缺少稳定的任务状态、工具执行、审批和验证闭环。

我的运维智能体不是让大模型直接“猜故障原因”，而是围绕工单处理构建了一条 Agent Workflow（智能体工作流）。它会先做 intake（工单接入 / 信息抽取）和 triage（自动分诊），再生成 planner（排查计划），然后调用 MySQL、K8s（Kubernetes，容器编排平台）、ALB（应用型负载均衡）、OSS（对象存储）等工具采集 evidence（证据），基于证据做 diagnosis（根因诊断），给出 remediation（处置建议）。涉及生产高风险动作时，会进入 approval（人工审批），执行后还要做 verify（结果验证），最后生成 RCA（根因分析 / 故障复盘）。

所以它和 ChatBot（聊天机器人）的区别在于：**它不是一次性回答，而是有状态、有工具、有证据、有审批、有验证、有复盘的生产级工作流系统。**

---

# 2. 你这个 Agent（智能体）的主链路是怎么设计的？

**回答：**

主链路我会拆成几个标准节点：

```text
intake（工单接入 / 信息抽取）
→ triage（自动分诊）
→ retrieve_memory（检索历史经验 / 记忆召回）
→ planner（排查计划生成）
→ evidence_fanout（多源证据并行采集）
→ evidence_aggregate（证据聚合）
→ diagnose / diagnosis（根因诊断）
→ critic（诊断自检 / 反思校验）
→ remediation（处置建议生成）
→ risk_gate（风险门禁）
→ approval（人工审批）
→ executor（执行器）
→ verify（结果验证）
→ RCA（Root Cause Analysis，根因分析 / 故障复盘）
```

这里不是每个节点都必须依赖 LLM（Large Language Model，大语言模型）。像工单硬字段抽取、权限判断、风险等级判断、工具参数校验，可以更多依赖规则和结构化逻辑；planner（排查计划生成）、diagnosis（根因诊断）、RCA（根因分析 / 故障复盘）这类复杂判断才更适合用 LLM（大语言模型）。

这种设计的好处是，每个节点的输入输出都比较清楚，后续可以单独 eval（评测）、observe（观测）和 optimize（优化），不会变成一个不可控的大 Prompt（提示词）。

---

# 3. 你为什么要用 Workflow（工作流）/ State Machine（状态机），而不是让大模型一次性回答？

**回答：**

运维场景不能让大模型一次性自由发挥，因为生产故障处理有几个要求：要可控、可追踪、可恢复、可审批、可验证。

如果一次性让模型回答，它可能会漏查关键证据，也可能在证据不足时过早下结论，甚至给出危险操作建议。State Machine（状态机）的价值是把复杂任务拆成多个确定节点，比如先 triage（自动分诊），再 planner（排查计划生成），再 evidence collection（证据采集），再 diagnosis（根因诊断），再 approval（人工审批），再 verify（结果验证）。每个节点都有明确输入输出，可以记录 checkpoint（检查点 / 状态快照），失败后可以 retry（重试），审批时可以 pause（暂停），审批后可以 resume（恢复执行）。

所以我使用 Workflow（工作流）/ State Machine（状态机），本质是把大模型的不确定推理，放进一个可控的工程流程里。

---

# 4. 你的 Agent State（智能体状态）里应该保存哪些核心字段？

**回答：**

Agent State（智能体状态）需要保存一次故障处理的完整上下文，核心包括几类。

第一是 `IncidentContext（故障上下文）`，也就是工单结构化结果，包括服务名、环境、严重等级、故障类型、时间窗口、影响范围。

第二是 `Plan（排查计划）`，包括排查步骤、每一步需要什么 evidence（证据）、目标资源类型、候选工具、风险等级。

第三是 `Evidence（证据）`，也就是工具返回后标准化的证据，比如 ALB 5xx、K8s Pod（容器组）状态、MySQL 慢查询、OSS 访问异常。

第四是 `Diagnosis（根因诊断）`，包括候选根因、supporting evidence（支持证据）、contradicting evidence（反证）、confidence（置信度）。

第五是 `Remediation（处置建议）/ Approval（人工审批）/ Execution（执行结果）/ Verify（结果验证）/ RCA（根因分析 / 故障复盘）`，分别记录处置建议、审批状态、执行结果、验证结果和最终复盘产物。

这样 State（状态）不是简单聊天上下文，而是一次故障处理的结构化状态快照，方便 recovery（恢复）、replay（回放）和 audit（审计）。

---

# 5. 工单进来后，你如何把自然语言变成 Agent（智能体）可执行的结构化输入？

**回答：**

我不会直接把工单原文丢给模型生成排查计划，而是先把它转成标准 `IncidentContext（故障上下文）`。

具体分四步：

第一步，用 rule extraction（规则抽取）抽取硬字段，比如 P1/P2、prod（生产环境）/ test（测试环境）、时间、状态码、接口路径、服务名候选。

第二步，用 LLM（大语言模型）做 semantic extraction（语义抽取），识别故障类型、业务影响、用户猜测、缺失字段。比如区分“明确发生了 500”和“用户猜测可能是发布导致”。

第三步，通过 CMDB（Configuration Management Database，配置管理数据库）或 service catalog（服务目录）做资源补全，把“订单服务”映射成真实资源，比如 K8s cluster（K8s 集群）、namespace（命名空间）、workload（工作负载）、ALB instance（负载均衡实例）、MySQL database（数据库）、OSS bucket（对象存储桶）。

第四步，做 validation（校验）和 confidence（置信度）判断，比如服务是否存在、环境是否合法、时间窗口是否合理、缺失字段是否需要追问。

最终 planner（排查计划生成器）消费的是结构化 `IncidentContext（故障上下文）`，而不是原始工单文本。

---

# 6. 排查计划是怎么生成的？依据是什么？

**回答：**

排查计划不是大模型凭空生成的，它主要基于六类信息。

第一是 ticket symptom（工单症状），比如 5xx、timeout（超时）、403、Pod restart（Pod 重启）。

第二是 incident type（故障类型）分类，比如 `http_5xx（HTTP 5xx 错误）`、`mysql_slow_query（MySQL 慢查询）`、`oss_access_error（OSS 访问异常）`。

第三是 service topology（服务拓扑），也就是这个服务依赖哪些 ALB（负载均衡）、K8s（容器平台）、MySQL、OSS、下游服务。

第四是历史 SOP（Standard Operating Procedure，标准操作流程）、Runbook（运维手册）和 RCA（根因分析 / 故障复盘），提供相似故障经验。

第五是 Tool Registry（工具注册表），告诉 planner（排查计划生成器）当前有哪些工具可以用。

第六是当前已有 evidence（证据），支持动态调整后续排查方向。

所以排查计划本质上是：

```text
工单症状 + 故障类型 + 服务拓扑 + 历史经验 + 工具能力 + 当前证据
```

生成的不是普通文字，而是结构化 `PlanStep（排查步骤）`，每一步都要说明查什么、为什么查、用什么工具、期望得到什么证据。

---

# 7. 你如何避免 Planner（排查计划生成器）生成一个“看起来合理但不可执行”的排查计划？

**回答：**

关键是让 planner（排查计划生成器）输出 structured plan（结构化计划），而不是 free text（自由文本）。

每个 `PlanStep（排查步骤）` 至少要包含：

```text
step_id（步骤 ID）
goal（排查目标）
target_layer（目标层级）
resource_type（资源类型）
evidence_needed（需要的证据）
candidate_tools（候选工具）
required_params（必要参数）
risk_level（风险等级）
expected_output（预期输出）
```

比如不能只写“检查数据库是否异常”，而要写成“采集 MySQL 连接数、慢查询和锁等待证据，候选工具是 `mysql.get_connection_stats（获取 MySQL 连接状态）`、`mysql.get_slow_queries（获取 MySQL 慢查询）`”。

然后在执行前还要由 Tool Router（工具路由器）和 Tool Runtime（工具运行时 / 工具执行网关）校验：工具是否存在、参数是否完整、资源是否能通过 CMDB（配置管理数据库）补全、权限是否允许、是否需要 approval（人工审批）。

这样可以避免 planner（排查计划生成器）生成看起来正确但系统无法执行的计划。

---

# 8. 如果排查计划第一轮查完发现方向错了，Agent（智能体）如何调整？

**回答：**

排查计划不应该是一次性固定的，而应该支持：

```text
plan（规划） → act（执行） → observe（观察） → re-plan（重新规划）
```

比如一开始判断是接口 5xx，计划会同时查 ALB（负载均衡）、K8s（容器平台）、MySQL 和 deployment record（发布记录）。第一轮执行后，如果发现 ALB 5xx 升高、K8s Pod（容器组）正常，但 MySQL 连接数接近上限，那么下一轮计划就应该收敛到数据库方向，继续查 slow query（慢查询）、lock wait（锁等待）、connection pool（连接池）、最近 SQL 变更。

反过来，如果 MySQL 正常，但 K8s 出现 CrashLoopBackOff（容器反复崩溃重启），就应该继续查 Pod events（Pod 事件）、最近 image version（镜像版本）、deployment record（发布记录）和 container logs（容器日志）。

所以 Agent（智能体）不是一次性排查，而是根据 evidence（证据）动态调整 hypothesis（假设）和下一步 tool call（工具调用）。

---

# 9. MySQL、K8s、ALB、OSS 这些基础设施能力，你是怎么抽象成标准工具的？

**回答：**

我会把它们都抽象成统一的 `ToolDefinition（工具定义）`，而不是让 Agent（智能体）直接调用底层 API。

每个工具定义包括：

```text
name（工具名）
domain（所属领域），比如 mysql / k8s / alb / oss
description（工具用途）
capabilities（能力标签）
inputSchema（入参结构）
outputSchema（出参结构）
riskLevel（风险等级）
requiresApproval（是否需要审批）
timeoutMs（超时时间）
retryPolicy（重试策略）
```

比如 MySQL 可以有：

```text
mysql.get_connection_stats（获取 MySQL 连接状态）
mysql.get_slow_queries（获取 MySQL 慢查询）
```

K8s（Kubernetes，容器编排平台）可以有：

```text
k8s.get_pod_status（获取 Pod 状态）
k8s.get_events（获取 K8s 事件）
```

ALB（应用型负载均衡）可以有：

```text
alb.get_traffic_metrics（获取流量指标）
alb.get_backend_health（获取后端健康状态）
```

OSS（对象存储）可以有：

```text
oss.check_object_exists（检查对象是否存在）
oss.get_access_errors（获取访问异常）
```

这样 Agent（智能体）面对的是标准工具能力，不需要关心底层系统 SDK（软件开发工具包）的差异。

---

# 10. 生成排查计划后，Agent（智能体）如何选择具体工具？

**回答：**

工具选择不是靠 keyword matching（关键词匹配），而是通过 Tool Router（工具路由器）基于 evidence need（证据需求）做匹配。

`PlanStep（排查步骤）` 里会描述需要什么证据，比如 `5xx_rate（5xx 错误率）`、`backend_health（后端健康状态）`、`pod_status（Pod 状态）`、`slow_query（慢查询）`、`oss_403（OSS 403 权限错误）`。Tool Router（工具路由器）会拿这些 `evidenceNeeded（需要的证据）` 去 Tool Registry（工具注册表）里匹配工具的 `capabilities（能力标签）`。

同时还会结合 resource type（资源类型）、CMDB resource enrichment（CMDB 资源补全）、parameter completeness（参数完整度）、permission risk（权限风险）和 current evidence state（当前证据状态）。

比如排查步骤是“判断入口层是否异常”，需要 `5xx_rate（5xx 错误率）` 和 `backend_health（后端健康状态）`，就会选择 ALB 指标和后端健康检查工具。如果步骤是“判断服务是否重启或 OOM（Out of Memory，内存溢出）”，就会选择 K8s Pod 状态和 events（事件）工具。如果步骤是“判断数据库是否拖慢接口”，就会选择 MySQL 连接数、慢查询和锁等待工具。

所以工具选择过程是：

```text
排查步骤 → 证据需求 → 工具能力匹配 → 资源补全 → 参数校验 → 权限风控 → 执行
```

---

# 11. Tool Runtime（工具运行时 / 工具执行网关）在你的架构里解决什么问题？

**回答：**

Tool Runtime（工具运行时 / 工具执行网关）是 Agent（智能体）和生产系统之间的安全执行网关。

Agent（智能体）不能直接访问 MySQL、K8s、ALB、OSS，因为模型输出不稳定，可能参数错误、越权访问，甚至触发高风险动作。Tool Runtime（工具运行时）统一负责把模型生成的 tool call（工具调用）请求变成安全、可靠、可追踪的工程动作。

它主要做几件事：

```text
permission check（权限校验）：判断用户、Agent、服务、环境是否允许调用
parameter validation（参数校验）：按 inputSchema 校验字段、类型、范围
risk assessment（风险判断）：高风险动作是否需要审批
timeout and retry（超时重试）：处理工具失败、超时、云 API 抖动
data masking（结果脱敏）：避免敏感数据进入模型上下文
evidence normalization（证据标准化）：把结果转成 EvidenceRecord
audit logging（审计留痕）：记录谁调用、为什么调用、结果如何
```

所以 Tool Runtime（工具运行时）的价值不是简单封装 API，而是保证 Agent（智能体）可以接生产系统，但不能失控。

---

# 12. 如果大模型生成了一个危险操作，比如重启生产服务，你怎么拦截？

**回答：**

不能只靠 Prompt（提示词）约束，真正的拦截必须在工具执行层。

我会在 `ToolDefinition（工具定义）` 里给每个工具标记 `riskLevel（风险等级）` 和 `requiresApproval（是否需要审批）`。比如 `k8s.get_pod_status（获取 Pod 状态）` 是低风险只读工具，可以自动执行；但 `k8s.rollout_restart（重启工作负载）`、`rollback_deployment（回滚发布）`、`mysql.kill_session（终止数据库会话）`、`alb.modify_backend（修改负载均衡后端）` 都是高风险动作，必须审批。

当 Agent（智能体）调用这类工具时，Tool Runtime（工具运行时）会检查：

```text
是否是 prod（生产环境）
action risk level（动作风险等级）是多少
是否已有 approval_id（审批 ID）
approval_id 是否审批通过
审批动作和执行动作是否一致
审批资源和执行资源是否一致
```

如果没有审批，Runtime（运行时）直接返回 `REQUIRE_APPROVAL（需要审批）`，生成 ApprovalCard（审批卡片），展示风险、影响范围、支持证据和 rollback plan（回滚方案）。审批通过后才允许执行。

所以模型可以提出建议，但不能绕过 Tool Runtime（工具运行时）直接操作生产。

---

# 13. MySQL 工具如何防止 Agent（智能体）执行危险 SQL？

**回答：**

MySQL 工具我会优先设计成 templated readonly tools（模板化只读工具），而不是开放任意 SQL。

比如：

```text
mysql.get_connection_stats（获取连接状态）
mysql.get_slow_queries（获取慢查询）
mysql.get_lock_waits（获取锁等待）
mysql.explain_query（分析 SQL 执行计划）
mysql.get_table_status（获取表状态）
```

如果确实要提供 readonly query（只读查询），也要做严格限制：

```text
只允许 SELECT（查询）
禁止 UPDATE / DELETE / INSERT / DROP / ALTER
database/table whitelist（库表白名单）
field whitelist（字段白名单）
强制 LIMIT（限制返回行数）
query timeout（查询超时限制）
max scanned rows（最大扫描行数限制）
sensitive field masking（敏感字段脱敏）
result summarization（结果摘要化）
```

而且 MySQL account（MySQL 账号）本身也应该是 readonly account（只读账号），从数据库权限层兜底，不能只靠应用层判断。

所以安全策略是三层：**readonly account（只读账号）+ SQL policy validation（SQL 策略校验）+ Tool Runtime audit（工具运行时审计）**。

---

# 14. K8s（Kubernetes，容器编排平台）工具如何设计安全边界？

**回答：**

K8s 工具也要分 readonly tools（只读工具）和 action tools（动作工具）两类。

只读工具包括：

```text
k8s.get_pod_status（获取 Pod 状态）
k8s.get_events（获取 K8s 事件）
k8s.get_pod_logs_summary（获取 Pod 日志摘要）
k8s.describe_deployment（查看 Deployment 详情）
k8s.get_resource_usage（获取资源使用情况）
```

这些可以自动执行，但要限制 namespace（命名空间）、日志行数、时间窗口，并做 sensitive data masking（敏感信息脱敏）。

动作工具包括：

```text
k8s.rollout_restart（重启工作负载）
k8s.scale_deployment（扩缩容 Deployment）
k8s.rollback_deployment（回滚 Deployment）
```

这些在 prod（生产环境）必须进入 approval（人工审批）。

底层还要使用 least privilege ServiceAccount（最小权限服务账号）和 RBAC（Role-Based Access Control，基于角色的访问控制）。比如只允许读指定 namespace（命名空间）的 Pod、Deployment、Event，不允许任意 exec（进入容器执行命令），不允许执行 shell，不允许跨 namespace 操作。

所以 K8s 的安全边界是：**最小 RBAC（基于角色的访问控制）+ namespace whitelist（命名空间白名单）+ 禁止任意 exec（容器命令执行）+ 高危动作审批**。

---

# 15. 你如何把不同工具返回的数据变成 Agent（智能体）能理解的证据？

**回答：**

我会在 Tool Adapter（工具适配器）后面加一层 Evidence Normalizer（证据标准化器），把不同工具的原始结果统一成 `EvidenceRecord（证据记录）`。

因为 MySQL、K8s、ALB、OSS 返回格式都不一样，如果直接丢给模型，diagnosis（根因诊断）会很混乱。

标准 `EvidenceRecord（证据记录）` 包括：

```text
evidence_id（证据 ID）
source_tool（来源工具）
resource_type（资源类型）
resource_id（资源 ID）
time_range（时间范围）
status（状态）：normal / warning / critical
finding（关键发现）
key_metrics（关键指标）
supports（支持哪些根因）
contradicts（反驳哪些根因）
confidence（置信度）
```

比如 MySQL 返回连接数 198/200，Normalizer（标准化器）会转成：

```text
MySQL 连接数接近上限，支持 mysql_connection_exhausted（MySQL 连接耗尽）根因。
```

K8s 返回 Pod 无重启，则会转成：

```text
Pod 状态正常，反驳 pod_crash（Pod 崩溃）/ oom_killed（内存溢出被杀）根因。
```

这样 Diagnosis（根因诊断）节点消费的是统一证据，而不是各种原始 API 结果。

---

# 16. 你的根因诊断是如何避免 hallucination（幻觉）的？

**回答：**

核心原则是：**diagnosis（根因诊断）必须基于 evidence（证据），不允许无证据下结论。**

具体做法有几层。

第一，Diagnosis（根因诊断）节点输入的是标准 `EvidenceRecord（证据记录）`，而不是原始日志堆砌。

第二，每个 `root cause candidate（候选根因）` 都必须绑定 `supportingEvidenceIds（支持证据 ID）` 和 `contradictingEvidenceIds（反证 ID）`。也就是说，它要说明哪些证据支持这个根因，哪些证据反驳这个根因。

第三，输出时要给 `confidence（置信度）`，并区分 fact（事实）和 hypothesis（推测）。比如“ALB 5xx 升高”是事实，“可能由 MySQL 连接池耗尽引发”是推断。

第四，可以增加 Critic（诊断自检 / 反思校验）节点，对诊断结果做自检，检查是否 evidence insufficient（证据不足）、是否忽略反证、是否 premature conclusion（过早下结论）、是否需要补充 tool call（工具调用）。

所以不是让模型凭经验猜，而是让模型在证据约束下做诊断。

---

# 17. 如果多个证据互相冲突，比如 ALB 5xx 升高但 K8s Pod 正常，Agent（智能体）怎么处理？

**回答：**

冲突证据不能简单忽略，而要显式记录成 contradicting evidence（反证）。

比如 ALB 5xx 升高说明用户侧确实有错误，但 K8s Pod 正常说明问题可能不在 Pod 崩溃或 OOM。这时 Diagnosis（根因诊断）不应该继续坚持 K8s 根因，而是降低 `pod_crash（Pod 崩溃）` 的 confidence（置信度），并继续扩展到其他方向，比如 MySQL、downstream service（下游服务）、deployment record（发布记录）、gateway config（网关配置）。

所以我会让 `EvidenceRecord（证据记录）` 支持：

```text
supports（支持哪些根因）
contradicts（反驳哪些根因）
```

诊断时根据 supporting evidence（支持证据）和 contradicting evidence（反证）综合打分。如果关键证据冲突，就触发下一轮补充排查，而不是直接下结论。

这也是 Agent（智能体）相比固定脚本的价值：它可以基于证据动态调整 hypothesis（假设）。

---

# 18. 你说项目要可评测，具体怎么评？指标是什么？

**回答：**

Eval（评测）不是看 Agent（智能体）回答得像不像，而是用固定 case（测试用例）和指标判断它有没有变好。

我会构建 offline eval set（离线评测集），每个 case（用例）包含：

```text
ticket input（工单输入）
expected incident type（期望故障类型）
expected service and env（期望服务和环境）
expected evidence sources（期望证据源）
expected root cause（期望根因）
expected risk level（期望风险等级）
tool fixture（固定工具返回数据）
```

然后每次修改 Prompt（提示词）、Planner（排查计划生成器）、Tool Router（工具路由器）或 RAG（Retrieval-Augmented Generation，检索增强生成）后，自动 replay（回放）这些 case，输出指标。

核心指标包括：

```text
ticket extraction accuracy（工单结构化准确率）
triage accuracy（分诊准确率）
plan coverage（排查计划覆盖率）
tool selection accuracy（工具选择准确率）
root cause Top1 / Top3 accuracy（根因 Top1 / Top3 命中率）
risk level accuracy（风险等级准确率）
average steps（平均步骤数）
average latency（平均耗时）
human takeover rate（人工接管率）
RCA quality score（RCA 质量评分）
```

比如一个 5xx case，标准期望要查 ALB、K8s、MySQL、deployment record（发布记录）。如果 Agent 只查了日志，最终即使猜对根因，plan coverage（排查计划覆盖率）也不高。

这样 Agent 迭代就不是凭感觉，而是可以用数据证明有没有提升。

---

# 19. 你说项目要可观测，具体要观测哪些内容？怎么实现？

**回答：**

Observability（可观测性）的目标是把 Agent（智能体）从 black box（黑盒）变成可 replay（回放）的工作流。

我会用统一 ID 串联一次任务：

```text
run_id（运行 ID）
node_id（节点 ID）
llm_call_id（模型调用 ID）
tool_call_id（工具调用 ID）
evidence_id（证据 ID）
approval_id（审批 ID）
```

然后通过 Event Log（事件日志）记录关键事件：

```text
run.started（运行开始）
node.started（节点开始）
node.completed（节点完成）
llm.completed（模型调用完成）
tool.started（工具调用开始）
tool.completed（工具调用完成）
tool.failed（工具调用失败）
evidence.created（证据创建）
approval.required（需要审批）
approval.completed（审批完成）
run.completed（运行完成）
```

具体要观测六层：

```text
Run 层（运行层）：任务状态、耗时、最终结论
Node 层（节点层）：每个节点输入输出和耗时
LLM 层（模型层）：模型、Prompt 版本、Token、耗时、解析状态
Tool 层（工具层）：工具名、参数摘要、资源、结果、重试、错误
Evidence 层（证据层）：证据来源、支持哪个根因、是否有反证
Human 层（人工层）：审批人、审批结果、人工接管
```

前端可以通过 SSE（Server-Sent Events，服务端事件推送）或 WebSocket（双向通信协议）订阅 run events（运行事件），在 RunDetail（运行详情）页面展示 timeline（时间线）、tool calls（工具调用）、evidence board（证据看板）和 approval status（审批状态）。

这样一旦误判，可以定位到底是工单抽取错、planner（排查计划生成）漏查、tool call（工具调用）失败，还是 diagnosis（根因诊断）没用上关键证据。

---

# 20. 如果这个系统要从 Demo（演示原型）走向 Production（生产环境），你认为最大的三个架构风险是什么？怎么解决？

**回答：**

我认为最大的三个风险是：model uncertainty（模型不可控）、production safety（生产操作安全）、scalability（规模化运行）。

第一，model uncertainty（模型不可控）。  
大模型可能误解工单、漏查证据、过早下结论。解决方式是用 structured Workflow（结构化工作流）约束它，把任务拆成 intake（工单接入）、planner（排查计划）、evidence（证据）、diagnosis（诊断）、critic（自检）等节点；诊断必须基于 `EvidenceRecord（证据记录）`；关键结论要有 evidence citation（证据引用）；必要时通过 Critic（诊断自检）和 human confirmation（人工确认）兜底。

第二，production safety（生产操作安全）风险。  
运维 Agent 可能触发 restart（重启）、rollback（回滚）、scale up/down（扩缩容）、kill session（终止会话）等高风险动作。解决方式是 Tool Runtime（工具运行时）+ RiskPolicy（风险策略），把所有工具分级，只读工具自动执行，高风险工具必须 approval（审批）；没有 `approval_id（审批 ID）` 或审批未通过不能执行；执行后还要 verify（验证）和 audit（审计）。

第三，scalability（规模化运行）风险。  
真实场景里会有多工单、多工具、多团队并发，如果同步执行很容易阻塞或打爆基础设施。解决方式是 Run（运行任务）+ Queue（队列）+ Worker（后台执行器）架构，长任务异步执行；state（状态）、checkpoint（检查点）、event（事件）、tool call（工具调用）、evidence（证据）持久化；工具调用做 rate limiting（限流）、circuit breaker（熔断）和 retry（重试）；多团队做 permission isolation（权限隔离）。

所以从 Demo（演示原型）到 Production（生产环境），不是简单多接几个工具，而是要补齐 eval（评测）、observability（可观测）、reusability（可复用）、scalability（可扩展）、auditability（可审计）这些工程能力。

---

# 20 题超短背诵索引

```text
1. ChatBot（聊天机器人） vs Agent（智能体）：问答 vs 工作流闭环
2. 主链路：工单 → 分诊 → 计划 → 工具 → 证据 → 诊断 → 审批 → 验证 → RCA
3. State Machine（状态机）价值：可控、可恢复、可审批、可追踪
4. State（状态）：工单、计划、证据、诊断、审批、执行、RCA
5. 工单结构化：规则 + LLM（大语言模型）+ CMDB（配置管理数据库）+ 校验
6. 排查计划：症状 + 拓扑 + SOP（标准操作流程）+ 工具 + 证据
7. 可执行计划：PlanStep（排查步骤）结构化，不是自由文本
8. 动态调整：plan-act-observe-replan（规划-执行-观察-重新规划）
9. 工具标准化：ToolDefinition（工具定义）
10. 工具选择：evidenceNeeded（证据需求）匹配 capabilities（能力标签）
11. Tool Runtime（工具运行时）：权限、参数、审批、重试、审计
12. 危险动作：Runtime（运行时）强制审批，不靠 Prompt（提示词）
13. MySQL 安全：只读、白名单、LIMIT、脱敏
14. K8s 安全：RBAC（基于角色的访问控制）、namespace（命名空间）、禁 exec（容器命令执行）、高危审批
15. 证据标准化：EvidenceRecord（证据记录）
16. 防幻觉：根因必须绑定证据和反证
17. 冲突证据：降低置信度，触发补充排查
18. 可评测：offline eval set（离线评测集）+ 指标回放
19. 可观测：Trace ID（链路追踪 ID）+ Event Log（事件日志）+ RunDetail（运行详情）
20. 生产风险：model uncertainty（模型不可控）、production safety（生产安全）、scalability（规模化）
```

## Prompt:
2026/5/15 15:21:03

`可评测`中，需要收集的指标有哪些

## Response:
2026/5/15 15:21:05

`可评测`里不要只收集“最终答案对不对”，而是要按 Agent 链路分层收集指标。

你可以记成 6 类：

```text
1. 输入理解指标
2. 规划质量指标
3. 工具调用指标
4. 诊断效果指标
5. 安全风控指标
6. 业务结果指标
```

---

# 1. 输入理解指标：工单有没有理解对

衡量 Agent 有没有把工单转成正确的 `IncidentContext（故障上下文）`。

| 指标 | 含义 |
|---|---|
| `service_extraction_accuracy（服务抽取准确率）` | 是否识别对故障服务，比如 order-service |
| `env_extraction_accuracy（环境抽取准确率）` | 是否识别 prod / test / staging |
| `severity_accuracy（严重等级准确率）` | 是否判断对 P0 / P1 / P2 |
| `symptom_classification_accuracy（故障现象分类准确率）` | 是否识别为 5xx、超时、OSS 403、Pod 重启等 |
| `time_range_accuracy（时间窗口准确率）` | 是否抽取对故障开始时间和排查时间范围 |
| `resource_mapping_accuracy（资源映射准确率）` | 是否通过 CMDB 映射到正确 K8s、MySQL、ALB、OSS 资源 |

面试里可以说：

> 第一类是输入理解指标，主要看工单结构化是否准确。因为服务名、环境、时间窗口一旦抽错，后面的排查计划和工具调用都会跑偏。

---

# 2. 规划质量指标：排查计划有没有覆盖关键路径

衡量 `planner（排查计划生成器）` 生成的计划是否合理。

| 指标 | 含义 |
|---|---|
| `plan_coverage（排查计划覆盖率）` | 是否覆盖期望证据源，比如 ALB、K8s、MySQL、发布记录 |
| `critical_step_recall（关键步骤召回率）` | 必查步骤有没有漏掉 |
| `invalid_step_rate（无效步骤率）` | 有没有生成不可执行、无关或重复步骤 |
| `over_check_rate（过度排查率）` | 是否调用太多无关工具 |
| `plan_executable_rate（计划可执行率）` | PlanStep 是否有资源、参数、工具映射 |
| `replan_success_rate（重规划成功率）` | 第一轮证据回来后，是否能正确调整方向 |

一个简单公式：

```text
排查计划覆盖率 = 命中的期望证据类别数 / 期望证据类别总数
```

比如 5xx 故障期望查：

```text
ALB 指标、ALB 后端健康、K8s Pod、应用日志、MySQL、发布记录
```

Agent 实际只查了：

```text
应用日志、MySQL、K8s Pod
```

那么覆盖率就是：

```text
3 / 6 = 50%
```

---

# 3. 工具调用指标：工具有没有选对、用好、稳定执行

衡量 `Tool Router（工具路由器）` 和 `Tool Runtime（工具运行时）` 的效果。

| 指标 | 含义 |
|---|---|
| `tool_selection_accuracy（工具选择准确率）` | 需要某类证据时，是否选对工具 |
| `tool_call_success_rate（工具调用成功率）` | 工具调用成功次数 / 总调用次数 |
| `tool_timeout_rate（工具超时率）` | 工具调用超时比例 |
| `tool_retry_rate（工具重试率）` | 调用中发生重试的比例 |
| `tool_error_rate（工具错误率）` | 参数错误、权限错误、资源不存在等比例 |
| `redundant_tool_call_rate（重复工具调用率）` | 是否重复查同一类证据 |
| `unsafe_tool_block_rate（危险工具拦截率）` | 高风险动作是否被正确拦截 |
| `avg_tool_latency（平均工具耗时）` | 工具平均响应时间 |

面试里可以重点讲：

> 工具调用指标不只是看成功率，还要看工具选得准不准、是否重复调用、是否超时、是否正确拦截高风险动作。

---

# 4. 诊断效果指标：根因有没有判断对

这是 Agent 效果最核心的部分。

| 指标 | 含义 |
|---|---|
| `root_cause_top1_accuracy（根因 Top1 命中率）` | 第一根因是否命中标准答案 |
| `root_cause_top3_accuracy（根因 Top3 命中率）` | 前三个候选根因是否包含标准答案 |
| `evidence_citation_rate（证据引用率）` | 根因是否绑定 evidence_id |
| `evidence_support_score（证据支撑度）` | 结论是否有足够证据支持 |
| `false_positive_rate（误报率）` | 把不是根因的问题判断成根因 |
| `false_negative_rate（漏报率）` | 漏掉真实根因 |
| `confidence_calibration（置信度校准）` | 置信度和真实准确率是否匹配 |
| `contradiction_handling_rate（反证处理率）` | 遇到冲突证据时是否正确降低置信度或补查 |

最关键是这两个：

```text
根因 Top1 命中率
根因 Top3 命中率
```

比如标准根因是：

```text
MySQL 连接池耗尽
```

Agent 输出：

```text
1. MySQL 连接池耗尽
2. order-service 线程阻塞
3. ALB 后端健康异常
```

那么：

```text
Top1 命中：是
Top3 命中：是
```

如果 Agent 输出：

```text
1. K8s Pod OOM
2. 发布回归
3. OSS 访问异常
```

那么：

```text
Top1 未命中
Top3 未命中
```

---

# 5. 安全风控指标：有没有误操作风险

运维 Agent 一定要收集安全指标。

| 指标 | 含义 |
|---|---|
| `risk_level_accuracy（风险等级准确率）` | 是否正确判断 P0/P1/P2 或 low/high risk |
| `approval_required_accuracy（审批判断准确率）` | 高风险动作是否正确进入审批 |
| `unsafe_action_prevention_rate（危险动作阻断率）` | 危险动作是否被 Tool Runtime 阻断 |
| `unauthorized_access_block_rate（越权访问拦截率）` | 用户无权限访问资源时是否被拒绝 |
| `approval_pass_rate（审批通过率）` | Agent 生成的高风险建议被审批通过比例 |
| `manual_override_rate（人工修改率）` | 人工是否频繁修改 Agent 建议 |
| `rollback_suggestion_coverage（回滚方案覆盖率）` | 高风险建议是否带回滚方案 |

这里面最重要的是：

```text
approval_required_accuracy（审批判断准确率）
unsafe_action_prevention_rate（危险动作阻断率）
```

因为架构师面试会很关心：

> 你怎么防止 Agent 误操作生产环境？

---

# 6. 业务结果指标：对真实运维效率有没有帮助

这类指标最适合写简历和讲成果。

| 指标 | 含义 |
|---|---|
| `MTTA（Mean Time To Acknowledge，平均响应时间）` | 从告警到开始处理的时间 |
| `MTTD（Mean Time To Diagnose，平均诊断时间）` | 从工单创建到定位根因的时间 |
| `MTTR（Mean Time To Recovery，平均恢复时间）` | 从故障发生到恢复的时间 |
| `automation_rate（自动化处理率）` | Agent 自动完成排查步骤的比例 |
| `human_takeover_rate（人工接管率）` | 需要人工中断接管的比例 |
| `recommendation_adoption_rate（建议采纳率）` | Agent 处置建议被采纳的比例 |
| `rca_acceptance_rate（RCA 通过率）` | RCA 被人工确认通过的比例 |
| `repeat_incident_reduction（重复故障下降率）` | 相似故障是否减少 |

面试里最好这样说：

> 技术指标证明 Agent 能力，业务指标证明 Agent 价值。比如根因命中率是能力指标，MTTD 和 MTTR 下降才是业务价值指标。

---

# 7. 最小必须收集的 10 个核心指标

如果你不想讲太散，就重点讲这 10 个：

```text
1. 工单结构化准确率
2. 分诊准确率
3. 排查计划覆盖率
4. 工具选择准确率
5. 工具调用成功率
6. 根因 Top1 命中率
7. 根因 Top3 命中率
8. 风险等级准确率
9. 人工接管率
10. 平均诊断时间 MTTD
```

这 10 个已经能覆盖：

```text
理解能力
规划能力
工具能力
诊断能力
安全能力
业务价值
```

---

# 8. 面试表达版

你可以这样说：

> 我会把运维 Agent 的可评测指标分成六类。第一是输入理解指标，比如服务名、环境、时间窗口、故障类型抽取准确率；第二是规划质量指标，比如排查计划覆盖率、关键步骤召回率和计划可执行率；第三是工具调用指标，比如工具选择准确率、工具成功率、超时率和重复调用率；第四是诊断效果指标，比如根因 Top1/Top3 命中率、证据引用率和反证处理率；第五是安全风控指标，比如风险等级准确率、审批判断准确率和危险动作阻断率；第六是业务结果指标，比如平均诊断时间 MTTD、平均恢复时间 MTTR、建议采纳率和人工接管率。  
>
> 如果先做最小闭环，我会优先收集 10 个核心指标：工单结构化准确率、分诊准确率、排查计划覆盖率、工具选择准确率、工具调用成功率、根因 Top1 命中率、根因 Top3 命中率、风险等级准确率、人工接管率和平均诊断时间。这样既能评估 Agent 的技术能力，也能评估它对运维效率的真实价值。

一句话版：

> **可评测指标要覆盖“理解是否正确、计划是否完整、工具是否选对、根因是否命中、风险是否可控、效率是否提升”这六个层面。**

## Prompt:
2026/5/15 15:34:48

你一直说的top1、top3指的是什么

## Response:
2026/5/15 15:34:49

`Top1`、`Top3` 是评估 **Agent 根因诊断准确率** 的指标。

简单理解：

> **Top1 = Agent 排在第 1 位的答案有没有命中真实根因。**  
> **Top3 = Agent 给出的前 3 个候选答案里，有没有包含真实根因。**

---

## 举个运维故障例子

真实根因是：

```text
MySQL 连接池耗尽
```

Agent 输出了 3 个候选根因：

```text
1. MySQL 连接池耗尽
2. order-service 线程池阻塞
3. ALB 后端实例不健康
```

那么：

```text
Top1 命中：是
Top3 命中：是
```

因为真实根因排在第 1 位。

---

再看一个例子。

真实根因还是：

```text
MySQL 连接池耗尽
```

Agent 输出：

```text
1. K8s Pod 重启
2. ALB 后端健康检查失败
3. MySQL 连接池耗尽
```

那么：

```text
Top1 命中：否
Top3 命中：是
```

因为第 1 个答案错了，但前 3 个候选里包含了真实根因。

---

再看一个失败例子。

真实根因：

```text
MySQL 连接池耗尽
```

Agent 输出：

```text
1. K8s Pod OOM
2. 最近发布导致接口异常
3. OSS 权限异常
```

那么：

```text
Top1 命中：否
Top3 命中：否
```

因为前三个都没有命中真实根因。

---

## 为什么要同时看 Top1 和 Top3？

因为运维诊断经常不是一次就能 100% 确定根因。

Agent 很可能会输出：

```text
候选根因 1：数据库连接池耗尽，置信度 0.72
候选根因 2：最近发布引入慢 SQL，置信度 0.64
候选根因 3：下游库存服务超时，置信度 0.51
```

这时候：

```text
Top1 看的是：Agent 最确信的判断准不准
Top3 看的是：Agent 有没有把正确方向纳入候选范围
```

换句话说：

```text
Top1 衡量最终判断能力
Top3 衡量排查方向召回能力
```

---

## 用在面试里的说法

你可以这样讲：

> Top1 和 Top3 是根因诊断评测指标。Top1 表示 Agent 排在第一位的根因是否命中真实根因，Top3 表示 Agent 给出的前三个候选根因里是否包含真实根因。  
>
> 在运维场景里，我会同时看这两个指标。Top1 代表 Agent 最终判断是否准确，Top3 代表 Agent 是否至少把正确排查方向纳入候选。如果 Top3 高但 Top1 低，说明 Agent 能找到方向，但排序和置信度判断还不够好；如果 Top3 也低，说明排查计划、工具选择或证据采集阶段可能就已经漏掉了关键线索。

一句话：

> **Top1 看“第一判断准不准”，Top3 看“前三个候选里有没有正确答案”。**

## Prompt:
2026/5/15 15:42:02

这些指标都是怎么计算的

## Response:
2026/5/15 15:42:07

> **解释评估指标的计算方法**
>
> 用户提到的“这些指标”应该是指前面提到的各类指标。我们需要解释如何计算，并简要描述这些指标的收集方式。主要涉及的指标类别包括输入理解、规划、工具使用、诊断、安全和商业等。每个场景可能需要黄金标准标签，根据实际运行记录进行比较。还需包含Top1/Top3指标，并讨论模糊匹配/语义匹配的注意事项。
>
> **在线指标的计算方法**
>
> 关于在线指标，没有统一的标准答案，通常是从日志中得出的。需要包含“分子分母”，因为用户特别喜欢这个表达。通过“分子分母”的方式，能够更清晰地描述计算公式和过程。
>
> 已思考 11s

这些指标的计算核心就一句话：

> **先准备“标准答案”，再让 Agent 跑一遍，最后比较“Agent 实际输出”和“标准答案”的差异。**

也就是：

```text
指标 = 实际结果 vs 期望结果
```

分两类：

```text
离线评测指标：有标准答案，可以算准确率、召回率、命中率
在线运行指标：没有标准答案，主要从日志里统计成功率、耗时、接管率、采纳率
```

---

# 1. 先准备评测 Case

比如一个标准 Case：

```json
{
  "caseId": "order_5xx_mysql_connection",
  "ticket": "订单服务 14:20 开始 500 增多，用户无法下单，生产环境 P1",
  "expected": {
    "service": "order-service",
    "env": "prod",
    "severity": "P1",
    "symptom": "http_5xx",
    "expectedEvidenceCategories": [
      "alb_metrics",
      "alb_backend_health",
      "k8s_pod_status",
      "mysql_connection",
      "app_logs",
      "deployment_record"
    ],
    "expectedTools": [
      "alb.get_traffic_metrics",
      "alb.get_backend_health",
      "k8s.get_pod_status",
      "mysql.get_connection_stats"
    ],
    "rootCause": "mysql_connection_exhausted",
    "riskLevel": "P1",
    "requiresApproval": true
  }
}
```

Agent 跑完后会产出：

```json
{
  "actual": {
    "service": "order-service",
    "env": "prod",
    "severity": "P1",
    "symptom": "http_5xx",
    "actualEvidenceCategories": [
      "alb_metrics",
      "k8s_pod_status",
      "mysql_connection"
    ],
    "actualTools": [
      "alb.get_traffic_metrics",
      "k8s.get_pod_status",
      "mysql.get_connection_stats"
    ],
    "rootCauseCandidates": [
      "mysql_connection_exhausted",
      "order_service_thread_blocked",
      "alb_backend_unhealthy"
    ],
    "riskLevel": "P1",
    "requiresApproval": true
  }
}
```

然后所有指标都是围绕 `expected` 和 `actual` 做对比。

---

# 2. 输入理解指标怎么算？

## 2.1 服务抽取准确率

看 Agent 是否抽对服务名。

```text
service_extraction_accuracy
= 服务名抽取正确的 case 数 / 总 case 数
```

例子：

```text
100 个工单里，Agent 有 92 个抽对 service
服务抽取准确率 = 92 / 100 = 92%
```

---

## 2.2 环境抽取准确率

```text
env_extraction_accuracy
= 环境抽取正确的 case 数 / 总 case 数
```

比如 expected 是 `prod`，actual 也是 `prod`，就是正确。

---

## 2.3 严重等级准确率

```text
severity_accuracy
= 严重等级判断正确的 case 数 / 总 case 数
```

比如 expected 是 `P1`，Agent 判断成 `P2`，就是错误。

---

## 2.4 故障类型分类准确率

```text
symptom_classification_accuracy
= 故障类型判断正确的 case 数 / 总 case 数
```

比如：

```text
expected: http_5xx
actual: http_5xx
正确
```

```text
expected: mysql_slow_query
actual: k8s_pod_crash
错误
```

---

## 2.5 时间窗口准确率

这个不能只做完全匹配，因为时间可能有轻微偏差。

可以设置容忍范围：

```text
如果 expected start_time 和 actual start_time 差距 <= 5 分钟，则算正确
```

公式：

```text
time_range_accuracy
= 时间窗口抽取正确的 case 数 / 总 case 数
```

---

## 2.6 资源映射准确率

比如 CMDB 应该把 `order-service` 映射到：

```text
cluster = prod-shenzhen-01
namespace = order
workload = order-service
mysql = order_db
alb = alb-prod-order
```

Agent 实际映射了其中 4 个正确，1 个错误。

可以按字段算：

```text
resource_mapping_accuracy
= 正确映射的资源字段数 / 应映射的资源字段总数
```

例子：

```text
正确 4 个，总共 5 个
资源映射准确率 = 4 / 5 = 80%
```

---

# 3. 规划质量指标怎么算？

## 3.1 排查计划覆盖率

这是最重要的规划指标。

```text
plan_coverage
= Agent 实际覆盖的期望证据类别数 / 标准答案要求的证据类别总数
```

比如 5xx 故障标准要求查 6 类：

```text
ALB 指标
ALB 后端健康
K8s Pod
应用日志
MySQL 连接
发布记录
```

Agent 实际查了 4 类：

```text
ALB 指标
K8s Pod
MySQL 连接
应用日志
```

那么：

```text
plan_coverage = 4 / 6 = 66.7%
```

---

## 3.2 关键步骤召回率

有些步骤是必须查的，比如 5xx 场景下 ALB 和 K8s 是必查。

```text
critical_step_recall
= 命中的必查步骤数 / 标准答案中的必查步骤数
```

例子：

```text
必查步骤：ALB 指标、K8s Pod、MySQL 连接
Agent 命中：ALB 指标、MySQL 连接
critical_step_recall = 2 / 3 = 66.7%
```

---

## 3.3 无效步骤率

看 Agent 有没有生成无关步骤。

```text
invalid_step_rate
= 无效步骤数 / Agent 生成的总步骤数
```

比如 Agent 生成了 10 个步骤，其中 2 个和故障无关：

```text
invalid_step_rate = 2 / 10 = 20%
```

---

## 3.4 过度排查率

比无效步骤更宽一点，表示 Agent 是否查得太散、太浪费。

```text
over_check_rate
= 非必要工具调用数 / 总工具调用数
```

比如一个 MySQL 连接池耗尽问题，Agent 又查了 OSS、CDN、支付下游 3 个无关方向，这些就算过度排查。

---

## 3.5 计划可执行率

看生成的 PlanStep 是否真的能执行。

```text
plan_executable_rate
= 可执行步骤数 / 总计划步骤数
```

一个步骤是否可执行，通常看：

```text
是否有明确 resourceType
是否能匹配到工具
是否参数完整
是否资源能通过 CMDB 补齐
是否没有违反权限和风险规则
```

例子：

```text
Agent 生成 8 个步骤，6 个能匹配工具并执行
计划可执行率 = 6 / 8 = 75%
```

---

# 4. 工具调用指标怎么算？

## 4.1 工具选择准确率

看 Agent 需要某类证据时，是否选对工具。

```text
tool_selection_accuracy
= 选对工具的步骤数 / 需要选择工具的步骤总数
```

或者按工具集合算：

```text
tool_selection_accuracy
= 命中的期望工具数 / 期望工具总数
```

例子：

标准期望工具：

```text
alb.get_traffic_metrics
k8s.get_pod_status
mysql.get_connection_stats
```

Agent 实际选择：

```text
alb.get_traffic_metrics
k8s.get_pod_logs
mysql.get_connection_stats
```

命中 2 个，总共 3 个：

```text
tool_selection_accuracy = 2 / 3 = 66.7%
```

---

## 4.2 工具调用成功率

这是从真实运行日志里统计。

```text
tool_call_success_rate
= 成功工具调用次数 / 总工具调用次数
```

例子：

```text
总共调用 1000 次工具，成功 940 次
工具调用成功率 = 94%
```

---

## 4.3 工具超时率

```text
tool_timeout_rate
= 超时工具调用次数 / 总工具调用次数
```

例子：

```text
1000 次工具调用里，50 次超时
工具超时率 = 5%
```

---

## 4.4 工具重试率

```text
tool_retry_rate
= 发生过重试的工具调用次数 / 总工具调用次数
```

如果一次调用重试了 2 次，也可以单独统计：

```text
avg_retry_count
= 总重试次数 / 总工具调用次数
```

---

## 4.5 工具错误率

```text
tool_error_rate
= 失败工具调用次数 / 总工具调用次数
```

失败原因可以再拆：

```text
参数错误率
权限错误率
资源不存在率
外部 API 错误率
超时率
```

---

## 4.6 重复工具调用率

```text
redundant_tool_call_rate
= 重复或无必要工具调用次数 / 总工具调用次数
```

比如同一个 run 里连续查了 3 次相同时间窗口的 `mysql.get_connection_stats`，但中间没有新证据变化，就算重复。

---

# 5. 诊断效果指标怎么算？

## 5.1 根因 Top1 命中率

```text
root_cause_top1_accuracy
= Top1 根因命中的 case 数 / 总 case 数
```

例子：

```text
100 个故障 case
Agent 第 1 个根因命中 68 个
Top1 命中率 = 68%
```

---

## 5.2 根因 Top3 命中率

```text
root_cause_top3_accuracy
= 前 3 个候选根因包含正确根因的 case 数 / 总 case 数
```

例子：

```text
100 个故障 case
有 84 个 case 的前三个候选里包含真实根因
Top3 命中率 = 84%
```

解释：

```text
Top1 看最终判断是否准确
Top3 看正确方向有没有被纳入候选
```

---

## 5.3 证据引用率

看 Agent 给出的根因是否绑定证据。

```text
evidence_citation_rate
= 带 evidence_id 的根因数量 / 总根因数量
```

比如 Agent 输出 100 个候选根因，其中 85 个绑定了 evidence_id：

```text
证据引用率 = 85%
```

---

## 5.4 证据支撑度

这个通常需要打分，可以用规则或人工标注。

比如满分 5 分：

```text
5 分：根因有 3 条以上强证据支持，并且时间窗口一致
4 分：有 2 条有效证据支持
3 分：有 1 条证据支持
2 分：证据弱或间接
1 分：几乎无证据
0 分：无证据或证据相反
```

最终：

```text
evidence_support_score
= 所有 case 的证据支撑得分平均值
```

---

## 5.5 误报率和漏报率

以某个根因类型为例，比如 `mysql_connection_exhausted`。

```text
TP = 真实是这个根因，Agent 也判断是
FP = 真实不是这个根因，Agent 却判断是
FN = 真实是这个根因，Agent 没判断出来
TN = 真实不是这个根因，Agent 也没判断
```

误报率：

```text
false_positive_rate
= FP / (FP + TN)
```

漏报率：

```text
false_negative_rate
= FN / (FN + TP)
```

实际面试里不用讲太公式化，可以说：

> 误报率看 Agent 有没有把不是根因的问题误判成根因；漏报率看 Agent 有没有漏掉真实根因。

---

## 5.6 置信度校准

这个稍微高级。

Agent 可能说：

```text
我有 90% 把握是 MySQL 问题
```

那你要看它在所有 90% 置信度的 case 里，实际准确率是不是也接近 90%。

简单做法：

```text
把置信度按区间分桶：
0.9-1.0
0.8-0.9
0.7-0.8
...
```

然后统计每个桶的真实准确率。

比如：

```text
Agent 置信度 0.8-0.9 的 case 有 100 个
实际命中 60 个
说明置信度虚高
```

这个指标用于判断 Agent 是否过度自信。

---

# 6. 安全风控指标怎么算？

## 6.1 风险等级准确率

```text
risk_level_accuracy
= 风险等级判断正确的 case 数 / 总 case 数
```

比如 expected 是高风险，Agent 判断成低风险，就是严重错误。

---

## 6.2 审批判断准确率

看该审批的动作有没有进入审批，不该审批的动作有没有误拦。

```text
approval_required_accuracy
= 审批判断正确的动作数 / 总动作数
```

例子：

```text
100 个动作建议
其中 30 个应该审批，70 个不需要审批
Agent 对 92 个动作判断正确
审批判断准确率 = 92%
```

---

## 6.3 危险动作阻断率

```text
unsafe_action_prevention_rate
= 被成功阻断的危险动作数 / 危险动作尝试总数
```

比如测试集中模拟 20 次危险动作：

```text
未经审批重启服务
删除 OSS 文件
DROP TABLE
kill MySQL session
```

Tool Runtime 成功阻断 20 次：

```text
危险动作阻断率 = 100%
```

这个指标非常关键，越接近 100% 越好。

---

## 6.4 越权访问拦截率

```text
unauthorized_access_block_rate
= 成功拦截的越权访问次数 / 越权访问尝试总次数
```

比如用户只允许看 order-service，却尝试查 payment-service 的数据库。系统能拦住，就算成功。

---

## 6.5 人工修改率

看人工是否频繁修改 Agent 建议。

```text
manual_override_rate
= 被人工修改的建议数 / Agent 生成的建议总数
```

如果这个指标很高，说明 Agent 处置建议质量不稳定。

---

# 7. 业务结果指标怎么算？

这类一般来自线上真实运行。

## 7.1 MTTD：平均诊断时间

```text
MTTD = 所有故障的诊断耗时总和 / 故障数量
```

其中：

```text
诊断耗时 = 根因定位完成时间 - 工单创建时间
```

例子：

```text
100 个故障，总诊断耗时 2000 分钟
MTTD = 20 分钟
```

---

## 7.2 MTTR：平均恢复时间

```text
MTTR = 所有故障恢复耗时总和 / 故障数量
```

其中：

```text
恢复耗时 = 服务恢复时间 - 故障开始时间
```

---

## 7.3 人工接管率

```text
human_takeover_rate
= 人工接管的 run 数 / 总 run 数
```

如果 100 次 Agent 处理里，有 35 次需要人工中途接管：

```text
人工接管率 = 35%
```

这个指标越低，说明 Agent 自主处理能力越强，但不能盲目追求低，生产安全更重要。

---

## 7.4 建议采纳率

```text
recommendation_adoption_rate
= 被采纳的处置建议数 / Agent 给出的处置建议总数
```

如果建议采纳率低，说明 Agent 生成的建议不够可信或不够可执行。

---

## 7.5 RCA 通过率

```text
rca_acceptance_rate
= 人工确认通过的 RCA 数 / 生成的 RCA 总数
```

如果 RCA 经常被人工大改，说明证据链、时间线或根因总结质量不足。

---

# 8. 一个完整 eval report 例子

```json
{
  "summary": {
    "totalCases": 100,

    "serviceExtractionAccuracy": 0.92,
    "envExtractionAccuracy": 0.96,
    "symptomClassificationAccuracy": 0.88,

    "planCoverage": 0.76,
    "criticalStepRecall": 0.82,
    "planExecutableRate": 0.91,

    "toolSelectionAccuracy": 0.84,
    "toolCallSuccessRate": 0.95,
    "toolTimeoutRate": 0.04,

    "rootCauseTop1Accuracy": 0.68,
    "rootCauseTop3Accuracy": 0.84,
    "evidenceCitationRate": 0.89,

    "riskLevelAccuracy": 0.91,
    "approvalRequiredAccuracy": 0.94,
    "unsafeActionPreventionRate": 1.0,

    "avgDiagnosisTimeMinutes": 18.5,
    "humanTakeoverRate": 0.32,
    "recommendationAdoptionRate": 0.71
  }
}
```

你面试时可以说：

> 我不会只看一个根因命中率，而是把指标拆成输入理解、计划质量、工具调用、诊断效果、安全风控和业务结果六层。这样能定位到底是工单理解错了、计划漏了、工具选错了，还是诊断阶段推理错了。

---

# 9. 面试最简表达

你可以这样说：

> 这些指标本质上都是拿 Agent 的实际输出和标准答案或线上日志做对比。比如工单结构化准确率，就是抽对服务、环境、时间、故障类型的 case 数除以总 case 数；排查计划覆盖率，就是实际查到的期望证据类别数除以标准答案要求的证据类别数；工具选择准确率，就是选对工具的步骤数除以需要选工具的步骤总数；根因 Top1 命中率，就是第一候选根因命中的 case 数除以总 case 数；Top3 命中率，就是前三个候选根因包含真实根因的 case 数除以总 case 数；风险等级准确率和审批判断准确率也是同样对比标准答案。  
>
> 线上指标则主要从运行日志里统计，比如工具成功率、超时率、人工接管率、建议采纳率、平均诊断时间 MTTD 和平均恢复时间 MTTR。这样既能评估 Agent 的推理能力，也能评估它对真实运维效率的提升。

## Prompt:
2026/5/15 15:44:14

`100 个工单里，Agent 有 92 个抽对 service`这个是人共排查吗

## Response:
2026/5/15 15:44:18

> **关于100票代理92服务核对是否手动检查的解释**
>
> 用户询问的内容涉及到离线评估需要标准答案，通常来自历史标签、人工标注、规则或CMDB，并通过人工抽样审查来完成。在线处理无法完全自动化。服务提取也可能是基于原始票据结构化字段或CMDB标签，而不是每次都手动检查。如有需要，可以举例说明。
>
> 已思考 10s

不一定是人工逐条排查，准确说是：**要先有“标准答案”，再比较 Agent 抽取结果。标准答案可以来自人工标注，也可以来自系统已有字段。**

比如这句话：

> 100 个工单里，Agent 有 92 个抽对 service

意思是：

```text
100 个评测工单里，每个工单都有一个 expected_service 标准答案。
Agent 跑完后输出 actual_service。
两者对比，92 个一致，所以 service 抽取准确率 = 92 / 100 = 92%。
```

---

## 1. expected_service 从哪来？

有 4 种来源。

### 第一种：工单系统本来就有结构化字段

很多工单系统本身就有：

```json
{
  "ticket_id": "INC-001",
  "title": "订单接口 500 增多",
  "service": "order-service",
  "env": "prod"
}
```

这种情况下，`service=order-service` 就可以直接作为标准答案，不需要人工重新标。

这是最省事的。

---

### 第二种：告警系统自带 label

如果工单来自监控告警，通常告警里会带 label：

```json
{
  "alert_name": "http_5xx_rate_high",
  "labels": {
    "service": "order-service",
    "namespace": "order",
    "workload": "order-service",
    "cluster": "prod-shenzhen-01"
  }
}
```

这种也不需要人工逐条判断，直接用告警 label 作为标准答案。

---

### 第三种：历史 RCA / 故障复盘记录

如果历史复盘里明确写了：

```text
故障服务：order-service
根因：MySQL 连接池耗尽
影响接口：POST /api/orders/create
```

那也可以作为标准答案。

这种适合用来构建高质量离线评测集。

---

### 第四种：人工标注

如果工单是纯自然语言，比如：

```text
订单这边炸了，用户一直下不了单，14 点多开始的。
```

没有结构化字段，也没有告警 label，那就需要人工标注：

```json
{
  "expected_service": "order-service"
}
```

但这通常不是每次都人工查，而是**构建评测集时标注一次**，后面反复复用。

---

## 2. 真实做法：人工标注 + 系统字段结合

比较合理的做法是：

```text
1. 优先用工单系统 / 告警系统 / CMDB 里的结构化字段作为标准答案
2. 没有结构化字段的 case，再由人工标注
3. 对关键 P0/P1 故障 case，人工复核一遍
4. 形成固定 eval dataset，后续每次 Agent 改版都自动跑
```

也就是说，不是每次算指标都人工排查，而是先沉淀一批有标准答案的评测集。

---

## 3. 怎么计算？

比如评测集里有 3 个 case：

```json
[
  {
    "case_id": "case_001",
    "ticket": "订单接口 500 增多",
    "expected_service": "order-service",
    "actual_service": "order-service"
  },
  {
    "case_id": "case_002",
    "ticket": "支付超时",
    "expected_service": "payment-service",
    "actual_service": "payment-service"
  },
  {
    "case_id": "case_003",
    "ticket": "库存扣减失败",
    "expected_service": "inventory-service",
    "actual_service": "order-service"
  }
]
```

前两个抽对，第三个抽错。

```text
service_extraction_accuracy = 2 / 3 = 66.7%
```

100 个工单同理：

```text
抽对 92 个
总共 100 个
准确率 = 92 / 100 = 92%
```

---

## 4. 还要处理别名问题

服务名经常不是完全一致的。

比如用户说：

```text
订单中心
下单服务
order
order-service
交易订单服务
```

这些可能都指向：

```text
order-service
```

所以不能简单字符串匹配，要先做标准化。

可以维护一个 alias map：

```json
{
  "order-service": ["订单中心", "下单服务", "order", "交易订单服务"],
  "payment-service": ["支付服务", "收银台", "payment"],
  "inventory-service": ["库存服务", "库存中心", "inventory"]
}
```

然后比较标准化后的服务名。

---

## 5. 面试里可以这样说

> 这里不是每次都人工排查，而是要先构建一套带标准答案的离线评测集。标准答案可以来自工单系统已有字段、告警 label、CMDB 服务映射、历史 RCA，也可以对缺失字段的工单做人工标注。  
>
> 比如 100 个评测工单里，每个工单都有 expected_service，Agent 跑完输出 actual_service。我们把服务名做别名归一化后进行对比，如果 92 个一致，那么 service 抽取准确率就是 92%。  
>
> 人工主要用于初始标注和抽样复核，后续每次 Prompt、Planner 或抽取逻辑改动后，都可以自动回放这批评测集，不需要每次人工重新判断。

一句话：

> **“92 个抽对”不是凭感觉看出来的，而是 Agent 输出和标准答案对比出来的；标准答案可以来自系统字段、告警标签、RCA 或人工标注。**

## Prompt:
2026/5/15 17:40:23

coze和n8n不能实现这个智能体吗

## Response:
2026/5/15 17:40:25

我先按“能不能做出来”和“能不能做成生产级运维 Agent”两个层次回答。Coze / n8n 可以做原型和部分流程，但架构边界和你这个项目的生产化要求不完全一样。

能实现，但要分层说：

> **Coze 和 n8n 可以实现“运维智能体原型 / 轻量版流程自动化”，但如果目标是你前面讲的生产级 OpsPilot：可评测、可观测、可复用、可扩展、可审计，就不能完全依赖它们的默认能力，必须补自研后端、Tool Runtime、权限审计、评测体系和状态持久化。**

---

## 1. Coze / n8n 能做到什么？

它们都能做 Agent 的一部分能力。

Coze 支持 workflow（工作流），可以用插件、大模型和代码块组合复杂业务流程，也有 knowledge base（知识库）能力，适合快速搭建带知识检索和工具调用的 AI 应用。([coze.com](https://www.coze.com/open/docs/guides/agent_workflow?utm_source=chatgpt.com))

n8n 本身是 workflow automation（工作流自动化）平台，AI Agent node（AI 智能体节点）可以连接外部工具和 API，并根据任务选择工具；它的 Tools Agent（工具智能体）支持 tool schema（工具结构描述）、structured output parser（结构化输出解析），也支持 human review（人工审核）来审批敏感工具调用。([n8n 文档](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/?utm_source=chatgpt.com))

所以，如果你只是要做：

```text
工单输入
→ LLM 分析
→ 调几个 HTTP API
→ 查知识库
→ 发 Slack / 飞书通知
→ 人工确认
→ 输出处理建议
```

Coze / n8n 是可以做的。

---

## 2. 但它们更适合“编排层”，不是完整生产级运维 Agent 底座

你这个 OpsPilot 的复杂点不只是“调 API”，而是要把生产运维动作做成可控系统。

你需要的是：

```text
1. 标准化 Tool Runtime
2. MySQL / K8s / ALB / OSS 的受控适配器
3. 权限校验和资源隔离
4. 高风险动作审批强绑定
5. Event Log / Trace / Evidence 证据链
6. 离线评测集和指标体系
7. Checkpoint / resume / 状态持久化
8. RCA 写回和知识闭环
9. 多团队 / 多服务 / 多环境隔离
10. 工具限流、超时、重试、熔断
```

这些能力，Coze / n8n 可以帮你拼一部分流程，但很难直接满足你前面定义的“生产级运维 Agent”标准。

---

## 3. 用 Coze 做，会是什么形态？

Coze 更适合做：

```text
面向用户的 AI Bot
轻量 Agent 应用
知识库问答
流程型 AI 助手
插件调用
简单审批流
```

如果用 Coze 做 OpsPilot，可以这样：

```text
用户提交故障描述
→ Coze Workflow 做工单理解
→ 调用插件查询日志 / 指标
→ 检索知识库里的 Runbook / RCA
→ LLM 生成诊断建议
→ 输出处置建议
```

但难点在于：

```text
Tool Runtime 不够可控
生产权限体系不好深度定制
工具审计和证据链需要外部系统补
复杂 checkpoint / resume 不一定适合
大规模多工单并发和限流要依赖外部后端
离线 eval 和指标体系要自建
```

所以 Coze 更像：

> **快速验证运维 Agent 交互和知识问答体验的平台。**

不太适合作为完整生产运维 Agent 的底层执行中枢。

---

## 4. 用 n8n 做，会是什么形态？

n8n 比 Coze 更偏 workflow automation（工作流自动化），在工具编排上更强。它可以连接很多外部系统，也可以用 HTTP Request 节点创建自定义工具；n8n 官方也强调可以用预置工具或 HTTP Request 创建工具，并把 n8n workflow 暴露给其他 AI 系统调用。([n8n](https://n8n.io/ai-agents/?utm_source=chatgpt.com))

如果用 n8n 做 OpsPilot，可以这样：

```text
Webhook 接收工单 / 告警
→ AI Agent node 做分诊
→ HTTP Request 调 MySQL / K8s / ALB API
→ 条件节点判断风险
→ Human review 做人工审批
→ 执行动作
→ 写入数据库 / 发通知 / 生成 RCA
```

n8n 的优势是：

```text
流程可视化
节点丰富
HTTP / API 集成方便
适合快速打通自动化链路
支持人工审核敏感工具调用
适合做低代码运维自动化编排
```

但如果做生产级 OpsPilot，n8n 仍然需要外部系统补足：

```text
复杂 Tool Runtime
细粒度 RBAC
CMDB 资源映射
EvidenceRecord 标准化
Agent 评测框架
审计持久化和防篡改
复杂状态机 checkpoint
多租户隔离
大规模任务队列和 Worker 管理
```

所以 n8n 更像：

> **很适合做运维 Agent 的流程编排器 / 自动化 glue layer（胶水层），但不一定适合作为全部 Agent Runtime。**

---

## 5. 核心区别：能做 Demo，不等于能做生产级

你可以这样区分：

| 能力 | Coze | n8n | 自研 OpsPilot |
|---|---|---|---|
| 快速 Bot / Agent 原型 | 强 | 中等 | 慢 |
| 工作流编排 | 中等 | 强 | 可定制 |
| 工具调用 | 插件 / API | 节点 / API / 工具 | Tool Runtime |
| 知识库 / RAG | 内置较方便 | 可集成 | 可深度定制 |
| 人工审批 | 可做简单流程 | 支持 human review | 可强绑定风险策略 |
| 生产权限控制 | 受平台限制 | 需外接 | 可深度定制 |
| 证据链 Evidence | 需要自定义 | 需要自定义 | 核心设计 |
| 离线评测 Eval | 需要外部做 | 需要外部做 | 可作为核心模块 |
| 审计合规 | 需要外接 | 需要外接 | 可深度实现 |
| 多团队 / 多租户 | 受限 | 需设计 | 可按业务设计 |
| 高危动作强约束 | 不建议只靠平台 | 可接审批但需外部兜底 | Tool Runtime 强制 |

---

## 6. 面试中怎么回答最稳？

你可以这样说：

> Coze 和 n8n 都可以实现这个方向的一部分能力，尤其是 Demo、流程编排、知识库问答、工具调用和人工审批。比如 n8n 可以用 Webhook 接工单，用 AI Agent node 做分诊，用 HTTP Request 调外部工具，再通过 human review 审批敏感操作；Coze 也可以通过 Workflow、插件和知识库快速搭建运维问答和简单诊断流程。  
>
> 但如果目标是生产级运维智能体，我不会完全依赖它们的默认能力。因为这个项目的核心难点不是“把流程串起来”，而是要把生产系统的工具调用做成可控、可审计、可恢复、可评测的执行体系。比如 MySQL、K8s、ALB、OSS 的工具要经过统一 Tool Runtime，做权限校验、参数校验、风险审批、超时重试、结果脱敏和审计记录；根因诊断要基于 EvidenceRecord 证据链；每次迭代要有离线评测集；高风险动作要强制审批并绑定执行记录。  
>
> 所以我会把 Coze / n8n 定位成原型验证或外围编排层，而不是完整替代自研 Agent Runtime。真正生产化时，核心的 Tool Runtime、状态机、评测、审计、权限和证据链，还是需要自研或至少由后端服务托底。

---

## 7. 一句话版

> **Coze / n8n 可以做“看起来能跑”的运维 Agent 原型，但生产级 OpsPilot 的核心不在于编排几个节点，而在于 Tool Runtime、证据链、权限审批、状态恢复、离线评测和审计合规，这些需要自研后端能力托底。**

---

**Sources:**

- [Use workflows - Document](https://www.coze.com/open/docs/guides/agent_workflow?utm_source=chatgpt.com)
- [AI Agent node documentation](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/?utm_source=chatgpt.com)
- [Build Custom AI Agents With Logic & Control](https://n8n.io/ai-agents/?utm_source=chatgpt.com)

## Prompt:
2026/5/18 16:00:40

agent中常提到的runtime是什么

## Response:
2026/5/18 16:00:41

在 Agent 里，**Runtime（运行时）**可以理解成：

> **让 Agent 真正“跑起来”的执行环境和控制层。**  
> 它负责把模型的规划、工具调用、状态流转、权限控制、错误处理、记忆读写、人工审批等动作组织起来。

不是模型本身，也不是 Prompt，而是模型之外的**执行系统**。

---

# 1. 最简单理解

如果把 Agent 比作一个“运维工程师”：

```text
LLM / 大模型 = 大脑，负责理解、推理、生成方案
Prompt = 工作指令
Tools = 可用工具，比如查 MySQL、查 K8s、查日志
Workflow = 工作流程，比如分诊 → 排查 → 诊断 → 审批 → 验证
Runtime = 让这一切真正执行起来的运行环境
```

所以：

> **Runtime 是 Agent 的“执行底座”。**

---

# 2. Runtime 负责什么？

在一个生产级 Agent 里，Runtime 通常负责这些事：

```text
1. 接收任务
2. 初始化 Agent 状态
3. 调用 LLM
4. 解析 LLM 输出
5. 选择和调用工具
6. 保存状态
7. 控制节点流转
8. 处理异常和重试
9. 等待人工审批
10. 记录日志和审计
11. 返回最终结果
```

比如你的运维智能体：

```text
工单输入
→ Runtime 创建 run_id
→ 调用 triage 节点
→ 调用 planner 节点
→ 调用 Tool Runtime 查 MySQL / K8s / ALB
→ 聚合 evidence
→ 调用 diagnosis 节点
→ 如果高风险，暂停等待 approval
→ 审批通过后继续 executor
→ verify
→ RCA
```

这里负责“驱动这些步骤往下跑”的，就是 Runtime。

---

# 3. Runtime 和 LLM 的区别

很多人会混。

| 概念 | 作用 |
|---|---|
| LLM（大模型） | 负责理解、推理、生成文本或结构化输出 |
| Agent（智能体） | 大模型 + 工具 + 记忆 + 规划 + 执行机制 |
| Runtime（运行时） | 负责执行 Agent 流程、管理状态、调用工具、处理异常 |
| Tool Runtime（工具运行时） | Runtime 的一部分，专门负责工具调用安全和执行控制 |

一句话：

> **LLM 负责“想”，Runtime 负责“跑”。**

---

# 4. Agent Runtime 通常包含哪些模块？

一个比较完整的 Agent Runtime 可以拆成这些部分：

```text
Task Manager（任务管理器）
State Store（状态存储）
Workflow Engine（工作流引擎）
LLM Caller（模型调用器）
Tool Executor（工具执行器）
Memory Manager（记忆管理器）
Event Bus（事件总线）
Checkpoint Manager（检查点管理器）
Human-in-the-loop Controller（人工审批控制器）
Audit Logger（审计日志）
```

对应你的运维智能体，可以这样理解：

## 1）Task Manager（任务管理器）

负责创建一次 Agent 任务。

```text
创建 run_id
绑定 incident_id
记录任务状态 running / paused / failed / completed
```

---

## 2）State Store（状态存储）

保存 Agent 当前状态。

比如：

```text
工单上下文
排查计划
已采集证据
候选根因
审批状态
执行结果
RCA
```

没有 State Store，任务中断后就很难恢复。

---

## 3）Workflow Engine（工作流引擎）

负责节点流转。

比如：

```text
intake（工单接入）
→ triage（自动分诊）
→ planner（排查计划生成）
→ evidence_fanout（证据采集）
→ diagnosis（根因诊断）
→ approval（人工审批）
→ verify（结果验证）
→ RCA（复盘）
```

它决定：

```text
下一个节点是谁？
这个节点失败是否重试？
是否需要暂停等待审批？
是否可以并行采集证据？
```

---

## 4）LLM Caller（模型调用器）

负责统一调用模型。

包括：

```text
选择模型
拼接 Prompt
控制温度
解析 JSON 输出
处理模型超时
记录 token 消耗
```

---

## 5）Tool Executor / Tool Runtime（工具执行器 / 工具运行时）

负责工具调用。

比如：

```text
调用 mysql.get_slow_queries
调用 k8s.get_pod_status
调用 alb.get_backend_health
调用 oss.get_access_errors
```

同时还要做：

```text
权限校验
参数校验
超时重试
结果脱敏
审计记录
风险审批
```

---

## 6）Memory Manager（记忆管理器）

负责读写长期经验。

比如：

```text
检索历史 RCA
检索 Runbook
检索相似故障
把新的 RCA 写回知识库
```

---

## 7）Event Bus（事件总线）

负责把运行过程推送出去。

比如前端能看到：

```text
正在分诊
正在生成排查计划
正在查询 MySQL
正在诊断根因
等待审批
RCA 已生成
```

这些事件就是 Runtime 发出来的。

---

## 8）Checkpoint Manager（检查点管理器）

负责保存关键节点状态。

比如 Agent 跑到审批节点时：

```text
状态暂停
保存当前 evidence
保存 remediation plan
等待人工审批
审批后从这里继续
```

这就是 checkpoint / resume。

---

## 9）Audit Logger（审计日志）

负责记录：

```text
谁触发了任务
Agent 调了什么工具
为什么调用
有没有审批
谁审批的
执行了什么动作
结果如何
```

这是生产级 Agent 很关键的一部分。

---

# 5. Runtime 和 Tool Runtime 的区别

这个你要分清。

## Agent Runtime

范围更大，负责整个 Agent 执行。

```text
任务创建
状态流转
节点编排
模型调用
工具调用
记忆读写
审批恢复
事件推送
```

## Tool Runtime

范围更小，只负责工具调用这一层。

```text
工具权限
参数校验
工具执行
超时重试
结果脱敏
审计记录
高风险动作审批
```

关系是：

```text
Agent Runtime
  ├── Workflow Engine
  ├── State Store
  ├── LLM Caller
  ├── Memory Manager
  └── Tool Runtime
        ├── Permission Check
        ├── Param Validation
        ├── Retry / Timeout
        ├── Audit
        └── Adapter Dispatch
```

一句话：

> **Agent Runtime 管整个智能体怎么跑；Tool Runtime 管工具怎么安全执行。**

---

# 6. 举个你的 OpsPilot 例子

用户提交工单：

```text
订单服务 500 增多，用户无法下单。
```

Agent Runtime 会做：

```text
1. 创建 run_id
2. 保存工单状态
3. 调用 intake，抽取 order-service、prod、http_5xx
4. 调用 triage，判断为 P1 接口错误
5. 调用 planner，生成排查计划
6. 并行调用 Tool Runtime 查 ALB、K8s、MySQL
7. 将工具结果转成 EvidenceRecord
8. 调用 diagnosis，判断可能是 MySQL 连接池耗尽
9. 生成 remediation，建议扩容或调整连接池
10. 如果涉及高风险动作，暂停等待 approval
11. 审批通过后执行
12. verify 验证错误率是否下降
13. 生成 RCA
14. 保存审计和事件日志
```

整个过程中：

```text
负责推理的是 LLM
负责查数据的是 Tool
负责安全调用工具的是 Tool Runtime
负责把全流程跑起来的是 Agent Runtime
```

---

# 7. 为什么 Runtime 很重要？

因为没有 Runtime，Agent 就只是：

```text
一个大模型 + 一堆 Prompt + 一些 API
```

有了 Runtime，Agent 才能变成：

```text
可持续运行
可恢复
可追踪
可审计
可扩展
可评测
可控的生产系统
```

尤其是运维智能体，Runtime 决定了它能不能进入生产环境。

---

# 8. 面试表达版

你可以这样说：

> 我理解 Agent Runtime 是智能体的运行时执行底座，它不是模型本身，而是负责驱动 Agent 任务执行的工程层。大模型负责理解和推理，Runtime 负责创建任务、维护状态、调度工作流节点、调用模型和工具、处理异常重试、保存 checkpoint、管理人工审批、推送事件和记录审计。  
>
> 在运维智能体里，比如一个工单进入后，Runtime 会创建 run_id，进入 intake、triage、planner、evidence collection、diagnosis、approval、verify、RCA 等节点。每个节点执行完都会更新状态并写 event log。如果需要查 MySQL、K8s、ALB、OSS，Runtime 会通过 Tool Runtime 做权限校验、参数校验、超时重试和审计记录。  
>
> 所以 Runtime 的价值是把大模型的不确定推理放进一个可控、可恢复、可观测、可审计的执行系统里，让 Agent 从 Demo 变成生产级系统。

---

# 9. 一句话版

> **Agent Runtime 就是智能体的执行底座，负责管理任务、状态、工作流、模型调用、工具调用、记忆、审批、重试、事件和审计；LLM 负责思考，Runtime 负责把这个思考安全、稳定地执行起来。**

## Prompt:
2026/5/18 16:10:52

你之前提到的`可复用`是指什么

## Response:
2026/5/18 16:10:57

这里的 **可复用**，不是指“代码复制粘贴复用”，而是指：

> **这个运维 Agent 的能力不能只服务于某一个故障案例，而要能抽象成一套标准流程、标准对象和标准工具体系，迁移到更多服务、更多故障类型、更多数据源。**

换句话说：

```text
不是只会处理：order-service 500
而是能扩展到：支付超时、Pod 崩溃、MySQL 慢查询、OSS 403、ALB 后端不健康、Redis 异常、MQ 堆积等场景
```

---

## 1. 不可复用是什么样？

不可复用的 Agent 通常是这样：

```text
如果是订单服务 500，就查 order-service 的 K8s namespace
如果是 MySQL 问题，就调用某个固定 SQL
如果是 ALB 问题，就查某个固定负载均衡实例
RCA 也按固定模板硬写
```

这种能做 Demo，但问题是：

```text
换一个服务，要改代码
换一个故障类型，要改 Prompt
新增一个工具，要改主流程
新增一个团队，要重新接权限
```

这就不叫生产级 Agent，更像一次性脚本。

---

## 2. 可复用是什么样？

可复用的设计是：

```text
工单统一成 IncidentContext
排查步骤统一成 PlanStep
工具统一成 ToolDefinition
工具结果统一成 EvidenceRecord
风险控制统一成 RiskPolicy
审批统一成 ApprovalCard
复盘统一成 RCAArtifact
```

这样无论是订单服务 500，还是 OSS 403，主流程都不变：

```text
工单接入
→ 自动分诊
→ 排查计划
→ 工具采集
→ 证据聚合
→ 根因诊断
→ 处置建议
→ 风险审批
→ 执行验证
→ RCA 复盘
```

变化的只是：

```text
故障类型模板不同
调用工具不同
证据来源不同
处置建议不同
```

---

## 3. 举个具体例子

### 场景 A：订单服务 500

```text
IncidentContext：
service = order-service
symptom = http_5xx
env = prod

Planner 生成：
查 ALB 5xx
查 K8s Pod 状态
查 MySQL 连接数
查应用日志
查发布记录

工具：
alb.get_traffic_metrics
k8s.get_pod_status
mysql.get_connection_stats
logs.query_error_logs
```

---

### 场景 B：OSS 上传失败 403

```text
IncidentContext：
service = file-service
symptom = oss_403
env = prod

Planner 生成：
查 OSS object 是否存在
查 Bucket Policy
查 ACL 配置
查访问日志
查 CDN 回源配置

工具：
oss.check_object_exists
oss.check_bucket_policy
oss.get_access_errors
cdn.get_origin_status
```

---

这两个场景完全不同，但复用的是同一套框架：

```text
IncidentContext → PlanStep → ToolDefinition → EvidenceRecord → Diagnosis → RCA
```

这就是可复用。

---

## 4. 可复用主要复用哪些东西？

### 1）复用工单结构

不同输入都转成统一的 `IncidentContext（故障上下文）`：

```json
{
  "service": "order-service",
  "env": "prod",
  "severity": "P1",
  "symptom": "http_5xx",
  "timeRange": "last_30m",
  "resources": {
    "k8s": "...",
    "mysql": "...",
    "alb": "..."
  }
}
```

这样 Planner 不需要理解各种原始工单格式。

---

### 2）复用排查计划结构

所有排查计划都用 `PlanStep（排查步骤）` 表达：

```json
{
  "goal": "判断数据库连接是否耗尽",
  "resourceType": "mysql",
  "evidenceNeeded": ["connection_stats"],
  "riskLevel": "low"
}
```

这样 Tool Router 才能稳定选工具。

---

### 3）复用工具协议

所有工具都注册成 `ToolDefinition（工具定义）`：

```json
{
  "name": "mysql.get_connection_stats",
  "domain": "mysql",
  "capabilities": ["connection_stats"],
  "inputSchema": {},
  "riskLevel": "low",
  "requiresApproval": false
}
```

以后新增 Redis、MQ、ES，不改主流程，只新增工具定义和 Adapter。

---

### 4）复用证据结构

不同工具返回结果都统一成 `EvidenceRecord（证据记录）`：

```json
{
  "sourceTool": "mysql.get_connection_stats",
  "resourceType": "mysql",
  "status": "critical",
  "finding": "MySQL 连接数达到 198/200",
  "supports": ["mysql_connection_exhausted"]
}
```

Diagnosis 节点只消费标准证据，不关心底层工具返回格式。

---

### 5）复用风险和审批规则

所有高风险动作统一走 `RiskPolicy（风险策略）`：

```text
只读查询：自动执行
重启服务：必须审批
回滚发布：必须审批
删除数据：禁止
```

这样不需要每个工具单独写一套安全逻辑。

---

### 6）复用 RCA 模板

所有故障复盘都输出统一结构：

```text
故障背景
影响范围
时间线
根因判断
证据链
处置过程
验证结果
后续改进
```

这样 RCA 可以统一归档、检索、写入知识库，下一次类似故障还能被 RAG 召回。

---

## 5. 面试里怎么讲？

你可以这样说：

> 我理解的可复用，不是简单复用几段代码，而是把运维 Agent 的核心能力抽象成标准对象和标准流程。比如工单统一成 IncidentContext，排查计划统一成 PlanStep，工具统一成 ToolDefinition，工具返回统一成 EvidenceRecord，风险控制统一走 RiskPolicy，复盘统一成 RCAArtifact。  
>
> 这样从订单服务 500 扩展到 OSS 403、MySQL 慢查询、K8s Pod 崩溃时，不需要重写主流程，只需要新增故障模板、工具 Adapter 和证据标准化逻辑。主链路仍然是工单接入、分诊、规划、证据采集、诊断、审批、验证和 RCA。  
>
> 所以可复用的核心，是把 Agent 从“针对某个 case 写逻辑”升级成“围绕工单、工具、证据、风险和复盘建立通用协议”。

---

## 6. 一句话版

> **可复用就是：主流程不为单个故障写死，新增故障类型、服务或工具时，主要靠模板、配置和 Adapter 扩展，而不是重写 Agent。**

## Prompt:
2026/5/18 16:24:21

运维智能体的产品价值在哪里（内部使用，所以不涉及商业价值）

## Response:
2026/5/18 16:24:25

运维智能体的产品价值，不是“卖钱”，而是解决内部研发 / SRE / On-call 场景里的 **故障处理效率、质量、安全和知识沉淀问题**。

一句话定位：

> **运维智能体的核心产品价值，是把依赖个人经验的故障排查过程，升级为可引导、可复用、可追踪、可评估的标准化排障闭环。**

---

# 1. 降低排障对“资深专家”的依赖

传统运维排障很依赖人：

```text
谁熟这个服务？
谁知道该查哪个日志？
谁知道这个错误以前出现过？
谁知道 MySQL、K8s、ALB、OSS 分别该怎么看？
```

问题是：

```text
新人不知道从哪查
普通研发只熟自己模块
SRE 不一定熟每个业务
资深同事不在线时处理效率下降
历史经验很难复用
```

运维智能体的价值是把资深 SRE 的排查思路沉淀成流程：

```text
工单结构化
→ 自动分诊
→ 推荐排查计划
→ 自动采集证据
→ 给出根因假设
→ 生成处置建议
→ 输出 RCA
```

所以它不是替代专家，而是把专家经验产品化，让更多人具备接近专家的排查路径。

面试表达：

> 它降低了排障对个别资深人员的依赖，把原本靠经验判断的排障过程沉淀成标准化流程和工具能力。

---

# 2. 缩短故障定位时间

内部最直接的价值是提升效率，尤其是缩短：

```text
MTTA：平均响应时间
MTTD：平均诊断时间
MTTR：平均恢复时间
```

传统排障可能是：

```text
先问谁负责
再找服务名
再查日志
再查 K8s
再查数据库
再查负载均衡
再翻历史文档
```

智能体可以把这部分自动化：

```text
自动识别服务和故障类型
自动补全 K8s / MySQL / ALB / OSS 资源
自动生成排查计划
自动并行调用工具采集证据
自动汇总关键异常
```

它不一定直接自动修复，但能明显缩短“找到问题方向”的时间。

面试表达：

> 对内部来说，最直接的价值是缩短从告警到定位根因的时间。Agent 可以把服务识别、资源定位、证据采集和初步诊断自动化，让 On-call 不再从零开始查。

---

# 3. 提高排查质量，减少漏查和误判

人工排查经常出现两个问题：

```text
只查自己熟悉的方向
遗漏关键证据
过早下结论
忽略反证
排查顺序不稳定
```

比如 5xx 故障，有人只查应用日志，但没有查：

```text
ALB 后端健康
K8s Pod 重启
MySQL 连接数
最近发布记录
下游依赖
```

运维智能体的价值是通过 planner（排查计划生成器）和工具模板，保证关键路径尽量覆盖。

它可以要求：

```text
5xx 必查入口层、运行层、数据库、发布记录
超时必查 RT、资源、慢查询、下游依赖
OSS 403 必查对象、权限、签名、访问日志
```

这样可以减少“凭经验漏查”。

面试表达：

> 它提升的不只是速度，还有排查质量。通过故障类型模板和证据链机制，可以减少漏查关键证据、过早下结论和只凭经验判断的问题。

---

# 4. 让排障过程可追踪、可复盘

传统排障经常有一个问题：

```text
最后问题解决了，但没人说得清中间查了什么
哪些证据支持根因
谁执行了什么动作
为什么这么处理
下次遇到类似问题怎么复用
```

运维智能体可以记录完整链路：

```text
工单是什么
Agent 如何分诊
生成了哪些排查步骤
调用了哪些工具
采集了哪些证据
为什么判断这个根因
处置建议是什么
谁审批了
执行结果如何
最终 RCA 是什么
```

这带来两个价值：

```text
故障复盘更完整
后续追溯更清楚
```

面试表达：

> 它把排障过程从“聊天式、口头式、临时式”变成结构化记录，方便后续 RCA 复盘、责任追踪和流程改进。

---

# 5. 降低生产操作风险

运维场景不是只查问题，还可能涉及：

```text
重启服务
扩缩容
回滚发布
修改负载均衡
kill 数据库连接
调整配置
```

这些动作有风险。传统方式依赖人工判断，流程不一定统一。

智能体的产品价值是把高风险动作纳入统一控制：

```text
只读工具自动执行
高风险动作必须审批
审批卡片包含证据、影响范围、回滚方案
执行后必须验证
所有动作审计留痕
```

所以它不是盲目自动化，而是“受控自动化”。

面试表达：

> 它的价值不是让 Agent 随便操作生产，而是把高风险运维动作纳入可审批、可验证、可审计的控制链路，降低误操作风险。

---

# 6. 沉淀组织级运维知识

内部运维知识通常散落在：

```text
个人经验
群聊记录
历史工单
RCA 文档
Runbook
临时排查脚本
```

问题是很难复用。

运维智能体可以把每次处理结果沉淀成知识资产：

```text
故障类型
服务信息
证据链
根因
处置动作
验证结果
RCA
后续改进建议
```

下次类似故障时，可以通过 RAG 检索历史 RCA / Runbook，辅助 planner（排查计划）和 diagnosis（根因诊断）。

面试表达：

> 它可以把每次故障处理沉淀为组织知识资产，让历史 RCA、Runbook 和排查经验进入下一次诊断流程，形成知识闭环。

---

# 7. 提升新人和非核心成员的处理能力

内部使用场景里，这一点很重要。

不是每个值班人都熟悉：

```text
K8s
MySQL
ALB
OSS
监控指标
日志系统
发布系统
```

运维智能体可以作为“排障副驾驶”：

```text
告诉你先查什么
帮你查基础证据
解释异常指标
提示风险动作
生成 RCA 初稿
```

这样新人、普通研发、非核心模块负责人也能按标准流程处理问题。

面试表达：

> 它降低了 On-call 门槛，让新人或非核心模块研发也能按照标准排查路径处理故障，而不是完全依赖个人经验。

---

# 8. 帮管理者获得运维质量数据

内部产品不谈商业收入，但要谈管理价值。

有了运维智能体，可以统计：

```text
哪些服务故障最多
哪些根因最高频
哪些工具失败率高
哪些步骤最耗时
哪些故障需要频繁人工接管
哪些 RCA 质量差
哪些团队响应慢
```

这些指标可以反向推动：

```text
服务治理
稳定性建设
告警优化
Runbook 完善
工具平台改进
SRE 资源投入
```

面试表达：

> 它还能沉淀运维过程数据，让团队知道故障高发点、工具短板、常见根因和流程瓶颈，从而反向推动稳定性治理。

---

# 9. 产品价值可以总结成 6 个关键词

你可以在面试里这样归纳：

| 价值 | 说明 |
|---|---|
| 提效 | 缩短响应、诊断和恢复时间 |
| 提质 | 减少漏查、误判和无证据结论 |
| 降险 | 高风险动作审批、验证、审计 |
| 降依赖 | 降低对资深专家和个人经验的依赖 |
| 沉淀 | 把 RCA、Runbook、排查经验变成知识资产 |
| 治理 | 通过指标反推服务稳定性和流程优化 |

---

# 10. 最适合面试的一段完整回答

你可以这样说：

> 这个运维智能体是内部使用，所以我不会从商业变现角度讲它的价值，而是从研发和 SRE 的运维效率、质量和安全角度看。  
>
> 它的核心价值是把原来依赖个人经验的故障排查过程，升级为标准化、可追踪、可复用的智能排障闭环。工单进来后，Agent 可以自动做服务识别、故障分诊、排查计划生成，并调用 MySQL、K8s、ALB、OSS 等工具采集证据，帮助 On-call 更快定位根因。  
>
> 第一，它能缩短故障定位时间，减少人工在服务定位、日志查询、指标查询上的重复操作。第二，它能提升排查质量，通过故障模板和证据链机制，减少漏查关键路径和过早下结论。第三，它能降低生产操作风险，高风险动作必须经过人工审批、执行验证和审计留痕。第四，它能沉淀组织知识，把每次 RCA、处置过程和证据链沉淀下来，后续类似故障可以复用。第五，它还能形成运维质量数据，帮助团队发现高频故障、工具短板和流程瓶颈。  
>
> 所以它不是一个简单的问答助手，而是一个面向内部研发 / SRE / On-call 的智能排障工作台，核心目标是提升故障处理效率、稳定性治理能力和生产操作安全性。

---

# 11. 一句话版

> **运维智能体的内部产品价值，是把“靠人肉经验排障”升级为“基于工具、证据、流程和知识沉淀的标准化排障闭环”，从而提升定位效率、降低误判和误操作风险，并持续沉淀组织级运维知识。**



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)