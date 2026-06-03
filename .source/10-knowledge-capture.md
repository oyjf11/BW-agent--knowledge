# 知识沉淀 — Specialist Agent Pool 设计

## 任务背景

OpsPilot 是一个 SRE 故障处置智能体，当前 evidence_fanout_node 只是将 plan 中的 task 通过
`asyncio.gather` 并行调用工具，返回 raw data 后由 aggregate 做简单规则评分。核心问题是：

- **证据采集缺乏分析能力**：每个工具调用是纯数据拉取，无推理
- **异常信号被淹没**：几百条 K8s events 中 1 条 CrashLoopBackOff → aggregate 无法识别
- **工具调用间无关联分析**：K8s pod 重启时间与 DB 慢查询时间窗口的关系未被发现

本次设计将 evidence_fanout_node 从纯工具并行升级为 **5 个独立 Specialist Agent 组成的分析池**，
每个 Agent 自带 ReAct 循环，产出结构化分析结论，并实现跨 Agent 关联推理。

---

## 关键设计

### 1. 从纯数据采集到"Agent 级推理分析"的范式升级

**旧路径**：`planner → tool calls (asyncio.gather) → raw EvidenceItem → aggregate 规则评分`

**新路径**：`planner → AgentTask × 5 → SpecialistAgent.run() (ReAct) → SpecialistAnalysis → aggregate 关联图 + 因果链 + 矛盾检测`

这是本项目最核心的架构升级。不改变 StateGraph 拓扑（builder.py 零改动），通过 Feature Flag 双路径
实现渐进式上线，保证了无风险回退能力。

**关键思路**：让 Agent 在工具返回数据的那一刻就做一级分析，而不是把所有 raw data 堆给下游。
这解决了"几百条 events 中 1 条 CrashLoopBackOff 被淹没"的经典问题。

### 2. ReAct 循环 + 规则兜底的双层推理架构

每个 SpecialistAgent 同时具备两类能力：

| 层级 | 机制 | 场景 | 输出 |
|------|------|------|------|
| **LLM 推理** | ReAct 循环（max 3 rounds）+ tool calling | LLM 可用 | 结构化 JSON 分析 |
| **规则兜底** | `_extract_signals_by_rules()` 硬编码规则 | LLM 超时/失败 | AnomalySignal 列表 |

规则兜底是**确定性安全网**：即使所有 LLM 调用都失败，K8s Agent 仍能通过检查
`containerStatuses.waiting.reason` 发现 CrashLoopBackOff，保证最坏情况下仍有可用的分析结论。

### 3. 跨 Agent 关联推理 — 关联图 + 因果链 + 矛盾检测

aggregate 从简单的"数 evidence 数量 + 关键词匹配"升级为三个维度的推理：

1. **关联图（correlation graph）**：利用 SpecialistAnalysis 中的 `correlation_hints` 构建邻接表。
   - concrete hints（confidence ≥ 0.6）→ 图边
   - speculative hints（0.3 ≤ confidence < 0.6）→ 仅辅助提示
   - 置信度 < 0.3 → 丢弃

2. **因果链（causal chains）**：DFS 从入度为零的节点出发，仅保留路径上每个节点都有 ≥1 个 anomaly
   的路径，按平均权重降序取前 5。

3. **矛盾检测（contradiction detection）**：6 条硬编码规则。例如：
   - K8s "异常:" + Metrics "正常:" → "可能非资源级故障"
   - Log "异常:" + K8s "正常:" → "应用层故障，非基础设施"

这种方法让 aggregate 从"做加法"变成"做推理"，真正实现了跨工具回落的关联分析。

### 4. Feature Flag 双路径渐进式上线

```python
# .env 控制，默认 false
AGENT_FEATURE_SPECIALIST_POOL=true  → v2 路径（SpecialistAgent）
AGENT_FEATURE_SPECIALIST_POOL=false → v1 路径（原 _collect_one）
```

**三个关键设计点**：
- **节点级开关**：仅 planner / fanout / aggregate 读取 flag，不影响其他节点
- **双写兼容**：v2 路径同时产出 v2 格式（agent_tasks + specialist_analyses）和 v1 格式（plan + evidence_items）
- **零回归**：flag=false 时原路径完全不受影响，保证渐进式上线安全

### 5. 级降级保护链

设计中的降级保护分三层：

| 层级 | 数据源降级 | 场景 |
|------|-----------|------|
| **Agent 层** | L0 正常 → L1 JSON 解析失败 → L2 LLM 超时有 raw data → L3 完全失败 | 单个 Agent |
| **Fanout 层** | agent_tasks 非空 → fallback_from_plan() → 5 个默认 AgentTask | agent_tasks 为空 |
| **整体** | 全部 Agent disabled → 自动 fallback 到 `_collect_one()` 原路径 | YAML 缺失 |

每一层降级都有明确的触发条件和输出格式，不会出现"静默失败"。

### 6. Agent 级原子写入 + 失败回滚

fanout 中每个 Agent 的 evidence_items 写入采用 Agent 级原子写入：

```
for result in results:
    agent_evidence = build_raw_evidence_items(result)
    try:
        state["evidence_items"].extend(agent_evidence)
        state["specialist_analyses"].append(result.model_dump())
    except Exception:
        # 回滚已写入的 evidence，保证 Agent 级原子性
        state["evidence_items"] = [e for e in state["evidence_items"] if e not in agent_evidence]
        state["specialist_analyses"].append(_build_degraded_shell(...))
```

注意此处用 `id()` 判断而非对象比较，因为 EvidenceItem 可能是 Pydantic 对象也可能是 dict。

### 7. Pydantic vs dict 二义性系统性处理

LangGraph 的 checkpoint 反序列化后，TypedDict state 中的 Pydantic 对象会变成 **dict**。
本项目在所有需要访问对象属性的位置，统一采用以下模式：

```python
# 兼容两种形式
cat = obj.get("agent_category", "") if isinstance(obj, dict) else obj.agent_category
```

**State 新增字段全部使用 `List[Dict[str, Any]]` 而非 `List[SpecialistAnalysis]`**，
从根本上避免反序列化类型错误。入口处统一防御转换，不引入 `parse_obj_as` 额外依赖。

### 8. 性能预算精细管控 — 时间优先于轮次

| 层级 | 预算 | 机制 |
|------|------|------|
| 单 Agent | 30s | `AgentTask.timeout_ms=30000` |
| LLM 单次调用 | min(15s, 剩余时间) | `asyncio.wait_for(timeout=...)` |
| 单工具调用 | min(30s, 剩余预算/tool_count) | 动态分配 |
| fanout 总 | 60s | `asyncio.wait_for(gather(...), timeout=60)` |

**时间预算严格优先于轮次**：每轮前检查 `deadline - now()`，< 2s 强制退出。即使 LLM 返回
tool_calls，超时也强制截断并标记 `truncated=True`。这保证了整个 fanout 在 60s 内必然返回。

### 9. 5 个 Specialist 的工具归属边界设计

每个工具只归属于一个 Agent，`tool_names` 白名单互不相交。关键边界澄清：

- `query_k8s_pod_logs_summary` → **K8s Specialist**（容器 stdout/stderr，K8s 视角）
- `query_logs` → **Log Specialist**（集中式日志平台，应用视角，是应用日志唯一入口）
- `query_k8s_deployment_status` → **K8s Specialist**（K8s Deployment 实时状态）
- `query_deployments` → **Deployment Specialist**（发布系统变更历史）
- Metrics Specialist 是**唯一指标查询入口**；K8s Specialist 不查询指标

这种边界划分避免了同一工具被多个 Agent 重复调用造成的浪费时间 + 分析冲突。

### 10. tool_names 运行时 guard

除 Agent 初始化时的白名单校验外，在 `SpecialistAgent._execute_tool()` 中增加运行时 guard：

```python
if tool_name not in self.config.tool_names:
    # LLM 幻觉出不在白名单的工具名
    messages.append({"role": "tool", "content": f"Error: tool '{tool_name}' not available"})
    continue  # 不调 gateway，进入下一轮
```

这防止了 LLM 幻觉绕过初始化检查直接调用危险工具。

### 11. conclusion 前缀约定 — 机器可读的分类约定

SpecialistEvidence 的 `conclusion` 字段按约定使用固定前缀：

| 前缀 | 含义 | aggregate 行为 |
|------|------|---------------|
| `正常:` | 无异常 | 正常纳入 |
| `异常:` | 有异常 | 用于矛盾检测 |
| `部分:` | 产出不完整 | 权重 ×0.5 |
| `失败:` | 完全失败 | 不计入评分 |

这种设计让 aggregate 的 `_detect_cross_agent_contradictions()` 可以**仅通过字符串前缀**
做分类匹配，不依赖 LLM 比对，避免了二次 LLM 调用的延迟和不确定性问题。

### 12. Tracing 层级结构设计

不改动 tracing.py，通过现有 `AgentTracer` API 构建清晰的 span 层级：

```
fanout span (parent)
├── specialist.k8s_specialist
│   ├── react.round.0
│   │   ├── tool.query_k8s_pods          ← gateway 自动继承 parent
│   │   └── tool.query_k8s_events
│   ├── react.round.1
│   │   └── tool.query_k8s_deployment_status
│   └── agent.final_analysis             ← event: degradation=L0, conf=0.85
├── specialist.db_specialist
│   ...
```

总计约 15-25 个 span（5 Agent × 平均 3-5 个 span），与现有 trace 粒度一致，不会造成
信息过载。通过 `/runs/{run_id}/trace` 可查看每个 Agent 的每轮 LLM 调用和工具调用详情。

### 13. 5 类 Agent 的规则兜底 — 各自领域的确定性信号

| Agent | 规则 | 产出 |
|-------|------|------|
| K8s | containerStatuses.waiting.reason ∈ {CrashLoopBackOff, ErrImagePull, OOMKilled} → AnomalySignal | 确定性 pod 级健康信号 |
| DB | COMMAND≠'Sleep' 连接数 > 50 → warning；慢查询 > 10 → anomaly | 确定性 DB 瓶颈判断 |
| Log | 正则计数 ERROR\|FATAL\|Exception > 10 → warning | 确定性日志异常量信号 |
| Metrics | 相邻两点变化率 > 50% → anomaly | 确定性指标突变信号 |
| Deployment | 最近部署 < 2h → correlation_hint(target="k8s" or "logs", confidence=0.6) | 发布窗口关联 |

每条规则都是**确定性的、可解释的**，用于 LLM 不可用时的最低保障。

---

## 重要取舍

| 决策 | 选择 | 放弃 | 理由 |
|------|------|------|------|
| **Agent 池方案** | 5 个 fixed Specialist Agent 全量调度 | Dynamic Orchestrator（LLM 按需调度）、Supervisor Agent（单一 Agent 主导） | v1 复杂度可控，全量调度保证覆盖度，固定 Agent 便于规则兜底 |
| **YAML 静态配置** | 启动时硬编码加载 | DB 动态加载 | v1 不需要管理 API，配置变更走 code review 可追溯 |
| **conclusion 前缀约定** | 字符串前缀匹配 | LLM 比对两个 Agent 的结论 | 前缀匹配确定性更高，无 LLM 二次调用延迟 |
| **Agent 级原子写入** | 单个 Agent 的成功/回滚 | 全局事务 | Agent 间无依赖关系，单 Agent 原子性已满足 |
| **confidence 代码封顶** | LLM 自评封顶 0.6 | 直接信任 LLM 自评 | LLM 自评准确率约 60-70%，封顶 0.6 预留跨 Agent 加权空间 |
| **evidence_items 双写** | v2 路径同时产出旧格式 | 只产出 SpecialistAnalysis | 保证 diagnose / rca 等下游节点无需改动 |

---

## 踩坑与根因

### Pydantic vs dict 二义性（已沉淀为 AGENTS.md 第 1 条陷阱）

**表现**：从 checkpoint 恢复的 state 中 `ticket.service` 报 `AttributeError`，因为对象已变成 dict。

**根因**：LangGraph 的 SqliteSaver 在序列化/反序列化时，TypedDict 中的 Pydantic 嵌套对象
会丢失类型信息，变成 plain dict。

**教训**：
- State 字段声明优先使用 `List[Dict[str, Any]]` 而非强类型 list
- 所有访问 state 中对象属性的地方统一做 `isinstance(obj, dict)` 防御检查
- **不引入 `parse_obj_as` 额外依赖**，保持防御逻辑的简单和内聚

### checkpoint resume 时新增 State 字段自动兼容

**发现**：TypedDict 使用 `total=False`，意味着新增的 State 字段（如 `agent_tasks`、
`specialist_analyses`）在旧的 checkpoint 中自然缺失，但不会导致 key 缺失错误。
builder.py 的节点函数签名也无需改动。

**价值**：这意味着本次改造**完全不需要做任何 checkpoint 迁移**。

### confidence LLM 自评不可靠

**发现**：LLM 自评 confidence 通常偏高（0.8-0.95），但实际准确率仅 60-70%。

**措施**：代码层强制封顶 0.6，且在 aggregate 中 `partial` 进一步降权 ×0.5。

---

## 测试经验

### 单元测试设计要点

1. **mock LLM 是关键**：所有 SpecialistAgent 的单元测试用 mock LLM 代替真实调用。
   通过控制 LLM 返回内容（正常 JSON / 非法 JSON / tool_calls / 无 tool_calls）
   覆盖 ReAct 循环的各种分支。

2. **3 种 round 边界**：需分别测试轮次 0 无 tool_calls、2 轮 + 最终分析、3 轮耗尽截断。

3. **LLM 幻觉工具名 guard**：mock LLM 返回不在白名单的工具名，验证 runtime guard 拦截
   且不调 gateway。

4. **checkpoint resume 测试**：完整 run 后 resume，验证 specialist_analyses 元素为 dict
   时 aggregate 仍可正常工作。

### 集成测试设计要点

1. **Happy path**：5 Agent 全部 COMPLETED + aggregate 关联图构建
2. **Partial degradation**：2 Agent 超时 + 3 Agent 正常，验证 aggregate 降权不崩溃
3. **All LLM failed**：所有 LLM 不可用，验证规则兜底产出 + quality_score ≈ 0
4. **Feature flag off 回归**：flag=false 时所有现有测试通过
5. **Agent 配置 YAML 缺失**：验证 fallback 到原路径
6. **Checkpoint round-trip**：验证反序列化兼容

### 7 种 run_status 测试覆盖要求

每种 AgentRunStatus 至少 1 个测试用例：COMPLETED、PARTIAL、DEGRADED（保留不可达）、
TIMEOUT、LLM_FAILED，确保每种状态下游消费逻辑正确。

---

## 可复用检查清单

### 新增 Feature Flag 检查清单

- [ ] Settings 中新增字段 + 默认值 = false（渐进式上线）
- [ ] .env 对应变量命名与 Settings 字段 snake_case → UPPER_CASE 自动映射一致
- [ ] Feature flag 仅在需要它的节点中读取，不扩散到全局
- [ ] flag=false 时旧路径完全不受影响
- [ ] 双写兼容：新路径同时产出旧格式，保证下游节点不改动
- [ ] YAML 配置缺失时自动 fallback 到旧路径

### Agent 安全边界检查清单

- [ ] FORBIDDEN_TOOLS 黑名单检查（execute_action）
- [ ] tool_names 前缀强制匹配 category（如 K8s Agent 只能调 `query_k8s_*`）
- [ ] 工具注册检查（gateway.describe_capability）
- [ ] 运行时 guard（LLM 幻觉工具名二次拦截）
- [ ] 校验失败 Agent 的降级行为明确（enabled=False + LLM_FAILED 空壳）

### 降级层级设计检查清单

- [ ] 每层降级有明确的触发条件和输出格式
- [ ] 降级输出对下游可见（partial/truncated 字段标记）
- [ ] 最底层降级保证系统不崩溃（返回空壳而非抛异常）
- [ ] 降级信号可观测（tracing event 中记录 degradation level）

### State 新增字段检查清单

- [ ] 使用 `List[Dict[str, Any]]` 而非强类型 list（checkpoint 兼容）
- [ ] TypedDict total=False 保证旧 checkpoint 自动兼容
- [ ] 所有访问处统一做 `isinstance(obj, dict)` 防御
- [ ] builder.py 节点函数签名无需改动

---

## 应更新的规则

### 应写入 AGENTS.md 的长期规则

1. **Feature Flag 双路径模式**：任何对现有工作流节点的重大改造，都必须采用 feature flag
   双路径架构，保证渐进式上线 + 无风险回退。

2. **State 字段统一防御**：所有消费 `List[Dict[str, Any]]` 类型 state 字段的代码，
   入口处统一做 `isinstance(obj, dict)` 检查。

3. **LLM 输出不可信**：任何 LLM 输出的 quality/confidence 自评字段，必须在代码层封顶
   （本项目设定为 0.6），只作为加权项之一，不作为最终决策依据。

4. **Agent 级安全校验**：所有调用外部工具/API 的 Agent，必须做 tool_names 白名单校验
   （初始化 + 运行时双重检查），禁止 execute_action 类危险操作出现在 Agent 配置中。

5. **降级路径必须可见**：任何降级/fallback 路径必须在 tracing 中记录 degradation level、
   partial/truncated 状态，保证线上排障时可追溯。

6. **确定性子串匹配 vs LLM 比对**：当两个 Agent 的结论需要做分类/匹配/矛盾检测时，
   优先使用确定性子串前缀匹配（如 conclusion 前缀约定），避免 LLM 二次调用的延迟和不确定性。

### 应补充到 AGENTS.md 的已知陷阱

7. **Pydantic 对象 vs dict 二义性（已存在，本次强化）**：
   > 从 checkpoint 反序列化后的 specialist_analyses 元素是 dict 而非 Pydantic 对象。
   > 所有访问必须兼容两种形式：
   > ```python
   > cat = obj.get("agent_category", "") if isinstance(obj, dict) else obj.agent_category
   > ```

---

## 应新增/更新的 Skill

### 新增 Skill 建议

- **checkpoint-migration**：提供 LangGraph checkpoint 兼容性检查流程，检查新增 State 字段是否
  导致 checkpoint 恢复失败，并提供 `total=False` 自动兼容验证脚本。

### 更新 Skill 建议

- **backstage-detailed-design**：补充 Feature Flag 双路径架构模板，包含 Settings 字段定义、
  .env 配置、双写兼容模式、YAML fallback 的模式代码段。

- **implementation-slice**：补充 Agent 类实现的代码模板（ReAct 循环 + 规则兜底 + 运行时 guard）。

---

## 后续改进建议

1. **Dynamic Orchestrator（后续版本）**：当前 v1 全量调度 5 个 Agent，后续可按需调度。
   LLM 驱动的多轮按需调度可减少不必要的 Agent 执行，但需解决调度时机和 Agent 间消息传递的问题。

2. **Agent 配置动态加载（v2）**：当前 YAML 启动时硬编码 + PR review。v2 可从管理 API/DB
   动态加载配置 + 热更新 system_prompt，但需解决并发安全、版本回滚和审计问题。

3. **confience 加权公式优化**：当前 LLM 自评 × 0.6 + partial × 0.5 的权重体系是经验值。
   后续可通过离线评测（Phase 8）对比人工标注，找到更精确的权重分配。

4. **矛盾检测规则扩展**：当前 6 条规则覆盖了常见的 pairwise 矛盾，但 3+ Agent 的三角矛盾
   （如 K8s 异常 + DB 异常 + Metrics 正常 → "？"）尚未定义。后续可扩展为 N 元矛盾检测。

5. **Agent 间通信机制**：当前 Agent 间无直接通信，仅通过 aggregate 做事后关联。
   后续可考虑在 agent_tasks 中增加 `cross_references` 字段，让 Agent 在分析时可以引用
   其他 Agent 的中间结论。

6. **_category_applies() 智能裁剪（当前硬编码 True）**：根据 incident_type 自动裁剪不需要的
   Agent（如纯 DB 问题不需要 K8s Agent），可显著减少不必要的时间和 LLM token 消耗。
