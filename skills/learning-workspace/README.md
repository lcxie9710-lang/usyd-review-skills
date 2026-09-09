# Learning Workspace — 学习工作区自动搭建与多模式复习

一个给 Hermes Agent 用的 skill，帮你**零手动**建好课程复习工作区，然后根据你的意图自动切换到合适的复习模式。

## 它做什么

1. **全自动搭建工作区** — 问 3 个问题（什么课、放哪、考试形式），一键生成 AGENTS / PROGRESS / DECISIONS / REVIEW / TOOL 全套文档
2. **引导补充材料** — 告诉你讲义、转录、习题、真题分别缺什么、放哪里
3. **5 种复习模式** — 根据你的意图自动匹配：
   - 从零开始逐知识点学
   - 先做题再补薄弱点
   - 逐题精讲模拟卷
   - 时间紧快速串讲考点
   - 全 MCQ 刷题

## 怎么安装

### Windows

1. 把 `learning-workspace` 文件夹**整个复制**到 Hermes skills 目录：
   ```
   %LOCALAPPDATA%\hermes\skills\education\
   ```
   （即 `C:\Users\你的用户名\AppData\Local\hermes\skills\education\`，若 `education` 文件夹不存在则新建。）

2. 搞定。Hermes 下次启动会自动发现。

### macOS / Linux

把文件夹复制到 `~/.hermes/skills/education/` 即可。

### 验证

在 Hermes 里输入：
```
hermes skills list
```
看到 `learning-workspace` 出现就说明安装成功了。

## 怎么用

在 Hermes 对话里说类似这样的话：

- 「帮我建立 COMP5318 的复习工作区」
- 「开始复习 ELEC5620」
- 「继续上次的复习」

Agent 会自动加载这个 skill，一步步引导你完成搭建和模式选择。

> **提示**：如果你想切换到别的复习方式，随时说「换个模式」「改成做题」「直接讲考点」就行。
