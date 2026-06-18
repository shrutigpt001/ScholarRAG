import json
import time
import requests
import urllib3
import argparse
from pathlib import Path
from dotenv import load_dotenv
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

FETCH_FILE     = Path("ingestion/fetch_papers.json")
ENRICHED_FILE  = Path("ingestion/papers_enriched.json")
PROGRESS_FILE  = Path("ingestion/fetch_progress.json")
PWC_LINKS_FILE = Path("ingestion/pwc_links.json")

PWC_ABSTRACTS_DS = "pwc-archive/papers-with-abstracts"

OA_BASE    = "https://api.openalex.org/works"
OA_HEADERS = {"User-Agent": "ScholarRAG/1.0 (mailto:24f3003029@ds.study.iitm.ac.in)"}

OA_FIELDS = [
    "Medicine",
    "Biology",
    "Astronomy",
    "Chemistry",
    "Environmental Science",
    "Psychology",
    "Economics",
    "Physics",
    "Political Science",
    "History",
]
OA_YEARS    = list(range(2014, 2026))  # 12 years
OA_PER_YEAR = 100

CURRENT_YEAR = 2025

_AREA_KEYWORDS: list[tuple[str, list[str]]] = [
    ("vision",   ["image classification", "image generation", "image segmentation",
                  "object detection", "depth estimation", "optical flow",
                  "pose estimation", "medical imaging", "3d generation",
                  "image synthesis", "text-to-image", "nerf", "neural radiance",
                  "inpainting", "style transfer", "stereo matching"]),
    ("video",    ["video classification", "video generation", "video segmentation",
                  "video understanding", "object tracking", "action recognition",
                  "video captioning", "activity recognition", "video question"]),
    ("language", ["machine translation", "named entity recognition", "question answering",
                  "relation extraction", "summarization", "text classification",
                  "text-to-sql", "sentiment", "coreference", "parsing",
                  "reading comprehension", "dialogue", "natural language inference",
                  "information extraction"]),
    ("audio",    ["automatic speech recognition", "text-to-speech", "voice cloning",
                  "audio classification", "audio generation", "speech recognition",
                  "speech synthesis", "speaker verification", "music generation",
                  "speech enhancement", "asr"]),
    ("other",    ["tabular", "time-series", "forecasting", "anomaly detection",
                  "drug discovery", "protein", "genomics", "bioinformatics",
                  "gradient boosting", "xgboost", "random forest"]),
    ("general",  ["reinforcement learning", "language model", "reasoning",
                  "autonomous driving", "robotics", "embedding", "retrieval",
                  "recommendation", "code generation", "federated",
                  "knowledge distillation", "neural architecture search",
                  "meta-learning", "few-shot", "transfer learning",
                  "self-supervised", "contrastive", "graph neural",
                  "knowledge graph", "multimodal", "vision-language",
                  "diffusion", "generative", "adversarial", "pruning",
                  "quantization", "classification", "regression", "optimization"]),
]


def _keyword_area(text: str) -> str:
    t = text.lower()
    for area, kws in _AREA_KEYWORDS:
        if any(k in t for k in kws):
            return area
    return "miscellaneous"


def paper_area(item: dict) -> str:
    tasks = item.get("tasks") or []
    for t in tasks:
        name = (t if isinstance(t, str) else t.get("name", "")).strip()
        area = _keyword_area(name)
        if area != "miscellaneous":
            return area
    text = (item.get("title", "") + " " + (item.get("abstract", "") or "")[:300])
    return _keyword_area(text)


def reconstruct_abstract(inv: dict) -> str:
    if not inv:
        return ""
    pairs = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((pos, word))
    pairs.sort()
    return " ".join(w for _, w in pairs)


def load_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                return set(json.load(f).get("done", []))
        except Exception:
            pass
    return set()


def save_progress(done: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"done": list(done)}, f)


def load_fetch_papers() -> tuple[list, set]:
    if not FETCH_FILE.exists():
        return [], set()
    try:
        import ijson
        papers = []
        seen   = set()
        with open(FETCH_FILE, "rb") as f:
            for p in ijson.items(f, "item"):
                papers.append(p)
                for k in ("arxiv_id", "doi", "id"):
                    v = p.get(k, "")
                    if v:
                        seen.add(v)
                        break
        return papers, seen
    except ImportError:
        with open(FETCH_FILE, encoding="utf-8") as f:
            papers = json.load(f)
        seen = set()
        for p in papers:
            for k in ("arxiv_id", "doi", "id"):
                v = p.get(k, "")
                if v:
                    seen.add(v)
                    break
        return papers, seen


def save_fetch_papers(papers: list):
    with open(FETCH_FILE, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)


# ── Phase 1 ────────────────────────────────────────────────────────────────────

def fetch_pwc(seen_ids: set, hf_token: str, test: bool) -> list:
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: install `datasets` package")
        return []

    print("\n[Phase 1] Streaming all PWC papers-with-abstracts ...")
    papers  = []
    skipped = 0
    total   = 0

    for item in load_dataset(PWC_ABSTRACTS_DS, split="train", streaming=True, token=hf_token):
        abstract = (item.get("abstract") or "").strip()
        if not abstract:
            skipped += 1
            continue

        arxiv_id = (item.get("arxiv_id") or "").strip()
        uid      = arxiv_id or item.get("paper_url", "").split("/")[-1]

        if not uid or uid in seen_ids:
            skipped += 1
            continue

        lang = (item.get("language") or "en").lower()
        if lang and lang not in ("en", "english", ""):
            skipped += 1
            continue

        seen_ids.add(uid)
        if arxiv_id:
            seen_ids.add(arxiv_id)

        raw_date  = item.get("date")
        published = str(raw_date.date()) if hasattr(raw_date, "date") else str(raw_date or "")
        year      = published[:4] if published else ""

        papers.append({
            "id":              uid,
            "arxiv_id":        arxiv_id,
            "title":           item.get("title", ""),
            "authors":         item.get("authors") or [],
            "summary":         abstract,
            "published":       published,
            "year":            year,
            "pdf_url":         f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "category":        paper_area(item),
            "journal":         "",
            "doi":             (item.get("doi") or "").strip(),
            "citations":       0,
            "fields_of_study": [t if isinstance(t, str) else t.get("name", "")
                                 for t in (item.get("tasks") or [])],
            "source":          "pwc",
            "github_repos":    [],
            "has_code":        False,
            "language":        "en",
        })

        total += 1
        if total % 50_000 == 0:
            print(f"  ... {total:,} collected", flush=True)

        if test and total >= 500:
            break

    print(f"  PWC done: {total:,} collected | {skipped:,} skipped\n")
    return papers


# ── Phase 2 ────────────────────────────────────────────────────────────────────

def fetch_openalex(seen_ids: set, test: bool) -> list:
    print("[Phase 2] Fetching OpenAlex non-tech papers ...")
    papers = []
    years  = OA_YEARS[:2] if test else OA_YEARS
    per_yr = 5 if test else OA_PER_YEAR

    for field in OA_FIELDS:
        field_count = 0
        for year in years:
            try:
                r = requests.get(
                    OA_BASE,
                    headers=OA_HEADERS,
                    params={
                        "filter":   f"concepts.display_name:{field},publication_year:{year},has_abstract:true",
                        "sort":     "cited_by_count:desc",
                        "per_page": per_yr,
                        "select":   "id,doi,display_name,authorships,publication_year,"
                                    "primary_location,abstract_inverted_index,"
                                    "cited_by_count,concepts,ids",
                    },
                    timeout=30,
                )
                if r.status_code == 429:
                    print(f"  Rate limited — sleeping 30s")
                    time.sleep(30)
                    continue
                if r.status_code != 200:
                    continue

                for w in r.json().get("results", []):
                    abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
                    if not abstract:
                        continue

                    doi    = (w.get("doi") or "").replace("https://doi.org/", "").strip()
                    oa_id  = w.get("id", "").split("/")[-1]
                    uid    = doi or oa_id

                    if not uid or uid in seen_ids:
                        continue
                    seen_ids.add(uid)
                    if doi:
                        seen_ids.add(doi)

                    authors = [
                        (a.get("author") or {}).get("display_name", "")
                        for a in (w.get("authorships") or [])
                        if (a.get("author") or {}).get("display_name")
                    ]

                    year_str = str(w.get("publication_year") or "")
                    loc      = w.get("primary_location") or {}
                    src      = loc.get("source") or {}
                    pdf_url  = loc.get("pdf_url") or loc.get("landing_page_url") or ""

                    concepts = [
                        c.get("display_name", "")
                        for c in (w.get("concepts") or [])
                        if c.get("score", 0) >= 0.3
                    ]

                    ext_ids  = w.get("ids") or {}
                    arxiv_id = (ext_ids.get("arxiv") or "").replace("https://arxiv.org/abs/", "").strip()

                    papers.append({
                        "id":              uid,
                        "arxiv_id":        arxiv_id,
                        "title":           w.get("display_name", ""),
                        "authors":         authors,
                        "summary":         abstract,
                        "published":       f"{year_str}-01-01",
                        "year":            year_str,
                        "pdf_url":         pdf_url,
                        "category":        field.lower().replace(" ", "_"),
                        "journal":         src.get("display_name", ""),
                        "doi":             doi,
                        "citations":       w.get("cited_by_count", 0),
                        "fields_of_study": concepts,
                        "source":          "openalex",
                        "github_repos":    [],
                        "has_code":        False,
                        "language":        "en",
                    })
                    field_count += 1

                time.sleep(0.15)

            except Exception as e:
                print(f"  Error {field} {year}: {e}")

        print(f"  {field:<25} {field_count:>5} papers")

    print(f"  OpenAlex done: {len(papers):,} papers\n")
    return papers


# ── Phase 3a ───────────────────────────────────────────────────────────────────

def enrich_github(papers: list, test: bool):
    print("[Phase 3a] Loading GitHub links from pwc_links.json ...")

    if not PWC_LINKS_FILE.exists():
        print(f"  WARNING: {PWC_LINKS_FILE} not found — skipping")
        return

    with open(PWC_LINKS_FILE, encoding="utf-8") as f:
        pwc_links: dict = json.load(f)

    print(f"  Loaded {len(pwc_links):,} entries")

    arxiv_index: dict[str, int] = {}
    for i, p in enumerate(papers):
        aid = p.get("arxiv_id", "")
        if aid:
            arxiv_index[aid] = i

    matched = 0
    for arxiv_id, repos in pwc_links.items():
        if arxiv_id not in arxiv_index:
            continue
        idx = arxiv_index[arxiv_id]
        p   = papers[idx]
        max_stars   = 0
        is_official = False
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            url = repo.get("url", "").strip()
            if url and url not in p["github_repos"]:
                p["github_repos"].append(url)
            stars = repo.get("stars") or 0
            if stars > max_stars:
                max_stars = stars
            if repo.get("is_official"):
                is_official = True
        if p["github_repos"]:
            p["has_code"]    = True
            p["max_stars"]   = max_stars
            p["num_repos"]   = len(p["github_repos"])
            p["is_official"] = is_official
            matched += 1

    print(f"  GitHub links matched: {matched:,} papers\n")


# ── Phase 3b ───────────────────────────────────────────────────────────────────

def enrich_citations_openalex(papers: list, test: bool):
    print("[Phase 3b] Enriching citations via OpenAlex ...")

    doi_index   = {}
    arxiv_index = {}

    for p in papers:
        if p.get("source") == "openalex":
            continue
        doi      = (p.get("doi") or "").strip()
        arxiv_id = (p.get("arxiv_id") or "").strip()
        if doi:
            doi_index[doi] = p
        elif arxiv_id:
            arxiv_index[arxiv_id] = p

    print(f"  {len(doi_index):,} via DOI  |  {len(arxiv_index):,} via arxiv ID")

    enriched   = 0
    batch_size = 100

    doi_list = list(doi_index.keys())
    if test:
        doi_list = doi_list[:200]

    for i in range(0, len(doi_list), batch_size):
        batch = doi_list[i:i + batch_size]
        try:
            r = requests.get(
                OA_BASE,
                headers=OA_HEADERS,
                params={
                    "filter":   "doi:" + "|".join(batch),
                    "select":   "doi,cited_by_count",
                    "per_page": batch_size,
                },
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(30)
                continue
            if r.status_code == 200:
                for w in r.json().get("results", []):
                    doi = (w.get("doi") or "").replace("https://doi.org/", "").strip()
                    p   = doi_index.get(doi)
                    if p:
                        p["citations"] = w.get("cited_by_count", 0)
                        enriched += 1
        except Exception as e:
            print(f"  DOI batch error: {e}")
        time.sleep(0.15)

        if i > 0 and i % 10_000 == 0:
            print(f"  DOI {i:,}/{len(doi_list):,} | enriched: {enriched:,}", flush=True)

    arxiv_list = list(arxiv_index.keys())
    if test:
        arxiv_list = arxiv_list[:200]

    for i in range(0, len(arxiv_list), batch_size):
        batch = arxiv_list[i:i + batch_size]
        try:
            r = requests.get(
                OA_BASE,
                headers=OA_HEADERS,
                params={
                    "filter":   "ids.arxiv:" + "|".join(
                        f"https://arxiv.org/abs/{aid}" for aid in batch
                    ),
                    "select":   "ids,cited_by_count",
                    "per_page": batch_size,
                },
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(30)
                continue
            if r.status_code == 200:
                for w in r.json().get("results", []):
                    ext = w.get("ids") or {}
                    aid = (ext.get("arxiv") or "").replace("https://arxiv.org/abs/", "").strip()
                    p   = arxiv_index.get(aid)
                    if p:
                        p["citations"] = w.get("cited_by_count", 0)
                        enriched += 1
        except Exception as e:
            print(f"  ArXiv batch error: {e}")
        time.sleep(0.15)

        if i > 0 and i % 10_000 == 0:
            print(f"  ArXiv {i:,}/{len(arxiv_list):,} | enriched: {enriched:,}", flush=True)

    total = len(doi_index) + len(arxiv_index)
    print(f"  Citations enriched: {enriched:,}/{total:,}\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main(test: bool):
    hf_token = os.getenv("HF_TOKEN", "")
    done     = load_progress()

    all_papers, seen_ids = load_fetch_papers()
    print(f"Loaded {len(all_papers):,} existing papers from {FETCH_FILE}\n")

    if not test and "pwc_abstracts" in done:
        print("[Phase 1] PWC abstracts — skipping (done)\n")
    else:
        pwc_papers = fetch_pwc(seen_ids, hf_token, test)
        all_papers.extend(pwc_papers)
        save_fetch_papers(all_papers)
        print(f"  Saved {len(all_papers):,} papers after PWC\n")
        if not test:
            done.add("pwc_abstracts")
            save_progress(done)

    if not test and "openalex_papers" in done:
        print("[Phase 2] OpenAlex papers — skipping (done)\n")
    else:
        oa_papers = fetch_openalex(seen_ids, test)
        all_papers.extend(oa_papers)
        save_fetch_papers(all_papers)
        print(f"  Saved {len(all_papers):,} papers after OpenAlex\n")
        if not test:
            done.add("openalex_papers")
            save_progress(done)

    if not test and "github_enriched" in done:
        print("[Phase 3a] GitHub links — skipping (done)\n")
    else:
        enrich_github(all_papers, test)
        save_fetch_papers(all_papers)
        if not test:
            done.add("github_enriched")
            save_progress(done)

    if not test and "citations_enriched" in done:
        print("[Phase 3b] Citations — skipping (done)\n")
    else:
        enrich_citations_openalex(all_papers, test)
        save_fetch_papers(all_papers)
        if not test:
            done.add("citations_enriched")
            save_progress(done)

    with open(ENRICHED_FILE, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)

    pwc_c  = sum(1 for p in all_papers if p.get("source") == "pwc")
    oa_c   = sum(1 for p in all_papers if p.get("source") == "openalex")
    code_c = sum(1 for p in all_papers if p.get("has_code"))
    cit_c  = sum(1 for p in all_papers if p.get("citations", 0) > 0)

    print(f"\n{'='*60}")
    print(f"DONE — {len(all_papers):,} papers → {ENRICHED_FILE}")
    print(f"  PWC             : {pwc_c:,}")
    print(f"  OpenAlex        : {oa_c:,}")
    print(f"  With GitHub     : {code_c:,}")
    print(f"  With citations  : {cit_c:,}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    main(args.test)
