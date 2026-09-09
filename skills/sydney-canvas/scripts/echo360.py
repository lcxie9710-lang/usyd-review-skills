#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sydney-canvas — Echo360 lecture-recording transcript tool (pure HTTP).

No browser needed. The agent calls ONE subcommand, on demand:

    python scripts/echo360.py list <course_id>
    python scripts/echo360.py transcript <course_id> --lesson "关键词"
    python scripts/echo360.py transcript <course_id> --all

Requires a Canvas personal access token (env CANVAS_TOKEN or config.json).
The Echo360 session is established automatically via the sessionless LTI launch
(no separate SSO login).
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

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from src.canvas_client import CanvasClient  # noqa: E402
from src.config import load_config, require_token  # noqa: E402
from src.echo360 import Echo360  # noqa: E402


def _client(args) -> CanvasClient:
    cfg = args.cfg
    token = require_token(cfg)
    return CanvasClient(base=cfg["canvas_base"], token=token)


def _echo(args) -> Echo360:
    cfg = args.cfg
    return Echo360(client=_client(args), tool_id=int(cfg.get("echo360_tool_id", 11653)))


def _find_course(client: CanvasClient, course_id: int) -> dict:
    for c in client.list_courses():
        if int(c["id"]) == int(course_id):
            return c
    sys.exit(f"[echo360] 未找到课程 id={course_id}（可能不在你的当学期课程里）。")


def _dump(obj, compact: bool) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=None if compact else 2))


def cmd_list(args) -> dict:
    client = _client(args)
    _find_course(client, args.course_id)
    e = _echo(args)
    meta = e.start_session(args.course_id)
    recs = e.list_recordings()
    return {
        "success": True,
        "course_id": args.course_id,
        "section_id": meta.get("section_id"),
        "count": len(recs),
        "recordings": recs,
    }


def cmd_transcript(args) -> dict:
    client = _client(args)
    course = _find_course(client, args.course_id)
    e = _echo(args)
    meta = e.start_session(args.course_id)
    recs = e.list_recordings()

    if args.all and args.lesson:
        sys.exit("[echo360] 不能同时使用 --all 与 --lesson。")
    if args.lesson:
        needle = args.lesson.strip().lower()
        recs = [r for r in recs if needle in r["name"].lower() or needle in (r.get("lesson_id") or "").lower()]

    course_code = str(course.get("course_code") or course["id"])
    out_dir = os.path.join(args.cfg.get("output_dir", "data"), "transcripts", _safe(course_code))
    os.makedirs(out_dir, exist_ok=True)

    saved = []
    for r in recs:
        media = _pick_media(r.get("medias", []))
        if not media:
            saved.append({"lesson": r.get("name"), "status": "no_media", "path": ""})
            continue
        dest = os.path.join(out_dir, f"{_safe(r.get('name') or media['media_id'])}.txt")
        try:
            path = e.download_transcript(r["lesson_id"], media["media_id"], dest)
            n = len(e.get_transcript(r["lesson_id"], media["media_id"]))
            saved.append({"lesson": r.get("name"), "media_id": media["media_id"], "cues": n, "path": path})
        except Exception as exc:  # noqa: BLE001
            saved.append({"lesson": r.get("name"), "media_id": media["media_id"], "status": "error", "error": str(exc)})

    return {
        "success": True,
        "course_id": args.course_id,
        "section_id": meta.get("section_id"),
        "transcripts": saved,
    }


def _pick_media(medias: list[dict]) -> dict | None:
    """Prefer an available Video media; else the first available media."""
    if not medias:
        return None
    avail = [m for m in medias if m.get("is_available") is not False]
    for m in avail:
        if m.get("media_type") == "Video":
            return m
    return avail[0] if avail else None


def _safe(name: str) -> str:
    import re

    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "untitled")).strip(". ") or "untitled"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="sydney-canvas — Echo360 转录工具（纯 HTTP）")
    p.add_argument("--config", default=None, help="config.json 路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出某课程的录播")
    p_list.add_argument("course_id", type=int)

    p_tr = sub.add_parser("transcript", help="下载转录 txt（默认单节，--all 全部，--lesson 按标题筛选）")
    p_tr.add_argument("course_id", type=int)
    p_tr.add_argument("--lesson", default=None, help="课程标题关键词（不区分大小写）")
    p_tr.add_argument("--all", action="store_true", help="下载该课全部录播转录")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    compact = "--compact" in argv
    argv = [a for a in argv if a != "--compact"]

    parser = build_parser()
    args = parser.parse_args(argv)
    args.compact = compact
    args.cfg = load_config(args.config)
    handlers = {"list": cmd_list, "transcript": cmd_transcript}
    try:
        result = handlers[args.cmd](args)
    except Exception as exc:  # noqa: BLE001
        result = {"success": False, "error": str(exc)}
    _dump(result, getattr(args, "compact", False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
