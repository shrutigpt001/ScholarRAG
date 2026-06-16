"""
build_sqlite.py — Build SQLite paper registry from papers_enriched.json

Creates ingestion/papers.db with a single 'papers' table for fast
frontend lookup by paper ID after a Qdrant semantic search.

Usage:
  python ingestion/build_sqlite.py
"""

import json
import sqlite3
from pathlib import Path

INPUT_FILE = Path("ingestion/papers_enriched.json")
DB_PATH    = Path("ingestion/papers.db")

# Fall back to base papers if enriched not available
if not INPUT_FILE.exists():
    INPUT_FILE = Path("ingestion/papers.json")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    id              TEXT PRIMARY KEY,
    title           TEXT,
    authors         TEXT,    -- JSON array
    summary         TEXT,
    published       TEXT,
    year            INTEGER,
    pdf_url         TEXT,
    category        TEXT,
    journal         TEXT,
    doi             TEXT,
    citations       INTEGER DEFAULT 0,
    fields_of_study TEXT,    -- JSON array
    github_repos    TEXT,    -- JSON array of {url, stars, framework, is_official}
    has_code        INTEGER DEFAULT 0,
    source          TEXT,
    authors_enriched TEXT    -- JSON array of {name, affiliations, country}
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_year      ON papers(year)",
    "CREATE INDEX IF NOT EXISTS idx_citations ON papers(citations DESC)",
    "CREATE INDEX IF NOT EXISTS idx_has_code  ON papers(has_code)",
    "CREATE INDEX IF NOT EXISTS idx_source    ON papers(source)",
]


def build():
    print(f"Reading {INPUT_FILE} ...")
    with open(INPUT_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers)} papers loaded\n")

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute(CREATE_TABLE)
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)

    rows = []
    for p in papers:
        rows.append((
            p.get("id", ""),
            p.get("title", ""),
            json.dumps(p.get("authors", [])),
            p.get("summary", ""),
            p.get("published", ""),
            p.get("year") or int(str(p.get("published", "0"))[:4] or 0),
            p.get("pdf_url", ""),
            p.get("category", ""),
            p.get("journal", ""),
            p.get("doi", ""),
            p.get("citations", 0),
            json.dumps(p.get("fields_of_study", [])),
            json.dumps(p.get("github_repos", [])),
            1 if p.get("has_code") else 0,
            p.get("source", ""),
            json.dumps(p.get("authors_enriched", [])),
        ))

    cur.executemany("""
        INSERT OR REPLACE INTO papers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    conn.commit()
    conn.close()

    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"Done! Saved to {DB_PATH} ({size_mb:.1f} MB)")
    print(f"  Total papers : {len(rows)}")
    print(f"  With code    : {sum(1 for r in rows if r[13] == 1)}")
    print(f"  With abstract: {sum(1 for r in rows if r[3])}")
    print(f"  With citations > 0: {sum(1 for r in rows if (r[10] or 0) > 0)}")


if __name__ == "__main__":
    build()
