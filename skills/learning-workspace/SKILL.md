---
name: learning-workspace
description: Auto-scaffold a self-documenting course review workspace, guide user to provide materials, then support 5 proven review modes (per-concept teaching, practice-first, exam walkthrough, fast scan, MCQ quiz). Pure document-driven — no scripts, no Makefile. 针对Hermes agent编写，其他agent请使用 /AGENT_AGNOSTIC.md
---

# Learning Workspace — 学习工作区自动搭建与多模式复习

## Trigger
User wants to start or resume structured review for a university course. They may say:
- "帮我建立复习工作区"
- "开始复习 XXX 课程"
- Any mention of course review + materials

## Phase 0: Workspace Scaffolding (全自动搭建)

### 0a. Gather Info
Ask the user via `clarify` (one at a time):
1. **Course code + name** (e.g. COMP9123 Data Structures & Algorithms)
2. **Target directory** — will be auto-detected from the current working directory. Common parent for review courses: `~/review/`. If user specifies a path, use it. Confirm it exists or offer to create it.
3. **Exam format** — what do they know about the final exam? (MCQ only? Short answer? Open/closed book? Cheatsheet allowed?)

### 0b. Create Directory Structure
```
{course-dir}/
├── AGENTS.md       ← 入口：概览、约束、会话流程
├── PROGRESS.md     ← 当前进度：任务状态、下一步
├── DECISIONS.md    ← 重要决策及原因
├── REVIEW.md       ← 易遗忘重难点，期末集中复习
├── TOOL.md         ← 本地工具索引
├── tool/           ← 稳定复习工具脚本
├── notes/          ← 各周知识笔记
└── materials/      ← 原始材料（只读）
    ├── lectures/
    ├── transcripts/
    ├── exercises/
    └── exams/
```

### 0c. Generate Core Documents from Templates
Load and fill the four templates in `templates/`:

1. **AGENTS.md** — load `templates/AGENTS.md`, replace `{Course Code}`, `{Course Name}`, `{brief scope}`, `{course-dir}` with values from 0a. Write to `{course-dir}/AGENTS.md`.
2. **PROGRESS.md** — load `templates/PROGRESS.md`, fill `{Course Code}`, `{start-date}`, set T01 as "提供课程材料". Write to `{course-dir}/PROGRESS.md`.
3. **DECISIONS.md** — load `templates/DECISIONS.md`, fill `{Course Code}`, `{date}`. Write to `{course-dir}/DECISIONS.md`.
4. **TOOL.md** — load `templates/TOOL.md`, fill `{Course Code}`. Check if `tool/render_pdf_page.py` exists in the workspace; if not, remove its row from the通用工具 table. Write to `{course-dir}/TOOL.md`.
5. **REVIEW.md** — load `templates/REVIEW.md`, fill `{Course Code}`. Write to `{course-dir}/REVIEW.md`.

All templates are at `templates/` in this skill. Load with `skill_view('learning-workspace', file_path='templates/AGENTS.md')` etc.

---

## Phase 1: Materials Collection (引导用户补充材料)

After workspace is created, guide the user to provide materials:

### Step 0: Materials may already be archived (sydney-canvas integration)

If the course is a University of Sydney course (or otherwise on Canvas/Echo360), the
`sydney-canvas` skill may have **already downloaded and archived** materials into this
workspace: 课件 → `materials/lectures/`, 转录 → `materials/transcripts/`,
作业附件 → `materials/exercises/`, 索引 → `INDEX.md`. When that is the case:

- Skip straight to **Step 1 inventory** — do NOT ask the user to re-provide materials.
- The workspace may lack `AGENTS.md`/`PROGRESS.md` if the download ran before this
  scaffold; if the five docs are missing, run Phase 0 scaffolding onto the existing
  directory (it will not touch `materials/`).
- Missing kinds (e.g. `exercises/` empty, no `exams/`) are real gaps — guide the user
  as usual for those.

### Step 1: Check what exists
Use `search_files(target='files')` on `materials/` to see what's already there.

### Step 2: Present gap report
Show what's missing vs what's needed:
```
materials/
├── lectures/        ✅ 3 PDFs found
├── transcripts/     ❌ empty — 有录音转录稿吗？
├── exercises/       ❌ empty — 有练习题/课后题吗？
└── exams/           ⚠️ 1 PDF found — 有几份模拟卷/真题？
```

### Step 3: Guide user to fill gaps
- Ask user to drop files into the corresponding directories, OR
- Ask user to tell you the path if files are elsewhere
- Do NOT proceed to teaching until at least one material source exists

### Step 4: Inventory materials
Once materials are provided, scan and catalog them:
- Count PDFs in lectures/
- Count transcript files
- List exercise files
- List exam PDFs → extract via `pdftotext` to identify exam structure

### Step 5: Create T02
After materials are in place, create T02 in PROGRESS.md:
```
### T02: 确定复习计划
- 状态: in_progress
- 验收标准: 用户确认复习模式和第1个任务的验收标准
- 开始: {today}
- 完成: -
```

---

## Phase 2: Intent Router — 意图路由（MANDATORY）

**After Phase 1 materials inventory is complete, the agent MUST proactively ask the user about their review intent. Do NOT skip this step or assume a default mode.**

### Intent Router Decision Tree

The agent constructs a `clarify` question with options tailored to available materials. The question is always:

> "这周/这次你想怎么复习？"

**Option construction rules** — include only options whose preconditions are met:

| # | Option text | Routes to | Precondition |
|---|-------------|-----------|--------------|
| 1 | "从零开始学，一个知识点一个知识点过" | Mode A | Always available |
| 2 | "先做这周的练习题，根据错题针对性补" | Mode B | `exercises/` not empty |
| 3 | "直接刷模拟卷/真题，以卷为纲" | Mode C | `exams/` not empty |
| 4 | "时间紧，快速过一遍考点就行" | Mode D | Always available |
| 5 | "只练 MCQ 选择题" | Mode E | Exam format from 0a is MCQ-only, OR user explicitly requests MCQ drill |

**Example**: If exercises/ is empty and exams/ has 2 PDFs:
→ Show options 1, 3, 4 (hide 2 because no exercises; hide 5 unless exam format is MCQ)

**After user picks**: Immediately enter the corresponding mode. Record the choice in DECISIONS.md:
```
| D002 | {date} | 选择复习模式: Mode {X} — {reason} | User chose via intent router |
```

**Mode switching**: User may change mode at any time ("换个模式", "改成做题"). When they do, record the switch in DECISIONS.md and immediately adapt.

---

### Mode A: Per-Knowledge-Point Teaching (最小知识点逐个过)
**Intent**: "从零开始学" / first-pass learning / weak foundation
**Flow**:
1. Read ALL materials for the topic (lecture PDF + transcript — MANDATORY before teaching)
2. Teach ONE knowledge point at a time (one concept, one table, one comparison)
3. After each point, wait for user to say "继续" (温和语气，不说"清楚了吗？继续？")
4. After ALL points in a section → MCQ quiz (via `clarify`, 4 options, one at a time)
5. After ALL sections in a week → write `notes/Week{NN}-{Topic}.md` → update PROGRESS.md
6. If cheatsheet is needed: append to CHEATSHEET.md after each section (per-section incremental)

**Embedded rules**:
- MCQ delivery: ONE at a time via `clarify` with 4 clickable options
- Fallback when `clarify` returns empty: plain text A/B/C/D, user types answer
- Tone: mild, supportive, no "清楚了吗？继续？" — use "有问题随时打断我~"
- Never interleave quiz with teaching — absorb all, then test

### Mode B: Practice-First Review (以练代学 / 刷题训练)
**Intent**: "先做题" / diagnostic-first / has exercises
**Precondition**: `exercises/` not empty for the current week
**Flow**:
1. Extract exercises for the week (original English, never translate)
2. Cross-validate against exam format — skip non-exam-style questions, tell user why
3. Present ONE question at a time (like a real test)
4. User attempts → brief feedback (correct/partial/wrong) → note gap, move on
5. Track errors in a 错题本 (error log) within the week's notes file
6. After all exercises: map results → deep-dive on wrong topics, brief recap on correct ones
7. Generate `notes/Week{NN}-{Topic}.md` (detailed weak areas, brief strong areas)
8. Optional MCQ quiz on weak spots only

**Pitfalls**:
- Don't deep-dive after a single wrong answer — note it, move on, synthesize at end
- Keep tone low-pressure — this is diagnostic, not graded
- If user can't answer because cheatsheet is missing the topic → give answer directly, flag gap

### Mode C: Exam Problem Walkthrough (模拟卷逐题精讲)
**Intent**: "刷模拟卷" / "以卷为纲" / learn FROM exams
**Precondition**: `exams/` not empty
**Flow**:
1. **BEFORE each question**: Search REVIEW.md + `session_search` for user's prior approach
2. Present full question text verbatim (don't summarize or pre-extract "核心考点")
3. Walk through step-by-step: 第一步/第二步/第三步... — build solution live
4. User may propose alternative approach → validate it; if correct, it becomes PRIMARY
5. After each question: write COMPLETE bilingual answer to CHEATSHEET.md at "满分级" detail
6. Show progress bar alongside each question
7. Wait for user confirmation before next question

**CRITICAL RULES**:
- **User's approach > official solution** — always check prior work first; use THEIRS in cheatsheet
- **Default is FULL detail**: Never compress cheatsheet without explicit permission. "所有过了的题，都要以照抄能拿满分的详细程度写在cheatsheet上"
- **Post-question audit (MANDATORY)**: Before writing cheatsheet, verify: (1) User's approach used? (2) Full-mark detail? (3) Bilingual?
- **Source declaration**: Always say "这是 Solution PDF 的做法" or "这是你之前在 REVIEW.md 里的做法"

**Sub-question mode** (逐小问):
- User says "一小问一小问发给我" or "我先想想思路"
- Present one sub-question at a time → user attempts → feedback → next sub-question
- After ALL sub-questions done → write complete answer to cheatsheet in one go

### Mode D: Fast Exam-Aligned Scan (快速串讲)
**Intent**: "时间紧" / "快速过考点" / "直接讲考点"
**Flow**:
1. Scan exam PDFs first → identify tested topics (serve as teaching compass, not filter)
2. Teach exam-relevant content at exam depth, section by section
3. Faster pace but still pause between sections — user can interrupt
4. Generate `notes/Week{NN}-{Topic}.md`
5. Skip MCQ quiz and practice → move to next week immediately

### Mode E: MCQ-Only Exam Workflow
**Intent**: "只练MCQ" / exam is 100% multiple-choice
**Precondition**: Exam format from 0a is MCQ-only, OR user explicitly requests
**Flow**:
1. Cheatsheet format: comparison tables (`| 中文 | English |`) — focus on concept contrast
2. Teaching: section by section → add to cheatsheet immediately → next section
3. Practice: MCQ via `clarify` after each topic
4. After wrong answers: explain why EACH distractor is wrong, not just the right answer

---

## Phase 3: Cheatsheet Management (速查表管理)

### When to create a cheatsheet
- Exam allows cheatsheet (open-book / semi-open-book)
- User explicitly asks for one

### Cheatsheet format
- **MD source**: Two-column table `| 中文 | English |` in `CHEATSHEET.md`
- **HTML output**: 3-column A4 portrait, bilingual merged, zoom toolbar (flexbox 3-column, font 4.5pt, inline Chinese+English per row, localStorage zoom persistence, print-hide toolbar)
- **Build incrementally**: After each section/topic taught, append to MD immediately — don't batch at end

### Default: Full detail
- All cheatsheet entries default to FULL bilingual detail — what user would hand-write on exam
- NEVER compress without explicit user permission
- User will say "这个缩一下" when they want less

---

## Teaching Style (Embedded from Memory)

1. **One knowledge point per message** — user explicitly said "降低我单次复习的难度"
2. **MCQ via `clarify` 4-option** — praised as "互动方式太好了"
3. **User's solution > official solution** — always check REVIEW.md first
4. **Mild, supportive tone** — no stiff checkpoint language
5. **Exercise questions in original English** — never translate
6. **Guided discovery first** — let user think, give direct answer only when they give up
7. **≥3 follow-ups on same topic** → auto-record in REVIEW.md
8. **Progress bar during mock exam practice**
9. **Per-section cheatsheet writing** — append after each section, don't wait

---

## Session Workflow Summary

### 上班 (Session Start)
1. Read PROGRESS.md → current state + next step
2. Read DECISIONS.md → important past decisions (including last used review mode)
3. **If no review mode is active for the current task → invoke Intent Router (Phase 2)** and ask user "这次想怎么复习？"
4. Confirm task with user + acceptance criteria → mark `in_progress`
5. If PROGRESS.md is stale (old timestamp, abnormal exit) → reconcile with `session_search`
6. Begin work in the selected mode

### 下班 (Session End)
1. Update PROGRESS.md — completed/blocked/next step
2. Log decisions to DECISIONS.md if any
3. Review ≥3 follow-ups → add to REVIEW.md
4. Scan all 5 docs for consistency
5. Verify TOOL.md ↔ tool/ directory
6. Ensure next agent can pick up from docs alone

---

## Pitfalls

1. **Don't create scripts/Makefile** — user rejected: "这不是编程任务"
2. **Read ALL materials before teaching** — never start teaching with partial reads
3. **Don't dump multiple knowledge points** — one concept per message
4. **Don't interleave quiz with teaching** — absorb first, then test
5. **Don't compress cheatsheet without permission** — strongest correction ever: "这复习是你在复习还是我在复习！"
6. **Check user's prior work before presenting any solution** — search REVIEW.md + session history
7. **Don't translate exercise/exam questions** — present in original English
8. **MCQ one at a time** — never batch-dump all questions
9. **Clarify fallback**: If `clarify` returns empty → plain text A/B/C/D immediately
10. **Keep workspace pure document-driven** — no automation scripts
