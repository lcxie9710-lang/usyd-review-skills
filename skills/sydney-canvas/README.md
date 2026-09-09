# sydney-canvas — 悉尼大学 Canvas 学习 Skill

一个给 **agent 用** 的技能（skill）：通过 Canvas 官方 REST API 读取悉尼大学
`canvas.sydney.edu.au` 当前学期的课程、作业、课件，并通过 Echo360
（external tool `11653`）**纯 HTTP** 抓取已录制课程的转录。

把能力封装成**两个参考工具脚本、多个子命令**，agent **按需**调用其中一个，
只取用户当前需要的内容，而不是一次性拉全库。

## 目录结构

```
canvas_workflow/                # skill 根目录（this repo）
  SKILL.md                      # 给 agent 的指令：何时用哪个工具、路由、输出规则
  _skillhub_meta.json           # skillhub 元数据
  config.example.json           # 配置模板（复制为 config.json）
  scripts/
    canvas_tools.py             # Canvas API 参考工具（多子命令）
    echo360.py                  # Echo360 转录参考工具（纯 HTTP，多子命令）
  references/
    api-reference.md           # Canvas 端点 + 字段笔记
    echo360-strategy.md        # 转录纯 HTTP 流程 + 排障
  src/                          # 共享实现（脚本 import 它）
    canvas_client.py            # Canvas REST 客户端（分页/下载/LTI）
    downloads.py                # 作业附件 / 课件文件下载
    index.py                    # 课程 Markdown 索引生成
    echo360.py                  # Echo360 转录纯 HTTP 客户端
    config.py                   # 配置读取（token 支持环境变量）
```

## 安装（一次）

```bash
cd canvas_workflow
pip install -r requirements.txt
```

> 只要 `requests`，无浏览器、无 Playwright、无额外内核。HTML 解析用标准库 `html.parser`。

## Echo360 转录（纯 HTTP，完全自动）

录播视频和转录在 Echo360（不在 Canvas）。脚本用 `sessionless_launch` 的 LTI 表单
**纯 HTTP** 建立 Echo360 会话（**无需学校登录、无需浏览器**），再列录播、拉转录。

```bash
# 列出某课的录播
python scripts/echo360.py list 12345

# 下载某节课的转录（存为 txt）
python scripts/echo360.py transcript 12345 --lesson "Week 01"

# 下载整门课的转录
python scripts/echo360.py transcript 12345 --all
```

## 使用（agent 按需调用）

```bash
# —— Canvas API 工具 ——
python scripts/canvas_tools.py whoami                       # 验证 token
python scripts/canvas_tools.py courses                      # 当学期课程
python scripts/canvas_tools.py assignments 123              # 某课作业+截止时间
python scripts/canvas_tools.py assignment-files 123 --assignment 5   # 下载某作业附件
python scripts/canvas_tools.py modules 123                  # 某课课件/模块结构
python scripts/canvas_tools.py material-files 123           # 下载某课课件文件
python scripts/canvas_tools.py index 123                    # 生成某课作业/课件索引文档
python scripts/canvas_tools.py echo-launch 123              # 打印 Echo360 启动 URL

# —— Echo360 转录工具（纯 HTTP、全自动） ——
python scripts/echo360.py list 123                          # 列出录播
python scripts/echo360.py transcript 123 --lesson "第3讲"    # 单节课转录
python scripts/echo360.py transcript 123 --all              # 整门课转录
```

所有命令输出 JSON（`--compact` 单行）。运行目录为 skill 根目录。

## 配置

复制 `config.example.json` 为 `config.json`：

```json
{
  "canvas_base": "https://canvas.sydney.edu.au",
  "canvas_token": "",            // 或用环境变量 CANVAS_TOKEN
  "echo360_tool_id": 11653,
  "output_dir": "data"
}
```

token 也可用环境变量 `CANVAS_TOKEN`（优先生效，避免写盘）。

## 你需要做的

1. **生成 Canvas 个人 access token**：Canvas → 头像 → Settings → Access Tokens →
   `+ New Access Token`。填到 `config.json` 或设 `CANVAS_TOKEN`。

## 只读边界

只读取你本人有权限的数据；不创建/修改任何 Canvas/Echo360 内容；不抓取他人私有内容。
若某节课没有转录，脚本会如实提示，不臆造。
