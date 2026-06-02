下面这版是按你刚修正后的真实口径重新梳理的，重点围绕这几个事实：

- 项目底座：**基于 LlamaCoder 二次改造**。
- 模型调用：**Together AI SDK**。
- 项目定位：**企业级 AI 轻应用生成平台 / AI Coding 工程化落地**。
- 数据分层：**平台控制面数据存 MySQL，用户业务数据存 PostgreSQL / Supabase**。
- 权限：**企业 SSO / 一体权限提供 user_id、tenant_id，再基于 Supabase JWT + RLS 做租户隔离**。
- 前端生成体验：**Together AI 流式返回 + 业务侧 runnable 封装 + Sandpack 预览**。
- 你的相关项目：AI 辅助研发提效工具包、AI 智能体应用生成平台、AI 运维智能体。简历里也确实写到了 OpenCode、Commands、Agents、Skills、Rules、Spec、Playwright、CI/CD、Bad Case、应用生成、Supabase、多租户、Sandpack、运维 Agent 等内容。

---

# 一、项目架构总览类

## 1. 你们这个 AI 应用生成平台整体架构是什么？

**面试官想看：** 你是不是只 fork 了 LlamaCoder，还是做了企业级二次改造。

### 回答要点

你可以这样讲：

```text
用户自然语言需求
  ↓
前端提交生成任务
  ↓
平台后端创建任务记录：MySQL
  ↓
调用 Together AI SDK
  ↓
流式返回生成内容
  ↓
Router 判断任务类型
  ↓
UIPlanner / SupabasePlanner / RoutingPlanner 分别规划页面、数据和路由
  ↓
Codegen 生成 React + TypeScript + Tailwind 代码
  ↓
生成 Schema / SQL
  ↓
在 PostgreSQL / Supabase 创建用户业务表
  ↓
企业 SSO 提供 user_id / tenant_id
  ↓
Supabase JWT + RLS 做租户隔离
  ↓
Sandpack 预览、调试、保存版本、打包部署
```

### 标准话术

> 我们项目早期基于 LlamaCoder 做二次改造。原版 LlamaCoder 更像开源版 Claude Artifacts，主要解决 prompt 生成 React 小应用和在线预览。我们在这个基础上做了企业化扩展：加入 Router / Planner 多阶段生成，拆出页面生成、Schema 生成、SQL 建表、路由规划和数据绑定；平台控制面数据放 MySQL，用户生成应用后的业务数据放 PostgreSQL / Supabase；权限接企业 SSO，拿到 user_id 和 tenant_id 后通过 Supabase JWT 和 RLS 做租户隔离；前端侧继续保留流式生成和 Sandpack 预览体验，但增加了流式解析、错误反馈和增量修改能力。

---

## 2. 你们和原版 LlamaCoder 的区别是什么？

这是非常可能被问到的，因为你一旦说“基于开源件改”，面试官会追问你们到底改了什么。

| 原版 LlamaCoder            | 你们二次改造后                           |
| -------------------------- | ---------------------------------------- |
| 一句 prompt 生成小应用     | 面向企业内部轻应用生成                   |
| 偏 Demo / Claude Artifacts | 偏企业级平台                             |
| 主要生成 React 前端代码    | 生成页面、Schema、SQL、CRUD、路由        |
| Together AI 直接生成代码   | Router / Planner / Codegen 多阶段控制    |
| 数据层较弱                 | MySQL 控制面 + PG/Supabase 数据面        |
| 无企业权限体系             | 企业 SSO + Supabase JWT + RLS            |
| 单次生成为主               | 支持对话式增量修改                       |
| 简单预览                   | Sandpack 预览 + 错误反馈 + 长代码优化    |
| 缺少平台元数据             | 应用、页面、版本、任务状态、审计落 MySQL |

### 标准话术

> 原版 LlamaCoder 更像验证“自然语言生成 React 应用”的交互闭环。我们真正做的是把它企业化：一方面把一次性代码生成拆成 Router、Planner、Codegen 多阶段，降低不可控风险；另一方面补齐数据层、权限层、版本层和交付层，让它从一个 Demo 工具变成企业内部轻应用生成平台。

---

## 3. 为什么选 LlamaCoder 和 Together AI SDK？

### 回答要点

- LlamaCoder 已经验证了 prompt-to-app 的产品体验。
- Together AI 对开源代码模型支持比较好。
- 适合快速验证 PoC。
- 你们的核心价值在企业化改造，不是从零造模型平台。
- 早期选择成熟开源底座可以降低试错成本。

### 标准话术

> 早期选 LlamaCoder 主要是为了快速验证自然语言生成轻应用的闭环。它本身已经打通了 Together AI 模型调用、React 代码生成和浏览器预览。我们当时更关注企业内部轻应用场景能不能成立，所以先基于它做 PoC，再逐步补齐 Router / Planner、Schema / SQL、权限、多租户、版本和部署能力。

---

# 二、前端流式生成与 SDK 类

## 4. Together AI SDK 在你们系统里负责什么？

### 回答要点

Together AI SDK 主要负责：

- 模型调用；
- 模型选择；
- 参数配置；
- prompt 请求；
- stream 流式返回；
- 错误处理；
- 和上层业务封装对接。

### 标准话术

> Together AI SDK 主要负责和 Together 托管模型服务交互，包括模型选择、请求发送、流式输出和错误处理。我们在 SDK 之上做了一层业务封装，把一次生成任务包装成可执行对象，前端消费它返回的文本、代码、状态和最终结果。

---

## 5. 你之前说的 runnable 是什么？

这里要避免说成 LangChain Runnable。

### 推荐回答

> runnable 不是我一定要绑定到某个三方框架的概念。我们项目里更像业务层对一次生成任务的封装。它把 Together AI SDK 的模型调用、流式输出、任务状态和前端 UI 分发封装起来。前端通过这个对象触发生成，并消费过程中产生的文本流、代码流、状态事件和最终结果。

### 可以画成：

```text
runnable
  ├─ input：用户需求、上下文、模型配置
  ├─ execute：调用 Together AI SDK
  ├─ stream：消费模型流式输出
  ├─ parse：拆分文本、代码、Schema、SQL
  ├─ dispatch：更新聊天区、代码区、预览区、状态区
  └─ final：返回最终代码和结构化产物
```

---

## 6. 前端如何处理模型流式返回？

### 回答要点

不要只说 SSE。你现在应该说：

- 底层是模型流式返回；
- 上层通过 Together AI SDK 或业务 runnable 消费；
- 前端按事件或内容类型分发；
- 文本、代码、Schema、SQL 分开处理；
- 最终代码进入 Sandpack；
- 不要每个 token 都触发重组件渲染。

### 标准话术

> 前端不会把所有流式内容直接塞进一个状态里。我们会把流式内容分成文本说明、代码片段、结构化 Schema / SQL 和状态信息。流式阶段主要做轻量展示，避免频繁触发 Sandpack 和代码高亮重渲染。等完整代码块结束后，再把最终代码提交给 Sandpack 预览。

---

## 7. 流式代码生成为什么会卡？怎么优化？

### 高频问题

因为你的项目里有 Sandpack 和长代码流式生成，面试官很可能追问。

### 回答要点

| 问题          | 原因                   | 解决                          |
| ------------- | ---------------------- | ----------------------------- |
| 页面卡顿      | 每个 token 都 setState | buffer 批量刷新               |
| 代码高亮卡顿  | 长代码频繁重新高亮     | 延迟高亮 / 最终态高亮         |
| Sandpack 卡顿 | 每次代码变化都重新编译 | 流式态和预览态分离            |
| Preview 重建  | 组件卸载重挂载         | 隐藏代替卸载                  |
| 内网依赖慢    | CDN / 外部依赖不可达   | 依赖白名单、本地化、shim      |
| 大文件渲染慢  | React render 频繁      | useRef 缓存、虚拟化、分片更新 |

### 标准话术

> 我们把“流式生成态”和“可运行预览态”分开。模型生成时先轻量展示代码，不实时推给 Sandpack 编译。等代码块完整后，或者用户点击 Run，再提交给 Sandpack。这样可以避免每个 token 都触发打包和预览重建。

---

## 8. Sandpack 在企业内网环境下有什么坑？

### 回答要点

- 依赖下载受限；
- CDN 不可用；
- 版本不稳定；
- Tailwind / CSS 注入异常；
- 运行时报错不易结构化；
- 长代码预览性能差；
- 沙箱和宿主通信要控制。

### 标准话术

> Sandpack 在公网 Demo 里比较顺，但企业内网会遇到依赖源不可达、CDN 受限、版本不一致等问题。我们会尽量固定模板和依赖版本，做依赖白名单，对常用库做本地化或 shim，并把 Sandpack 的编译错误、运行时错误和 console 输出统一收集，反馈给前端调试区和后续 QA Agent。

---

# 三、Router / Planner / Codegen 类

## 9. 为什么要拆 Router、UIPlanner、SupabasePlanner、RoutingPlanner？

### 回答要点

原版 LlamaCoder 一次性生成容易不可控。企业级场景需要拆任务。

| 模块            | 职责                                                 |
| --------------- | ---------------------------------------------------- |
| Router          | 判断任务类型：新建、修改页面、加字段、加路由、修 bug |
| UIPlanner       | 规划页面结构、组件、交互                             |
| SupabasePlanner | 规划业务 Schema、表、字段、RLS、CRUD                 |
| RoutingPlanner  | 规划路由、导航、页面路径                             |
| Codegen         | 生成具体代码                                         |
| QA              | 验证结果是否可运行                                   |

### 标准话术

> 一次性让模型生成完整应用很容易失控，尤其是企业应用里页面、数据表、权限和路由都要一致。所以我们拆成多阶段：Router 先判断任务类型，Planner 分别处理 UI、数据和路由，最后 Codegen 执行生成。这样每一层输入更小、输出更结构化，也更容易验证和回滚。

---

## 10. Router 是怎么设计的？

### 推荐回答结构

```text
第一层：quick rules
  - 关键词、正则、页面名、字段名、路径

第二层：场景化检索
  - 从历史任务样例、意图样例、平台规则中找相似案例

第三层：模型兜底
  - 输出结构化 intent JSON
```

### 输出示例

```json
{
  "intent": "modify_app",
  "tasks": ["ui_change", "schema_change", "routing_change"],
  "targets": {
    "pages": ["customer-list"],
    "tables": ["customers"]
  },
  "confidence": 0.86
}
```

### 标准话术

> Router 阶段不应该读取全量源码，它只需要用户需求、轻量页面元信息、路由信息和少量历史样例。先用规则覆盖高确定性场景，再用相似案例检索增强，最后才用模型兜底输出结构化 intent。

---

## 11. Planner 和 Router 的区别是什么？

| 模块               | 回答一句话               |
| ------------------ | ------------------------ |
| Router             | 判断“这是什么任务”       |
| Planner            | 判断“这个任务具体怎么做” |
| Executor / Codegen | 真正生成或修改代码       |
| QA                 | 判断结果是否正确         |

### 标准话术

> Router 解决方向问题，Planner 解决路径问题。比如用户说“给客户列表加一个导出按钮，同时记录导出日志”，Router 判断这是 UI 修改加数据能力修改；UIPlanner 规划按钮放在哪里，SupabasePlanner 规划是否要新增 export_logs 表，RoutingPlanner 判断是否影响路由，最后 Codegen 才生成代码。

---

## 12. 怎么避免 AI 每次全量重写项目？

### 回答要点

- 保存 project snapshot；
- 保存页面元数据；
- 保存路由元数据；
- 保存 Schema 版本；
- Router 定位任务类型；
- Planner 输出 target_files；
- Codegen 只允许改目标文件；
- 用 Git diff / 文件白名单检查；
- 增量修改前对比新旧 Schema。

### 标准话术

> 我们会把应用、页面、路由、Schema 和版本信息作为平台元数据存下来。增量修改时先判断影响范围，只把相关页面、表结构和路由信息给模型，而不是全量项目。Planner 会输出 target_files 和 allowed_changes，Codegen 只能在这个范围内修改，最后通过 diff 和 QA 校验是否越界。

---

# 四、数据架构：MySQL + PostgreSQL / Supabase

## 13. 为什么平台数据存 MySQL，用户业务数据存 PG / Supabase？

这是你刚修正后的重点，必须讲准。

### 标准回答

> 我们做了控制面和数据面的拆分。平台控制面数据放 MySQL，包括应用、页面、版本、任务状态、生成记录、审计日志、租户映射等。这些数据生命周期稳定、强结构化，方便和企业内部已有系统集成。用户生成应用后的业务表和业务数据放 PostgreSQL / Supabase，因为这些表是 AI 根据 Schema 动态生成的，需要自动建表、自动 CRUD 和 RLS 隔离，PG / Supabase 在这方面更合适。

---

## 14. MySQL 具体存哪些表？

### 可回答表设计

| 表                     | 用途                                |
| ---------------------- | ----------------------------------- |
| `apps`                 | 应用基本信息                        |
| `app_pages`            | 页面元数据                          |
| `app_versions`         | 应用版本                            |
| `agent_runs`           | 一次生成 / 修改任务                 |
| `agent_steps`          | Router、Planner、Codegen、QA 等步骤 |
| `generation_artifacts` | 生成代码、SQL、Schema、预览地址     |
| `project_snapshots`    | 文件树、路由、Schema 快照           |
| `tenant_app_bindings`  | 租户和应用关系                      |
| `audit_logs`           | 操作审计                            |
| `prompt_versions`      | Prompt / 模板版本                   |
| `bad_cases`            | 失败样本和原因                      |

### 标准话术

> MySQL 是平台自己的控制面数据库。它存的是“平台如何管理应用”，不是用户应用里的业务数据。比如应用、页面、版本、任务状态、生成产物、Prompt 版本、审计日志和 Bad Case。

---

## 15. PostgreSQL / Supabase 具体存什么？

### 回答

> PG / Supabase 存的是用户生成应用运行时的业务表和业务数据。比如用户生成客户管理应用，就会创建 customers、contacts、follow_records 之类的业务表。每张业务表会统一带 tenant_id，必要时带 created_by / updated_by，用于 RLS 策略。

### 业务表示例

```sql
create table customers (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  name text not null,
  phone text,
  status text,
  created_by text,
  created_at timestamptz default now()
);
```

---

## 16. MySQL 和 Supabase 之间怎么关联？

### 回答要点

MySQL 存映射关系：

```text
app_id
tenant_id
version_id
schema_version
supabase_project_id
table_name
field_schema
rls_policy_version
```

### 标准话术

> MySQL 里会存应用版本对应的 Schema 元信息、业务表名、字段配置和 Supabase 侧的表映射。真正的数据在 Supabase / PG，但平台通过 MySQL 的元数据知道某个应用版本对应哪些表、哪些字段、哪些 RLS 策略，以及前端应该如何渲染和绑定数据。

---

# 五、企业 SSO + Supabase RLS 权限类

## 17. 你们的租户权限怎么做？

### 标准回答

> 我们没有重新造一套账号体系，而是接企业已有的单点登录和一体权限系统。用户登录后，平台可以拿到 user_id / employee_id 和 tenant_id。平台后端基于这些可信身份信息生成或传递 Supabase 可识别的 JWT。前端通过 Supabase Client 访问业务数据时携带这个 token，Supabase RLS 从 JWT 中读取 tenant_id，和业务表里的 tenant_id 做匹配，从数据库层实现租户隔离。

---

## 18. 为什么不只在前端过滤 tenant_id？

### 标准回答

> 前端过滤只能提升体验，不能作为安全边界。用户可以绕过前端直接请求接口或 Supabase。如果只靠前端过滤，就存在越权风险。RLS 是数据库层的强约束，即使用户绕过前端，只要 JWT 里的 tenant_id 和数据行的 tenant_id 不一致，数据库也不会返回数据。

---

## 19. Supabase RLS 策略怎么写？

### 示例

```sql
create policy "tenant_isolation"
on customers
for select
using (
  tenant_id = auth.jwt() ->> 'tenant_id'
);
```

如果涉及写入：

```sql
create policy "tenant_insert"
on customers
for insert
with check (
  tenant_id = auth.jwt() ->> 'tenant_id'
);
```

### 标准话术

> 查询策略用 `using` 控制哪些行可见，写入策略用 `with check` 控制写入的数据是否属于当前租户。这样不仅能防止越权查询，也能防止用户伪造 tenant_id 写入其他租户数据。

---

## 20. tenant_id 从哪里来？可信吗？

### 标准回答

> tenant_id 来自企业 SSO / 一体权限系统，不是前端自己传的。用户登录成功后，后端从可信身份系统拿到 user_id 和 tenant_id，再放进 Supabase JWT。前端只能携带 token，不能随意修改 token 里的租户身份。

---

## 21. 如果一个用户属于多个租户怎么办？

### 回答思路

- 企业权限系统返回用户可访问租户列表；
- 当前工作空间选择一个 active_tenant_id；
- JWT 中放当前租户；
- 切换租户时重新签发 token；
- MySQL 存 app 与 tenant 的归属；
- Supabase RLS 按 active tenant 隔离。

### 标准话术

> 多租户用户不能简单把所有 tenant_id 都放开。更稳的方式是用户进入某个工作空间时确定 active_tenant_id，后端基于这个租户签发当前 Supabase JWT。切换租户时重新换 token。这样 RLS 判断简单，也更容易审计。

---

# 六、Schema / SQL / 动态建表类

## 22. 你们怎么从自然语言生成 Schema 和 SQL？

### 回答链路

```text
用户需求
  ↓
UIPlanner 提取字段和页面结构
  ↓
SupabasePlanner 生成业务 Schema
  ↓
Schema 校验
  ↓
SQL 生成
  ↓
SQL 安全检查
  ↓
执行建表 / 迁移
  ↓
保存 Schema 版本到 MySQL
```

### 标准话术

> 我们不会直接让模型生成 SQL 就立刻执行。中间会先生成结构化 Schema，比如表名、字段名、字段类型、是否必填、默认值、索引建议、tenant_id 字段等。Schema 经过校验后再生成 SQL。执行后把 Schema 版本和表映射保存到 MySQL，供后续页面渲染和增量修改使用。

---

## 23. 动态建表有什么风险？怎么控制？

| 风险           | 控制方式                            |
| -------------- | ----------------------------------- |
| SQL 注入       | 不直接拼用户输入，Schema 白名单生成 |
| 表名混乱       | 统一命名规则                        |
| 字段类型错误   | 类型枚举限制                        |
| 缺少 tenant_id | 建表模板强制注入                    |
| 缺少 RLS       | 建表后强制启用 RLS                  |
| 重复建表       | MySQL 记录 schema_version           |
| 破坏旧数据     | 迁移前 diff 和备份                  |
| SQL 执行失败   | dry-run / transaction / rollback    |
| 字段删除风险   | 默认禁止自动删除字段                |

### 标准话术

> 动态建表的核心风险是模型输出不可控，所以我们不让模型自由写任意 SQL，而是先约束成 Schema，再由平台模板生成 SQL。所有业务表强制带 tenant_id，建表后自动开启 RLS。增量迁移默认只允许新增表和新增字段，删除字段、改字段类型这类高风险操作需要人工确认。

---

## 24. 新旧 Schema 怎么做增量修改？

### 回答

```text
旧 Schema
  ↓
新需求生成候选 Schema
  ↓
Schema diff
  ├─ 新增字段
  ├─ 新增表
  ├─ 字段类型变化
  ├─ 字段删除
  └─ 关系变化
  ↓
生成迁移计划
  ↓
低风险自动执行，高风险人工确认
```

### 标准话术

> 对话式改表时，我们会把新旧 Schema 做 diff。新增字段、新增表一般可以自动迁移；字段删除、字段类型变更、关系变更可能影响历史数据，需要提示风险并走人工确认。迁移执行后更新 MySQL 里的 Schema 版本，前端再基于新 Schema 更新表单和列表。

---

# 七、AI Coding / Harness / SDD 类

## 25. 你理解的 AI Coding 工程化是什么？

### 标准回答

> AI Coding 工程化不是简单用 AI 写代码，而是把需求、Spec、上下文、执行、验证、代码审查、CI/CD 和反馈迭代串成闭环。模型只负责生成，真正能落地靠外层 Harness：包括上下文装配、工具边界、任务状态、自动测试、失败重试、质量门禁和 Bad Case 沉淀。

---

## 26. Command、Agent、Skill、Rule 分别是什么？

结合你的 AI 研发提效工具包讲，因为简历里写了 Commands、Agents、Skills、Rules。

| 概念    | 面试表达                                             |
| ------- | ---------------------------------------------------- |
| Command | 用户触发的任务入口，如修 bug、生成测试、代码审查     |
| Agent   | 执行某类任务的角色，如测试 Agent、Review Agent       |
| Skill   | 可复用能力包，如 Playwright 执行、接口校验、错误归因 |
| Rule    | 执行约束，如不能改某些文件、必须跑哪些命令           |
| Spec    | 需求和验收标准                                       |
| Runner  | 执行命令、收集日志和测试结果                         |

### 标准话术

> Command 是入口，Agent 是角色，Skill 是能力模块，Rule 是边界约束，Spec 是验收标准，Runner 是执行和反馈环境。AI Coding 要团队级落地，就要把这些东西标准化，而不是每个人随便和模型对话。

---

## 27. 什么是 Harness Engineering？

### 标准回答

> Harness Engineering 可以理解为包在 AI 外面的一整套工程控制框架。它不改变模型本身，但通过上下文管理、工具权限、执行记录、自动验证、失败重试、质量门禁和审计日志，让 AI 的输出可控、可验证、可回滚。

### 可以拆成：

| 层                | 做什么                        |
| ----------------- | ----------------------------- |
| Context Harness   | 控制给模型什么上下文          |
| Tool Harness      | 控制能调用什么工具            |
| Execution Harness | 控制命令怎么执行              |
| Test Harness      | 自动跑 lint、tsc、test、build |
| Review Harness    | 代码审查、安全检查            |
| Eval Harness      | 记录成功率、失败原因、ROI     |
| Audit Harness     | 保存日志、diff、报告          |

---

## 28. SDD / Spec Driven Development 怎么落地？

### 标准回答

> 在 AI Coding 里，Spec 是控制模型输出的第一道门禁。我们会把需求转成结构化 Spec，包括业务目标、页面行为、接口约束、数据结构、验收标准、测试点和禁止事项。Agent 执行时围绕 Spec 做任务拆解，生成代码后通过测试和自检报告验证是否满足 Spec。

### Spec 字段示例

```json
{
  "goal": "为客户列表增加导出功能",
  "scope": ["src/pages/customer-list.tsx"],
  "acceptance": [
    "列表页出现导出按钮",
    "点击后生成导出记录",
    "导出失败时展示错误提示"
  ],
  "constraints": ["不能修改登录模块", "不能新增未批准依赖"],
  "tests": ["Playwright 验证按钮可见", "模拟导出失败时展示 toast"]
}
```

---

# 八、测试、Playwright、TDD / BDD 类

## 29. AI 生成代码后如何验证？

### 回答链路

```text
代码生成
  ↓
静态检查：ESLint / Prettier
  ↓
类型检查：TypeScript
  ↓
单元测试：Vitest
  ↓
E2E：Playwright
  ↓
构建验证：npm run build
  ↓
代码审查：规则 + AI Review
  ↓
生成自测报告
```

### 标准话术

> AI 生成代码不能靠肉眼看。最基本要经过 lint、类型检查、测试和构建。对于前端页面，Playwright 很关键，因为它能验证真实交互路径。执行失败后，Runner 会收集错误日志、截图、trace、console 和 network，作为下一轮修复依据。

---

## 30. Playwright 测试失败，怎么判断是代码错还是用例错？

| 证据               | 可能原因                       |
| ------------------ | ------------------------------ |
| 页面白屏           | 代码运行错误                   |
| console error      | JS 异常                        |
| network 404/500    | 接口或 mock 问题               |
| selector 找不到    | 页面没渲染或选择器错           |
| 截图正常但断言失败 | 断言文案或业务预期错           |
| 点击无效           | 遮罩、disabled、异步状态       |
| 超时               | 时序问题、接口慢、等待条件错误 |

### 标准话术

> 我不会直接把测试失败归因给代码。会结合截图、trace、console、network、DOM snapshot 和测试日志判断。如果是 selector 不稳定，可能要修测试；如果是页面状态不对或 JS 报错，就回到代码修复。归因结果也会沉淀为 Bad Case。

---

## 31. TDD / BDD 在 AI Coding 中怎么做？

### TDD

```text
先根据 Spec 生成测试
  ↓
测试审核
  ↓
AI 生成实现
  ↓
运行测试
  ↓
失败修复
```

### BDD

```text
Given 某个用户状态
When 用户执行某个行为
Then 页面或系统应该产生某个结果
```

### 标准话术

> TDD 在 AI Coding 中很重要，因为测试相当于可执行验收标准。BDD 更适合和业务方对齐用户行为，比如 Given 当前用户已登录，When 点击导出按钮，Then 应生成导出任务并展示成功提示。这样既方便业务理解，也方便自动化测试生成。

---

# 九、CI/CD / DevOps / 部署类

## 32. 怎么把 AI Coding 接入 CI/CD？

### 回答链路

```text
需求 / Issue
  ↓
Spec 生成
  ↓
Agent 执行代码修改
  ↓
本地 Runner 验证
  ↓
生成 MR
  ↓
CI 执行 lint / test / build
  ↓
AI Review 输出风险说明
  ↓
人工合并
  ↓
灰度发布
  ↓
线上监控
  ↓
Bad Case 回流
```

### 标准话术

> AI Coding 不能绕过现有研发流程。它应该接入 CI/CD，作为代码变更的生产者，同时仍然接受 lint、测试、构建、代码审查和发布门禁。这样 AI 提交和人提交遵循同一套质量标准。

---

## 33. 如果让你部署这个 AI 应用生成平台，怎么设计？

### 回答

| 服务                  | 部署方式                     |
| --------------------- | ---------------------------- |
| Web 前端              | 静态资源 / CDN / 内部门户    |
| Platform API          | Node / NestJS 服务           |
| LLM Gateway           | 统一模型调用、流式处理       |
| Orchestrator          | Agent 编排服务               |
| Runner / Sandbox      | 独立容器，限制权限           |
| MySQL                 | 平台控制面数据库             |
| PostgreSQL / Supabase | 用户业务数据                 |
| Redis                 | 队列、缓存、锁、任务心跳     |
| OSS / 对象存储        | 代码包、截图、日志、预览产物 |
| Observability         | 日志、trace、指标            |

### 标准话术

> 生产部署时，我会把平台 API、LLM Gateway、Agent Orchestrator、Runner、数据库和对象存储拆开。Runner 要特别隔离，因为它会执行代码和命令，必须限制 CPU、内存、文件系统和网络权限。任务状态和版本记录放 MySQL，大文件产物放对象存储。

---

## 34. Runner 执行 AI 生成代码有什么安全风险？

| 风险     | 控制                          |
| -------- | ----------------------------- |
| 删除文件 | 命令白名单、工作目录隔离      |
| 读取密钥 | secret 脱敏、禁止访问敏感路径 |
| 恶意依赖 | 依赖白名单                    |
| 网络外连 | 网络限制                      |
| 无限循环 | 超时和资源限制                |
| 越权操作 | 租户隔离、权限校验            |
| 破坏环境 | 容器隔离                      |
| 误部署   | 人工审批、灰度、回滚          |

### 标准话术

> AI 生成代码不能直接在宿主机跑。Runner 应该放在受限容器或沙箱里，限制命令、网络、文件系统和资源。高风险操作必须 dry-run 或人工确认。

---

# 十、RAG / 上下文工程类

## 35. 你们应用生成平台里 RAG 存什么？

### 回答要结合你的真实项目

| 数据            | 用途                       |
| --------------- | -------------------------- |
| 页面元信息      | Router 判断目标页面        |
| 路由信息        | RoutingPlanner 判断路径    |
| Schema 历史版本 | SupabasePlanner 做增量修改 |
| 历史生成任务    | 相似场景参考               |
| 平台规则        | 约束模型输出               |
| 组件模板        | UIPlanner / Codegen 参考   |
| Bad Case        | 避免重复错误               |
| 字段命名规则    | 生成一致字段               |
| 企业规范        | 代码风格、权限规则         |

### 标准话术

> RAG 在我们这里不是普通知识库问答，而是给 Router、Planner 和 Codegen 注入证据。比如用户说“给客户页加一个跟进状态”，Router 可以通过页面元信息知道目标页面，SupabasePlanner 可以通过 Schema 历史知道 customers 表已有字段，Codegen 可以通过组件模板保持风格一致。

---

## 36. 代码 RAG 和文档 RAG 有什么区别？

| 对比     | 文档 RAG   | 代码 / 项目 RAG                |
| -------- | ---------- | ------------------------------ |
| 分块     | 标题、段落 | 文件、组件、函数、路由、Schema |
| 检索     | 语义相似   | 语义 + 路径 + 符号 + import    |
| 目标     | 回答问题   | 定位修改点                     |
| 输出验证 | 答案忠实度 | 编译、测试、运行               |
| 风险     | 答案幻觉   | 改错文件、破坏依赖             |

### 标准话术

> 代码 RAG 不能只按文本切 chunk，要保留文件路径、组件名、函数名、import/export、路由、Schema 关系。它的目标不是回答问题，而是帮助 Agent 精准定位该改哪里。

---

# 十一、全栈基础类

## 37. 前端怎么和后端协作完成动态应用生成？

### 回答

前端负责：

- 需求输入；
- 流式展示；
- 代码预览；
- Schema 变更展示；
- Supabase Client 接入；
- 错误反馈；
- 版本切换；
- 发布入口。

后端负责：

- 任务创建；
- 模型调用；
- Router / Planner；
- SQL 生成和执行；
- MySQL 元数据保存；
- 权限 token；
- 打包部署；
- 日志审计。

### 标准话术

> 这个项目不是纯前端，也不是纯后端。前端负责交互、流式生成体验、预览调试和数据绑定展示；后端负责任务编排、模型调用、SQL 执行、元数据管理、权限和部署。两边通过 run_id、schema_version、app_id、version_id 这些关键 ID 串起来。

---

## 38. 你作为前端背景，怎么证明自己具备全栈能力？

### 推荐回答

> 我的优势不是传统后端深度，而是能把前端工程、AI 生成链路、数据 Schema、权限、预览、测试和交付串起来。比如在应用生成平台里，我不只是写页面，还参与了 Together AI 流式结果承接、Schema / SQL 产物承接、Supabase Client、多租户身份传递、RLS 配合、Sandpack 调试和版本交付链路。对于后端侧，我更熟 TypeScript / Node 的实现方式，也能讲清 MySQL、PG、Redis、Runner、CI/CD 在系统里的分工。

---

# 十二、运维智能体补充类

虽然这个 JD 更偏 AI Coding，但他们可能会问你的运维智能体，因为简历里也写了。

## 39. 运维智能体和应用生成智能体的架构有什么不同？

| 对比     | 应用生成智能体                  | 运维智能体                             |
| -------- | ------------------------------- | -------------------------------------- |
| 目标     | 生成应用                        | 诊断和处置故障                         |
| 输入     | 自然语言需求                    | 工单、告警、日志                       |
| 核心链路 | Router → Planner → Codegen → QA | 分诊 → 证据 → 诊断 → 审批 → 执行 → RCA |
| 风险     | 生成错误代码                    | 误操作生产                             |
| 安全重点 | 权限、数据隔离、代码验证        | 人审、只读优先、模拟执行、回滚         |
| 产物     | 应用、代码、Schema              | 根因、处置建议、RCA                    |

### 标准话术

> 应用生成智能体偏创造型任务，重点是生成正确应用；运维智能体偏诊断和决策任务，重点是证据链、安全边界和人审。两者都需要 Agent Workflow、Checkpoint 和日志审计，但风险控制重点不同。

---

## 40. 运维 Agent 为什么不能全自动执行？

### 标准回答

> 运维场景涉及生产系统，错误动作可能造成事故。Agent 可以做证据收集、根因假设、处置建议，但重启、扩容、回滚、删除、配置变更这类动作必须人工审批。我们的设计是只读证据优先，写操作走建议生成、人工确认、模拟执行、受控执行、结果验证和 RCA。

---

# 十三、面试官可能会组合出的系统设计题

## 41. 设计一个企业 AI Coding 平台

你可以按这八层回答：

```text
1. 用户入口
   IDE 插件 / CLI / Web / IM

2. 任务层
   Issue / Spec / Command / Agent Run

3. 编排层
   Router / Planner / Executor / QA

4. 上下文层
   代码索引 / RAG / 项目快照 / 规范库

5. 执行层
   文件修改 / 命令执行 / 测试 / 构建 / MR

6. 数据层
   MySQL 控制面 / Redis 队列 / 对象存储 / 向量库

7. 安全层
   权限 / 沙箱 / 审批 / 审计 / 租户隔离

8. 评估层
   成功率 / 失败原因 / ROI / Bad Case
```

---

## 42. 设计一个企业轻应用生成平台

你可以按这个回答：

```text
1. 输入层
   自然语言需求、模板选择、业务场景

2. 生成编排层
   Router、UIPlanner、DataPlanner、RoutingPlanner、Codegen

3. 模型层
   Together AI SDK、模型选择、Prompt 模板、流式返回

4. 平台数据层
   MySQL：应用、页面、版本、任务、审计

5. 用户业务数据层
   PG / Supabase：业务表、业务数据、RLS

6. 权限层
   企业 SSO、user_id、tenant_id、Supabase JWT

7. 预览层
   Sandpack、错误反馈、调试面板

8. 发布层
   打包、部署、版本管理、回滚

9. 评估层
   生成成功率、预览成功率、修改成功率、耗时、Bad Case
```

---

# 十四、最可能被问的 25 个全栈技术问题清单

建议你优先背这 25 个：

1. 你们为什么基于 LlamaCoder 改，而不是自研？
2. 原版 LlamaCoder 和你们改造后的平台有什么区别？
3. Together AI SDK 在系统里负责什么？
4. 你们的 runnable 是什么？和 LangChain Runnable 是一回事吗？
5. 前端怎么处理模型流式返回？
6. 为什么 Sandpack 在流式生成场景会卡？
7. 你们怎么优化长代码流式渲染？
8. Router、UIPlanner、SupabasePlanner、RoutingPlanner 分别负责什么？
9. Router 和 Planner 的区别是什么？
10. 为什么要拆多阶段生成，而不是一次性生成？
11. 平台数据为什么存 MySQL？
12. 用户业务数据为什么存 PostgreSQL / Supabase？
13. MySQL 和 Supabase 之间如何关联？
14. 企业 SSO 和 Supabase RLS 怎么打通？
15. tenant_id 从哪里来？如何保证可信？
16. RLS 的 `using` 和 `with check` 有什么区别？
17. 动态建表怎么保证安全？
18. 新旧 Schema 如何 diff 和迁移？
19. 如何避免 AI 每次全量重写项目？
20. AI Coding 里的 Command、Agent、Skill、Rule 是什么？
21. 什么是 Harness Engineering？
22. SDD / Spec Driven Development 怎么落地？
23. AI 生成代码后怎么验证？
24. Playwright 失败怎么判断是代码错还是用例错？
25. 怎么把 AI Coding 接入 CI/CD 并衡量 ROI？

---

# 十五、你的最终技术定位话术

你面试这个 JD，建议用这段作为核心口径：

> 我的背景是前端和工程化，但最近一年做的工作已经偏 AI Coding 和 Agent 工程落地。我们基于 LlamaCoder 和 Together AI SDK 做了企业级 AI 轻应用生成平台，把原来 prompt 生成 React 小应用的 Demo 能力，扩展成 Router / Planner 多阶段生成、Schema / SQL 自动建表、MySQL 平台控制面、PostgreSQL / Supabase 用户业务数据面、企业 SSO 鉴权、Supabase RLS 租户隔离、Sandpack 预览调试和版本化交付闭环。
>
> 同时我也参与了 AI 研发提效工具包建设，把 Commands、Agents、Skills、Rules、Spec、Playwright、CI/CD、质量门禁和 Bad Case 反馈串成 AI Coding 工程化流程。我的优势不是单点模型能力，而是能把 AI 工具、前端工程、数据权限、测试验证和企业交付结合起来，形成可控、可验证、可推广的解决方案。
