#!/usr/bin/env python3
"""Render the README charts (light + dark SVG) from evals/results/value-*.json. Stdlib only.

    python docs/charts/make_charts.py evals/results/value-2026-10-21.json

Colors: dataviz reference palette slots 1-2 (blue, orange), validated with
validate_palette.js on GitHub's light (#ffffff) and dark (#0d1117) backgrounds:
all checks pass (CVD ΔE 24.7 light / 26.8 dark). Text uses text tokens, never the
series color. Labels are guarded by a measured character width: 6.6 px per char at
13 px (DejaVu Sans, the widest fallback measured in Chromium).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

CHAR_W = 6.6  # px per character at 13 px, measured (see docstring)
THEMES = {
    "light": {"bg": "#ffffff", "text": "#1f2328", "muted": "#59636e", "grid": "#d1d9e0",
              "with": "#2a78d6", "without": "#eb6834"},
    "dark": {"bg": "#0d1117", "text": "#f0f6fc", "muted": "#9198a1", "grid": "#3d444d",
             "with": "#3987e5", "without": "#d95926"},
}
SERIES = (("with", "with the skill"), ("without", "without the skill"))


def text_w(s: str) -> float:
    return len(s) * CHAR_W


def bar(x, y, w, h, r, fill):
    """Bar anchored at the baseline (left), 4 px rounding only on the data end (right)."""
    if w <= 0:
        return f'<rect x="{x}" y="{y}" width="1.5" height="{h}" fill="{fill}"/>'
    r = min(r, w, h / 2)
    return (f'<path d="M{x},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} V{y + h - r} '
            f'Q{x + w},{y + h} {x + w - r},{y + h} H{x} Z" fill="{fill}"/>')


def pass_rate_chart(data: dict, theme: str) -> str:
    t = THEMES[theme]
    rows = data["scenarios"]
    label_w = max(text_w(r["label"]) for r in rows) + 16
    width, plot_w = 760, 760 - label_w - 70
    bar_h, gap, group_gap, top = 14, 2, 20, 92
    group_h = 2 * bar_h + gap
    height = top + len(rows) * (group_h + group_gap) + 16
    assert label_w < 300, "labels too long for the chart"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" '
           f'role="img" aria-labelledby="t d">',
           f'<title id="t">{escape(data["title"])}</title>',
           f'<desc id="d">{escape(data["desc"])}</desc>',
           f'<rect width="{width}" height="{height}" fill="{t["bg"]}"/>',
           f'<text x="0" y="20" font-size="15" font-weight="600" fill="{t["text"]}">{escape(data["title"])}</text>']
    lx = 0  # legend: always present for 2 series
    for key, name in SERIES:
        out.append(f'<rect x="{lx}" y="36" width="12" height="12" rx="3" fill="{t[key]}"/>')
        out.append(f'<text x="{lx + 18}" y="46" font-size="13" fill="{t["muted"]}">{name}</text>')
        lx += 18 + text_w(name) + 24
    for pct in (0, 50, 100):  # recessive grid
        gx = label_w + plot_w * pct / 100
        out.append(f'<line x1="{gx}" y1="{top - 8}" x2="{gx}" y2="{height - 12}" stroke="{t["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{gx}" y="{top - 12}" font-size="11" text-anchor="middle" fill="{t["muted"]}">{pct}%</text>')
    for i, r in enumerate(rows):
        y = top + i * (group_h + group_gap)
        out.append(f'<text x="{label_w - 10}" y="{y + group_h / 2 + 4.5}" font-size="13" text-anchor="end" '
                   f'fill="{t["text"]}">{escape(r["label"])}</text>')
        for j, (key, _) in enumerate(SERIES):
            v = r[key]
            by = y + j * (bar_h + gap)
            w = plot_w * v / 100
            out.append(bar(label_w, by, w, bar_h, 4, t[key]))
            out.append(f'<text x="{label_w + w + 6}" y="{by + bar_h - 3}" font-size="11.5" '
                       f'fill="{t["text"]}">{v:.0f}%</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    src = Path(argv[0])
    data = json.loads(src.read_text(encoding="utf-8"))
    chart = {
        "title": "Scenario assertions passed (mean of 3 runs)",
        "desc": "; ".join(f"{s['label']}: {s['with']['pass_rate']:.0f}% with the skill, "
                          f"{s['without']['pass_rate']:.0f}% without" for s in data["scenarios"]),
        "scenarios": [{"label": s["label"], "with": s["with"]["pass_rate"], "without": s["without"]["pass_rate"]}
                      for s in data["scenarios"]],
    }
    out_dir = Path(__file__).resolve().parent
    rendered = {theme: pass_rate_chart(chart, theme) for theme in THEMES}  # build all, then write
    for theme, svg in rendered.items():
        (out_dir / f"value-{theme}.svg").write_text(svg, encoding="utf-8")
    print("wrote", ", ".join(f"value-{t}.svg" for t in rendered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
