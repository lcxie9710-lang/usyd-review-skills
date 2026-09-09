#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sydney-canvas — Canvas LMS API reference tool.

The agent calls ONE subcommand at a time, on demand, for the specific content the
user wants. It does NOT download everything at once.

Requires a Canvas personal access token (env CANVAS_TOKEN or config.json).

Usage (run from the skill root, i.e. canvas_workflow/):
    python scripts/canvas_tools.py whoami
    python scripts/canvas_tools.py courses
    python scripts/canvas_tools.py assignments <course_id>
    python scripts/canvas_tools.py assignment-files <course_id> [--assignment <id>]
    python scripts/canvas_tools.py modules <course_id>
    python scripts/canvas_tools.py material-files <course_id>
    python scripts/canvas_tools.py echo-launch <course_id>

Output is JSON (add --compact for one-line).
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


configure_output_encoding()

# Make `src` importable regardless of cwd.
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from src.canvas_client import CanvasClient  # noqa: E402
from src.config import load_config, require_token  # noqa: E402
from src.downloads import download_assignment_attachments, download_course_materials  # noqa: E402
from src.index import relpath  # noqa: E402


def _client(cfg: dict) -> CanvasClient:
    token = require_token(cfg)
    return CanvasClient(base=cfg["canvas_base"], token=token)


def _dump(obj, compact: bool) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=None if compact else 2))


# --- subcommands -----------------------------------------------------------

def cmd_whoami(args) -> dict:
    me = _client(args.cfg).whoami()
    return {"success": True, "user": {"id": me.get("id"), "name": me.get("name"), "login": me.get("login_id")}}


def cmd_courses(args) -> dict:
    courses = _client(args.cfg).list_courses()
    items = [
        {
            "id": c["id"],
            "course_code": c.get("course_code", ""),
            "name": c.get("name", ""),
            "term": (c.get("term") or {}).get("name", ""),
            "start_at": (c.get("start_at") or ""),
            "url": f"{args.cfg['canvas_base']}/courses/{c['id']}",
        }
        for c in courses
    ]
    return {"success": True, "count": len(items), "courses": items}


def cmd_assignments(args) -> dict:
    client = _client(args.cfg)
    assignments = client.list_assignments(args.course_id)
    items = []
    for a in assignments:
        sub = a.get("submission") or {}
        items.append({
            "id": a["id"],
            "name": a.get("name", ""),
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "submission_types": a.get("submission_types", []),
            "submit_status": sub.get("workflow_state", ""),
            "html_url": a.get("html_url", ""),
            "has_attachments": bool(_attachment_ids(a.get("description", ""))),
        })
    items.sort(key=lambda x: x["due_at"] or "9999")
    return {"success": True, "course_id": args.course_id, "count": len(items), "assignments": items}


def cmd_assignment_files(args) -> dict:
    client = _client(args.cfg)
    course = client.get_course(args.course_id)
    output_dir = args.cfg["output_dir"]
    if args.assignment:
        assignments = [a for a in client.list_assignments(args.course_id) if str(a["id"]) == str(args.assignment)]
    else:
        assignments = client.list_assignments(args.course_id)
    files = []
    for a in assignments:
        for f in download_assignment_attachments(client, output_dir, course, a):
            files.append({
                "assignment_id": a["id"],
                "assignment": a.get("name", ""),
                "filename": f.filename,
                "path": f.path or "",
                "relpath": relpath(output_dir, f.path) if f.path else "",
            })
    return {"success": True, "course_id": args.course_id, "count": len(files), "files": files}


def cmd_modules(args) -> dict:
    client = _client(args.cfg)
    modules = client.list_modules(args.course_id)
    items = []
    for m in modules:
        items.append({
            "id": m["id"],
            "name": m.get("name", ""),
            "items": [
                {"type": it.get("type", ""), "title": it.get("title", ""), "url": it.get("url", ""),
                 "content_id": it.get("content_id")}
                for it in client.list_module_items(args.course_id, int(m["id"]))
            ],
        })
    return {"success": True, "course_id": args.course_id, "count": len(items), "modules": items}


def cmd_material_files(args) -> dict:
    client = _client(args.cfg)
    course = client.get_course(args.course_id)
    output_dir = args.cfg["output_dir"]
    mats = download_course_materials(client, output_dir, course)
    files = [
        {
            "module": m.module_title,
            "type": m.item_type,
            "title": m.title,
            "filename": m.filename,
            "path": m.path or "",
            "relpath": relpath(output_dir, m.path) if m.path else "",
            "source_url": m.source_url or "",
        }
        for m in mats
    ]
    return {"success": True, "course_id": args.course_id, "count": len(files), "materials": files}


def cmd_index(args) -> dict:
    """Build one Markdown index for a course: assignments + due dates + downloaded files + materials."""
    client = _client(args.cfg)
    course = client.get_course(args.course_id)  # real name/code/term
    output_dir = args.cfg["output_dir"]

    assignments = client.list_assignments(args.course_id)
    assignment_files = []
    for a in assignments:
        assignment_files.extend(download_assignment_attachments(client, output_dir, course, a))

    if args.no_materials:
        materials = []
    else:
        materials = download_course_materials(client, output_dir, course)

    from src.index import build_course_index

    path = build_course_index(output_dir, course, assignments, assignment_files, materials, [])
    return {
        "success": True,
        "course_id": args.course_id,
        "index_path": path,
        "assignments": len(assignments),
        "assignment_files": len(assignment_files),
        "materials": len(materials),
        "note": "转录（Echo360）不在其中；需要转录请调 scripts/echo360.py。",
    }


def cmd_echo_launch(args) -> dict:
    client = _client(args.cfg)
    tool_id = int(args.cfg.get("echo360_tool_id", 11653))
    url = client.sessionless_launch(args.course_id, tool_id)
    tool = {}
    try:
        t = client.get_external_tool(args.course_id, tool_id)
        tool = {"id": t.get("id"), "name": t.get("name"), "url": t.get("url")}
    except Exception as exc:  # noqa: BLE001 - tool likely account-level; detail is best-effort
        tool = {"note": f"课程级工具详情不可查（{exc}）；可能为账户级工具。启动 URL 仍有效。"}
    return {
        "success": True,
        "course_id": args.course_id,
        "tool": tool,
        "launch_url": url,
        "note": "在浏览器打开此 URL 会进入 Echo360。转录抓取请用 scripts/echo360.py。",
    }


# --- small helpers ---------------------------------------------------------

def _attachment_ids(description_html: str) -> list[int]:
    from src.downloads import extract_assignment_file_ids

    return extract_assignment_file_ids(description_html)


# --- CLI -------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="sydney-canvas — Canvas LMS API 参考工具")
    p.add_argument("--config", default=None, help="config.json 路径（默认 skill 根目录下的 config.json）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami", help="验证 token，返回当前用户")
    sub.add_parser("courses", help="列出当学期 active 课程")

    p_as = sub.add_parser("assignments", help="列出某课程的作业与截止时间")
    p_as.add_argument("course_id", type=int)

    p_af = sub.add_parser("assignment-files", help="下载作业附件文件")
    p_af.add_argument("course_id", type=int)
    p_af.add_argument("--assignment", default=None, help="只下载指定作业 id 的附件")

    p_mod = sub.add_parser("modules", help="列出某课程的模块/课件")
    p_mod.add_argument("course_id", type=int)

    p_mf = sub.add_parser("material-files", help="下载课程模块里的课件文件")
    p_mf.add_argument("course_id", type=int)

    p_ix = sub.add_parser("index", help="生成课程 markdown 索引（作业+截止时间+已下载文件）")
    p_ix.add_argument("course_id", type=int)
    p_ix.add_argument("--no-materials", action="store_true", help="索引中不含课件文件")

    p_el = sub.add_parser("echo-launch", help="打印 Echo360 工具的 LTI 启动 URL")
    p_el.add_argument("course_id", type=int)
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    compact = "--compact" in argv
    argv = [a for a in argv if a != "--compact"]

    parser = build_parser()
    args = parser.parse_args(argv)
    args.compact = compact
    cfg = load_config(args.config)
    args.cfg = cfg

    handlers = {
        "whoami": cmd_whoami,
        "courses": cmd_courses,
        "assignments": cmd_assignments,
        "assignment-files": cmd_assignment_files,
        "modules": cmd_modules,
        "material-files": cmd_material_files,
        "index": cmd_index,
        "echo-launch": cmd_echo_launch,
    }
    try:
        result = handlers[args.cmd](args)
    except Exception as exc:  # noqa: BLE001
        result = {"success": False, "error": str(exc)}
    _dump(result, getattr(args, "compact", False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
