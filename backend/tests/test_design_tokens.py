"""The Horizon token JSON is the source of truth; the CSS variables used by the UI must match it."""
import json
import re
from pathlib import Path

THEME = Path(__file__).resolve().parents[2] / "frontend" / "src" / "theme"


def flatten(node, prefix=""):
    for key, val in node.items():
        if isinstance(val, dict) and "$value" in val:
            yield f"{prefix}{key}", val["$value"]
        elif isinstance(val, dict):
            yield from flatten(val, f"{prefix}{key}-")


def test_theme_css_matches_tokens():
    tokens = json.loads((THEME / "horizon.tokens.json").read_text(encoding="utf-8"))
    css = (THEME / "horizon.theme.css").read_text(encoding="utf-8")
    root = css.split("@media")[0]
    declared = dict(re.findall(r"--h-([\w-]+):\s*([^;]+);", root))
    checked = 0
    for group in ("color", "spacing", "radius", "duration", "borderWidth", "fontWeight"):
        for name, value in flatten(tokens[group]):
            assert declared[f"{group}-{name}"].strip().lower() == str(value).lower(), name
            checked += 1
    assert checked > 30
