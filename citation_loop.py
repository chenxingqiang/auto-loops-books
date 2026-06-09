#!/usr/bin/env python3
"""
Per-chapter citation catalog, sentence bindings, and strict verification (ch01-ch27).

Each chapter:
  books/research/<ch>/chapter.bib
  books/research/<ch>/citation_catalog.json
  books/research/<ch>/citation_bindings.jsonl
  books/research/<ch>/citation_strict_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from book_prepare import CHAPTERS, OUTLINE, ChapterSpec, read_chapter_text


def chapter_tex_path(spec: ChapterSpec) -> Path:
    return CHAPTERS / spec.filename
from research_tools import (
    BIB_PATH,
    CROSSREF_EMAIL,
    RESEARCH_ROOT,
    ROOT,
    SCHOLAR_YEAR_LO,
    analyze_relevance,
    binding_passes_quality,
    classify_source_tier,
    dedupe_papers,
    effective_binding_keywords,
    extract_chapter_keywords,
    format_reference,
    generate_chapter_queries,
    parse_bib_entries,
    persist_keywords,
    search_google_scholar,
    text_matches_keyword,
)

MIN_CHAPTER_PAPERS = 25
MIN_BINDING_SCORE = 12
MIN_BINDING_KEYWORDS = 2
MIN_QUALITY_BINDINGS = 8
MIN_SENTENCE_WORDS = 8
CLAIM_SENTENCE_MIN_WORDS = 10
MAX_CROSSREF_QUERIES = 10
MERGED_BIB_PATH = ROOT / "books" / "citations_merged.bib"
QUALITY_REPORT_NAME = "citation_quality_report.json"
CITE_CMD_RE = re.compile(r"\\cite([tp])?\{([^}]+)\}")

SKIP_APPLY_MARKERS = (
    r"\begin{figure}",
    r"\begin{table}",
    r"\begin{equation}",
    r"\begin{tikzpicture}",
    r"\begin{algorithm}",
    r"\includegraphics",
)

SKIP_REDISTRIBUTE_SECTIONS = frozenset(
    {
        "Engineering Deep Dive",
    }
)
MAX_CITES_PER_SENTENCE = 1
REDISTRIBUTE_POOL_NAME = "citation_pool.json"
REDISTRIBUTE_REPORT_NAME = "citation_redistribute_report.json"


@dataclass(frozen=True)
class CitationQualityOptions:
    min_binding_score: int = MIN_BINDING_SCORE
    min_matched_keywords: int = MIN_BINDING_KEYWORDS
    tier_a_only: bool = False
    min_quality_bindings: int = MIN_QUALITY_BINDINGS


def quality_report_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / QUALITY_REPORT_NAME


def load_catalog(chapter_id: str) -> list[dict]:
    cat_file = catalog_path(chapter_id)
    if not cat_file.exists():
        return []
    return json.loads(cat_file.read_text(encoding="utf-8")).get("papers", [])


def catalog_tier_map(catalog: list[dict]) -> dict[str, str]:
    return {item["bib_key"]: item.get("source_tier", "B") for item in catalog}


def enrich_catalog_tiers(spec: ChapterSpec) -> dict:
    catalog = load_catalog(spec.chapter_id)
    if not catalog:
        return {"chapter_id": spec.chapter_id, "updated": 0}
    counts = Counter()
    for item in catalog:
        paper = {
            "title": item.get("title"),
            "link": item.get("link"),
            "source": item.get("source"),
            "publication_info": {},
        }
        tier = classify_source_tier(paper, bib_key=item.get("bib_key"))
        item["source_tier"] = tier
        counts[tier] += 1
    cat_path = catalog_path(spec.chapter_id)
    data = json.loads(cat_path.read_text(encoding="utf-8"))
    data["papers"] = catalog
    data["tier_counts"] = dict(counts)
    data["tiers_enriched_at"] = datetime.now().isoformat()
    cat_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "chapter_id": spec.chapter_id,
        "updated": len(catalog),
        "tier_counts": dict(counts),
    }


def filter_bindings(bindings: list[dict], opts: CitationQualityOptions) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    rejected: list[dict] = []
    for b in bindings:
        row = dict(b)
        if "effective_keywords" not in row:
            row["effective_keywords"] = effective_binding_keywords(row.get("matched_keywords"))
        ok, reason = binding_passes_quality(
            row,
            min_score=opts.min_binding_score,
            min_keywords=opts.min_matched_keywords,
            tier_a_only=opts.tier_a_only,
        )
        if ok:
            kept.append(row)
        else:
            rejected.append({**row, "reject_reason": reason})
    return kept, rejected


def add_quality_cli_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--min-binding-score",
        type=int,
        default=MIN_BINDING_SCORE,
        help=f"Minimum relevance score for bindings (default {MIN_BINDING_SCORE})",
    )
    parser.add_argument(
        "--min-matched-keywords",
        type=int,
        default=MIN_BINDING_KEYWORDS,
        help=f"Min non-generic matched keywords (default {MIN_BINDING_KEYWORDS})",
    )
    parser.add_argument(
        "--tier-a-only",
        action="store_true",
        help="Only bind/apply Tier-A sources (arXiv, ACM/IEEE, vendor docs, book.bib)",
    )


def quality_opts_from_args(args: argparse.Namespace) -> CitationQualityOptions:
    return CitationQualityOptions(
        min_binding_score=getattr(args, "min_binding_score", MIN_BINDING_SCORE),
        min_matched_keywords=getattr(args, "min_matched_keywords", MIN_BINDING_KEYWORDS),
        tier_a_only=getattr(args, "tier_a_only", False),
    )

TECH_TERMS = re.compile(
    r"\b(?:LLM|GPU|CPU|NPU|CUDA|HIP|MLIR|TVM|Triton|XLA|KV|HBM|"
    r"PyTorch|FlashAttention|vLLM|MegaKernel|YiRage|XDNA|AIE|"
    r"GEMM|SIMD|NUMA|Warp|tensor core|PagedAttention|Hopper|Blackwell)\b",
    re.IGNORECASE,
)


def chapter_dir(chapter_id: str) -> Path:
    return RESEARCH_ROOT / chapter_id


def chapter_bib_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / "chapter.bib"


def catalog_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / "citation_catalog.json"


def bindings_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / "citation_bindings.jsonl"


def strict_report_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / "citation_strict_report.json"


def strip_latex_inline(text: str) -> str:
    text = re.sub(r"\\cite[tp]?\{[^}]+\}", "", text)
    text = re.sub(r"\\(?:label|typeout|index|newterm)\{[^}]+\}", "", text)
    text = re.sub(r"\\[a-zA-Z@]+(\[[^\]]*\])?", " ", text)
    text = re.sub(r"\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\$[^$]+\$", " ", text)
    text = re.sub(r"%.*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_content_sentences(tex: str) -> list[dict]:
    current_section = "chapter"
    sentences: list[dict] = []
    sid = 0

    for para in re.split(r"\n\s*\n", tex):
        para = para.strip()
        if not para or para.startswith("%"):
            continue
        sec_m = re.search(r"\\section\{([^}]+)\}", para)
        if sec_m:
            current_section = sec_m.group(1)
        sub_m = re.search(r"\\subsection\{([^}]+)\}", para)
        if sub_m:
            current_section = sub_m.group(1)

        plain = strip_latex_inline(para)
        if len(plain.split()) < MIN_SENTENCE_WORDS:
            continue

        for sent in re.split(r"(?<=[.!?])\s+", plain):
            sent = sent.strip()
            if len(sent.split()) < MIN_SENTENCE_WORDS:
                continue
            sid += 1
            sentences.append(
                {
                    "id": f"s{sid:04d}",
                    "section": current_section,
                    "text": sent,
                    "word_count": len(sent.split()),
                    "is_claim": len(sent.split()) >= CLAIM_SENTENCE_MIN_WORDS,
                }
            )
    return sentences


def sentence_keywords(
    sentence: str, chapter_keywords: list[tuple[str, int]]
) -> list[tuple[str, int]]:
    sent_l = sentence.lower()
    matched: list[tuple[str, int]] = []
    for term, weight in chapter_keywords:
        if text_matches_keyword(sent_l, term):
            matched.append((term, weight))
    if matched:
        return sorted(matched, key=lambda x: (-x[1], x[0]))[:12]

    tokens = Counter(
        t.lower()
        for t in re.findall(r"[A-Za-z][A-Za-z0-9'\-]{2,}", sentence)
        if len(t) >= 4
    )
    extra: list[tuple[str, int]] = []
    for tok, _ in tokens.most_common(6):
        extra.append((tok, 8))
    for m in TECH_TERMS.findall(sentence):
        extra.append((m.lower(), 10))
    return extra[:12] if extra else chapter_keywords[:8]


def crossref_search(query: str, *, rows: int = 20) -> list[dict]:
    params = {
        "query": query,
        "rows": rows,
        "mailto": CROSSREF_EMAIL,
        "filter": f"from-pub-date:{SCHOLAR_YEAR_LO}",
    }
    try:
        resp = requests.get(
            "https://api.crossref.org/works", params=params, timeout=45
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
    except requests.RequestException as exc:
        print(f"    Crossref search error ({query[:40]}...): {exc}")
        return []

    papers: list[dict] = []
    for item in items:
        title = " ".join(item.get("title") or []).strip()
        if not title:
            continue
        abstract = ""
        if item.get("abstract"):
            abstract = BeautifulSoup(item["abstract"], "html.parser").get_text()
        authors = []
        for a in item.get("author") or []:
            fam = a.get("family", "")
            giv = a.get("given", "")
            name = f"{giv} {fam}".strip() or fam
            if name:
                authors.append({"name": name})
        year = None
        for key in ("published-print", "published-online", "created"):
            parts = (item.get(key) or {}).get("date-parts")
            if parts and parts[0]:
                year = parts[0][0]
                break
        papers.append(
            {
                "title": title,
                "abstract": abstract,
                "snippet": abstract,
                "link": item.get("URL", ""),
                "year": year,
                "publication_info": {"authors": authors},
                "source": "crossref",
            }
        )
    return papers


def bib_key_for_paper(paper: dict, chapter_id: str, index: int) -> str:
    title = paper.get("title", "paper")
    slug = re.sub(r"[^a-z0-9]", "", title.lower())[:18] or "paper"
    year = paper.get("year") or datetime.now().year
    year = str(year)[:4]
    authors = paper.get("publication_info", {}).get("authors", [])
    first = "anon"
    if authors:
        name = authors[0].get("name", "") if isinstance(authors[0], dict) else str(authors[0])
        parts = name.split()
        if parts:
            first = re.sub(r"[^a-z]", "", parts[-1].lower())[:12] or "anon"
    base = f"{first}{year}{slug}"
    return re.sub(r"[^a-zA-Z0-9]", "", base)[:48] or f"{chapter_id}_{index:04d}"


def flatten_bib_field_newlines(text: str) -> str:
    out: list[str] = []
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
            out.append(ch)
        elif ch == "}":
            depth = max(0, depth - 1)
            out.append(ch)
        elif ch in "\n\r" and depth > 0:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def sanitize_bib_value(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace("&amp;", "&").replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("_", r"\_")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fallback_author_from_key(bib_key: str) -> str:
    m = re.match(r"^([A-Za-z]+)", bib_key)
    if not m:
        return "Anonymous"
    stem = m.group(1)
    if stem.lower() == "anon":
        return "Anonymous"
    last = f"{stem[0].upper()}{stem[1:]}"
    return f"{last}, X"


def format_bib_authors(paper: dict, bib_key: str) -> str:
    authors = paper.get("publication_info", {}).get("authors", [])
    names: list[str] = []
    for a in authors[:6]:
        name = a.get("name", "") if isinstance(a, dict) else str(a)
        name = sanitize_bib_value(name.replace("{", "").replace("}", ""))
        if name and name.lower() not in {"unknown", "anonymous"}:
            names.append(name)
    if names:
        return " and ".join(names)
    return fallback_author_from_key(bib_key)


def strip_note_field(block: str) -> str:
    while True:
        m = re.search(r",\s*note=\{", block)
        if not m:
            break
        start = m.start()
        i = m.end()
        depth = 1
        while i < len(block) and depth > 0:
            if block[i] == "{":
                depth += 1
            elif block[i] == "}":
                depth -= 1
            i += 1
        block = block[:start] + block[i:]
    return block


def sanitize_bib_block(block: str) -> str:
    block = flatten_bib_field_newlines(block.strip())
    key_m = re.search(r"@\w+\{([^,\s]+)", block)
    bib_key = key_m.group(1) if key_m else ""
    block = strip_note_field(block)
    if bib_key:
        block = block.replace(
            "author={Unknown}",
            f"author={{{fallback_author_from_key(bib_key)}}}",
        )
    block = block.replace("&amp;", r"\&")
    block = re.sub(r"(?<![\\])&", r"\\&", block)
    if not block.endswith("}"):
        block = block.rstrip(",") + "\n}"
    return block


def paper_to_bibtex(bib_key: str, paper: dict) -> str:
    raw_title = paper.get("title", "Untitled")
    title = sanitize_bib_value(raw_title.replace("{", "").replace("}", ""))
    year = paper.get("year") or datetime.now().year
    link = paper.get("link", "")
    author_str = format_bib_authors(paper, bib_key)
    lines = [
        f"@article{{{bib_key},",
        f"  title={{{title}}},",
        f"  author={{{author_str}}},",
        f"  year={{{year}}},",
    ]
    if link:
        lines.append(f"  url={{{link}}},")
    lines.append("}")
    return "\n".join(lines)


def load_existing_catalog_papers(chapter_id: str) -> list[dict]:
    papers: list[dict] = []
    search_path = chapter_dir(chapter_id) / "search_data.json"
    if search_path.exists():
        data = json.loads(search_path.read_text(encoding="utf-8"))
        for p in data.get("papers", []):
            raw = dict(p.get("raw") or p)
            raw.setdefault("title", p.get("title"))
            raw.setdefault("abstract", p.get("abstract"))
            raw["source"] = raw.get("source", "search_data")
            papers.append(raw)
    return papers


def seed_papers_from_book_bib() -> list[dict]:
    papers: list[dict] = []
    for key, entry in parse_bib_entries(BIB_PATH).items():
        papers.append(
            {
                "title": entry.get("title", ""),
                "abstract": " ".join(
                    entry.get(f, "")
                    for f in ("note", "journal", "booktitle", "howpublished")
                ),
                "snippet": entry.get("title", ""),
                "link": "",
                "year": entry.get("year"),
                "publication_info": {"authors": [{"name": entry.get("author", "")}]},
                "source": "book.bib",
                "bib_key": key,
            }
        )
    return papers


def gather_chapter_papers(
    spec: ChapterSpec,
    queries: list[str],
    *,
    dry_run: bool = False,
    use_scholar: bool = True,
) -> list[dict]:
    pool: list[dict] = []
    pool.extend(load_existing_catalog_papers(spec.chapter_id))
    pool.extend(seed_papers_from_book_bib())

    if dry_run:
        return dedupe_papers(pool)

    for query in queries[:MAX_CROSSREF_QUERIES]:
        pool.extend(crossref_search(query, rows=25))
        if len(dedupe_papers(pool)) >= MIN_CHAPTER_PAPERS * 2:
            break
        time.sleep(0.35)

    if use_scholar and os.environ.get("SERPAPI_KEY"):
        for query in queries[:4]:
            pool.extend(search_google_scholar(query, max_pages=1, query_delay_s=1.5))
            if len(dedupe_papers(pool)) >= MIN_CHAPTER_PAPERS * 3:
                break

    return dedupe_papers(pool)


def build_catalog(
    spec: ChapterSpec,
    papers: list[dict],
    keywords: list[tuple[str, int]],
) -> list[dict]:
    catalog: list[dict] = []
    used_keys: set[str] = set()

    for i, paper in enumerate(papers):
        score, matched = analyze_relevance(paper, keywords)
        if score < 1 and paper.get("source") != "book.bib":
            continue
        bib_key = paper.get("bib_key") or bib_key_for_paper(paper, spec.chapter_id, i)
        while bib_key in used_keys:
            bib_key = f"{bib_key}_{i}"
        used_keys.add(bib_key)
        paper_for_tier = dict(paper)
        paper_for_tier.setdefault("link", paper.get("link"))
        tier = classify_source_tier(paper_for_tier, bib_key=bib_key)
        catalog.append(
            {
                "bib_key": bib_key,
                "title": paper.get("title"),
                "link": paper.get("link"),
                "year": paper.get("year"),
                "source": paper.get("source", "unknown"),
                "source_tier": tier,
                "relevance_score": score,
                "matched_keywords": matched,
                "reference": format_reference(paper),
                "abstract": (paper.get("abstract") or paper.get("snippet") or "")[:800],
                "paper": paper,
            }
        )

    catalog.sort(key=lambda x: x["relevance_score"], reverse=True)
    return catalog


def bind_sentences_to_catalog(
    sentences: list[dict],
    catalog: list[dict],
    chapter_keywords: list[tuple[str, int]],
    *,
    opts: CitationQualityOptions | None = None,
) -> list[dict]:
    bindings: list[dict] = []
    if not catalog:
        return bindings

    opts = opts or CitationQualityOptions()
    pool = catalog
    if opts.tier_a_only:
        pool = [c for c in catalog if c.get("source_tier") == "A"]
        if not pool:
            pool = catalog

    claim_sentences = [s for s in sentences if s.get("is_claim")]
    targets = claim_sentences if claim_sentences else sentences

    for sent in targets:
        skw = sentence_keywords(sent["text"], chapter_keywords)
        best_item = None
        best_score = 0
        best_matched: list[str] = []

        for item in pool:
            paper = {
                "title": item.get("title", ""),
                "abstract": item.get("abstract", ""),
                "snippet": item.get("abstract", ""),
            }
            score, matched = analyze_relevance(paper, skw or chapter_keywords)
            if score > best_score:
                best_score = score
                best_item = item
                best_matched = matched

        if not best_item or best_score < opts.min_binding_score:
            continue
        if len(effective_binding_keywords(best_matched)) < opts.min_matched_keywords:
            eff = effective_binding_keywords(best_matched)
            if not (len(eff) >= 1 and best_score >= 16):
                continue

        bindings.append(
            {
                "sentence_id": sent["id"],
                "section": sent["section"],
                "sentence": sent["text"],
                "word_count": sent["word_count"],
                "bib_key": best_item["bib_key"],
                "title": best_item.get("title"),
                "source_tier": best_item.get("source_tier", "B"),
                "relevance_score": best_score,
                "matched_keywords": best_matched,
                "effective_keywords": effective_binding_keywords(best_matched),
                "sentence_keywords": [k for k, _ in skw[:8]],
            }
        )
    return bindings


def write_chapter_bib(chapter_id: str, catalog: list[dict]) -> Path:
    path = chapter_bib_path(chapter_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for item in catalog:
        paper = dict(item.get("paper") or item)
        paper.setdefault("title", item.get("title"))
        paper.setdefault("abstract", item.get("abstract"))
        paper.setdefault("year", item.get("year"))
        paper.setdefault("link", item.get("link"))
        blocks.append(sanitize_bib_block(paper_to_bibtex(item["bib_key"], paper)))
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return path


def run_chapter_citation_plan(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    min_papers: int = MIN_CHAPTER_PAPERS,
    crossref_only: bool = False,
    quality: CitationQualityOptions | None = None,
) -> dict:
    tex = read_chapter_text(spec)
    keywords = extract_chapter_keywords(spec)
    queries = generate_chapter_queries(spec, keywords)
    persist_keywords(spec, keywords)
    (chapter_dir(spec.chapter_id) / "queries.json").write_text(
        json.dumps(queries, indent=2), encoding="utf-8"
    )

    sentences = extract_content_sentences(tex)
    raw_papers = gather_chapter_papers(
        spec, queries, dry_run=dry_run, use_scholar=(not dry_run and not crossref_only)
    )
    catalog = build_catalog(spec, raw_papers, keywords)

    if len(catalog) < min_papers and not dry_run:
        extra = queries[MAX_CROSSREF_QUERIES:] + [
            f"{spec.title} LLM inference compiler",
            f"{spec.chapter_id} GPU kernel optimization",
        ]
        for q in extra[:8]:
            if len(catalog) >= min_papers:
                break
            raw_papers = dedupe_papers(raw_papers + crossref_search(q, rows=30))
            catalog = build_catalog(spec, raw_papers, keywords)
            time.sleep(0.35)

    bindings = bind_sentences_to_catalog(
        sentences, catalog, keywords, opts=quality or CitationQualityOptions()
    )

    out_dir = chapter_dir(spec.chapter_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    cat_path = catalog_path(spec.chapter_id)
    cat_path.write_text(
        json.dumps(
            {
                "chapter_id": spec.chapter_id,
                "timestamp": datetime.now().isoformat(),
                "min_papers": min_papers,
                "paper_count": len(catalog),
                "sentence_count": len(sentences),
                "binding_count": len(bindings),
                "papers": [
                    {k: v for k, v in item.items() if k != "paper"} for item in catalog
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    bind_path = bindings_path(spec.chapter_id)
    with bind_path.open("w", encoding="utf-8") as fh:
        for row in bindings:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    bib_path = None
    if catalog and not dry_run:
        bib_path = write_chapter_bib(spec.chapter_id, catalog)

    return {
        "chapter_id": spec.chapter_id,
        "paper_count": len(catalog),
        "sentence_count": len(sentences),
        "binding_count": len(bindings),
        "keyword_count": len(keywords),
        "catalog_path": str(cat_path.relative_to(ROOT)),
        "bindings_path": str(bind_path.relative_to(ROOT)),
        "chapter_bib": str(bib_path.relative_to(ROOT)) if bib_path else None,
        "dry_run": dry_run,
        "meets_min_papers": len(catalog) >= min_papers,
    }


def refilter_chapter_bindings(
    spec: ChapterSpec,
    opts: CitationQualityOptions,
) -> dict:
    enrich_catalog_tiers(spec)
    catalog = load_catalog(spec.chapter_id)
    tex = read_chapter_text(spec)
    keywords = extract_chapter_keywords(spec)
    sentences = extract_content_sentences(tex)

    all_bindings = bind_sentences_to_catalog(
        sentences, catalog, keywords, opts=opts
    )
    if not all_bindings and opts.tier_a_only:
        relaxed = CitationQualityOptions(
            min_binding_score=max(8, opts.min_binding_score - 4),
            min_matched_keywords=max(1, opts.min_matched_keywords - 1),
            tier_a_only=True,
            min_quality_bindings=opts.min_quality_bindings,
        )
        all_bindings = bind_sentences_to_catalog(
            sentences, catalog, keywords, opts=relaxed
        )
        if all_bindings:
            report_note = "relaxed_tier_a_fallback"
        else:
            report_note = None
    else:
        report_note = None
    raw_bindings = load_bindings(spec.chapter_id)
    _, rejected_from_raw = filter_bindings(raw_bindings, opts) if raw_bindings else ([], [])

    bind_path = bindings_path(spec.chapter_id)
    with bind_path.open("w", encoding="utf-8") as fh:
        for row in all_bindings:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    tier_counts = Counter(b.get("source_tier", "?") for b in all_bindings)
    report = {
        "chapter_id": spec.chapter_id,
        "timestamp": datetime.now().isoformat(),
        "min_binding_score": opts.min_binding_score,
        "min_matched_keywords": opts.min_matched_keywords,
        "tier_a_only": opts.tier_a_only,
        "bindings_before": len(raw_bindings),
        "bindings_after": len(all_bindings),
        "rejected_from_previous": len(rejected_from_raw),
        "tier_counts_in_bindings": dict(tier_counts),
        "catalog_tier_a": sum(1 for c in catalog if c.get("source_tier") == "A"),
        "catalog_total": len(catalog),
    }
    if report_note:
        report["fallback"] = report_note
    quality_report_path(spec.chapter_id).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def remove_cite_keys_from_tex(tex: str, keys_to_remove: set[str]) -> tuple[str, int]:
    if not keys_to_remove:
        return tex, 0
    removed = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal removed
        cmd = match.group(1)
        group = match.group(2)
        keys = [k.strip() for k in group.split(",") if k.strip()]
        kept = [k for k in keys if k not in keys_to_remove]
        removed += len(keys) - len(kept)
        if not kept:
            return ""
        return f"\\{cmd}{{{','.join(kept)}}}"

    tex = re.sub(r"\\(cite[tp]?)\{([^}]+)\}", repl, tex)
    tex = re.sub(r"\s+\.", ".", tex)
    tex = re.sub(r"  +", " ", tex)
    return tex, removed


def prune_non_tier_a_cites_from_tex(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
) -> dict:
    enrich_catalog_tiers(spec)
    catalog = load_catalog(spec.chapter_id)
    book_keys = set(parse_bib_entries(BIB_PATH).keys())
    remove_keys = {
        item["bib_key"]
        for item in catalog
        if item.get("source_tier") in ("B", "C") and item["bib_key"] not in book_keys
    }
    path = chapter_tex_path(spec)
    tex = path.read_text(encoding="utf-8")
    new_tex, n_removed = remove_cite_keys_from_tex(tex, remove_keys)
    report = {
        "chapter_id": spec.chapter_id,
        "keys_pruned": len(remove_keys),
        "cite_key_removals": n_removed,
        "dry_run": dry_run,
    }
    if not dry_run and new_tex != tex:
        path.write_text(new_tex, encoding="utf-8")
        report["updated"] = True
    else:
        report["updated"] = False
    return report


def strict_verify_chapter_citations(
    spec: ChapterSpec,
    *,
    min_papers: int = MIN_CHAPTER_PAPERS,
    quality: CitationQualityOptions | None = None,
) -> dict:
    tex = read_chapter_text(spec)
    keywords = extract_chapter_keywords(spec)
    sentences = extract_content_sentences(tex)

    cat_file = catalog_path(spec.chapter_id)
    bind_file = bindings_path(spec.chapter_id)
    bib_file = chapter_bib_path(spec.chapter_id)

    issues: list[str] = []
    catalog: list[dict] = []
    bindings: list[dict] = []

    if not cat_file.exists():
        issues.append("missing citation_catalog.json")
    else:
        catalog = json.loads(cat_file.read_text(encoding="utf-8")).get("papers", [])

    if not bind_file.exists():
        issues.append("missing citation_bindings.jsonl")
    else:
        for line in bind_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                bindings.append(json.loads(line))

    tier_map = catalog_tier_map(catalog)
    for b in bindings:
        b.setdefault("source_tier", tier_map.get(b.get("bib_key", ""), "C"))
        b.setdefault(
            "effective_keywords",
            effective_binding_keywords(b.get("matched_keywords")),
        )

    bib_keys: set[str] = set()
    if not bib_file.exists():
        issues.append("missing chapter.bib")
    else:
        bib_keys = set(parse_bib_entries(bib_file).keys())
        if len(bib_keys) < min_papers:
            issues.append(f"chapter.bib has {len(bib_keys)} entries (need >={min_papers})")

    if len(catalog) < min_papers:
        issues.append(f"catalog has {len(catalog)} papers (need >={min_papers})")

    opts = quality or CitationQualityOptions()
    quality_bindings, weak_bindings = filter_bindings(bindings, opts)

    missing_bib_keys: list[str] = []
    for b in quality_bindings:
        if b.get("bib_key") not in bib_keys:
            missing_bib_keys.append(b.get("bib_key", ""))

    if len(quality_bindings) < opts.min_quality_bindings:
        issues.append(
            f"quality bindings {len(quality_bindings)} < {opts.min_quality_bindings}"
        )

    bound_ids = {b["sentence_id"] for b in quality_bindings}
    claim_sentences = [s for s in sentences if s.get("is_claim")]
    unbound = [s for s in claim_sentences if s["id"] not in bound_ids]
    unbound_ratio = len(unbound) / len(claim_sentences) if claim_sentences else 0.0
    if claim_sentences and unbound_ratio > 0.92 and not opts.tier_a_only:
        issues.append(
            f"too many unbound claim sentences ({len(unbound)}/{len(claim_sentences)})"
        )

    tier_a_in_catalog = sum(1 for c in catalog if c.get("source_tier") == "A")
    min_tier_a = max(opts.min_quality_bindings, 12)
    if opts.tier_a_only and tier_a_in_catalog < min_tier_a:
        issues.append(
            f"tier-A catalog {tier_a_in_catalog} < {min_tier_a} (enrich or relax tier filter)"
        )

    status = "pass" if not issues and not missing_bib_keys else "fail"

    report = {
        "chapter_id": spec.chapter_id,
        "chapter_title": spec.title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "min_papers": min_papers,
        "catalog_count": len(catalog),
        "catalog_tier_a": tier_a_in_catalog,
        "binding_count": len(bindings),
        "quality_binding_count": len(quality_bindings),
        "sentence_count": len(sentences),
        "claim_sentence_count": len(claim_sentences),
        "unbound_claim_sentences": len(unbound),
        "weak_bindings": weak_bindings[:20],
        "missing_bib_keys": missing_bib_keys,
        "issues": issues,
        "keyword_count": len(keywords),
        "quality": {
            "min_binding_score": opts.min_binding_score,
            "min_matched_keywords": opts.min_matched_keywords,
            "tier_a_only": opts.tier_a_only,
        },
    }

    strict_report_path(spec.chapter_id).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def parse_cite_keys(group: str) -> list[str]:
    return [k.strip() for k in group.split(",") if k.strip()]


def collect_cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for m in CITE_CMD_RE.finditer(tex):
        keys.update(parse_cite_keys(m.group(2)))
    return keys


def _dedupe_cites_in_text(
    tex: str,
    seen: set[str],
    stats: dict[str, int],
) -> str:
    def repl(m: re.Match[str]) -> str:
        tp = m.group(1) or "p"
        keys = parse_cite_keys(m.group(2))
        fresh: list[str] = []
        for k in keys:
            if k not in seen:
                fresh.append(k)
            seen.add(k)
        if not fresh:
            stats["groups_removed"] += 1
            return ""
        if len(fresh) < len(keys):
            stats["keys_suppressed"] += len(keys) - len(fresh)
        stats["groups_kept"] += 1
        return f"\\cite{tp}{{{','.join(fresh)}}}"

    out = CITE_CMD_RE.sub(repl, tex)
    out = re.sub(r"\s+\.", ".", out)
    out = re.sub(r"  +", " ", out)
    out = re.sub(r" ([,.;:])", r"\1", out)
    return out


def dedupe_chapter_citations(
    tex: str,
    *,
    per_section: bool = False,
) -> tuple[str, dict[str, int]]:
    stats = {"groups_removed": 0, "keys_suppressed": 0, "groups_kept": 0}
    if per_section:
        parts = re.split(r"(?=\\(?:section|chapter)\{)", tex)
        chunks: list[str] = []
        for part in parts:
            seen: set[str] = set()
            chunks.append(_dedupe_cites_in_text(part, seen, stats))
        return "".join(chunks), stats
    seen: set[str] = set()
    return _dedupe_cites_in_text(tex, seen, stats), stats


def dedupe_chapter_citations_tex(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    per_section: bool = False,
) -> dict:
    path = chapter_tex_path(spec)
    tex = path.read_text(encoding="utf-8")
    before = len(collect_cite_keys(tex))
    cite_groups_before = len(CITE_CMD_RE.findall(tex))
    new_tex, stats = dedupe_chapter_citations(tex, per_section=per_section)
    after = len(collect_cite_keys(new_tex))
    cite_groups_after = len(CITE_CMD_RE.findall(new_tex))
    report = {
        "chapter_id": spec.chapter_id,
        "unique_keys_before": before,
        "unique_keys_after": after,
        "cite_groups_before": cite_groups_before,
        "cite_groups_after": cite_groups_after,
        "per_section": per_section,
        "dry_run": dry_run,
        **stats,
    }
    if not dry_run and new_tex != tex:
        path.write_text(new_tex, encoding="utf-8")
        report["updated"] = True
    else:
        report["updated"] = False
    return report


def remove_cite_commands(tex: str) -> str:
    out = CITE_CMD_RE.sub("", tex)
    out = re.sub(r"\s+\.", ".", out)
    out = re.sub(r"  +", " ", out)
    out = re.sub(r" ([,.;:])", r"\1", out)
    return out


def redistribute_pool_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / REDISTRIBUTE_POOL_NAME


def redistribute_report_path(chapter_id: str) -> Path:
    return chapter_dir(chapter_id) / REDISTRIBUTE_REPORT_NAME


def catalog_item_passes_pool(item: dict, opts: CitationQualityOptions) -> bool:
    if opts.tier_a_only and item.get("source_tier") != "A":
        return False
    score = int(item.get("relevance_score") or 0)
    if score < opts.min_binding_score:
        return False
    matched = effective_binding_keywords(item.get("matched_keywords"))
    if len(matched) >= opts.min_matched_keywords:
        return True
    return len(matched) >= 1 and score >= 16


def consolidate_chapter_citation_pool(
    spec: ChapterSpec,
    opts: CitationQualityOptions,
) -> list[dict]:
    """Merge Tier-A catalog entries into one deduped pool per chapter."""
    enrich_catalog_tiers(spec)
    catalog = load_catalog(spec.chapter_id)
    book_keys = set(parse_bib_entries(BIB_PATH).keys())
    by_key: dict[str, dict] = {}

    for item in catalog:
        if not catalog_item_passes_pool(item, opts) and item["bib_key"] not in book_keys:
            continue
        key = item["bib_key"]
        prev = by_key.get(key)
        if prev is None or int(item.get("relevance_score") or 0) > int(
            prev.get("relevance_score") or 0
        ):
            by_key[key] = dict(item)

    pool = sorted(
        by_key.values(),
        key=lambda x: int(x.get("relevance_score") or 0),
        reverse=True,
    )
    pool_path = redistribute_pool_path(spec.chapter_id)
    pool_path.write_text(
        json.dumps(
            {
                "chapter_id": spec.chapter_id,
                "pool_count": len(pool),
                "bib_keys": [p["bib_key"] for p in pool],
                "papers": [
                    {
                        "bib_key": p["bib_key"],
                        "title": p.get("title"),
                        "source_tier": p.get("source_tier"),
                        "relevance_score": p.get("relevance_score"),
                        "matched_keywords": p.get("matched_keywords"),
                    }
                    for p in pool
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return pool


def score_paper_for_sentence(
    item: dict,
    sent: dict,
    chapter_keywords: list[tuple[str, int]],
    *,
    opts: CitationQualityOptions,
) -> tuple[int, list[str]]:
    paper = {
        "title": item.get("title", ""),
        "abstract": item.get("abstract", ""),
        "snippet": item.get("abstract", ""),
    }
    skw = sentence_keywords(sent["text"], chapter_keywords)
    score, matched = analyze_relevance(paper, skw or chapter_keywords)
    if score < opts.min_binding_score:
        return 0, matched
    eff = effective_binding_keywords(matched)
    if len(eff) < opts.min_matched_keywords and not (
        len(eff) >= 1 and score >= 16
    ):
        return 0, matched
    return score, matched


def plan_citation_assignments(
    spec: ChapterSpec,
    pool: list[dict],
    opts: CitationQualityOptions,
) -> list[dict]:
    """Pick one sentence per bib_key — spread cites across sections, skip template blocks."""
    tex = read_chapter_text(spec)
    chapter_keywords = extract_chapter_keywords(spec)
    sentences = [
        s
        for s in extract_content_sentences(tex)
        if s.get("is_claim") and s["section"] not in SKIP_REDISTRIBUTE_SECTIONS
    ]
    if not sentences:
        sentences = [
            s
            for s in extract_content_sentences(tex)
            if s["section"] not in SKIP_REDISTRIBUTE_SECTIONS
        ]

    candidates: list[tuple[int, str, str, str, list[str]]] = []
    for item in pool:
        for sent in sentences:
            score, matched = score_paper_for_sentence(
                item, sent, chapter_keywords, opts=opts
            )
            if score <= 0:
                continue
            candidates.append(
                (score, item["bib_key"], sent["id"], sent["section"], matched)
            )

    candidates.sort(key=lambda row: (-row[0], row[2]))
    assigned_keys: set[str] = set()
    used_sentences: set[str] = set()
    assignments: list[dict] = []

    for score, bib_key, sid, section, matched in candidates:
        if bib_key in assigned_keys or sid in used_sentences:
            continue
        assigned_keys.add(bib_key)
        used_sentences.add(sid)
        assignments.append(
            {
                "sentence_id": sid,
                "bib_key": bib_key,
                "section": section,
                "relevance_score": score,
                "matched_keywords": matched,
            }
        )

    fallback_opts = CitationQualityOptions(
        min_binding_score=max(8, opts.min_binding_score - 4),
        min_matched_keywords=max(1, opts.min_matched_keywords - 1),
        tier_a_only=opts.tier_a_only,
        min_quality_bindings=opts.min_quality_bindings,
    )
    section_index: dict[str, list[dict]] = {}
    for sent in sentences:
        section_index.setdefault(sent["section"], []).append(sent)

    for item in pool:
        key = item["bib_key"]
        if key in assigned_keys:
            continue
        best_sent = None
        best_score = 0
        best_matched: list[str] = []
        for sent in sentences:
            if sent["id"] in used_sentences:
                continue
            score, matched = score_paper_for_sentence(
                item, sent, chapter_keywords, opts=fallback_opts
            )
            if score > best_score:
                best_score = score
                best_sent = sent
                best_matched = matched
        if best_sent is None:
            for sents in section_index.values():
                for sent in sents:
                    if sent["id"] not in used_sentences:
                        best_sent = sent
                        best_score = 1
                        best_matched = item.get("matched_keywords") or []
                        break
                if best_sent:
                    break
        if best_sent is None:
            continue
        assigned_keys.add(key)
        used_sentences.add(best_sent["id"])
        assignments.append(
            {
                "sentence_id": best_sent["id"],
                "bib_key": key,
                "section": best_sent["section"],
                "relevance_score": best_score,
                "matched_keywords": best_matched,
                "fallback": best_score <= 1,
            }
        )

    assignments.sort(key=lambda row: row["sentence_id"])
    return assignments


def apply_planned_citations_to_tex(
    spec: ChapterSpec,
    assignments: list[dict],
    *,
    dry_run: bool = False,
) -> dict:
    path = chapter_tex_path(spec)
    original = path.read_text(encoding="utf-8")
    tex = remove_cite_commands(original)
    binding_by_id = {
        row["sentence_id"]: {
            "sentence_id": row["sentence_id"],
            "bib_key": row["bib_key"],
        }
        for row in assignments
    }

    sid = 0
    applied_total = 0
    parts = re.split(r"(\n\s*\n)", tex)
    new_parts: list[str] = []
    for part in parts:
        if not part.strip() or part.strip().startswith("%") or re.fullmatch(
            r"\s*\n\s*", part
        ):
            new_parts.append(part)
            continue
        new_para, sid, n = apply_bindings_to_paragraph(
            part,
            binding_by_id,
            sid_start=sid,
            merge_existing=False,
            chapter_cited=None,
        )
        applied_total += n
        new_parts.append(new_para)

    new_tex = "".join(new_parts)
    updated = False
    if not dry_run and new_tex != original:
        path.write_text(new_tex, encoding="utf-8")
        updated = True
    return {
        "chapter_id": spec.chapter_id,
        "cites_applied": applied_total,
        "assignments": len(assignments),
        "dry_run": dry_run,
        "updated": updated,
        "tex_path": str(path.relative_to(ROOT)),
    }


def redistribute_citations_to_tex(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    quality: CitationQualityOptions | None = None,
) -> dict:
    opts = quality or CitationQualityOptions(tier_a_only=True)
    pool = consolidate_chapter_citation_pool(spec, opts)
    assignments = plan_citation_assignments(spec, pool, opts)
    apply_report = apply_planned_citations_to_tex(
        spec, assignments, dry_run=dry_run
    )
    sections_used = sorted({a["section"] for a in assignments})
    if dry_run:
        keys_count = len({a["bib_key"] for a in assignments})
    else:
        keys_count = len(collect_cite_keys(chapter_tex_path(spec).read_text(encoding="utf-8")))
    report = {
        "chapter_id": spec.chapter_id,
        "pool_count": len(pool),
        "assigned_count": len(assignments),
        "unassigned_count": max(0, len(pool) - len(assignments)),
        "sections_with_cites": len(sections_used),
        "unique_keys_in_tex": keys_count,
        "pool_path": str(redistribute_pool_path(spec.chapter_id).relative_to(ROOT)),
        "sections_used": sections_used,
        **apply_report,
    }
    if not dry_run:
        redistribute_report_path(spec.chapter_id).write_text(
            json.dumps(
                {
                    **{k: v for k, v in report.items() if k != "assignments"},
                    "assignment_samples": assignments[:12],
                    "generated_at": datetime.now().isoformat(),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return report



def load_bindings(chapter_id: str) -> list[dict]:
    path = bindings_path(chapter_id)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def extract_bib_blocks(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    blocks: dict[str, str] = {}
    entry_starts = list(re.finditer(r"^@\w+\{([^,\s]+),", text, re.MULTILINE))
    for i, m in enumerate(entry_starts):
        key = m.group(1)
        end = entry_starts[i + 1].start() if i + 1 < len(entry_starts) else len(text)
        block = text[m.start() : end].strip()
        blocks[key] = block
    return blocks


def attach_cite_to_sentence(
    raw_sent: str,
    bib_key: str,
    *,
    merge_existing: bool = True,
    chapter_cited: set[str] | None = None,
) -> str:
    if chapter_cited is not None and bib_key in chapter_cited:
        return raw_sent

    cite_re = re.compile(r"\\cite[tp]?\{([^}]+)\}")
    match = cite_re.search(raw_sent)
    if match and merge_existing:
        keys = [k.strip() for k in match.group(1).split(",") if k.strip()]
        if bib_key not in keys:
            if chapter_cited is not None and bib_key in chapter_cited:
                return raw_sent
            keys.append(bib_key)
            if chapter_cited is not None:
                chapter_cited.add(bib_key)
            replacement = f"\\citep{{{','.join(keys)}}}"
            return raw_sent[: match.start()] + replacement + raw_sent[match.end() :]
        return raw_sent
    if match:
        return raw_sent

    if chapter_cited is not None:
        chapter_cited.add(bib_key)

    trimmed = raw_sent.rstrip()
    if trimmed.endswith("."):
        return trimmed[:-1] + f" \\citep{{{bib_key}}}." + raw_sent[len(trimmed) :]
    return trimmed + f" \\citep{{{bib_key}}}" + raw_sent[len(trimmed) :]


def paragraph_skipped_for_apply(para: str) -> bool:
    if any(marker in para for marker in SKIP_APPLY_MARKERS):
        return True
    if re.match(r"^\s*\\(?:chapter|part)\{", para.strip()):
        return True
    return False


def apply_bindings_to_paragraph(
    para: str,
    binding_by_id: dict[str, dict],
    *,
    sid_start: int,
    merge_existing: bool = True,
    chapter_cited: set[str] | None = None,
) -> tuple[str, int, int]:
    """Return (new_para, next_sid, applied_count)."""
    sid = sid_start
    if paragraph_skipped_for_apply(para):
        plain = strip_latex_inline(para)
        if len(plain.split()) >= MIN_SENTENCE_WORDS:
            for _ in re.split(r"(?<=[.!?])\s+", plain):
                sent = _.strip()
                if len(sent.split()) >= MIN_SENTENCE_WORDS:
                    sid += 1
        return para, sid, 0

    plain = strip_latex_inline(para)
    if len(plain.split()) < MIN_SENTENCE_WORDS:
        return para, sid, 0

    plain_sents = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", plain)
        if len(s.strip().split()) >= MIN_SENTENCE_WORDS
    ]
    raw_sents = re.split(r"(?<=[.!?])\s+", para.strip())
    applied = 0

    if len(raw_sents) == len(plain_sents):
        new_parts: list[str] = []
        for raw_sent, _plain in zip(raw_sents, plain_sents):
            sid += 1
            binding = binding_by_id.get(f"s{sid:04d}")
            if binding and "tikzpicture" not in binding.get("sentence", "").lower():
                new_parts.append(
                    attach_cite_to_sentence(
                        raw_sent,
                        binding["bib_key"],
                        merge_existing=merge_existing,
                        chapter_cited=chapter_cited,
                    )
                )
                applied += 1
            else:
                new_parts.append(raw_sent)
        return " ".join(new_parts), sid, applied

    modified = para
    for plain_sent in plain_sents:
        sid += 1
        binding = binding_by_id.get(f"s{sid:04d}")
        if not binding or "tikzpicture" in binding.get("sentence", "").lower():
            continue
        words = [
            w
            for w in re.findall(r"[A-Za-z0-9']+", plain_sent)
            if len(w) >= 4
        ][:6]
        if len(words) < 3:
            continue
        pattern = re.escape(words[0])
        for w in words[1:4]:
            pattern += r"[\s\S]{0,120}?" + re.escape(w)
        match = re.search(pattern, modified, re.IGNORECASE)
        if not match:
            continue
        end = modified.find(".", match.end())
        if end == -1:
            end = len(modified) - 1
        sent_raw = modified[match.start() : end + 1]
        new_sent = attach_cite_to_sentence(
            sent_raw,
            binding["bib_key"],
            merge_existing=merge_existing,
            chapter_cited=chapter_cited,
        )
        modified = modified[: match.start()] + new_sent + modified[end + 1 :]
        applied += 1
    return modified, sid, applied


def apply_citation_bindings_to_tex(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    merge_existing: bool = True,
    quality: CitationQualityOptions | None = None,
    prune_non_tier_a: bool = False,
    dedupe_cites: bool = True,
    dedupe_per_section: bool = False,
) -> dict:
    opts = quality or CitationQualityOptions()
    enrich_catalog_tiers(spec)

    path = chapter_tex_path(spec)
    tex = path.read_text(encoding="utf-8")
    all_bindings = load_bindings(spec.chapter_id)
    catalog = load_catalog(spec.chapter_id)
    tier_map = catalog_tier_map(catalog)
    for b in all_bindings:
        b.setdefault("source_tier", tier_map.get(b.get("bib_key", ""), "C"))
    bindings, rejected = filter_bindings(all_bindings, opts)
    binding_by_id = {b["sentence_id"]: b for b in bindings}

    if prune_non_tier_a:
        prune_report = prune_non_tier_a_cites_from_tex(spec, dry_run=dry_run)
        tex = path.read_text(encoding="utf-8") if not dry_run else tex
    else:
        prune_report = None

    original_tex = tex
    chapter_cited = collect_cite_keys(tex)
    sid = 0
    applied_total = 0
    parts = re.split(r"(\n\s*\n)", tex)
    new_parts: list[str] = []

    for part in parts:
        if not part.strip() or part.strip().startswith("%") or re.fullmatch(
            r"\s*\n\s*", part
        ):
            new_parts.append(part)
            continue
        new_para, sid, n = apply_bindings_to_paragraph(
            part,
            binding_by_id,
            sid_start=sid,
            merge_existing=merge_existing,
            chapter_cited=chapter_cited,
        )
        applied_total += n
        new_parts.append(new_para)

    new_tex = "".join(new_parts)
    apply_changed = new_tex != original_tex
    if not dry_run and apply_changed:
        path.write_text(new_tex, encoding="utf-8")
        tex = new_tex

    dedupe_report = None
    if dedupe_cites and not dry_run:
        dedupe_report = dedupe_chapter_citations_tex(
            spec,
            dry_run=False,
            per_section=dedupe_per_section,
        )
    report = {
        "chapter_id": spec.chapter_id,
        "bindings_loaded": len(all_bindings),
        "bindings_quality": len(bindings),
        "bindings_rejected": len(rejected),
        "cites_applied": applied_total,
        "dry_run": dry_run,
        "tex_path": str(path.relative_to(ROOT)),
        "quality": {
            "min_binding_score": opts.min_binding_score,
            "min_matched_keywords": opts.min_matched_keywords,
            "tier_a_only": opts.tier_a_only,
        },
    }
    if prune_report:
        report["prune"] = prune_report
    if dedupe_report:
        report["dedupe"] = dedupe_report
    report["updated"] = apply_changed or bool(
        dedupe_report and dedupe_report.get("updated")
    )
    if dry_run:
        report["updated"] = new_tex != original_tex
    return report


def merge_all_chapter_bibs(
    output_path: Path = MERGED_BIB_PATH,
    *,
    include_book_bib: bool = False,
    tier_a_only: bool = False,
) -> dict:
    merged: dict[str, str] = {}
    sources: dict[str, str] = {}
    tier_skipped = 0
    book_keys = set(parse_bib_entries(BIB_PATH).keys()) if BIB_PATH.exists() else set()

    if include_book_bib and BIB_PATH.exists():
        for key, block in extract_bib_blocks(BIB_PATH).items():
            merged[key] = sanitize_bib_block(block)
            sources[key] = "book.bib"

    for spec in OUTLINE:
        cat_file = catalog_path(spec.chapter_id)
        tier_map: dict[str, str] = {}
        if cat_file.exists():
            for item in load_catalog(spec.chapter_id):
                tier_map[item["bib_key"]] = item.get("source_tier", "B")
        bib_file = chapter_bib_path(spec.chapter_id)
        if not bib_file.exists():
            continue
        for key, block in extract_bib_blocks(bib_file).items():
            if key in book_keys and not include_book_bib:
                continue
            if tier_a_only and tier_map.get(key, "B") != "A" and key not in merged:
                tier_skipped += 1
                continue
            clean = sanitize_bib_block(block)
            if key not in merged:
                merged[key] = clean
                sources[key] = f"{spec.chapter_id}/chapter.bib"

    header = (
        "% Auto-generated by citation-loop merge-bib — do not edit by hand.\n"
        f"% {datetime.now().isoformat()} — {len(merged)} entries\n\n"
    )
    body = "\n\n".join(merged[k] for k in sorted(merged.keys()))
    output_path.write_text(header + body + "\n", encoding="utf-8")

    return {
        "output": str(output_path.relative_to(ROOT)),
        "entry_count": len(merged),
        "book_bib_count": sum(1 for s in sources.values() if s == "book.bib"),
        "chapter_only_count": sum(1 for s in sources.values() if s != "book.bib"),
        "tier_skipped": tier_skipped,
        "tier_a_only": tier_a_only,
    }


def verify_cites_in_merged_bib(spec: ChapterSpec) -> dict:
    tex = read_chapter_text(spec)
    from research_tools import extract_cite_keys

    keys = extract_cite_keys(tex)
    merged = set(extract_bib_blocks(MERGED_BIB_PATH).keys())
    book = set(extract_bib_blocks(BIB_PATH).keys())
    available = merged | book
    missing = [k for k in keys if k not in available]
    return {
        "chapter_id": spec.chapter_id,
        "cite_keys_in_tex": len(keys),
        "missing_keys": missing,
        "status": "pass" if not missing else "fail",
    }


def rebuild_chapter_bib_from_catalog(spec: ChapterSpec) -> int:
    cat_file = catalog_path(spec.chapter_id)
    if not cat_file.exists():
        return 0
    papers = json.loads(cat_file.read_text(encoding="utf-8")).get("papers", [])
    if not papers:
        return 0
    catalog: list[dict] = []
    for item in papers:
        catalog.append(
            {
                "bib_key": item["bib_key"],
                "title": item.get("title"),
                "abstract": item.get("abstract"),
                "link": item.get("link"),
                "year": item.get("year"),
                "paper": {
                    "title": item.get("title"),
                    "abstract": item.get("abstract"),
                    "link": item.get("link"),
                    "year": item.get("year"),
                    "publication_info": {"authors": []},
                },
            }
        )
    write_chapter_bib(spec.chapter_id, catalog)
    return len(catalog)


def citation_strict_tasks(chapter_id: str) -> list[str]:
    path = strict_report_path(chapter_id)
    if not path.exists():
        return [f"Citation loop: run citation-loop plan --chapter {chapter_id}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    tasks: list[str] = []
    for issue in data.get("issues", []):
        tasks.append(f"Citation strict: {issue}")
    for b in data.get("weak_bindings", [])[:5]:
        tasks.append(
            f"Citation binding weak `{b.get('bib_key')}` score={b.get('relevance_score')}"
        )
    if data.get("status") == "pass":
        tasks.append(
            f"Citation loop PASS {chapter_id}: "
            f"{data.get('catalog_count')} papers, {data.get('binding_count')} bindings"
        )
    return tasks


def resolve_specs(chapter_id: str | None) -> tuple[ChapterSpec, ...]:
    if chapter_id:
        specs = tuple(s for s in OUTLINE if s.chapter_id == chapter_id)
        if not specs:
            print(f"Unknown chapter: {chapter_id}", file=sys.stderr)
            sys.exit(1)
        return specs
    return OUTLINE


def main() -> int:
    parser = argparse.ArgumentParser(description="Citation catalog + strict loop")
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--chapter")
    plan_p.add_argument("--all", action="store_true")
    plan_p.add_argument("--dry-run", action="store_true")
    plan_p.add_argument("--min-papers", type=int, default=MIN_CHAPTER_PAPERS)
    plan_p.add_argument("--crossref-only", action="store_true")
    add_quality_cli_args(plan_p)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--chapter")
    verify_p.add_argument("--all", action="store_true")
    verify_p.add_argument("--min-papers", type=int, default=MIN_CHAPTER_PAPERS)
    add_quality_cli_args(verify_p)

    loop_p = sub.add_parser("loop")
    loop_p.add_argument("--chapter")
    loop_p.add_argument("--all", action="store_true")
    loop_p.add_argument("--dry-run", action="store_true")
    loop_p.add_argument("--min-papers", type=int, default=MIN_CHAPTER_PAPERS)
    loop_p.add_argument("--crossref-only", action="store_true")
    loop_p.add_argument(
        "--apply-tex",
        action="store_true",
        help="After verify pass, write \\citep bindings into chapter .tex",
    )
    loop_p.add_argument(
        "--merge-bib",
        action="store_true",
        help="After loop, merge all chapter.bib into citations_merged.bib",
    )
    add_quality_cli_args(loop_p)

    apply_p = sub.add_parser("apply", help="Write citation_bindings into chapter .tex")
    apply_p.add_argument("--chapter")
    apply_p.add_argument("--all", action="store_true")
    apply_p.add_argument("--dry-run", action="store_true")
    apply_p.add_argument(
        "--no-merge-existing",
        action="store_true",
        help="Do not append to existing \\citep keys",
    )
    add_quality_cli_args(apply_p)
    apply_p.add_argument(
        "--prune-non-tier-a",
        action="store_true",
        help="Strip Tier-B/C keys before applying quality bindings",
    )
    apply_p.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not remove duplicate cite keys within the chapter after apply",
    )
    apply_p.add_argument(
        "--dedupe-per-section",
        action="store_true",
        help="Reset dedupe tracking at each \\section/\\chapter (default: whole chapter)",
    )

    dedupe_p = sub.add_parser(
        "dedupe-cites",
        help="Keep each bib key at its first \\citep/\\citet in a chapter; strip repeats",
    )
    dedupe_p.add_argument("--chapter")
    dedupe_p.add_argument("--all", action="store_true")
    dedupe_p.add_argument("--dry-run", action="store_true")
    dedupe_p.add_argument(
        "--per-section",
        action="store_true",
        help="Allow the same key once per \\section instead of once per chapter",
    )


    redist_p = sub.add_parser(
        "redistribute-cites",
        help="Consolidate Tier-A catalog pool, dedupe keys, assign one cite per paper",
    )
    redist_p.add_argument("--chapter")
    redist_p.add_argument("--all", action="store_true")
    redist_p.add_argument("--dry-run", action="store_true")
    add_quality_cli_args(redist_p)

    merge_p = sub.add_parser(
        "merge-bib", help="Merge book.bib + all chapter.bib → citations_merged.bib"
    )
    add_quality_cli_args(merge_p)

    enrich_p = sub.add_parser(
        "enrich-tiers", help="Add source_tier (A/B/C) to citation_catalog.json"
    )
    enrich_p.add_argument("--chapter")
    enrich_p.add_argument("--all", action="store_true")

    refilter_p = sub.add_parser(
        "refilter",
        help="Re-bind sentences with quality thresholds; rewrite citation_bindings.jsonl",
    )
    refilter_p.add_argument("--chapter")
    refilter_p.add_argument("--all", action="store_true")
    add_quality_cli_args(refilter_p)

    prune_p = sub.add_parser(
        "prune",
        help="Remove Tier-B/C cite keys from chapter .tex (keep book.bib keys)",
    )
    prune_p.add_argument("--chapter")
    prune_p.add_argument("--all", action="store_true")
    prune_p.add_argument("--dry-run", action="store_true")

    rebuild_p = sub.add_parser(
        "rebuild-bib",
        help="Regenerate chapter.bib from citation_catalog.json (sanitize entries)",
    )
    rebuild_p.add_argument("--chapter")
    rebuild_p.add_argument("--all", action="store_true")

    args = parser.parse_args()

    if args.command == "merge-bib":
        m = merge_all_chapter_bibs(
            tier_a_only=getattr(args, "tier_a_only", False),
        )
        print(
            f"Wrote {m['entry_count']} entries "
            f"(book={m['book_bib_count']} chapter-only={m['chapter_only_count']}"
            f"{', tier_skipped=' + str(m['tier_skipped']) if m.get('tier_a_only') else ''}) "
            f"-> {m['output']}"
        )
        return 0

    if args.command == "enrich-tiers":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        for spec in specs:
            r = enrich_catalog_tiers(spec)
            print(
                f"{spec.chapter_id}: tiers {r.get('tier_counts', {})} "
                f"({r.get('updated', 0)} papers)"
            )
        return 0

    if args.command == "refilter":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        opts = quality_opts_from_args(args)
        for spec in specs:
            r = refilter_chapter_bindings(spec, opts)
            print(
                f"{spec.chapter_id}: bindings {r['bindings_before']} -> "
                f"{r['bindings_after']} tier_a_only={opts.tier_a_only}"
            )
        return 0

    if args.command == "prune":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        for spec in specs:
            r = prune_non_tier_a_cites_from_tex(spec, dry_run=getattr(args, "dry_run", False))
            print(
                f"{spec.chapter_id}: pruned {r['cite_key_removals']} cite keys "
                f"from {r['keys_pruned']} tier-B/C entries updated={r['updated']}"
            )
        return 0

    if args.command == "rebuild-bib":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        for spec in specs:
            n = rebuild_chapter_bib_from_catalog(spec)
            print(f"{spec.chapter_id}: rebuilt {n} entries")
        return 0


    if args.command == "redistribute-cites":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        opts = quality_opts_from_args(args)
        for spec in specs:
            r = redistribute_citations_to_tex(
                spec,
                dry_run=getattr(args, "dry_run", False),
                quality=opts,
            )
            print(
                f"{spec.chapter_id}: pool={r['pool_count']} assigned={r['assigned_count']} "
                f"sections={r['sections_with_cites']} keys_in_tex={r['unique_keys_in_tex']} "
                f"updated={r['updated']}"
            )
        return 0

    if args.command == "dedupe-cites":
        if not getattr(args, "chapter", None) and not getattr(args, "all", False):
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = resolve_specs(args.chapter if not args.all else None)
        for spec in specs:
            r = dedupe_chapter_citations_tex(
                spec,
                dry_run=getattr(args, "dry_run", False),
                per_section=getattr(args, "per_section", False),
            )
            print(
                f"{spec.chapter_id}: groups {r['cite_groups_before']} -> "
                f"{r['cite_groups_after']} keys_suppressed={r['keys_suppressed']} "
                f"groups_removed={r['groups_removed']} updated={r['updated']}"
            )
        return 0

    if not getattr(args, "chapter", None) and not getattr(args, "all", False):
        print("Specify --chapter or --all", file=sys.stderr)
        return 1

    specs = resolve_specs(args.chapter if not args.all else None)

    if args.command == "plan":
        opts = quality_opts_from_args(args)
        for spec in specs:
            r = run_chapter_citation_plan(
                spec,
                dry_run=args.dry_run,
                min_papers=args.min_papers,
                crossref_only=getattr(args, "crossref_only", False),
                quality=opts,
            )
            print(
                f"{spec.chapter_id}: papers={r['paper_count']} "
                f"bindings={r['binding_count']} min_ok={r['meets_min_papers']}"
            )
        return 0

    if args.command == "verify":
        opts = quality_opts_from_args(args)
        fails = 0
        for spec in specs:
            report = strict_verify_chapter_citations(
                spec, min_papers=args.min_papers, quality=opts
            )
            rel = strict_report_path(spec.chapter_id).relative_to(ROOT)
            print(
                f"{spec.chapter_id}: {report['status']} catalog={report['catalog_count']} "
                f"bindings={report['binding_count']} -> {rel}"
            )
            if report["status"] != "pass":
                fails += 1
        return 1 if fails else 0

    if args.command == "loop":
        opts = quality_opts_from_args(args)
        for spec in specs:
            run_chapter_citation_plan(
                spec,
                dry_run=args.dry_run,
                min_papers=args.min_papers,
                crossref_only=getattr(args, "crossref_only", False),
                quality=opts,
            )
        fails = 0
        for spec in specs:
            report = strict_verify_chapter_citations(
                spec, min_papers=args.min_papers, quality=opts
            )
            print(
                f"{spec.chapter_id}: {report['status']} papers={report['catalog_count']} "
                f"bindings={report['binding_count']}"
            )
            if report["status"] != "pass":
                fails += 1
        if fails:
            return 1
        if getattr(args, "apply_tex", False):
            for spec in specs:
                r = apply_citation_bindings_to_tex(
                    spec,
                    quality=opts,
                    prune_non_tier_a=getattr(args, "prune_non_tier_a", False)
                    or opts.tier_a_only,
                )
                ded = r.get("dedupe") or {}
                print(
                    f"{spec.chapter_id}: applied {r['cites_applied']} cites "
                    f"updated={r['updated']}"
                    + (
                        f" deduped groups {ded.get('cite_groups_before')}->{ded.get('cite_groups_after')}"
                        if ded
                        else ""
                    )
                )
        if getattr(args, "merge_bib", False):
            m = merge_all_chapter_bibs(tier_a_only=opts.tier_a_only)
            print(f"merged {m['entry_count']} entries -> {m['output']}")
        return 0

    if args.command == "apply":
        opts = quality_opts_from_args(args)
        for spec in specs:
            r = apply_citation_bindings_to_tex(
                spec,
                dry_run=args.dry_run,
                merge_existing=not args.no_merge_existing,
                quality=opts,
                prune_non_tier_a=getattr(args, "prune_non_tier_a", False)
                or opts.tier_a_only,
                dedupe_cites=not getattr(args, "no_dedupe", False),
                dedupe_per_section=getattr(args, "dedupe_per_section", False),
            )
            ded = r.get("dedupe") or {}
            print(
                f"{spec.chapter_id}: loaded={r['bindings_loaded']} "
                f"quality={r['bindings_quality']} rejected={r['bindings_rejected']} "
                f"applied={r['cites_applied']} updated={r['updated']}"
                + (
                    f" dedupe_groups={ded.get('cite_groups_before')}->{ded.get('cite_groups_after')}"
                    if ded
                    else ""
                )
            )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
