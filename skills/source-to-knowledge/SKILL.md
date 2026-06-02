---
name: source-to-knowledge
description: Use when a user provides a source document (ChatGPT export, article, PRD, transcript) and asks to extract knowledge points and integrate them into the Obsidian knowledge vault. Trigger phrases: 这份文档涉及的知识点, 写入工程知识库, 集成到vault, 知识提取.
---

# source-to-knowledge

## 目标
将外部源文档（ChatGPT 导出、技术文章、PRD、会议纪要等）中的知识，通过系统化提取、冲突检测和结构写入，集成到 Obsidian 知识库中。

## 工作流（四个阶段）

### 阶段一：知识点提取
1. 完整阅读源文档。
2. 逐一梳理所有知识点，不遗漏。
3. 对每个知识点编号（格式 `KP-N`），标注所在文档章节。
4. 使用 `references/knowledge-point-template.md` 输出「知识点清单表」。

### 阶段二：映射到知识库
1. 读取 `references/vault-structure-overview.md`，了解知识库的 44 分支结构和文件命名规范。
2. 将每个知识点与已有 vault 内容逐一交叉对比（读取对应分支的现有 .md 文件）。
3. 为每个知识点标记映射状态：已覆盖 / 空白填补 / 新增 / 潜在冲突。

### 阶段三：冲突检测与处理
1. 识别源文档声明与 vault 已有事实的差异。
2. 按 `references/conflict-detection-guide.md` 分类：无冲突 / 追加 / 命名差异 / 实质性冲突。
3. vault 已有事实为权威源。源文档的冲突主张修正后再写入。
4. 发现实质性冲突 → 标记「待确认」→ 通知用户，不写入。

### 阶段四：写入知识库
1. 对空白填补和新增知识点，写入对应分支的 .md 文件。
2. 遵循概念笔记模板格式：
   - frontmatter：`type: concept`、`status: done`、`tags: AI-Agent面试 + 主题标签`
   - 六个标准节：一句话定义 / 解决什么问题 / 如何实现 / 项目映射 / 高频追问 / 我的回答要点
3. 如新增子节点文件，更新对应目录的 `_index.md`。
4. 对已覆盖的知识点，不重复写入（可补充此前的遗漏细节，追加而非覆盖）。

## 约束
- 不删除文件。
- 不覆盖已有内容（仅追加或补充空模板）。
- 不编造项目指标。
- 不将大段源码复制到笔记中。
- 区分"已确认实现"和"表达方向"（后者标注「可作为表达方向，待补充事实依据」）。

## 输出格式
任务完成后返回：
- **知识点清单**：总数、各状态分布
- **变更摘要**：修改了哪些文件、新增了多少知识点
- **冲突报告**：发现多少冲突、如何处理、待确认项

## 参考文件
- `references/vault-structure-overview.md` — 知识库 44 分支地图和文件命名规范
- `references/knowledge-point-template.md` — 知识点提取表格模板和映射状态定义
- `references/conflict-detection-guide.md` — 冲突分类与处理规则
