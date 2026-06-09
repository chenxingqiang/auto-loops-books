"""
Nature-journal visual style system for autobooks (code-controlled).

Single source of truth for TikZ tokens, NPG palette, figure geometry, and
LaTeX emission. book_visuals.py imports VISUAL_STYLE and layout constants.

Usage:
    uv run python books/visuals_style.py --emit
    uv run python books/visuals_style.py --show-tokens
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BOOKS = Path(__file__).resolve().parent
TEX_OUTPUT = BOOKS / "visuals_style.tex"

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class ColorToken:
    name: str
    rgb: RGB
    role: str


NPG_PALETTE: tuple[ColorToken, ...] = (
    ColorToken("npg_red", (231, 75, 53), "primary"),
    ColorToken("npg_blue", (60, 84, 136), "primary"),
    ColorToken("npg_green", (0, 160, 135), "secondary"),
    ColorToken("npg_cyan", (77, 187, 213), "secondary"),
    ColorToken("npg_orange", (243, 155, 127), "accent"),
    ColorToken("npg_navy", (44, 62, 80), "neutral"),
    ColorToken("npg_lavender", (132, 145, 180), "neutral"),
    ColorToken("npg_mint", (145, 209, 194), "fill"),
    ColorToken("npg_sky", (210, 236, 245), "fill"),
    ColorToken("npg_peach", (252, 238, 228), "fill"),
    ColorToken("npg_table_head", (245, 247, 250), "table"),
    ColorToken("npg_placeholder", (250, 250, 250), "fill"),
)

SEMANTIC_COLOR: dict[str, str] = {
    "visPrimary": "npg_blue",
    "visSecondary": "npg_green",
    "visAccent": "npg_red",
    "visFillPrimary": "npg_sky",
    "visFillSecondary": "npg_mint",
    "visFillAccent": "npg_peach",
    "visTableHead": "npg_table_head",
    "visPlaceholderFill": "npg_placeholder",
    "visAxis": "npg_navy",
    "visText": "npg_navy",
}

GRAYSCALE_COLOR: dict[str, str] = {
    "visPrimary": "black!72",
    "visSecondary": "black!50",
    "visAccent": "black!35",
    "visFillPrimary": "black!8",
    "visFillSecondary": "black!14",
    "visFillAccent": "black!6",
    "visTableHead": "black!6",
    "visPlaceholderFill": "black!4",
    "visAxis": "black!55",
    "visText": "black!80",
}


@dataclass(frozen=True)
class NatureFigureGeometry:
    single_column_mm: float = 89.0
    double_column_mm: float = 183.0
    font_size_pt: float = 7.0
    panel_font_size_pt: float = 9.0
    min_line_width_pt: float = 0.5
    axis_line_width_pt: float = 0.55
    node_line_width_pt: float = 0.6
    arrow_line_width_pt: float = 0.65
    roof_line_width_pt: float = 0.75
    node_corner_radius_pt: float = 1.5
    node_min_width_cm: float = 2.2
    node_min_height_cm: float = 1.0
    pipeline_block_gap_cm: float = 0.75
    pipeline_scale: float = 0.88
    roofline_scale: float = 0.82
    bar_scale: float = 0.88

    @property
    def single_column_scale(self) -> float:
        return round(self.single_column_mm / 100.0, 3)


GEOMETRY = NatureFigureGeometry()

VISUAL_STYLE: dict[str, str] = {
    "tikz_base": "vis base",
    "pipeline_node": "vis pipeline node",
    "arch_node": "vis arch node",
    "arrow": "vis arrow",
    "axis": "vis axis",
    "roof_bandwidth": "vis roof bandwidth",
    "roof_compute": "vis roof compute",
    "point_a": "vis point a",
    "point_b": "vis point b",
    "bar_one": "vis bar one",
    "bar_two": "vis bar two",
    "panel_label": "vis panel label",
    "grid_minor": "vis grid minor",
    "table_header": r"\visTableHeader",
}


def _rgb_define(name: str, rgb: RGB) -> str:
    return f"  \\definecolor{{{name}}}{{RGB}}{{{rgb[0]},{rgb[1]},{rgb[2]}}}"


def _color_block() -> str:
    by_name = {t.name: t for t in NPG_PALETTE}
    lines = ["\\ifColor"]
    for token in sorted(set(SEMANTIC_COLOR.values())):
        lines.append(_rgb_define(token, by_name[token].rgb))
    for vis_name, npg_name in SEMANTIC_COLOR.items():
        lines.append(f"  \\colorlet{{{vis_name}}}{{{npg_name}}}")
    lines.append("\\else")
    for vis_name, gray in GRAYSCALE_COLOR.items():
        lines.append(f"  \\colorlet{{{vis_name}}}{{{gray}}}")
    lines.append("\\fi")
    return "\n".join(lines)


def _tikzset_block(g: NatureFigureGeometry) -> str:
    return f"""\\tikzset{{
  vis base/.style={{
    font=\\sffamily\\footnotesize,
    text=visText,
    line cap=round,
    line join=round,
  }},
  vis pipeline node/.style={{
    vis base,
    draw=visPrimary,
    line width={g.node_line_width_pt}pt,
    fill=visFillPrimary,
    rounded corners={g.node_corner_radius_pt}pt,
    minimum width={g.node_min_width_cm}cm,
    minimum height={g.node_min_height_cm}cm,
    align=center,
    inner sep=3.5pt,
  }},
  vis arch node/.style={{
    vis pipeline node,
    fill=visFillSecondary,
    draw=visSecondary,
  }},
  vis arrow/.style={{
    ->,
    >=Stealth,
    line width={g.arrow_line_width_pt}pt,
    draw=visPrimary,
  }},
  vis axis/.style={{
    ->,
    >=Stealth,
    line width={g.axis_line_width_pt}pt,
    draw=visAxis,
  }},
  vis grid minor/.style={{
    line width={g.min_line_width_pt}pt,
    draw=visAxis,
    opacity=0.25,
  }},
  vis roof bandwidth/.style={{
    line width={g.roof_line_width_pt}pt,
    draw=visSecondary,
    dash pattern=on 3pt off 2pt,
  }},
  vis roof compute/.style={{
    line width={g.roof_line_width_pt}pt,
    draw=visPrimary,
  }},
  vis point a/.style={{
    fill=visPrimary,
    draw=visPrimary,
    circle,
    inner sep=1.4pt,
  }},
  vis point b/.style={{
    fill=visSecondary,
    draw=visSecondary,
    circle,
    inner sep=1.4pt,
  }},
  vis bar one/.style={{
    fill=visFillPrimary,
    draw=visPrimary,
    line width={g.min_line_width_pt}pt,
  }},
  vis bar two/.style={{
    fill=visFillSecondary,
    draw=visSecondary,
    line width={g.min_line_width_pt}pt,
  }},
  vis panel label/.style={{
    font=\\sffamily\\bfseries\\fontsize{{9}}{{10}}\\selectfont,
    text=visText,
    anchor=north west,
    inner sep=0pt,
  }},
  vis placeholder box/.style={{
    vis base,
    draw=visAccent,
    line width={g.node_line_width_pt}pt,
    fill=visPlaceholderFill,
    rounded corners=1.5pt,
    inner sep=8pt,
  }},
}}"""


def generate_visuals_style_tex(geo: NatureFigureGeometry = GEOMETRY) -> str:
    header = (
        "% AUTO-GENERATED by books/visuals_style.py — do not edit by hand.\n"
        "% Nature-journal figure system (NPG palette, sans-serif, thin axes).\n"
        "% Regenerate: uv run python books/visuals_style.py --emit\n\n"
        "\\usepackage[table]{xcolor}\n"
        "% Sans-serif in figures only (Nature labels); body text unchanged.\n"
        "\\usepackage{helvet}\n\n"
    )
    macros = (
        "\n\\newcommand{\\visTableHeader}{%\n"
        "  \\rowcolor{visTableHead}%\n"
        "}\n\n"
        "\\newcommand{\\visPanelLabel}[1]{{\\sffamily\\bfseries #1}\\quad}\n"
    )
    return header + _color_block() + "\n\n" + _tikzset_block(geo) + "\n" + macros


def emit_tex(path: Path = TEX_OUTPUT) -> Path:
    path.write_text(generate_visuals_style_tex(), encoding="utf-8")
    return path


def panel_label_tex(panel: str) -> str:
    return f"\\visPanelLabel{{{panel.strip().lower()}}}"


def figure_tikz_opening(kind: str = "pipeline") -> str:
    scales = {
        "pipeline": GEOMETRY.pipeline_scale,
        "roofline": GEOMETRY.roofline_scale,
        "bar": GEOMETRY.bar_scale,
    }
    scale = scales.get(kind, GEOMETRY.pipeline_scale)
    base = VISUAL_STYLE["tikz_base"]
    return f"\\begin{{tikzpicture}}[{base}, scale={scale}, transform shape]"


def pipeline_layout(n_stages: int) -> tuple[float, float]:
    block_w = GEOMETRY.node_min_width_cm + 0.4
    gap = GEOMETRY.pipeline_block_gap_cm
    span = n_stages * block_w + max(0, n_stages - 1) * gap
    return block_w, -span / 2 + block_w / 2


def style_tokens_json() -> dict[str, Any]:
    return {
        "preset": "nature_npg",
        "geometry": {
            "single_column_mm": GEOMETRY.single_column_mm,
            "double_column_mm": GEOMETRY.double_column_mm,
            "pipeline_scale": GEOMETRY.pipeline_scale,
            "roofline_scale": GEOMETRY.roofline_scale,
        },
        "visual_style": VISUAL_STYLE,
        "npg_palette": {t.name: t.rgb for t in NPG_PALETTE},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nature visual style for autobooks")
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--show-tokens", action="store_true")
    parser.add_argument("--preview-colors", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.show_tokens:
        for k, v in VISUAL_STYLE.items():
            print(f"{k}\t{v}")
        return 0
    if args.preview_colors:
        print(json.dumps(style_tokens_json(), indent=2))
        return 0
    if args.emit:
        tex = generate_visuals_style_tex()
        if args.dry_run:
            print(tex)
            return 0
        print(f"Wrote {emit_tex()}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
