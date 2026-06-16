"""
enrich_papers.py — Add GitHub repos to papers using Papers With Code index

Works on ALL papers (PWC and OpenAlex sources).  Any paper that carries an
arxiv_id gets looked up in pwc_links.json; if found, github_repos and
has_code are filled in.  Papers without an arxiv_id (pure journal articles
from Medicine / Biology / Astronomy / Economics) are left as-is.

PWC index (pwc_links.json) must exist — run fetch_all.py first, then:
  python ingestion/enrich_papers.py           # full run
  python ingestion/enrich_papers.py --test    # 5 papers only
"""

import re
import json
import argparse
from pathlib import Path

# New-style ArXiv IDs: 1706.03762  or  1706.03762v5
# Old-style ArXiv IDs: hep-ph/9901001
_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-z\-]+/\d{7}(v\d+)?$", re.I)

INPUT_FILE    = Path("ingestion/papers.json")
OUTPUT_FILE   = Path("ingestion/papers_enriched.json")
PROGRESS_FILE = Path("ingestion/enrich_progress.json")
PWC_CACHE     = Path("ingestion/pwc_links.json")


# ── Load PWC index ─────────────────────────────────────────────────────────────

def load_pwc_index() -> dict:
    if not PWC_CACHE.exists():
        print(f"ERROR: {PWC_CACHE} not found.")
        print("The PWC index was built during setup. If missing, re-run:")
        print("  python ingestion/build_pwc_index.py")
        return {}
    print(f"Loading PWC index from {PWC_CACHE} ...")
    with open(PWC_CACHE, encoding="utf-8") as f:
        index = json.load(f)
    print(f"  {len(index)} papers with code indexed\n")
    return index


# ── Helpers ────────────────────────────────────────────────────────────────────

def clean_id(raw: str) -> str:
    """Strip version suffix: 1706.03762v5 -> 1706.03762"""
    return raw.split("v")[0]


def is_arxiv_id(pid: str) -> bool:
    """True only for valid ArXiv ID formats (PWC index is keyed by ArXiv ID)."""
    return bool(pid and _ARXIV_RE.match(pid.strip()))


def load_progress() -> set:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f).get("done", []))
    return set()


def save_progress(done: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"done": list(done)}, f)


def flush(papers: list, out_file: Path):
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)


# ── Main ───────────────────────────────────────────────────────────────────────

def main(test: bool):
    # Load papers
    with open(INPUT_FILE, encoding="utf-8") as f:
        papers = json.load(f)

    if test:
        papers = papers[:5]
        print(f"=== TEST MODE: 5 papers ===\n")
    else:
        print(f"=== FULL RUN: {len(papers)} papers ===\n")

    # Load PWC index
    pwc_index = load_pwc_index()
    if not pwc_index:
        return

    done = set() if test else load_progress()

    # Load existing enriched output to resume
    enriched_map: dict = {}
    if OUTPUT_FILE.exists() and not test:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            for p in json.load(f):
                enriched_map[p["id"]] = p

    total = len(papers)

    for i, paper in enumerate(papers):
        pid = paper.get("id", "")

        # Skip already enriched
        if not test and pid in done:
            enriched_map[pid] = paper
            continue

        # Prefer explicit arxiv_id field; fall back to stripping version from pid
        arxiv_id = paper.get("arxiv_id", "") or clean_id(pid)
        repos = []
        if is_arxiv_id(arxiv_id):
            repos = pwc_index.get(arxiv_id, [])

        enriched = {
            **paper,
            "github_repos": repos,
            "has_code":     len(repos) > 0,
        }

        if repos:
            src = paper.get("source", "?")
            print(f"[{i+1}/{total}] [{src}] {arxiv_id[:20]} — {len(repos)} repo(s)")

        enriched_map[pid] = enriched

        if not test:
            done.add(pid)
            if (i + 1) % 500 == 0:
                save_progress(done)
                flush(list(enriched_map.values()), OUTPUT_FILE)
                print(f"  Checkpoint: {i+1}/{total} processed")

    # Final save
    out = list(enriched_map.values())
    flush(out, OUTPUT_FILE if not test else Path("ingestion/papers_enriched_test.json"))

    if not test:
        save_progress(done)

    # Per-source summary
    sources = {}
    for p in out:
        src = p.get("source", "unknown")
        sources.setdefault(src, {"total": 0, "has_code": 0})
        sources[src]["total"] += 1
        if p.get("has_code"):
            sources[src]["has_code"] += 1

    print(f"\n{'='*50}")
    print(f"DONE — {len(out)} papers saved")
    for src, counts in sorted(sources.items()):
        pct = counts["has_code"] / counts["total"] * 100 if counts["total"] else 0
        print(f"  [{src:10s}]  {counts['total']:>6} papers  |  {counts['has_code']:>5} with code  ({pct:.1f}%)")
    print(f"{'='*50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run on 5 papers only")
    args = parser.parse_args()
    main(args.test)
