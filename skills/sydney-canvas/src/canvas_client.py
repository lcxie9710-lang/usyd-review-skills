"""
Canvas LMS REST API client for the University of Sydney instance.

Handles authentication (Bearer token from canvas_token), pagination via the
Link header, and the endpoints this workflow needs:

  * list current-term active courses
  * list assignments (with due dates / submission info)
  * list modules and module items (course materials)
  * list/download course files
  * get the Echo360 (external tool) sessionless launch URL

All timestamps come back in ISO8601 UTC; helpers here normalise them to local
time where useful.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional

import requests


@dataclass
class CanvasClient:
    """Thin wrapper over the Canvas REST API."""

    base: str
    token: str
    timeout: int = 30
    page_size: int = 100
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self) -> None:
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.session.headers.update({"Accept": "application/json"})

    # --- low-level ---------------------------------------------------------

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self.base.rstrip('/')}{path}"

    def _iter_pages(self, path: str, params: Optional[dict] = None) -> Iterator[list]:
        """Yield each page of a paginated Canvas endpoint (follows Link: next)."""
        url = self._url(path)
        params = {**(params or {}), "per_page": self.page_size}
        while url:
            resp = self.session.get(url, params=params if url == self._url(path) else None, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                yield data
            else:
                # Some endpoints return a bare object; wrap it as a single-page list.
                yield [data]
            url = _next_page(resp.headers.get("Link", ""))
            params = None  # next pages already carry their query string

    def _get_all(self, path: str, params: Optional[dict] = None) -> list:
        """Fetch every page of a paginated endpoint into one list."""
        out: list = []
        for page in self._iter_pages(path, params):
            out.extend(page)
        return out

    # --- auth check --------------------------------------------------------

    def whoami(self) -> dict:
        """GET /api/v1/users/self — verifies the token and returns the user."""
        return self._get_all("/api/v1/users/self")[0]

    # --- courses -----------------------------------------------------------

    def list_courses(self) -> list[dict]:
        """Active courses the current user is enrolled in (student scope)."""
        return self._get_all(
            "/api/v1/courses",
            {
                "enrollment_state": "active",
                "enrollment_type": "student",
                "include[]": ["term", "total_scores"],
                "state[]": ["available"],
            },
        )

    def get_course(self, course_id: int) -> dict:
        return self._get_all(f"/api/v1/courses/{course_id}")[0]

    # --- assignments -------------------------------------------------------

    def list_assignments(self, course_id: int) -> list[dict]:
        """Assignments for a course, with the requesting user's submission included."""
        return self._get_all(
            f"/api/v1/courses/{course_id}/assignments",
            {"include[]": ["submission"], "order_by": "due_at"},
        )

    # --- modules / files ---------------------------------------------------

    def list_modules(self, course_id: int) -> list[dict]:
        return self._get_all(f"/api/v1/courses/{course_id}/modules")

    def list_module_items(self, course_id: int, module_id: int) -> list[dict]:
        return self._get_all(
            f"/api/v1/courses/{course_id}/modules/{module_id}/items",
            {"include[]": ["content_details"]},
        )

    def list_course_files(self, course_id: int) -> list[dict]:
        """All course files (a File object has id, filename, url, content_type, size)."""
        return self._get_all(f"/api/v1/courses/{course_id}/files")

    def get_file(self, course_id: int, file_id: int) -> dict:
        return self._get_all(f"/api/v1/courses/{course_id}/files/{file_id}")[0]

    def download_file(self, course_id: int, file_id: int, dest: str) -> str:
        """Download a course file (follows the secure 302 to the content host)."""
        meta = self.get_file(course_id, file_id)
        url = meta.get("url") or meta.get("preview_url") or f"{self._url('/api/v1/courses')}/{course_id}/files/{file_id}"
        # The file endpoint returns a one-time URL that 302s to the content domain;
        # follow redirects and stream to disk. Some instances need download_frd=1.
        if "download_frd=1" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}download_frd=1"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with self.session.get(url, stream=True, timeout=self.timeout, allow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
        return dest

    # --- external tool (Echo360) ------------------------------------------

    def get_external_tool(self, course_id: int, tool_id: int) -> dict:
        """Confirm details of the external tool (should be Echo360 / Lecture Recordings)."""
        return self._get_all(f"/api/v1/courses/{course_id}/external_tools/{tool_id}")[0]

    def sessionless_launch(self, course_id: int, tool_id: int) -> str:
        """Return a sessionless LTI launch URL for the given external tool."""
        data = self._get_all(
            f"/api/v1/courses/{course_id}/external_tools/sessionless_launch",
            {"id": tool_id},
        )[0]
        return data["url"]


# --- helpers ---------------------------------------------------------------

def _next_page(link_header: str) -> Optional[str]:
    """Extract the rel=next URL from a Canvas Link header, if present."""
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part or "rel=next" in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


def file_id_from_canvas_href(href: str) -> Optional[int]:
    """Pull a Canvas file id out of a link like /courses/123/files/99 (or /files/99)."""
    if not href:
        return None
    m = re.search(r"/(?:courses/\d+/)?files/(\d+)", href)
    return int(m.group(1)) if m else None
