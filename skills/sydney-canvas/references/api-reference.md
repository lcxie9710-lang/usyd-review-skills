<!-- sydney-canvas | Canvas REST API 参考笔记 -->

# Canvas REST API 参考（sydney-canvas）

Base：`https://canvas.sydney.edu.au/api/v1`，Bearer token 认证。所有脚本已封装。
本文件供你在需要理解字段/端点时查阅。

## 认证

- 个人 access token：Canvas → 头像 → Settings → Access Tokens → `+ New Access Token`。
- 脚本读取顺序：环境变量 `CANVAS_TOKEN` > `config.json` 的 `canvas_token`。
- 用 `Bearer <token>` 头发送；推荐。

## 客户端封装（`scripts/canvas_tools.py` 已实现）

| 子命令 | 端点 | 说明 |
|---|---|---|
| `whoami` | `GET /users/self` | 校验 token，返回当前用户 |
| `courses` | `GET /courses?enrollment_state=active&enrollment_type=student` | 当学期 active 课程 |
| `assignments <id>` | `GET /courses/:id/assignments?include[]=submission` | 作业 + 截止时间 + 状态 |
| `assignment-files <id>` | `GET /courses/:id/files/:file_id` 下载 | 从作业描述里解析附件并下载 |
| `modules <id>` | `GET /courses/:id/modules` + `/modules/:m/items` | 课件/模块结构 |
| `material-files <id>` | 同上，仅下载 `File` 类型 item | 下载课件文件 |
| `echo-launch <id>` | `GET /courses/:id/external_tools/sessionless_launch?id=11653` | 拿 Echo360 LTI 启动 URL |

## 关键字段

**Course**：`id` `course_code` `name` `term.name` `start_at` `enrollments`
**Assignment**：
- `id` `name` `due_at` `lock_at` `unlock_at`（ISO8601 UTC；注意本地时区）
- `points_possible` `submission_types[]`（`online_upload`/`online_text_entry`/`online_quiz`/...）
- `html_url`（前端页面）
- `submission.workflow_state`（`unsubmitted`/`submitted`/`graded`）
- `description`：HTML，里面可能引用 `/courses/:id/files/:file_id` 附件
**File**：`id` `display_name` `filename` `url`（实际下载地址，会 302 到内容 CDN）`size`
**Module/Item**：`Module.id` `Module.name`；`Item.type`（`File`/`Page`/`ExternalUrl`/`Assignment`/...）`Item.content_id` `Item.url` `Item.title`

## 下载文件

`course_files/<course>/assignments/` 和 `course_files/<course>/materials/` 是默认落盘位置（相对 `config.output_dir`）。

## 注意事项

- 分页：脚本自动跟 `Link: rel=next`；无需手写。
- 时间字段为 UTC ISO8601，展示时需转本地时区。
- 一个 course 的 `files` 用 `GET /courses/:id/files` 也能列出，但更常用的是从模块/作业描述反查。
- 只读：不调用任何 POST/PUT/DELETE 写操作。
