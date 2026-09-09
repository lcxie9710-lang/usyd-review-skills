<!-- sydney-canvas | Echo360 转录抓取（纯 HTTP） -->

# Echo360 转录抓取（sydney-canvas，纯 HTTP）

## 原理

- Canvas 里的「Lecture Recordings」菜单项 = external tool `11653` = **Echo360**。
- **录播视频 + 自动转录都在 Echo360**，不在 Canvas。Canvas 只给我们一个
  sessionless LTI 启动 URL。
- **无需浏览器、无需学校登录**：`sessionless_launch` 用 Canvas token 代我们完成身份，
  Echo360 直接信任该 LTI 启动。我们只要跟着启动流程走 HTTP 即可建立会话。

## 完整流水线（`scripts/echo360.py` 已实现）

1. **建立会话**：`GET /api/v1/courses/{id}/external_tools/sessionless_launch?id=11653`
   → 解析 HTML 里的 `<form method="POST" action="https://echo360.net.au/lti/...">`
   → `POST`（带 38 个隐藏 LTI 字段）→ 获得 Echo360 会话 cookies
   （`ECHO_JWT`、`PLAY_SESSION`、CloudFront 签名）→ 拿到 `sectionId`。
2. **列录播**：`GET /section/{sectionId}/syllabus`（JSON）→ 每节课的 `lesson.id`、
   `name`、`timing.start`、`medias[].id`。
3. **取转录**：`GET /api/ui/echoplayer/lessons/{lessonId}/medias/{mediaId}/transcript`
   （JSON）→ `data.contentJSON.cues[]`，每条含 `startMs / endMs / speaker / content`。
   > 备选：`https://captions.echo360.net.au/{institutionId}/captions-{mediaId}-{ts}.vtt`
   > （WebVTT，需会话）。

## 注意

- `sessionless_launch` 的直链（`/external_tools/11653`）带 Bearer 时会跳到
  `sso.sydney.edu.au` 登录页——**必须走 `sessionless_launch` 这个 API 端点**，
  它绕开 SSO。
- 转录是结构化数据（时间戳+说话人），比 VTT 更好用；`transcript_text` 已拼成
  `[hh:mm:ss] Speaker N: 内容` 格式。
- 若某课 `medias` 为空（直播尚未转码）或转录 `status != "Available"`，如实提示，
  不臆造。

## 命令

```bash
python scripts/echo360.py list <course_id>                      # 列录播
python scripts/echo360.py transcript <course_id> --lesson "第3讲" # 单节
python scripts/echo360.py transcript <course_id> --all          # 整门
```

## 排障

| 现象 | 处理 |
|---|---|
| 缺 token | 设 `CANVAS_TOKEN` 或填 `config.json` |
| LTI 表单解析失败 | 检查 `echo360_tool_id` 是否 11653；`sessionless_launch` 页面结构变化时改 `_parse_hidden_inputs` |
| `list` 为空 | 该课可能暂无可用录播（直播未转码），可稍后再试 |
| `transcript` 报错 | 多是某个 lesson 无 media / 转录未生成；结果里会有 `status: "error"` 字段，逐个看 |
