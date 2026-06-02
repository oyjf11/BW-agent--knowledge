---
type: project
status: done
tags:
  - 项目案例
  - 高频面试
---

# AI Coding工程化项目

## 30 秒版本
构建 AI 研发提效工具包，把 Commands、Agents、Skills、Rules、Spec、Playwright、CI/CD、质量门禁和 Bad Case 反馈串成 AI Coding 工程化闭环。模型只负责生成，真正落地靠外层 Harness。

## 1 分钟版本
AI Coding 工程化不是简单用 AI 写代码，而是把需求、Spec、上下文、执行、验证、代码审查、CI/CD 和反馈迭代串成闭环。我们建立了七层 Harness 体系：
- Context Harness：代码索引、RAG、项目快照
- Tool Harness：命令白名单、权限分级
- Execution Harness：容器隔离、超时控制
- Test Harness：lint → tsc → test → build 自动执行
- Review Harness：规则 + AI Review 双重审查
- Eval Harness：成功率、失败原因、ROI 追踪
- Audit Harness：操作日志、diff、审计报告

同时通过 SDD（Spec Driven Development）把需求转成结构化 Spec，作为模型执行的第一道门禁。核心概念包括 Command（入口）、Agent（角色）、Skill（能力模块）、Rule（边界约束）。

## 核心流程
```text
需求/Issue → Spec 生成 → Agent 执行代码修改 → 本地 Runner 验证
  → 生成 MR → CI 执行 lint/test/build → AI Review
  → 人工合并 → 灰度发布 → 线上监控 → Bad Case 回流
```

## 技术亮点
- **Harness Engineering**：七层控制框架包在 AI 外面，让输出可控可验证可回滚
- **SDD**：结构化 Spec（goal + scope + acceptance + constraints + tests）
- **质量门禁**：ESLint → TypeScript → Vitest → Playwright → Build → Review
- **Playwright 失败归因**：结合截图、trace、console、network、DOM snapshot 多证据判断
- **TDD in AI Coding**：先根据 Spec 生成测试 → 审核 → AI 实现 → 运行测试 → 修复
- **Bad Case 闭环**：失败归因 → 分类 → 知识回流的持续改进机制

## 产品价值
- 标准化 AI Coding 流程：不是每个人随便和模型对话
- 质量可度量：首次通过率、修复时间、Bad Case 分类
- 可推广：工程化体系不绑定特定模型或工具

## 可映射知识节点
- [[23.1 AI Coding应用场景✅]] - 核心概念
- [[23.2 AI Coding流程✅]] - CI/CD 集成
- [[23.3 Harness Engineering✅]] - 七层体系
- [[23.4 质量门禁✅]] - 验证链路
- [[23.5 AI Coding指标✅]] - 指标与 Bad Case
- [[23.6 高级面试关键词✅]] - 高频问答

## 高频追问
1. AI Coding 里的 Command、Agent、Skill、Rule 是什么？
2. 什么是 Harness Engineering？
3. SDD / Spec Driven Development 怎么落地？
4. AI 生成代码后怎么验证？
5. Playwright 失败怎么判断是代码错还是用例错？
6. 怎么把 AI Coding 接入 CI/CD 并衡量 ROI？
7. Runner 执行代码有什么安全风险？
