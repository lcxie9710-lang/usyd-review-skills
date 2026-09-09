"""Download course materials (module files) and assignment attachments.

Everything here talks to the Canvas REST API (no browser needed).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .canvas_client import CanvasClient, file_id_from_canvas_href


@dataclass
class DownloadedFile:
    """One file we fetched, with where it landed on disk."""

    course_id: int
    course_code: str
    kind: str  # 'assignment' | 'module' | 'file'
    title: str
    filename: str
    path: str
    source_url: str = ""
    size: int = 0


@dataclass
class CourseMaterial:
    """A module item that is useful to record (file downloaded, or link/pageref)."""

    course_id: int
    module_title: str
    item_type: str
    title: str
    filename: str = ""
    path: str = ""
    source_url: str = ""


_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name: str, max_len: int = 120) -> str:
    """Make a filename safe across OSes (notably Windows)."""
    name = _UNSAFE_CHARS.sub("_", (name or "untitled").strip())
    name = name.strip(". ")
    return name[:max_len] or "untitled"


def _course_dir(output_dir: str, course_code: str) -> str:
    d = os.path.join(output_dir, "course_files", safe_name(course_code))
    os.makedirs(d, exist_ok=True)
    return d


# --- assignments -----------------------------------------------------------

def extract_assignment_file_ids(description_html: str) -> list[int]:
    """Find Canvas file ids referenced in an assignment description.

    Pure-stdlib HTML parsing (html.parser) — no BeautifulSoup dependency.
    """
    if not description_html:
        return []
    from html.parser import HTMLParser

    class _HrefCollector(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.hrefs: list[str] = []

        def handle_starttag(self, tag: str, attrs) -> None:
            if tag == "a":
                for key, value in attrs:
                    if key == "href" and value:
                        self.hrefs.append(value)

    collector = _HrefCollector()
    collector.feed(description_html)
    ids: list[int] = []
    for href in collector.hrefs:
        fid = file_id_from_canvas_href(href)
        if fid and fid not in ids:
            ids.append(fid)
    return ids


def download_assignment_attachments(
    client: CanvasClient, output_dir: str, course: dict, assignment: dict
) -> list[DownloadedFile]:
    """Download files referenced by an assignment's description."""
    course_id = int(course["id"])
    course_code = str(course.get("course_code") or course_id)
    results: list[DownloadedFile] = []
    seen: set[int] = set()

    for fid in extract_assignment_file_ids(assignment.get("description", "")):
        if fid in seen:
            continue
        seen.add(fid)
        try:
            meta = client.get_file(course_id, fid)
            filename = meta.get("display_name") or meta.get("filename") or f"file_{fid}"
            dest_dir = os.path.join(_course_dir(output_dir, course_code), "assignments")
            dest = os.path.join(dest_dir, safe_name(filename))
            client.download_file(course_id, fid, dest)
            results.append(
                DownloadedFile(
                    course_id=course_id,
                    course_code=course_code,
                    kind="assignment",
                    title=assignment.get("name", filename),
                    filename=filename,
                    path=dest,
                    source_url=meta.get("url", ""),
                    size=os.path.getsize(dest),
                )
            )
        except Exception as exc:  # noqa: BLE001 — surface per-file failure, keep going
            results.append(
                DownloadedFile(
                    course_id=course_id,
                    course_code=course_code,
                    kind="assignment",
                    title=assignment.get("name", ""),
                    filename=f"file_{fid}",
                    path="",
                    source_url=f"file_id:{fid}",
                    size=0,
                )
            )
    return results


# --- modules / course materials -------------------------------------------

def download_course_materials(
    client: CanvasClient, output_dir: str, course: dict
) -> list[CourseMaterial]:
    """Walk modules and download files (slides/PDFs) referenced by module items."""
    course_id = int(course["id"])
    course_code = str(course.get("course_code") or course_id)
    out: list[CourseMaterial] = []

    for module in client.list_modules(course_id):
        module_title = module.get("name", "Module")
        for item in client.list_module_items(course_id, int(module["id"])):
            itype = item.get("type", "")
            title = item.get("title", "")
            source_url = item.get("url", "") or ""
            rec = CourseMaterial(
                course_id=course_id,
                module_title=module_title,
                item_type=itype,
                title=title,
                source_url=source_url,
            )
            # File items carry the canvas file id in content_id (or in url).
            file_id = None
            if itype == "File":
                file_id = item.get("content_id")
            if file_id is None:
                file_id = file_id_from_canvas_href(source_url)
            if file_id:
                try:
                    meta = client.get_file(course_id, int(file_id))
                    filename = meta.get("display_name") or meta.get("filename") or f"file_{file_id}"
                    dest_dir = os.path.join(_course_dir(output_dir, course_code), "materials")
                    dest = os.path.join(dest_dir, safe_name(filename))
                    client.download_file(course_id, int(file_id), dest)
                    rec.filename = filename
                    rec.path = dest
                except Exception as exc:  # noqa: BLE001
                    rec.source_url = f"file_id:{file_id} (error: {exc})"
            out.append(rec)
    return out
