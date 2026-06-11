#!/usr/bin/env python3
"""
Web fact verification for autobooks.

Fetches source_url / corroboration_url from verified_facts.jsonl, extracts page
content (craw4ai preferred; requests+BeautifulSoup fallback), caches excerpts under
books/research/<chapter>/fact_sources/, and checks that claim tokens appear in text.

Usage:
    uv run fact_verify.py --chapter ch01
    uv run fact_verify.py --all
    uv run fact-verify --chapter ch01
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from book_prepare import OUTLINE, ChapterSpec

ROOT = Path(__file__).resolve().parent
RESEARCH_ROOT = ROOT / "books" / "research"
CONTENT_EXCERPT_CHARS = 4000
REQUEST_TIMEOUT_S = 45
USER_AGENT = "autobooks-fact-verify/1.0"


def verified_facts_path(chapter_id: str) -> Path:
    return RESEARCH_ROOT / chapter_id / "verified_facts.jsonl"


def sources_dir(chapter_id: str) -> Path:
    return RESEARCH_ROOT / chapter_id / "fact_sources"


def report_path(chapter_id: str) -> Path:
    return RESEARCH_ROOT / chapter_id / "fact_verify_report.json"


def url_cache_key(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


def load_verified_facts(chapter_id: str) -> list[dict[str, Any]]:
    path = verified_facts_path(chapter_id)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def claim_match_tokens(claim: str) -> list[str]:
    tokens: list[str] = []
    for num in re.findall(r"\d[\d,.]*(?:×|x|%|ms|μs|us|gb/s|tb/s|tok/s)?", claim, flags=re.I):
        tokens.append(num.lower().replace("×", "x"))
    for word in re.findall(r"[A-Za-z][A-Za-z0-9./+\-]{2,}", claim):
        if word.lower() not in {"the", "and", "for", "with", "from", "this", "that"}:
            tokens.append(word.lower())
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:12]


def content_matches_claim(content: str, claim: str) -> tuple[bool, list[str]]:
    if not content.strip():
        return False, ["empty content"]
    lowered = content.lower()
    tokens = claim_match_tokens(claim)
    if not tokens:
        return True, []
    missing = [t for t in tokens if t not in lowered]
    need = max(1, len(tokens) // 2) if len(tokens) > 3 else len(tokens)
    matched = len(tokens) - len(missing)
    return matched >= need, missing


def fetch_with_requests(url: str) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(separator="\n", strip=True)
        return {
            "url": url,
            "fetched_at": fetched_at,
            "success": True,
            "method": "requests",
            "status_code": resp.status_code,
            "title": title,
            "content_excerpt": text[:CONTENT_EXCERPT_CHARS],
            "content_chars": len(text),
            "error": None,
        }
    except Exception as exc:
        return {
            "url": url,
            "fetched_at": fetched_at,
            "success": False,
            "method": "requests",
            "status_code": None,
            "title": "",
            "content_excerpt": "",
            "content_chars": 0,
            "error": str(exc),
        }


async def _fetch_with_craw4ai(url: str, claim: str) -> dict[str, Any]:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    from crawl4ai.content_filter_strategy import BM25ContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    fetched_at = datetime.now(timezone.utc).isoformat()
    query = " ".join(claim_match_tokens(claim)[:6]) or urlparse(url).path.split("/")[-1]
    bm25 = BM25ContentFilter(user_query=query or "abstract", bm25_threshold=1.0)
    md_gen = DefaultMarkdownGenerator(content_filter=bm25)
    config = CrawlerRunConfig(markdown_generator=md_gen)

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=config)
        if not result.success:
            return {
                "url": url,
                "fetched_at": fetched_at,
                "success": False,
                "method": "craw4ai",
                "status_code": getattr(result, "status_code", None),
                "title": "",
                "content_excerpt": "",
                "content_chars": 0,
                "error": result.error_message or "crawl failed",
            }
        md = result.markdown
        fit = getattr(md, "fit_markdown", None) or ""
        raw = getattr(md, "raw_markdown", None) or str(md or "")
        text = fit if len(fit) > 200 else raw
        title = (result.metadata or {}).get("title", "") if result.metadata else ""
        return {
            "url": url,
            "fetched_at": fetched_at,
            "success": True,
            "method": "craw4ai",
            "status_code": getattr(result, "status_code", 200),
            "title": title,
            "content_excerpt": text[:CONTENT_EXCERPT_CHARS],
            "content_chars": len(text),
            "error": None,
        }
    except Exception as exc:
        return {
            "url": url,
            "fetched_at": fetched_at,
            "success": False,
            "method": "craw4ai",
            "status_code": None,
            "title": "",
            "content_excerpt": "",
            "content_chars": 0,
            "error": str(exc),
        }


def arxiv_alternate_urls(url: str) -> list[str]:
    """HTML full text often contains table numbers missing from abs abstracts."""
    m = re.search(r"arxiv\.org/abs/([\d.]+)", url, flags=re.I)
    if not m:
        return []
    aid = m.group(1)
    return [f"https://arxiv.org/html/{aid}v1", f"https://arxiv.org/html/{aid}"]


def fetch_url_content(url: str, *, claim: str = "", prefer_craw4ai: bool = True) -> dict[str, Any]:
    if not url or not url.startswith(("http://", "https://")):
        return {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "method": "none",
            "status_code": None,
            "title": "",
            "content_excerpt": "",
            "content_chars": 0,
            "error": "invalid url",
        }
    if prefer_craw4ai:
        try:
            import crawl4ai  # noqa: F401
            result = asyncio.run(_fetch_with_craw4ai(url, claim))
            if result.get("success"):
                return result
            fb = fetch_with_requests(url)
            fb["craw4ai_error"] = result.get("error")
            return fb
        except ImportError:
            pass
        except Exception as exc:
            fb = fetch_with_requests(url)
            fb["craw4ai_error"] = str(exc)
            return fb
    return fetch_with_requests(url)


def load_cached_source(cache_file: Path) -> dict[str, Any] | None:
    if not cache_file.exists():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def cache_source(chapter_id: str, url: str, payload: dict[str, Any]) -> Path:
    out_dir = sources_dir(chapter_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{url_cache_key(url)}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def get_or_fetch_source(
    chapter_id: str,
    url: str,
    *,
    claim: str,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    cache_file = sources_dir(chapter_id) / f"{url_cache_key(url)}.json"
    if not force_refresh:
        cached = load_cached_source(cache_file)
        if cached and cached.get("url") == url and cached.get("success"):
            return cached
    if dry_run:
        return {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "method": "dry-run",
            "status_code": None,
            "title": "",
            "content_excerpt": "",
            "content_chars": 0,
            "error": "dry-run",
        }
    payload = fetch_url_content(url, claim=claim)
    cache_source(chapter_id, url, payload)
    return payload


def fetch_best_source_for_claim(
    chapter_id: str,
    url: str,
    *,
    claim: str,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fetch primary URL; for arXiv abs pages, retry HTML when claim tokens are missing."""
    primary = get_or_fetch_source(
        chapter_id, url, claim=claim, force_refresh=force_refresh, dry_run=dry_run
    )
    if dry_run or not primary.get("success"):
        return primary
    matched, _ = content_matches_claim(primary.get("content_excerpt", ""), claim)
    if matched or "arxiv.org/abs/" not in url:
        return primary
    for alt_url in arxiv_alternate_urls(url):
        alt = get_or_fetch_source(
            chapter_id, alt_url, claim=claim, force_refresh=force_refresh, dry_run=dry_run
        )
        if not alt.get("success"):
            continue
        alt_matched, _ = content_matches_claim(alt.get("content_excerpt", ""), claim)
        if alt_matched or len(alt.get("content_excerpt", "")) > len(primary.get("content_excerpt", "")):
            alt["primary_url"] = url
            alt["resolved_url"] = alt_url
            return alt
    return primary


def verify_entry(
    chapter_id: str,
    entry: dict[str, Any],
    *,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    claim = str(entry.get("claim", ""))
    source_url = str(entry.get("source_url", ""))
    corroboration_url = str(entry.get("corroboration_url", "") or "")

    source = fetch_best_source_for_claim(
        chapter_id, source_url, claim=claim, force_refresh=force_refresh, dry_run=dry_run
    )
    source_match, source_missing = content_matches_claim(source.get("content_excerpt", ""), claim)

    corroboration: dict[str, Any] | None = None
    corr_match = True
    corr_missing: list[str] = []
    if corroboration_url and corroboration_url != source_url:
        corroboration = fetch_best_source_for_claim(
            chapter_id,
            corroboration_url,
            claim=claim,
            force_refresh=force_refresh,
            dry_run=dry_run,
        )
        corr_match, corr_missing = content_matches_claim(
            corroboration.get("content_excerpt", ""), claim
        )

    ok = bool(source.get("success")) and source_match
    if entry.get("table_claim"):
        ok = bool(source.get("success"))
    elif corroboration_url and corroboration_url != source_url and corroboration:
        ok = ok and bool(corroboration.get("success")) and corr_match
    elif entry.get("accept_source_only"):
        ok = bool(source.get("success")) and source_match

    return {
        "claim": claim,
        "bib_key": entry.get("bib_key"),
        "source_url": source_url,
        "corroboration_url": corroboration_url or None,
        "source_fetch_ok": bool(source.get("success")),
        "source_content_match": source_match,
        "source_missing_tokens": source_missing,
        "corroboration_fetch_ok": None if not corroboration else bool(corroboration.get("success")),
        "corroboration_content_match": None if not corroboration else corr_match,
        "corroboration_missing_tokens": corr_missing if corroboration else [],
        "verified_ok": ok,
        "source_method": source.get("method"),
        "source_cache": str(sources_dir(chapter_id) / f"{url_cache_key(source_url)}.json"),
    }


def run_chapter_fact_verify(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    entries = load_verified_facts(spec.chapter_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    if not entries:
        report = {
            "chapter_id": spec.chapter_id,
            "timestamp": timestamp,
            "entry_count": 0,
            "verified_ok_count": 0,
            "entries": [],
            "status": "no_facts",
        }
        report_path(spec.chapter_id).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return report

    results = [
        verify_entry(spec.chapter_id, e, force_refresh=force_refresh, dry_run=dry_run)
        for e in entries
    ]
    ok_count = sum(1 for r in results if r.get("verified_ok"))
    report = {
        "chapter_id": spec.chapter_id,
        "timestamp": timestamp,
        "entry_count": len(entries),
        "verified_ok_count": ok_count,
        "entries": results,
        "status": "ok" if ok_count == len(results) else "issues",
    }
    report_path(spec.chapter_id).parent.mkdir(parents=True, exist_ok=True)
    report_path(spec.chapter_id).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def fact_verify_tasks(chapter_id: str) -> list[str]:
    path = report_path(chapter_id)
    if not path.exists():
        return [f"Fact crawl: run fact_verify for {chapter_id} (craw4ai source extraction)"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"Fact crawl: invalid {path.name} — re-run fact_verify"]

    tasks: list[str] = []
    for row in report.get("entries", []):
        if row.get("verified_ok"):
            continue
        claim = str(row.get("claim", ""))[:80]
        if not row.get("source_fetch_ok"):
            tasks.append(f"Fact crawl failed (source): {claim}… — {row.get('source_url')}")
        elif not row.get("source_content_match"):
            missing = ", ".join(row.get("source_missing_tokens") or [])
            tasks.append(f"Fact content mismatch (source): {claim}… — missing [{missing}]")
        if row.get("corroboration_url") and not row.get("corroboration_fetch_ok"):
            tasks.append(f"Fact crawl failed (corroboration): {row.get('corroboration_url')}")
        elif row.get("corroboration_url") and row.get("corroboration_content_match") is False:
            missing = ", ".join(row.get("corroboration_missing_tokens") or [])
            tasks.append(f"Fact content mismatch (corroboration): missing [{missing}]")
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
    parser = argparse.ArgumentParser(description="Web fact verification via craw4ai")
    parser.add_argument("--chapter", help="Chapter id, e.g. ch01")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()
    if not args.chapter and not args.all:
        parser.error("Specify --chapter <id> or --all")
    for spec in resolve_specs(args.chapter if not args.all else None):
        report = run_chapter_fact_verify(
            spec, dry_run=args.dry_run, force_refresh=args.force_refresh
        )
        print(
            f"{spec.chapter_id}: {report['verified_ok_count']}/{report['entry_count']} "
            f"({report['status']}) -> {report_path(spec.chapter_id)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
