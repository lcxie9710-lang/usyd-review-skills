"""
Echo360 lecture-transcript client — pure HTTP (no browser, no Playwright).

The recorded video and its auto transcript live in Echo360 (not Canvas). Canvas
only hands us a *sessionless LTI launch URL* for external tool 11653. We follow
that launch with plain HTTP to establish an Echo360 session (no SSO login — the
LTI launch authenticates us), then:

    1. GET /section/{sectionId}/syllabus      -> list of lessons + media ids
    2. GET /api/ui/echoplayer/lessons/{lessonId}/medias/{mediaId}/transcript
                                             -> structured transcript cues

All requests carry the Echo360 session cookies (ECHO_JWT / PLAY_SESSION /
CloudFront signatures) set by the LTI launch. Works for every course on this
instance; only the sectionId / lessonId / mediaId vary.
"""

from __future__ import annotations

import html as htmllib
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

from .canvas_client import CanvasClient


class Echo360Error(RuntimeError):
    """Raised when an Echo360 step fails (bad URL / payload)."""


@dataclass
class Echo360:
    client: CanvasClient
    tool_id: int = 11653
    base: str = "https://echo360.net.au"
    session: requests.Session = field(default_factory=requests.Session)
    section_id: str = ""
    institution_id: str = ""

    # -- session ------------------------------------------------------------

    def start_session(self, course_id: int) -> dict:
        """Follow the sessionless LTI launch and establish an Echo360 session.

        Returns {section_id, institution_id} and leaves ``self.session`` ready
        for further authenticated calls.
        """
        launch_url = self.client.sessionless_launch(course_id, self.tool_id)
        r = self.session.get(launch_url, allow_redirects=True, timeout=60)
        m = re.search(r'<form[^>]+action="([^"]+)"[^>]*method="POST"[^>]*>', r.text, re.I)
        if not m:
            raise Echo360Error("未在 sessionless_launch 页面找到 LTI 表单")
        action = htmllib.unescape(m.group(1))
        fields = _parse_hidden_inputs(r.text)
        r2 = self.session.post(action, data=fields, allow_redirects=True, timeout=60)
        if r2.status_code != 200:
            raise Echo360Error(f"LTI 启动失败：HTTP {r2.status_code}")

        final = r2.url
        m2 = re.search(r"/section/([0-9a-f-]{36})", final)
        if m2:
            self.section_id = m2.group(1)
        else:
            raise Echo360Error(f"无法从启动响应解析 section id：{final[:120]}")

        # institution id appears in the transcript payload; grab it lazily on
        # first transcript call. For now try to read it from the section page.
        return {"section_id": self.section_id, "final_url": final[:160]}

    # -- recordings ---------------------------------------------------------

    def list_recordings(self) -> list[dict]:
        """Return the course's recordings (lessons) with their media ids."""
        if not self.section_id:
            raise Echo360Error("请先 start_session()")
        sy = self._get_json(f"/section/{self.section_id}/syllabus")
        data = sy.get("data") or []
        lessons: list[dict] = []
        for item in data:
            L = item.get("lesson")
            if not L:
                continue
            obj = L.get("lesson") or {}
            lesson_id = obj.get("id")
            if not lesson_id:
                continue
            timing = (obj.get("timing") or {}).get("start", "")
            medias = []
            for m in L.get("medias", []):
                medias.append({
                    "media_id": m.get("id"),
                    "media_type": m.get("mediaType"),
                    "title": m.get("title"),
                    "is_available": m.get("isAvailable"),
                })
            lessons.append({
                "lesson_id": lesson_id,
                "name": obj.get("name") or obj.get("displayName") or "",
                "date": timing,
                "medias": medias,
            })
        return lessons

    # -- transcript ---------------------------------------------------------

    def get_transcript(self, lesson_id: str, media_id: str) -> list[dict]:
        """Return the structured transcript cues for a media.

        Each cue: {start_ms, end_ms, speaker, content, confidence?}.
        """
        path = f"/api/ui/echoplayer/lessons/{lesson_id}/medias/{media_id}/transcript"
        d = self._get_json(path)
        data = d.get("data") or {}
        if not self.institution_id:
            self.institution_id = data.get("institutionId", self.institution_id)
        cues = (data.get("contentJSON") or {}).get("cues", [])
        out = []
        for c in cues:
            out.append({
                "start_ms": c.get("startMs"),
                "end_ms": c.get("endMs"),
                "speaker": c.get("speaker", ""),
                "content": c.get("content", ""),
            })
        return out

    def transcript_text(self, lesson_id: str, media_id: str) -> str:
        """Build a readable plain-text transcript (time + speaker + line)."""
        cues = self.get_transcript(lesson_id, media_id)
        lines = []
        for c in cues:
            t = _ms_to_ts(c.get("start_ms"))
            speaker = (c.get("speaker") or "").strip()
            content = (c.get("content") or "").strip()
            line = f"[{t}]" + (f" {speaker}:" if speaker else "") + f" {content}"
            lines.append(line)
        return "\n".join(lines)

    def download_transcript(self, lesson_id: str, media_id: str, dest: str) -> str:
        text = self.transcript_text(lesson_id, media_id)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        return dest

    # -- helpers ------------------------------------------------------------

    def _get_json(self, path: str) -> dict:
        url = path if path.startswith("http") else self.base + path
        r = self.session.get(url, headers={"Accept": "application/json"}, timeout=45)
        if r.status_code != 200:
            raise Echo360Error(f"HTTP {r.status_code} for {path}")
        try:
            return r.json()
        except ValueError as exc:
            raise Echo360Error(f"非 JSON 响应（HTTP {r.status_code}）: {path}") from exc


# --- helpers ---------------------------------------------------------------

def _parse_hidden_inputs(html_text: str) -> dict:
    fields: dict = {}
    for inp in re.finditer(r"<input[^>]+>", html_text, re.I):
        tag = inp.group(0)
        nm = re.search(r'name=["\']([^"\']+)["\']', tag, re.I)
        if nm:
            vl = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
            fields[nm.group(1)] = htmllib.unescape(vl.group(1)) if vl else ""
    return fields


def _ms_to_ts(ms) -> str:
    try:
        ms = int(ms or 0)
        s = ms // 1000
        h, rem = divmod(s, 3600)
        mm, ss = divmod(rem, 60)
        return f"{h:02d}:{mm:02d}:{ss:02d}"
    except Exception:
        return "00:00:00"
