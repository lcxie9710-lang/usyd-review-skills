# USyd Review Skills — 悉尼大学课程复习工具集

给 **agent（AI 助手）** 用的两个配套 skill,帮你把悉尼大学 Canvas 课程材料自动拉下来、整理成可复习的工作区,然后按你的意图进入不同复习模式。

```
usyd-review-skills/
├── learning-workspace/    # ① 复习工作区引擎：建区 + 5 种复习模式
│   ├── SKILL.md
│   ├── AGENT_AGNOSTIC.md  # 非 Hermes agent 的说明（Claude Code 等）
│   └── templates/         # AGENTS/PROGRESS/DECISIONS/REVIEW/TOOL 模板
└── sydney-canvas/         # ② 材料拉取器：Canvas 课件/作业 + Echo360 录播转录
    ├── SKILL.md
    ├── scripts/           # canvas_tools.py + echo360.py（多子命令）
    ├── src/               # 共享实现（requests，无浏览器）
    └── references/        # API 参考 + 排障
```

**配套逻辑**:`sydney-canvas` 负责「把材料下载并归档到工作区」,`learning-workspace` 负责「材料齐了之后怎么复习」。两个都装,体验最完整。

---

## 安装

### 方式 A:用 Hermes 安装(推荐)

```bash
# 装复习工作区引擎
hermes skills install <your-github>/usyd-review-skills/skills/learning-workspace

# 装 Canvas 材料拉取器
hermes skills install <your-github>/usyd-review-skills/skills/sydney-canvas
```

或把整个仓库设为 tap 源后搜索安装:

```bash
hermes skills tap add <your-github>/usyd-review-skills
hermes skills search canvas
hermes skills install sydney-canvas
```

### 方式 B:手动复制(任意 agent,无需命令行)

把对应 skill 文件夹整个复制到你的 skills 目录:

| 平台 | 目录 |
|---|---|
| Hermes (Windows) | `C:\Users\<你>\AppData\Local\hermes\skills\education\` |
| Hermes (macOS/Linux) | `~/.hermes/skills/education/` |
| Claude Code | `~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` |

> `sydney-canvas` 需要 Python 3.9+ 和 `requests`(`pip install requests`);`learning-workspace` 零依赖。
> 非 Hermes agent 请看 `learning-workspace/AGENT_AGNOSTIC.md`。

### 验证

```bash
hermes skills list        # 应看到 learning-workspace 和 sydney-canvas
```

---

## 快速开始(sydney-canvas)

### 1. 生成 Canvas 个人 token(必须,每人用自己的)

1. 登录 [canvas.sydney.edu.au](https://canvas.sydney.edu.au)
2. 点头像 → **Settings** → **Access Tokens** → **`+ New Access Token`**
3. 生成后设置环境变量(推荐,不落盘):

```bash
# Windows (PowerShell)
setx CANVAS_TOKEN "你的token"      # 或当前会话: $env:CANVAS_TOKEN="你的token"

# macOS / Linux
export CANVAS_TOKEN="你的token"     # 想持久化就写进 ~/.zshrc / ~/.bashrc
```

> 也可以复制 `config.example.json` 为 `config.json` 并填入 token,但**别把 config.json 提交进 git**。

### 2. 试跑

```bash
cd sydney-canvas
python scripts/canvas_tools.py whoami      # 应返回你的名字
python scripts/canvas_tools.py courses     # 列出当学期课程(记下 course_id)
python scripts/canvas_tools.py assignments <course_id>      # 作业+截止时间
python scripts/canvas_tools.py material-files <course_id>   # 下载课件
python scripts/echo360.py list <course_id>                  # 录播清单
python scripts/echo360.py transcript <course_id> --all      # 下载全部转录
```

所有命令输出 JSON。只读,不修改任何课程内容。

### 3. 配合 learning-workspace 使用(完整流程)

1. 说:「下载 COMP5318 的课件和转录」→ `sydney-canvas` 拉取并归档到复习工作区
2. 说:「开始复习 COMP5318」→ `learning-workspace` 接手,进入材料盘点 + 复习模式选择

---

## ⚖️ 合规与使用边界(请务必阅读)

本工具**只读取你自己 enrolled 课程的内容**,请在使用时遵守以下边界:

1. **仅限个人学习**:转录和课件仅供你复习使用。**不要**把抓到的转录、课件 PDF 再分发——包括发给未选课的同学、上传到任何笔记分享网站、给补习/代写机构。悉尼大学学术诚信政策明确将「上传课程材料到分享网站」列为违规。
2. **每人用自己的 token**:token 等同你的 UniKey 凭证。不要把自己的 token 给别人,也不要收集他人的。
3. **转录下载是官方已有功能**:Echo360 网页本身就提供转录 TXT 下载,本工具只是把这个动作自动化(通过 Canvas 官方的 `sessionless_launch` API 建立会话)。工具不含任何真实课程内容样本。
4. **学校政策优先**:如果某门课的老师明确关闭了转录或下载,请尊重该设置,不要尝试绕过。

**免责声明**:本项目仅供学习交流,不提供任何法律建议。使用前请自行确认符合悉尼大学学生政策和 Echo360 服务条款。

---

## 目录内 skill 自带文档

| skill | 文件 | 内容 |
|---|---|---|
| learning-workspace | `SKILL.md` | agent 指令:建区流程、5 种复习模式、意图路由 |
| learning-workspace | `AGENT_AGNOSTIC.md` | 非 Hermes agent 的完整说明 |
| sydney-canvas | `SKILL.md` | agent 指令:命令路由、归档规则、token 获取流程 |
| sydney-canvas | `README.md` | 人类可读的安装/使用说明 |
| sydney-canvas | `references/api-reference.md` | Canvas REST 端点笔记 |
| sydney-canvas | `references/echo360-strategy.md` | 转录抓取原理与排障 |

---


