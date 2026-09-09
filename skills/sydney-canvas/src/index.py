"""Build human-readable Markdown index documents for the downloaded data.

Per-course index: assignment table (due date, points, submission type, status,
link) + the downloaded assignment files; plus the course-materials listing and
(if present) the Echo360 transcript files. A master index ties everything
together.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from .downloads import CourseMaterial, DownloadedFile


def _fmt_dt(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def _status(assignment: dict) -> str:
    sub = assignment.get("submission")
    if sub and sub.get("workflow_state"):
        state = sub["workflow_state"]
        return {"submitted": "已提交", "graded": "已批改", "unsubmitted": "未提交"}.get(state, state)
    return "未提交"


def _submission_types(assignment: dict) -> str:
    types = assignment.get("submission_types", [])
    pretty = {
        "online_upload": "上传文件",
        "online_text_entry": "文本",
        "online_url": "链接",
        "online_quiz": "测验",
        "discussion_topic": "讨论",
        "external_tool": "外部工具",
        "on_paper": "纸质",
        "media_recording": "录屏",
        "student_annotation": "批注",
        "none": "无",
    }
    return ", ".join(pretty.get(t, t) for t in types) or "—"


def build_course_index(
    output_dir: str,
    course: dict,
    assignments: list[dict],
    assignment_files: list[DownloadedFile],
    materials: list[CourseMaterial],
    transcripts: list[str],
) -> str:
    """Write one course index document; returns its path."""
    course_code = str(course.get("course_code") or course["id"])
    course_name = course.get("name") or course_code
    base = os.path.join(output_dir, "index", safe(course_code))
    os.makedirs(base, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# {course_name}")
    lines.append("")
    lines.append(f"- Course id: `{course['id']}`")
    if course.get("term"):
        lines.append(f"- Term: {course['term'].get('name', '—')}")
    if course.get("start_at"):
        lines.append(f"- Start: {_fmt_dt(course['start_at'])}")
    lines.append(f"- Canvas url: https://canvas.sydney.edu.au/courses/{course['id']}")
    lines.append("")

    # Assignments table
    lines.append("## 作业清单")
    lines.append("")
    if assignments:
        lines.append("| 截止时间 | 名称 | 分值 | 提交方式 | 状态 | 链接 |")
        lines.append("|---|---|---|---|---|---|")
        for a in sorted(assignments, key=lambda x: x.get("due_at") or "9999"):
            due = _fmt_dt(a.get("due_at"))
            name = escape_cell(a.get("name", ""))
            pts = a.get("points_possible")
            pts_str = "—" if pts is None else str(pts)
            stype = _submission_types(a)
            status = _status(a)
            link = f"[打开](https://canvas.sydney.edu.au{course['id'] and '/courses/' + str(course['id']) + '/assignments/' + str(a['id'])})"
            lines.append(f"| {due} | {name} | {pts_str} | {stype} | {status} | {link} |")
        lines.append("")
        lines.append("### 已下载的作业文件")
        lines.append("")
        if assignment_files:
            lines.append("| 作业 | 文件 | 本地路径 |")
            lines.append("|---|---|---|")
            for f in assignment_files:
                lines.append(f"| {escape_cell(f.title)} | {escape_cell(f.filename)} | `{relpath(output_dir, f.path)}` |")
        else:
            lines.append("_（无下载的附件文件）_")
    else:
        lines.append("_（无作业）_")
    lines.append("")

    # Course materials
    lines.append("## 课件 / 课程资料")
    lines.append("")
    if materials:
        lines.append("| 模块 | 类型 | 标题 | 文件 / 链接 |")
        lines.append("|---|---|---|---|")
        for m in materials:
            link = f"[打开]({m.source_url})" if m.source_url and not m.path else ""
            local = f"`{relpath(output_dir, m.path)}`" if m.path else link
            lines.append(f"| {escape_cell(m.module_title)} | {m.item_type} | {escape_cell(m.title)} | {local} |")
    else:
        lines.append("_（无可下载的课件）_")
    lines.append("")

    # Transcripts (populated by the Echo360 step)
    lines.append("## 课程转录")
    lines.append("")
    if transcripts:
        for t in transcripts:
            lines.append(f"- `{relpath(output_dir, t)}`")
    else:
        lines.append("_（尚未抓取 / 无转录）_")
    lines.append("")

    dest = os.path.join(base, "index.md")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return dest


def build_master_index(output_dir: str, course_indexes: list[dict]) -> str:
    """Top-level README listing every course's index."""
    lines = ["# Canvas 课程汇总", ""]
    for item in course_indexes:
        lines.append(f"- [{item['name']}]({relpath(output_dir, item['index'])})  \n  id `{item['id']}`")
    if not course_indexes:
        lines.append("_（暂无课程）_")
    lines.append("")
    dest = os.path.join(output_dir, "INDEX.md")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return dest


# --- small helpers ---------------------------------------------------------

def safe(name: str) -> str:
    import re

    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ") or "untitled"


def escape_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def relpath(root: str, path: str) -> str:
    if not path:
        return ""
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path
