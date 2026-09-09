"""Shared configuration loading for the sydney-canvas skill scripts.

Reads `config.json` in the skill root (or `config.example.json`), and lets the
`CANVAS_TOKEN` / `CANVAS_BASE` environment variables override secrets/URLs so the
token does not have to sit on disk.

Schema (config.json):
    {
      "canvas_base": "https://canvas.sydney.edu.au",
      "canvas_token": "",            // usually supplied via CANVAS_TOKEN instead
      "echo360_tool_id": 11653,
      "headless": false,
      "browser_user_data_dir": "data/profile",
      "output_dir": "data"
    }
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def skill_root() -> str:
    return _SKILL_ROOT


def default_config_path() -> str:
    return os.path.join(_SKILL_ROOT, "config.json")


def _default() -> dict:
    return {
        "canvas_base": "https://canvas.sydney.edu.au",
        "canvas_token": "",
        "echo360_tool_id": 11653,
        "headless": False,
        "browser_user_data_dir": "data/profile",
        "output_dir": "data",
    }


def load_config(path: Optional[str] = None) -> dict:
    cfg_path = path or default_config_path()
    if not os.path.exists(cfg_path):
        alt = os.path.join(_SKILL_ROOT, "config.example.json")
        if os.path.exists(alt):
            cfg_path = alt
            print(f"[sydney-canvas] 未找到 config.json，使用 config.example.json：{cfg_path}", file=sys.stderr)
        else:
            print(f"[sydney-canvas] 未找到配置文件，使用默认值：{cfg_path}", file=sys.stderr)

    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            file_cfg = json.load(fh)
    else:
        file_cfg = {}

    cfg = {**_default(), **file_cfg}
    # environment overrides (keep secrets out of disk)
    cfg["canvas_token"] = os.environ.get("CANVAS_TOKEN", cfg.get("canvas_token", ""))
    cfg["canvas_base"] = os.environ.get("CANVAS_BASE", cfg.get("canvas_base", "https://canvas.sydney.edu.au"))
    return cfg


def require_token(cfg: dict) -> str:
    token = cfg.get("canvas_token", "")
    if not token or "PASTE" in str(token) or "HERE" in str(token):
        sys.exit(
            "[sydney-canvas] 缺少 Canvas access token。\n"
            "请设置环境变量 CANVAS_TOKEN=<你的token>，或把 token 填入 config.json。\n"
            "生成方式：Canvas → 头像 → Settings → Access Tokens → + New Access Token。"
        )
    return token
