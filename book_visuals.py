"""
Figure and table planning / rendering for autobooks.

Each chapter keeps a visual plan under books/visuals/<chapter_id>/plan.json.
The agent iterates: plan -> render LaTeX snippets -> paste into chapters/*.tex.

Usage:
    uv run book_visuals.py --chapter ch01 --plan
    uv run book_visuals.py --chapter ch01 --audit
    uv run book_visuals.py --chapter ch01 --render
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from book_prepare import OUTLINE, ChapterSpec

ROOT = Path(__file__).resolve().parent
BOOKS = ROOT / "books"
CHAPTERS = BOOKS / "chapters"
VISUALS_ROOT = BOOKS / "visuals"
GENERATED = "generated"

# Nature-journal style tokens — source of truth: books/visuals_style.py
import importlib.util

_style_spec = importlib.util.spec_from_file_location(
    "visuals_style", BOOKS / "visuals_style.py"
)
assert _style_spec and _style_spec.loader
_visuals_style = importlib.util.module_from_spec(_style_spec)
sys.modules[_style_spec.name] = _visuals_style
_style_spec.loader.exec_module(_visuals_style)

VISUAL_STYLE: dict[str, str] = _visuals_style.VISUAL_STYLE
GEOMETRY = _visuals_style.GEOMETRY
figure_tikz_opening = _visuals_style.figure_tikz_opening
pipeline_layout = _visuals_style.pipeline_layout
panel_label_tex = _visuals_style.panel_label_tex

VISUAL_KINDS: dict[str, str] = {
    "comparison_table": "Qualitative side-by-side (e.g. prefill vs decode)",
    "benchmark_table": "Numeric measurements with units and cite",
    "reference_snapshot": "Literature-backed metric snapshot rows",
    "checklist_table": "Hardware/strategy priority matrix",
    "roofline_figure": "TikZ roofline / arithmetic-intensity diagram",
    "pipeline_figure": "TikZ dataflow or phase pipeline",
    "architecture_figure": "TikZ memory hierarchy or system block diagram",
    "bar_figure": "TikZ simple bar comparison",
    "placeholder_figure": "Explicit pending benchmark slot",
}

SECTION_VISUAL_RECIPES: dict[str, dict[str, list[dict[str, Any]]]] = {
    "ch01": {
        "prefill_decode": [
            {
                "id": "tab_prefill_decode",
                "kind": "comparison_table",
                "caption": "Qualitative comparison of prefill vs.\\ decode on a single transformer layer.",
                "label": "tab:prefill_decode",
                "columns": ["", "Prefill", "Decode (batch-1)"],
                "rows": [
                    ["Tokens processed per step", "$L$ (prompt length)", "$1$"],
                    ["Typical arithmetic intensity", "Higher", "Lower"],
                    ["Dominant limiter", "Compute / tensor cores", "Memory traffic / orchestration"],
                    ["KV cache growth per step", "Written in bulk", "Read + append one step"],
                    ["Serving objective", "Throughput (tok/s)", "Latency (ms/token)"],
                ],
            },
            {
                "id": "fig_prefill_decode_pipeline",
                "kind": "pipeline_figure",
                "caption": "Prefill processes prompt chunks in parallel; decode appends one token per step via KV cache.",
                "label": "fig:prefill_decode_pipeline",
                "stages": [
                    {"name": "Prefill", "detail": "Parallel over $L$ tokens"},
                    {"name": "KV write", "detail": "Bulk cache fill"},
                    {"name": "Decode loop", "detail": "One token / step"},
                    {"name": "KV read+append", "detail": "Growing context"},
                ],
            },
        ],
        "overhead_quant": [
            {
                "id": "tab_taxbreak_kernels",
                "kind": "benchmark_table",
                "caption": "Verified kernel fragmentation on H100 decode (BS$=4$, SL$=2048$, $m=10$ tokens), from TaxBreak.",
                "label": "tab:taxbreak_kernels",
                "cite": "taxbreak2026",
                "columns": ["Model", "Kernels/token", "Total launches", "GPU util. (\\%)"],
                "rows": [
                    ["Llama-3.2-1B", "847.5", "8,475", "58.9"],
                    ["Llama-3.2-3B", "1,536.9", "15,369", "67.6"],
                    ["OLMoE-1B/7B", "9,305.3", "93,053", "15.5"],
                    ["Qwen1.5-MoE-A2.7B", "6,695.1", "66,951", "27.7"],
                ],
            },
        ],
        "memory_not_compute": [
            {
                "id": "fig_roofline_decode",
                "kind": "roofline_figure",
                "caption": "Decode sits on the memory-bandwidth slope of the roofline at low arithmetic intensity.",
                "label": "fig:roofline_decode",
                "peak_gflops": 989,
                "peak_gbps": 3350,
                "points": [
                    {"name": "Prefill GEMM", "ai": 120},
                    {"name": "Decode batch-1", "ai": 8},
                ],
            },
        ],
        "multi_hardware": [
            {
                "id": "tab_hw_priorities",
                "kind": "checklist_table",
                "caption": "Decode optimization priorities by hardware class.",
                "label": "tab:hw_priorities",
                "columns": ["Hardware", "First-order decode levers"],
                "rows": [
                    ["NVIDIA GPU", "Fusion, graphs, KV bandwidth, shared mem tiling"],
                    ["AMD GPU", "HIP fusion, LDS reuse, launch reduction"],
                    ["CPU", "Cache blocking, SIMD, NUMA, coarse fusion"],
                    ["Edge NPU", "Static ADF graphs, DMA ping-pong, full-layer fusion"],
                ],
            },
        ],
        "benchmark_gap": [
            {
                "id": "fig_fusion_gap",
                "kind": "placeholder_figure",
                "caption": "Pending: YiRage/MegaKernel vs.\\ PyTorch eager speedup (Appendix~B harness).",
                "label": "fig:fusion_gap",
                "pending_note": "Run Appendix B harness before filling bars",
            },
        ],
        "yirage_preview": [
            {
                "id": "fig_yirage_pipeline",
                "kind": "pipeline_figure",
                "caption": "YiRage decode compilation pipeline (preview).",
                "label": "fig:yirage_pipeline",
                "stages": [
                    {"name": "Hardware probe", "detail": "SRAM, BW, launch rules"},
                    {"name": "Dataflow plan", "detail": "Tensor lifetimes"},
                    {"name": "Fusion passes", "detail": "Layer collapse"},
                    {"name": "Codegen", "detail": "CUDA / CPU / XDNA"},
                    {"name": "Regression", "detail": "vs. open baselines"},
                ],
            },
        ],
    },
    "ch02": {
        "operator_first": [
            {
                "id": "fig_operator_graph",
                "kind": "architecture_figure",
                "caption": "Operator-driven schedule: each op reads/writes global memory.",
                "label": "fig:operator_graph",
                "blocks": ["LayerNorm", "QKV", "Attn", "MLP", "HBM"],
            },
        ],
        "dataflow_philosophy": [
            {
                "id": "fig_dataflow_residency",
                "kind": "pipeline_figure",
                "caption": "Dataflow-driven schedule: activations stay on-chip across fused stages.",
                "label": "fig:dataflow_residency",
                "stages": [
                    {"name": "On-chip tile", "detail": "Register / shared"},
                    {"name": "Fused QKV+Attn", "detail": "No HBM export"},
                    {"name": "Fused MLP", "detail": "Pipeline"},
                ],
            },
        ],
        "cross_hardware": [
            {
                "id": "tab_mindset_hw",
                "kind": "comparison_table",
                "caption": "Design mindset vs.\\ hardware enforcement model.",
                "label": "tab:mindset_hw",
                "columns": ["Target", "Data residency model"],
                "rows": [
                    ["CUDA GPU", "Software-managed hierarchy"],
                    ["XDNA / AIE", "Hardware-enforced spatial buffers"],
                    ["CPU", "Cache hierarchy + explicit blocking"],
                ],
            },
        ],
    },
    "ch03": {
        "hardware_landscape": [
            {
                "id": "tab_hw_landscape",
                "kind": "comparison_table",
                "caption": "AI accelerator classes and primary execution models.",
                "label": "tab:hw_landscape",
                "columns": ["Class", "Execution model", "Decode fit"],
                "rows": [
                    ["NVIDIA GPU", "SIMT + tensor cores", "Graphs, fusion"],
                    ["AMD GPU", "Wavefront + matrix cores", "HIP fusion"],
                    ["x86/ARM CPU", "Cache + SIMD", "Coarse fusion"],
                    ["Edge NPU", "Spatial dataflow", "Static megakernel"],
                ],
            },
        ],
        "constraint_matrix": [
            {
                "id": "tab_constraint_matrix",
                "kind": "checklist_table",
                "caption": "Cross-hardware constraint matrix.",
                "label": "tab:constraint_matrix",
                "columns": ["Dimension", "GPU", "CPU", "NPU"],
                "rows": [
                    ["On-chip SRAM", "Shared mem / L1", "L1/L2/L3", "Tile buffers"],
                    ["Parallel grain", "Warp", "Core + SIMD", "Spatial PE array"],
                    ["Dynamic shapes", "Flexible", "Flexible", "Restricted"],
                ],
            },
        ],
        "benchmark_method": [
            {
                "id": "fig_benchmark_method",
                "kind": "pipeline_figure",
                "caption": "Cross-hardware benchmark methodology used in this book.",
                "label": "fig:benchmark_method",
                "stages": [
                    {"name": "Fixed model+ctx", "detail": "Repro config"},
                    {"name": "Normalize metrics", "detail": "bytes/token"},
                    {"name": "Compare targets", "detail": "GPU / CPU / NPU"},
                ],
            },
        ],
        "gpu_constraints": [
            {
                "id": "fig_gpu_memory_hierarchy",
                "kind": "architecture_figure",
                "caption": "GPU memory hierarchy constraints for decode megakernels.",
                "label": "fig:gpu_memory_hierarchy",
                "blocks": ["Register file", "Shared memory", "L2 cache", "HBM"],
            },
        ],
    },
    "ch04": {
        "cuda_memory_hierarchy": [
            {
                "id": "tab_cuda_memory",
                "kind": "comparison_table",
                "caption": "CUDA memory spaces relevant to decode megakernels (Hopper-class).",
                "label": "tab:cuda_memory",
                "columns": ["Space", "Scope", "Decode role"],
                "rows": [
                    ["Register", "Thread", "Online softmax carriers, thin GEMM fragments"],
                    ["Shared memory", "Block", "Fused QKV/MLP tiles, TMA staging"],
                    ["Global (HBM)", "Grid", "Weights, KV cache, spill traffic"],
                ],
            },
        ],
        "tma": [
            {
                "id": "fig_tma_pipeline",
                "kind": "pipeline_figure",
                "caption": "TMA double-buffer pattern: async global-to-shared copy overlaps tensor-core math.",
                "label": "fig:tma_pipeline",
                "stages": [
                    {"name": "TMA load", "detail": "Async to shared"},
                    {"name": "MMA compute", "detail": "Previous tile"},
                    {"name": "Epilogue", "detail": "Fused in shared"},
                    {"name": "TMA prefetch", "detail": "Next tile"},
                ],
            },
        ],
        "sync_mechanisms": [
            {
                "id": "fig_cuda_sync_levels",
                "kind": "architecture_figure",
                "caption": "CUDA synchronization hierarchy used in decoder megakernels.",
                "label": "fig:cuda_sync_levels",
                "blocks": ["Warp shuffle", "Block sync", "Cluster DSM", "Grid sync"],
            },
        ],
    },
}


def _humanize_section(label: str) -> str:
    from book_proper_nouns import canonicalize_prose

    return canonicalize_prose(label.replace("_", " "))


def default_figure_recipe(spec: ChapterSpec, section: SectionSpec, kind_idx: int) -> dict[str, Any]:
    human = _humanize_section(section.label)
    if kind_idx % 2 == 0:
        return {
            "id": f"fig_{section.label}_pipeline",
            "kind": "pipeline_figure",
            "caption": f"{human} optimization pipeline in {spec.title}.",
            "label": f"fig:{section.label}_pipeline",
            "stages": [
                {"name": "Input", "detail": human},
                {"name": "On-chip", "detail": "Tiling / residency"},
                {"name": "Fused compute", "detail": "Megakernel stage"},
                {"name": "Output", "detail": "Next layer / KV"},
            ],
        }
    return {
        "id": f"fig_{section.label}_architecture",
        "kind": "architecture_figure",
        "caption": f"{human} block diagram for {spec.title}.",
        "label": f"fig:{section.label}_architecture",
        "blocks": ["Host", "On-chip buffer", "Compute array", "Memory tier"],
    }


CHAPTER_VISUAL_TARGETS: dict[str, dict[str, int]] = {
    "ch01": {"min_tables": 3, "min_figures": 2},
    "ch02": {"min_tables": 1, "min_figures": 2},
    "ch03": {"min_tables": 2, "min_figures": 2},
    "ch04": {"min_tables": 1, "min_figures": 2},
}


@dataclass
class VisualSpec:
    id: str
    kind: str
    section: str
    label: str
    caption: str
    status: str = "planned"
    placement: str = "t"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        extra = d.pop("extra", {})
        d.update(extra)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VisualSpec:
        known = {"id", "kind", "section", "label", "caption", "status", "placement"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            id=data["id"],
            kind=data["kind"],
            section=data["section"],
            label=data["label"],
            caption=data["caption"],
            status=data.get("status", "planned"),
            placement=data.get("placement", "t"),
            extra=extra,
        )


def chapter_spec(chapter_id: str) -> ChapterSpec | None:
    for spec in OUTLINE:
        if spec.chapter_id == chapter_id:
            return spec
    return None


def plan_path(chapter_id: str) -> Path:
    return VISUALS_ROOT / chapter_id / "plan.json"


def generated_dir(chapter_id: str) -> Path:
    return VISUALS_ROOT / chapter_id / GENERATED


def escape_latex(text: str) -> str:
    for char, repl in {"%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_"}.items():
        text = text.replace(char, repl)
    return text


def scan_chapter_visuals(tex: str) -> dict[str, Any]:
    tables = len(re.findall(r"\\begin\{table\}", tex))
    figures = len(re.findall(r"\\begin\{figure\}", tex))
    labels = re.findall(r"\\label\{(fig|tab):([^}]+)\}", tex)
    return {
        "table_count": tables,
        "figure_count": figures,
        "figure_labels": [f"fig:{n}" for k, n in labels if k == "fig"],
        "table_labels": [f"tab:{n}" for k, n in labels if k == "tab"],
    }


def build_plan_from_recipes(spec: ChapterSpec) -> list[VisualSpec]:
    recipes = SECTION_VISUAL_RECIPES.get(spec.chapter_id, {})
    visuals: list[VisualSpec] = []
    default_figures = 0
    max_default_figures = 2
    for section in spec.sections:
        raw_items = list(recipes.get(section.label, []))
        if not raw_items and spec.chapter_id not in SECTION_VISUAL_RECIPES:
            if default_figures < max_default_figures:
                raw_items = [default_figure_recipe(spec, section, default_figures)]
                default_figures += 1
        for raw in raw_items:
            extra = {k: v for k, v in raw.items() if k not in {"id", "kind", "caption", "label", "status"}}
            visuals.append(
                VisualSpec(
                    id=raw["id"],
                    kind=raw["kind"],
                    section=section.label,
                    label=raw["label"],
                    caption=raw["caption"],
                    status=raw.get("status", "planned"),
                    extra=extra,
                )
            )
    return visuals


def merge_plan_with_tex(plan: list[VisualSpec], tex: str) -> list[VisualSpec]:
    present = set(scan_chapter_visuals(tex)["figure_labels"] + scan_chapter_visuals(tex)["table_labels"])
    for vis in plan:
        if vis.label in present:
            vis.status = "done"
    return plan


def load_plan(chapter_id: str) -> list[VisualSpec]:
    path = plan_path(chapter_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [VisualSpec.from_dict(v) for v in data.get("visuals", [])]


def save_plan(chapter_id: str, visuals: list[VisualSpec], title: str) -> Path:
    out = plan_path(chapter_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"chapter_id": chapter_id, "chapter_title": title, "visuals": [v.to_dict() for v in visuals]}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _format_table_header(cols: list[str]) -> str:
    cells = []
    for i, col in enumerate(cols):
        if i == 0 and col == "":
            cells.append("")
        else:
            cells.append(f"\\textbf{{{col}}}")
    return " & ".join(cells)


def _autowidth_open() -> str:
    return "\\begin{adjustbox}{max width=\\linewidth,center}"


def _autowidth_close() -> str:
    return "\\end{adjustbox}"


def render_comparison_table(vis: VisualSpec) -> str:
    cols = vis.extra.get("columns", [])
    rows = vis.extra.get("rows", [])
    col_spec = "l" + "c" * (len(cols) - 1) if cols else "lc"
    lines = [
        f"\\begin{{table}}[{vis.placement}]",
        "\\centering",
        f"\\caption{{{vis.caption}}}",
        f"\\label{{{vis.label}}}",
        _autowidth_open(),
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule",
        VISUAL_STYLE["table_header"],
        _format_table_header(cols) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + " \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        _autowidth_close(),
        "\\end{table}",
    ]
    return "\n".join(lines)


def render_benchmark_table(vis: VisualSpec) -> str:
    cite = vis.extra.get("cite", "")
    caption = vis.caption + (f" \\citep{{{cite}}}" if cite else "")
    vis2 = VisualSpec(
        id=vis.id,
        kind=vis.kind,
        section=vis.section,
        label=vis.label,
        caption=caption,
        placement=vis.placement,
        extra=vis.extra,
    )
    return render_comparison_table(vis2)


def render_table(vis: VisualSpec) -> str:
    if vis.kind == "benchmark_table":
        return render_benchmark_table(vis)
    return render_comparison_table(vis)


def render_pipeline_figure(vis: VisualSpec, *, node_style: str = "pipeline_node") -> str:
    stages = vis.extra.get("stages", [])
    n = max(len(stages), 1)
    block_w, start_x = pipeline_layout(n)
    gap = GEOMETRY.pipeline_block_gap_cm
    node_token = VISUAL_STYLE[node_style]
    nodes, arrows = [], []
    for i, stage in enumerate(stages):
        x = start_x + i * (block_w + gap)
        name = escape_latex(stage["name"])
        detail = escape_latex(stage.get("detail", ""))
        style = node_token
        if node_style == "pipeline_node" and i % 2 == 1:
            style = VISUAL_STYLE["arch_node"]
        nodes.append(
            f"    \\node[{style}] (s{i}) at ({x:.2f},0) {{\\footnotesize {name}\\\\{detail}}};"
        )
        if i < n - 1:
            arrows.append(f"    \\draw[{VISUAL_STYLE['arrow']}] (s{i}.east) -- (s{i+1}.west);")
    return "\n".join(
        [
            f"\\begin{{figure}}[{vis.placement}]",
            "\\centering",
            _autowidth_open(),
            figure_tikz_opening("pipeline"),
            *nodes,
            *arrows,
            "\\end{tikzpicture}",
            _autowidth_close(),
            f"\\caption{{{vis.caption}}}",
            f"\\label{{{vis.label}}}",
            "\\end{figure}",
        ]
    )


def render_roofline_figure(vis: VisualSpec) -> str:
    peak_gflops = float(vis.extra.get("peak_gflops", 500))
    peak_gbps = float(vis.extra.get("peak_gbps", 2000))
    ridge_ai = peak_gflops / peak_gbps
    scale_y = 6.0 / max(peak_gflops, 1.0)
    ridge_x = min(ridge_ai, 7.5)
    ridge_y = ridge_x * peak_gbps * scale_y
    pts = []
    for i, pt in enumerate(vis.extra.get("points", [])):
        ai = min(float(pt.get("ai", 10)), 7.8)
        raw_att = min(peak_gflops, peak_gbps * float(pt.get("ai", 10)))
        y = raw_att * scale_y
        name = escape_latex(pt["name"])
        style = VISUAL_STYLE["point_a"] if i % 2 == 0 else VISUAL_STYLE["point_b"]
        pts.append(f"    \\node[{style}] at ({ai:.2f},{y:.2f}) {{}};")
        pts.append(f"    \\node[above right, text=visText] at ({ai:.2f},{y:.2f}) {{\\scriptsize {name}}};")
    return "\n".join(
        [
            f"\\begin{{figure}}[{vis.placement}]",
            "\\centering",
            _autowidth_open(),
            figure_tikz_opening("roofline"),
            f"    \\draw[{VISUAL_STYLE['axis']}] (0,0) -- (8,0) node[right] {{\\footnotesize Arithmetic intensity}};",
            f"    \\draw[{VISUAL_STYLE['axis']}] (0,0) -- (0,6) node[above] {{\\footnotesize GFLOP/s}};",
            f"    \\draw[{VISUAL_STYLE['roof_bandwidth']}] (0,0) -- ({ridge_x:.2f},{ridge_y:.2f});",
            f"    \\draw[{VISUAL_STYLE['roof_compute']}] ({ridge_x:.2f},{ridge_y:.2f}) -- (8,{ridge_y:.2f});",
            *pts,
            "\\end{tikzpicture}",
            _autowidth_close(),
            f"\\caption{{{vis.caption}}}",
            f"\\label{{{vis.label}}}",
            "\\end{figure}",
        ]
    )


def render_bar_figure(vis: VisualSpec) -> str:
    bars = vis.extra.get("bars", [])
    ymax = max((float(b.get("value", 1)) for b in bars), default=1.0)
    y_label = escape_latex(vis.extra.get("y_label", "Value"))
    lines = [
        f"\\begin{{figure}}[{vis.placement}]",
        "\\centering",
        _autowidth_open(),
        figure_tikz_opening("bar"),
        f"    \\draw[{VISUAL_STYLE['axis']}] (0,0) -- (0,4.5) node[above] {{\\footnotesize {y_label}}};",
        f"    \\draw[{VISUAL_STYLE['axis']}] (0,0) -- (6.5,0);",
    ]
    for i, bar in enumerate(bars):
        h = 4.0 * float(bar.get("value", 0)) / ymax
        style = VISUAL_STYLE["bar_one"] if i % 2 == 0 else VISUAL_STYLE["bar_two"]
        lines.append(f"    \\draw[{style}] ({i*1.6},0) rectangle ({i*1.6+1.2},{h:.2f});")
        lines.append(
            f"    \\node[text=visText] at ({i*1.6+0.6},-0.35) {{\\scriptsize {escape_latex(bar['name'])}}};"
        )
    lines += [
        "\\end{tikzpicture}",
        _autowidth_close(),
        f"\\caption{{{vis.caption}}}",
        f"\\label{{{vis.label}}}",
        "\\end{figure}",
    ]
    return "\n".join(lines)


def render_architecture_figure(vis: VisualSpec) -> str:
    vis.extra["stages"] = [{"name": b, "detail": ""} for b in vis.extra.get("blocks", [])]
    return render_pipeline_figure(vis, node_style="arch_node")


def render_placeholder_figure(vis: VisualSpec) -> str:
    note = escape_latex(vis.extra.get("pending_note", "Pending measured data"))
    return "\n".join(
        [
            f"\\begin{{figure}}[{vis.placement}]",
            "\\centering",
            f"\\vispending{{{note}}}",
            f"\\caption{{{vis.caption}}}",
            f"\\label{{{vis.label}}}",
            "\\end{figure}",
        ]
    )


def render_visual(vis: VisualSpec) -> str:
    renderers = {
        "comparison_table": render_table,
        "benchmark_table": render_table,
        "checklist_table": render_table,
        "reference_snapshot": render_table,
        "pipeline_figure": render_pipeline_figure,
        "roofline_figure": render_roofline_figure,
        "bar_figure": render_bar_figure,
        "architecture_figure": render_architecture_figure,
        "placeholder_figure": render_placeholder_figure,
    }
    fn = renderers.get(vis.kind)
    if not fn:
        raise ValueError(f"Unknown visual kind: {vis.kind}")
    return fn(vis)


def cmd_plan(chapter_id: str) -> int:
    spec = chapter_spec(chapter_id)
    if not spec:
        print(f"Unknown chapter: {chapter_id}", file=sys.stderr)
        return 1
    tex_path = CHAPTERS / spec.filename
    tex = tex_path.read_text(encoding="utf-8") if tex_path.exists() else ""
    existing = {v.id: v for v in load_plan(chapter_id)}
    merged: list[VisualSpec] = []
    for vis in build_plan_from_recipes(spec):
        merged.append(existing.get(vis.id, vis))
    merged = merge_plan_with_tex(merged, tex)
    path = save_plan(chapter_id, merged, spec.title)
    print(f"Wrote plan: {path} ({len(merged)} visuals)")
    return 0


def audit_chapter(chapter_id: str) -> dict[str, Any]:
    spec = chapter_spec(chapter_id)
    if not spec:
        return {"error": f"unknown chapter {chapter_id}"}
    tex_path = CHAPTERS / spec.filename
    tex = tex_path.read_text(encoding="utf-8") if tex_path.exists() else ""
    scan = scan_chapter_visuals(tex)
    plan = load_plan(chapter_id) or merge_plan_with_tex(build_plan_from_recipes(spec), tex)
    targets = CHAPTER_VISUAL_TARGETS.get(chapter_id, {"min_tables": 1, "min_figures": 1})
    present = set(scan["figure_labels"] + scan["table_labels"])
    missing = [v.id for v in plan if v.label not in present]
    done = [v.id for v in plan if v.label in present]
    return {
        "chapter": chapter_id,
        "table_count": scan["table_count"],
        "figure_count": scan["figure_count"],
        "min_tables": targets["min_tables"],
        "min_figures": targets["min_figures"],
        "table_gap": max(0, targets["min_tables"] - scan["table_count"]),
        "figure_gap": max(0, targets["min_figures"] - scan["figure_count"]),
        "planned_visuals": len(plan),
        "done_visuals": len(done),
        "missing_ids": missing,
    }


def cmd_audit(chapter_id: str | None) -> int:
    ids = [chapter_id] if chapter_id else [s.chapter_id for s in OUTLINE]
    for cid in ids:
        report = audit_chapter(cid)
        if "error" in report:
            print(report["error"], file=sys.stderr)
            return 1
        print("---")
        print(f"chapter:       {report['chapter']}")
        print(f"tables:        {report['table_count']} (min {report['min_tables']}, gap {report['table_gap']})")
        print(f"figures:       {report['figure_count']} (min {report['min_figures']}, gap {report['figure_gap']})")
        print(f"plan:          {report['done_visuals']}/{report['planned_visuals']} done")
        if report["missing_ids"]:
            print(f"missing_ids:   {','.join(report['missing_ids'])}")
    return 0


def cmd_render(chapter_id: str, visual_id: str | None) -> int:
    plan = load_plan(chapter_id)
    if not plan:
        print("No plan found. Run with --plan first.", file=sys.stderr)
        return 1
    out_dir = generated_dir(chapter_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = plan if not visual_id else [v for v in plan if v.id == visual_id]
    if visual_id and not selected:
        print(f"Visual id not in plan: {visual_id}", file=sys.stderr)
        return 1
    for vis in selected:
        if vis.status == "done":
            print(f"Skip {vis.id} (already in chapter .tex)")
            continue
        (out_dir / f"{vis.id}.tex").write_text(render_visual(vis) + "\n", encoding="utf-8")
        print(f"Rendered {out_dir / (vis.id + '.tex')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and render book figures/tables.")
    parser.add_argument("--chapter")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--render", nargs="?", const="__all__", metavar="VISUAL_ID")
    parser.add_argument("--list-kinds", action="store_true")
    parser.add_argument(
        "--emit-style",
        action="store_true",
        help="Regenerate books/visuals_style.tex from books/visuals_style.py (Nature NPG)",
    )
    args = parser.parse_args()
    if args.emit_style:
        path = _visuals_style.emit_tex()
        print(f"Wrote {path}")
        return 0
    if args.list_kinds:
        for kind, desc in VISUAL_KINDS.items():
            print(f"{kind}\t{desc}")
        return 0
    if not args.chapter and (args.plan or args.audit or args.render is not None):
        parser.error("--chapter is required")
    if args.plan:
        return cmd_plan(args.chapter)
    if args.audit:
        return cmd_audit(args.chapter)
    if args.render is not None:
        vid = None if args.render == "__all__" else args.render
        return cmd_render(args.chapter, vid)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

for _spec in OUTLINE:
    CHAPTER_VISUAL_TARGETS.setdefault(_spec.chapter_id, {"min_tables": 0, "min_figures": 2})
