# {Course Code} {Course Name} — 期末复习工作区

## 项目概览
- **课程**: {Course Code} {Course Name}
- **内容**: {brief scope}
- **目标**: 系统化期末复习，互动式辅导达成深度理解
- **语言**: 简体中文

## 目录
```
{course-dir}/
├── AGENTS.md       ← 本文件：入口、规范
├── PROGRESS.md     ← 当前进度
├── DECISIONS.md    ← 重要决策及原因
├── REVIEW.md       ← 易遗忘重难点，期末集中复习
├── TOOL.md         ← 本地工具索引
├── tool/           ← 稳定复习工具脚本
├── notes/          ← 各周知识笔记（每任务对应一个文件）
│   ├── Week01-{Topic}.md
│   └── ...
└── materials/      ← 原始材料（只读，绝不修改）
    ├── lectures/
    ├── transcripts/
    ├── exercises/
    └── exams/
```

## 硬约束
1. `materials/` 下的一切只读，笔记和总结写入`notes/` 目录
2. 任一时刻只有 1 个任务处于"进行中"，验收标准满足才能关闭
3. 状态完全由 PROGRESS.md / DECISIONS.md / AGENTS.md 描述，不依赖会话记忆
4. 解答优先基于原始材料，不足时联网补充并注明来源
5. 引导式教学：提问引导用户推理，用户放弃时才直接给答案
6. 同一个知识点被反复追问（≥3 次）时，自动记入 REVIEW.md 标题，并在 REVIEW.md 记录核心要点供期末集中复习
7. 每个任务知识梳理阶段必须生成对应笔记文件到 `notes/` 目录，命名格式 `Week{NN}-{Topic}.md`；已完成的任务若缺失笔记文件也需补上

## 每次会话开始（上班）
1. 读 PROGRESS.md 了解当前状态和下一步
2. 读 DECISIONS.md 了解重要决策
3. 与用户确认本次任务、验收标准，在 PROGRESS.md 中标记为"进行中"
4. 开始工作

## 每次会话结束（下班）
1. 更新 PROGRESS.md：完成/阻塞/下一步
2. 如有重要决策，记录到 DECISIONS.md
3. 回顾本次任务中哪些知识点被反复追问（≥3 次），记入 REVIEW.md
4. 扫一眼 AGENTS.md / PROGRESS.md / DECISIONS.md / REVIEW.md / TOOL.md，确保无矛盾（状态一致、无断裂引用）
5. 检查 TOOL.md 与 tool/ 目录下工具文件名一致：TOOL.md 列出的工具必须存在；tool/ 新增、删除、重命名后必须同步更新 TOOL.md
6. 确保下一个 Agent 只读文档就能接手

## 任务格式（PROGRESS.md）
```
### T{NN}: {描述}
- 状态: pending | in_progress | completed | blocked
- 验收标准: {可验证的完成条件}
- 开始: {时间}
- 完成: {时间 或 -}
- 备注: {阻塞原因等}
```

## 工具速查
| 材料类型 | 读取方式 |
|----------|----------|
| TXT/MD 文本 | `read_file` |
| PDF 幻灯片 | `terminal` + `pdftotext` / `pdfplumber` |
| 图片/图表 | vision 分析 |
| PDF 页面截图 | `python tool/render_pdf_page.py <pdf> <page> <output.png>` |
| 关键词搜索 | `search_files` |
| 写笔记 | `write_file` / `patch` |
