#!/usr/bin/env python3
"""
Per-chapter literature research for autobooks.

Keywords are derived automatically from:
  - book_prepare.OUTLINE (title, section labels, coverage patterns)
  - Chinese outline markdown (chapter bullets)
  - Existing chapter .tex (section titles, index/newterm, body terms)

Results are saved under books/research/<chapter_id>/ with no hard cap on paper count.

Usage:
    uv run research_tools.py --chapter ch01
    uv run research_tools.py --all
    uv run research_tools.py --chapter ch01 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from book_prepare import OUTLINE, ChapterSpec

ROOT = Path(__file__).resolve().parent
BOOKS = ROOT / "books"
CHAPTERS = BOOKS / "chapters"
RESEARCH_ROOT = BOOKS / "research"
OUTLINE_MD = ROOT / "AI Compiler Performance Engineering.md"

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "research@autobooks.local")
SCHOLAR_PAGE_SIZE = 20
SCHOLAR_YEAR_LO = 2018

CHAPTER_SEEDS: dict[str, list[tuple[str, int]]] = {
    "ch01": [
        ("LLM inference prefill decode", 18),
        ("single token decode latency", 16),
        ("kernel launch overhead GPU", 15),
        ("PyTorch Hugging Face inference", 14),
        ("memory bandwidth bound decode", 15),
        ("PagedAttention vLLM", 14),
        ("FlashAttention Flash-Decoding", 14),
        ("KV cache optimization", 13),
        ("operator fusion megakernel", 14),
        ("CUDA graphs inference", 12),
        ("cross-hardware LLM serving", 12),
        ("YiRage compiler", 10),
    ],
    "ch02": [
        ("operator-driven kernel design", 16),
        ("dataflow-driven optimization", 16),
        ("data residency on-chip", 15),
        ("static pipeline dataflow", 14),
        ("XDNA AIE dataflow accelerator", 14),
        ("CUDA memory hierarchy optimization", 13),
        ("register shared memory global", 12),
        ("megakernel fusion LLM", 15),
        ("compiler automated kernel fusion", 13),
    ],
    "ch03": [
        ("AI hardware architecture GPU CPU NPU", 16),
        ("memory hierarchy bandwidth roofline", 15),
        ("warp scheduling shared memory tensor core", 14),
        ("CPU cache SIMD NUMA", 13),
        ("edge NPU static scheduling", 13),
        ("hardware-aware tiling compiler", 14),
        ("cross-platform code generation MLIR", 13),
        ("benchmark methodology LLM inference", 12),
        ("chip architecture modeling compiler", 12),
    ],
}

STOPWORDS = frozenset(
    """
    the a an and or for with from into over under between among through during
    before after above below this that these those such other than when where
    while also only both each more most very much many some any all not but
    are was were been being have has had does did doing would could should
    about across within without using used use make made making like just
    chapter section label file text will can may must one two new term
    """.split()
)


def _require_serpapi_key() -> str:
    if not SERPAPI_KEY:
        print(
            "SERPAPI_KEY is not set. Export it before running:\n"
            "  export SERPAPI_KEY='your-key'",
            file=sys.stderr,
        )
        sys.exit(1)
    return SERPAPI_KEY


def search_google_scholar_page(
    query: str,
    *,
    num_results: int = SCHOLAR_PAGE_SIZE,
    start: int = 0,
    year_hi: int | None = None,
) -> list[dict]:
    api_key = _require_serpapi_key()
    year_hi = year_hi or datetime.now().year

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": num_results,
        "start": start,
        "as_ylo": SCHOLAR_YEAR_LO,
        "as_yhi": year_hi,
        "hl": "en",
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        print(f"  API error for query '{query}' (start={start}): {exc}")
        return []

    organic = payload.get("organic_results", [])
    if not organic:
        return []

    enhanced: list[dict] = []
    for i, paper in enumerate(organic):
        title = paper.get("title", "No title")
        print(f"  [{start + i + 1}] {title[:70]}...")
        enhanced.append(enhance_paper_with_abstract(paper))
        time.sleep(0.8)
    return enhanced


def search_google_scholar(
    query: str,
    *,
    page_size: int = SCHOLAR_PAGE_SIZE,
    max_pages: int | None = None,
    query_delay_s: float = 2.0,
) -> list[dict]:
    print(f"\nSearching: {query}")
    all_results: list[dict] = []
    start = 0
    page = 0

    while True:
        if max_pages is not None and page >= max_pages:
            break

        batch = search_google_scholar_page(query, num_results=page_size, start=start)
        if not batch:
            break

        all_results.extend(batch)
        if len(batch) < page_size:
            break

        start += page_size
        page += 1
        time.sleep(query_delay_s)

    print(f"  -> {len(all_results)} papers from this query")
    return all_results


def enhance_paper_with_abstract(paper: dict) -> dict:
    snippet = paper.get("snippet", "")
    link = paper.get("link", "")
    title = paper.get("title", "")
    authors = extract_authors_from_paper(paper)

    better_abstract = fetch_abstract_via_crossref(title, authors)
    if not better_abstract and link:
        better_abstract = fetch_abstract_via_serpapi(title, link)

    if better_abstract:
        paper["original_snippet"] = snippet
        paper["abstract"] = better_abstract
        paper["snippet"] = better_abstract
    else:
        paper["abstract"] = snippet

    return paper


def extract_authors_from_paper(paper: dict) -> list:
    pub_info = paper.get("publication_info", {})
    authors = pub_info.get("authors", [])

    if not authors and "summary" in pub_info:
        summary = pub_info["summary"]
        parts = summary.split("-")
        if parts:
            potential_authors = parts[0].strip()
            author_list = re.split(r",|\u2026", potential_authors)
            authors = [a.strip() for a in author_list if a.strip()]

    return authors


def fetch_abstract_via_crossref(title: str, authors: list) -> str | None:
    first_author = ""
    if authors:
        if isinstance(authors[0], dict) and "name" in authors[0]:
            first_author = authors[0]["name"]
        elif isinstance(authors[0], str):
            first_author = authors[0]
        if " " in first_author:
            first_author = first_author.split()[-1]

    params = {
        "query": f"{first_author} {title}".strip(),
        "rows": 3,
        "mailto": CROSSREF_EMAIL,
    }

    try:
        response = requests.get("https://api.crossref.org/works", params=params, timeout=30)
        data = response.json()
        items = data.get("message", {}).get("items", [])
        for item in items:
            if "abstract" in item:
                return BeautifulSoup(item["abstract"], "html.parser").get_text()
    except Exception as exc:
        print(f"    Crossref error: {exc}")

    return None


def fetch_abstract_via_serpapi(title: str, url: str) -> str | None:
    api_key = _require_serpapi_key()
    query = f"{title} abstract"
    if url:
        domain = url.split("//")[1].split("/")[0]
        query += f" site:{domain}"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 3,
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=30)
        data = response.json()
        for result in data.get("organic_results", []):
            snippet = result.get("snippet", "")
            if len(snippet) > 200:
                return snippet
    except Exception as exc:
        print(f"    SerpAPI abstract error: {exc}")

    return None


def format_reference(paper: dict) -> str:
    title = paper.get("title", "")
    authors = paper.get("publication_info", {}).get("authors", [])
    if not authors and "authors" in paper:
        authors = paper["authors"]

    author_names: list[str] = []
    for author in authors:
        if isinstance(author, dict) and "name" in author:
            author_names.append(author["name"])
        elif isinstance(author, str):
            author_names.append(author)

    if len(author_names) > 3:
        authors_str = f"{author_names[0]}, {author_names[1]}, et al."
    else:
        authors_str = ", ".join(author_names)

    year = ""
    pub_info = paper.get("publication_info", {})
    if "summary" in pub_info:
        year_match = re.search(r"20\d{2}", pub_info["summary"])
        if year_match:
            year = year_match.group(0)
    if not year and "year" in paper:
        year = str(paper["year"])
    if not year:
        year = str(datetime.now().year)

    venue = ""
    if "venue" in paper:
        venue = paper["venue"]
    elif "publisher" in pub_info:
        venue = pub_info["publisher"]
    elif "summary" in pub_info:
        venue = pub_info["summary"].split(",")[0]

    link = paper.get("link", "")
    reference = f"{authors_str} ({year}). {title}. "
    if venue:
        reference += f"{venue}. "
    if link:
        reference += f"Retrieved from {link}"
    return reference


def analyze_relevance(paper: dict, keywords: list[tuple[str, int]]) -> tuple[int, list[str]]:
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", paper.get("snippet", "")).lower()

    score = 0
    matched: list[str] = []

    for keyword, weight in keywords:
        kw = keyword.lower()
        if kw in title:
            score += weight * 2
            matched.append(keyword)
        elif kw in abstract:
            score += weight
            matched.append(keyword)

    return score, matched


def chapter_number(chapter_id: str) -> int:
    match = re.search(r"(\d+)", chapter_id)
    return int(match.group(1)) if match else 0


def humanize_pattern(pattern: str) -> str:
    text = pattern.replace(r"\s*", " ")
    text = re.sub(r"\.?\?", " ", text)
    text = text.replace("|", " ")
    text = re.sub(r"[\\^$()\[\]]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_outline_bullets(chapter_num: int) -> list[str]:
    if not OUTLINE_MD.exists():
        return []

    text = OUTLINE_MD.read_text(encoding="utf-8")
    block_match = re.search(
        rf"####\s*第{chapter_num}章.*?\n(.*?)(?=\n####|\n### |\Z)",
        text,
        flags=re.DOTALL,
    )
    if not block_match:
        return []

    bullets: list[str] = []
    for line in block_match.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def extract_english_terms_from_text(text: str) -> list[str]:
    terms: list[str] = []

    for match in re.finditer(
        r"\\(?:section|subsection)\{([^}]+)\}", text, flags=re.IGNORECASE
    ):
        terms.append(match.group(1))

    for match in re.finditer(r"\\(?:index|newterm)\{([^}]+)\}", text):
        terms.append(match.group(1))

    for match in re.finditer(
        r"\b(?:LLM|GPU|CPU|NPU|CUDA|HIP|MLIR|TVM|Triton|XLA|KV|HBM|"
        r"PyTorch|FlashAttention|vLLM|MegaKernel|YiRage|XDNA|AIE|"
        r"GEMM|SIMD|NUMA|Warp|tensor core|PagedAttention)\b",
        text,
        flags=re.IGNORECASE,
    ):
        terms.append(match.group(0))

    cleaned = re.sub(r"\\[a-zA-Z@]+(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    cleaned = re.sub(r"%.*", " ", cleaned)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'\-]{2,}", cleaned)
    freq = Counter(t.lower() for t in tokens if t.lower() not in STOPWORDS)

    for token, count in freq.most_common(30):
        if count >= 2 and len(token) >= 4:
            terms.append(token)

    return terms


def extract_chapter_keywords(spec: ChapterSpec) -> list[tuple[str, int]]:
    weighted: dict[str, int] = {}

    def add(term: str, weight: int) -> None:
        term = re.sub(r"\s+", " ", term.strip())
        if len(term) < 3:
            return
        key = term.lower()
        weighted[key] = max(weighted.get(key, 0), weight)

    add(spec.title, 18)

    for section in spec.sections:
        add(section.label.replace("_", " "), 14)
        for pat in section.patterns:
            add(humanize_pattern(pat), 10)

    for term, weight in CHAPTER_SEEDS.get(spec.chapter_id, []):
        add(term, weight)

    ch_num = chapter_number(spec.chapter_id)
    for bullet in extract_outline_bullets(ch_num):
        for eng in re.findall(
            r"[A-Za-z][A-Za-z0-9./+\-]{1,}(?:\s+[A-Za-z][A-Za-z0-9./+\-]{1,})*",
            bullet,
        ):
            add(eng, 11)
        for zh_term, en_term in (
            ("Prefill", "prefill decode LLM"),
            ("Decode", "decode latency LLM"),
            ("Kernel Launch", "kernel launch overhead"),
            ("PyTorch", "PyTorch inference optimization"),
            ("HuggingFace", "Hugging Face transformers inference"),
            ("算子", "operator fusion kernel"),
            ("数据流", "dataflow kernel optimization"),
            ("编译", "AI compiler optimization"),
            ("硬件", "AI hardware architecture"),
            ("带宽", "memory bandwidth"),
            ("融合", "kernel fusion megakernel"),
        ):
            if zh_term in bullet:
                add(en_term, 12)

    tex_path = CHAPTERS / spec.filename
    if tex_path.exists():
        tex = tex_path.read_text(encoding="utf-8")
        for term in extract_english_terms_from_text(tex):
            add(term, 9)

    return sorted(
        ((term, weight) for term, weight in weighted.items()),
        key=lambda item: (-item[1], item[0]),
    )


def generate_chapter_queries(
    spec: ChapterSpec,
    keywords: list[tuple[str, int]],
) -> list[str]:
    top_terms = [k for k, _ in keywords[:16]]
    queries: list[str] = [f'"{spec.title}"']

    for section in spec.sections:
        patterns = [humanize_pattern(p) for p in section.patterns if humanize_pattern(p)]
        if len(patterns) >= 2:
            queries.append(f'"{patterns[0]}" AND "{patterns[1]}"')
        elif patterns:
            queries.append(f'"{patterns[0]}" LLM inference optimization')

    for i in range(0, len(top_terms) - 1, 2):
        queries.append(f'"{top_terms[i]}" AND "{top_terms[i + 1]}"')

    for seed, _ in CHAPTER_SEEDS.get(spec.chapter_id, [])[:6]:
        queries.append(f'"{seed}"')

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        q_norm = q.strip().lower()
        if q_norm and q_norm not in seen:
            seen.add(q_norm)
            unique.append(q.strip())

    return unique


def dedupe_papers(papers: list[dict]) -> list[dict]:
    unique: list[dict] = []
    seen: set[str] = set()

    for paper in papers:
        title = paper.get("title", "").strip()
        if not title:
            continue
        key = re.sub(r"\s+", " ", title.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)

    return unique


def categorize_by_sections(
    analyzed_papers: list[tuple[dict, int, list[str]]],
    spec: ChapterSpec,
    timestamp: str,
) -> str:
    categories = {section.label: [] for section in spec.sections}

    for paper, score, matched in analyzed_papers:
        content = (
            paper.get("title", "")
            + " "
            + paper.get("abstract", paper.get("snippet", ""))
        ).lower()

        for section in spec.sections:
            if all(re.search(pat, content) for pat in section.patterns):
                categories[section.label].append((paper, score, matched))

    md = f"# Section-Categorized References — {spec.chapter_id}\n\n"
    md += f"**Generated on:** {timestamp}\n\n"

    for label, papers in categories.items():
        if not papers:
            continue
        md += f"## {label}\n\n"
        for i, (paper, score, _) in enumerate(
            sorted(papers, key=lambda x: x[1], reverse=True), 1
        ):
            md += f"{i}. {format_reference(paper)} (score={score})\n\n"

    return md


def generate_detailed_markdown(
    spec: ChapterSpec,
    analyzed_papers: list[tuple[dict, int, list[str]]],
    keywords: list[tuple[str, int]],
    search_queries: list[str],
    timestamp: str,
) -> str:
    md = f"# Literature Search — {spec.chapter_id}: {spec.title}\n\n"
    md += "## Search Information\n\n"
    md += f"**Date:** {timestamp}\n\n"
    md += f"**Papers (no cap):** {len(analyzed_papers)}\n\n"
    md += "**Queries:**\n\n"
    for query in search_queries:
        md += f"- {query}\n"

    md += "\n**Locked keywords:**\n\n"
    for keyword, weight in keywords:
        md += f"- {keyword} (weight={weight})\n"

    md += "\n## Papers (by relevance)\n\n"
    for i, (paper, score, matched_keywords) in enumerate(analyzed_papers, 1):
        md += f"### {i}. {paper.get('title', 'No Title')}\n\n"
        md += f"**Reference:** {format_reference(paper)}\n\n"
        md += f"**Relevance score:** {score}\n\n"
        md += f"**Matched keywords:** {', '.join(matched_keywords) or '—'}\n\n"
        abstract = paper.get("abstract", paper.get("snippet", "No abstract available"))
        md += f"**Abstract:** {abstract}\n\n"
        if link := paper.get("link"):
            md += f"**Link:** [{link}]({link})\n\n"
        if cited := paper.get("cited_by", {}).get("value"):
            md += f"**Cited by:** {cited}\n\n"
        md += "---\n\n"

    return md


def generate_reference_markdown(
    spec: ChapterSpec,
    analyzed_papers: list[tuple[dict, int, list[str]]],
    timestamp: str,
) -> str:
    md = f"# References — {spec.chapter_id}: {spec.title}\n\n"
    md += f"**Generated on:** {timestamp}\n\n"
    for i, (paper, _, _) in enumerate(analyzed_papers, 1):
        md += f"{i}. {format_reference(paper)}\n\n"
    return md


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Saved {path}")


def run_chapter_research(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    min_relevance: int = 1,
    max_pages_per_query: int | None = None,
    query_delay_s: float = 2.0,
) -> dict:
    formatted_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = RESEARCH_ROOT / spec.chapter_id
    run_dir = out_dir / "runs" / run_ts

    print(f"\n{'=' * 60}")
    print(f"Chapter: {spec.chapter_id} — {spec.title}")
    print(f"Output:  {out_dir}")

    keywords = extract_chapter_keywords(spec)
    queries = generate_chapter_queries(spec, keywords)

    print(f"\nLocked {len(keywords)} keywords, {len(queries)} queries")
    for kw, w in keywords[:12]:
        print(f"  [{w:2d}] {kw}")
    if len(keywords) > 12:
        print(f"  ... and {len(keywords) - 12} more")

    if dry_run:
        print("\n[dry-run] Skipping API calls.")
        return {
            "chapter": spec.chapter_id,
            "keywords": keywords,
            "queries": queries,
            "paper_count": 0,
            "dry_run": True,
        }

    raw_papers: list[dict] = []
    for query in queries:
        raw_papers.extend(
            search_google_scholar(
                query,
                max_pages=max_pages_per_query,
                query_delay_s=query_delay_s,
            )
        )
        time.sleep(query_delay_s)

    unique_papers = dedupe_papers(raw_papers)
    analyzed: list[tuple[dict, int, list[str]]] = []

    for paper in unique_papers:
        score, matched = analyze_relevance(paper, keywords)
        if score >= min_relevance:
            analyzed.append((paper, score, matched))

    analyzed.sort(key=lambda item: item[1], reverse=True)

    print(f"\n=== {spec.chapter_id}: {len(analyzed)} relevant papers (no upper limit) ===")

    payload = {
        "timestamp": formatted_ts,
        "chapter_id": spec.chapter_id,
        "chapter_title": spec.title,
        "keywords": [{"term": k, "weight": w} for k, w in keywords],
        "search_queries": queries,
        "paper_count": len(analyzed),
        "papers": [
            {
                "title": p.get("title"),
                "link": p.get("link"),
                "relevance_score": score,
                "matched_keywords": matched,
                "reference": format_reference(p),
                "abstract": p.get("abstract", p.get("snippet", "")),
                "raw": p,
            }
            for p, score, matched in analyzed
        ],
    }

    detailed_md = generate_detailed_markdown(
        spec, analyzed, keywords, queries, formatted_ts
    )
    refs_md = generate_reference_markdown(spec, analyzed, formatted_ts)
    section_md = categorize_by_sections(analyzed, spec, formatted_ts)

    for target in (run_dir, out_dir):
        save_text(target / "keywords.json", json.dumps(payload["keywords"], indent=2))
        save_text(target / "queries.json", json.dumps(queries, indent=2))
        save_text(target / "search_results.md", detailed_md)
        save_text(target / "references.md", refs_md)
        save_text(target / "section_references.md", section_md)
        save_text(
            target / "search_data.json",
            json.dumps(payload, indent=2, ensure_ascii=False),
        )

    return {
        "chapter": spec.chapter_id,
        "keywords": keywords,
        "queries": queries,
        "paper_count": len(analyzed),
        "output_dir": str(out_dir),
    }


def resolve_specs(chapter_id: str | None) -> tuple[ChapterSpec, ...]:
    if chapter_id:
        specs = tuple(s for s in OUTLINE if s.chapter_id == chapter_id)
        if not specs:
            print(f"Unknown chapter: {chapter_id}", file=sys.stderr)
            sys.exit(1)
        return specs
    return OUTLINE


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-chapter literature research for autobooks (keywords auto-locked from chapter content)."
    )
    parser.add_argument("--chapter", help="Chapter id, e.g. ch01")
    parser.add_argument("--all", action="store_true", help="Research all chapters in OUTLINE")
    parser.add_argument("--dry-run", action="store_true", help="Extract keywords/queries only")
    parser.add_argument(
        "--min-relevance",
        type=int,
        default=1,
        help="Minimum relevance score to keep a paper (default: 1)",
    )
    parser.add_argument(
        "--max-pages-per-query",
        type=int,
        default=None,
        help="Optional Scholar page limit per query (default: unlimited until empty page)",
    )
    parser.add_argument(
        "--query-delay",
        type=float,
        default=2.0,
        help="Seconds between paginated query requests",
    )
    args = parser.parse_args()

    if not args.chapter and not args.all:
        parser.error("Specify --chapter <id> or --all")

    specs = resolve_specs(args.chapter if not args.all else None)
    results = []

    for spec in specs:
        result = run_chapter_research(
            spec,
            dry_run=args.dry_run,
            min_relevance=args.min_relevance,
            max_pages_per_query=args.max_pages_per_query,
            query_delay_s=args.query_delay,
        )
        results.append(result)

    print("\n--- Summary ---")
    for r in results:
        print(
            f"{r['chapter']}: {r['paper_count']} papers"
            + (f" -> {r.get('output_dir', '')}" if not r.get("dry_run") else " (dry-run)")
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
