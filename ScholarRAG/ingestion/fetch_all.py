import json
import time
import math
import random
import heapq
import argparse
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

DATA_PATH     = Path("ingestion/papers.json")
PROGRESS_FILE = Path("ingestion/fetch_progress.json")

PWC_HF_DATASET = "pwc-archive/papers-with-abstracts"
PWC_TARGET     = 20_000
PWC_OVERSAMPLE = 3

S2_BATCH_URL  = "https://api.semanticscholar.org/graph/v1/paper/batch"
S2_BATCH_SIZE = 500

OA_BASE    = "https://api.openalex.org/works"
OA_HEADERS = {
    "User-Agent": "ScholarRAG/1.0 (mailto:24f3003029@ds.study.iitm.ac.in)",
    "Accept":     "application/json",
}
OA_SELECT = (
    "id,doi,title,authorships,publication_date,publication_year,"
    "primary_location,abstract_inverted_index,cited_by_count,concepts,type"
)
OA_DELAY    = 0.12
OA_YEARS    = list(range(2012, 2026))
OA_PER_YEAR = 100

OA_DOMAINS = [
    ("Medicine",              "C71924100"),
    ("Biology",               "C86803240"),
    ("Chemistry",             "C185592680"),
    ("Physics",               "C121332964"),
    ("Mathematics",           "C33923547"),
    ("Economics",             "C162324750"),
    ("Psychology",            "C15744967"),
    ("Environmental Science", "C39432304"),
    ("Materials Science",     "C192562407"),
    ("Political Science",     "C17744445"),
    ("Geology",               "C127313418"),
    ("Astronomy",             "C1276947"),
]


def load_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return set(data.get("done", []))
        except (json.JSONDecodeError, AttributeError):
            pass
    return set()


def save_progress(done: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"done": list(done)}, f)


def dedup(papers: list) -> list:
    seen = set()
    out  = []
    for p in papers:
        key = p.get("id", "") or p.get("title", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(p)
    return out


def save(papers: list) -> list:
    deduped = dedup(papers)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    return deduped


_AREA_KEYWORDS: list[tuple[str, list[str]]] = [
    ("vision", ["image classification", "image generation", "image segmentation",
                "image editing", "image restoration", "image understanding",
                "image super-resolution", "image matching", "image matting",
                "object detection", "object counting",
                "depth estimation", "optical flow", "stereo matching",
                "pose estimation", "medical imaging",
                "3d generation", "3d understanding", "3d object detection",
                "3d instance segmentation", "3d semantic segmentation",
                "zero-shot segmentation", "inpainting", "style transfer",
                "image synthesis", "text-to-image", "nerf", "neural radiance"]),

    ("video", ["video classification", "video generation", "video segmentation",
               "video understanding", "video super-resolution", "video matting",
               "object tracking", "action recognition", "temporal action",
               "video captioning", "activity recognition", "action detection",
               "video question", "video grounding"]),

    ("language", ["machine translation", "named entity recognition", "question answering",
                  "relation extraction", "summarization", "text classification",
                  "text-to-sql", "table question answering", "part-of-speech",
                  "entity typing", "sentiment", "coreference", "parsing",
                  "reading comprehension", "dialogue", "natural language inference",
                  "information extraction", "slot filling"]),

    ("audio", ["automatic speech recognition", "text-to-speech", "voice cloning",
               "audio classification", "audio generation", "audio understanding",
               "speech recognition", "speech synthesis", "speaker verification",
               "speaker diarization", "sound event detection", "music generation",
               "speech enhancement", "asr"]),

    ("other", ["tabular learning", "tabular data", "time-series classification",
               "time-series forecasting", "time series", "forecasting",
               "anomaly detection", "biology", "drug discovery", "protein",
               "genomics", "bioinformatics", "gradient boosting", "xgboost",
               "random forest", "decision tree"]),

    ("general", ["reinforcement learning", "language model", "reasoning",
                 "autonomous driving", "robotics", "robot", "navigation",
                 "document understanding", "ocr", "optical character",
                 "scene text", "embedding", "retrieval", "recommendation",
                 "anomaly", "world model", "remote sensing",
                 "code generation", "program synthesis", "software",
                 "deepfake", "federated", "knowledge distillation",
                 "neural architecture search", "meta-learning", "few-shot",
                 "transfer learning", "self-supervised", "contrastive",
                 "graph neural", "knowledge graph", "multimodal",
                 "vision-language", "diffusion", "generative",
                 "classification", "regression", "optimization",
                 "adversarial", "pruning", "quantization"]),
]


def _keyword_area(task_name: str) -> str:
    t = task_name.lower()
    for area, keywords in _AREA_KEYWORDS:
        if any(k in t for k in keywords):
            return area
    return "miscellaneous"


def paper_area(item: dict) -> str:
    tasks = item.get("tasks") or []
    for t in tasks:
        name = (t if isinstance(t, str) else t.get("name", "")).strip().lower()
        area = _keyword_area(name)
        if area != "miscellaneous":
            return area
    text = (item.get("title", "") + " " + (item.get("abstract", "") or "")[:300]).lower()
    return _keyword_area(text)


CURRENT_YEAR = 2026

def paper_weight(citations: int, year: str) -> float:
    base = math.log(max(citations, 0) + 2)
    try:
        age = CURRENT_YEAR - int(str(year)[:4])
    except (ValueError, TypeError):
        age = 5
    if age <= 1:
        recency = 3.0
    elif age <= 2:
        recency = 2.5
    elif age <= 3:
        recency = 2.0
    elif age <= 5:
        recency = 1.5
    else:
        recency = 1.0
    return base * recency


PWC_AREA_QUOTAS = {
    "general":       6000,
    "vision":        5000,
    "language":      4000,
    "video":         2000,
    "audio":         1400,
    "other":         1000,
    "miscellaneous":  600,
}

PWC_TEST_QUOTA = 2


def fetch_pwc_bulk(target: int, test: bool) -> list:
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: `datasets` not installed.")
        return []

    import os
    api_key  = os.getenv("S2_API_KEY", "")
    hf_token = os.getenv("HF_TOKEN")
    quotas   = {area: PWC_TEST_QUOTA for area in PWC_AREA_QUOTAS} if test else PWC_AREA_QUOTAS

    print("  Pass 1: streaming metadata from HF ...")
    metadata      = []
    total_seen    = 0
    total_skipped = 0

    for item in load_dataset(PWC_HF_DATASET, split="train", streaming=True, token=hf_token):
        if not (item.get("abstract") or "").strip():
            total_skipped += 1
            continue

        arxiv_id  = item.get("arxiv_id") or ""
        raw_date  = item.get("date")
        published = str(raw_date.date()) if hasattr(raw_date, "date") else str(raw_date or "")
        year      = published[:4] if published else ""
        area      = paper_area(item)
        uid       = arxiv_id or item.get("paper_url", "").split("/")[-1]

        metadata.append({"uid": uid, "arxiv_id": arxiv_id, "year": year, "area": area})
        total_seen += 1

        if total_seen % 50_000 == 0:
            print(f"  ... {total_seen:,} metadata collected", flush=True)

        if test and total_seen >= 500:
            break

    print(f"  Pass 1 done: {total_seen:,} papers | {total_skipped:,} skipped\n")

    citation_map: dict[str, int] = {}
    print("  S2: skipped — using pure random sampling within area quotas\n")

    print("  Sampling: weighted A-Res reservoir per area ...")
    heaps: dict[str, list] = defaultdict(list)

    for m in metadata:
        score = random.random()
        area  = m["area"]
        quota = quotas.get(area, quotas["miscellaneous"])
        heap  = heaps[area]
        if len(heap) < quota:
            heapq.heappush(heap, (score, m["uid"]))
        elif score > heap[0][0]:
            heapq.heapreplace(heap, (score, m["uid"]))

    winning_ids = {uid for heap in heaps.values() for _, uid in heap}
    print(f"  Selected {len(winning_ids):,} papers:")
    for area in sorted(heaps):
        print(f"    {area:<16} {len(heaps[area]):>5}/{quotas.get(area, quotas['miscellaneous'])}")
    print()

    print("  Pass 2: collecting full paper data for selected IDs ...")
    papers: list = []

    for item in load_dataset(PWC_HF_DATASET, split="train", streaming=True, token=hf_token):
        abstract = (item.get("abstract") or "").strip()
        if not abstract:
            continue

        arxiv_id = item.get("arxiv_id") or ""
        uid      = arxiv_id or item.get("paper_url", "").split("/")[-1]

        if uid not in winning_ids:
            continue

        raw_date  = item.get("date")
        published = str(raw_date.date()) if hasattr(raw_date, "date") else str(raw_date or "")
        year      = published[:4] if published else ""

        papers.append({
            "id":               uid,
            "arxiv_id":         arxiv_id,
            "title":            item.get("title", ""),
            "authors":          item.get("authors") or [],
            "authors_enriched": [],
            "summary":          abstract,
            "published":        published,
            "year":             year,
            "pdf_url":          f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "category":         paper_area(item),
            "journal":          "",
            "doi":              item.get("doi", "") or "",
            "citations":        citation_map.get(arxiv_id, 0),
            "fields_of_study":  [t if isinstance(t, str) else t.get("name", "")
                                  for t in (item.get("tasks") or [])],
            "source":           "pwc",
            "github_repos":     [],
            "has_code":         False,
        })

        if len(papers) % 1000 == 0:
            print(f"  ... {len(papers):,}/{len(winning_ids):,} collected", flush=True)

        if len(papers) == len(winning_ids):
            break

        if test and len(papers) >= sum(quotas.values()):
            break

    area_map: dict[str, list] = defaultdict(list)
    for p in papers:
        area_map[p["category"]].append(p)
    for area in sorted(area_map):
        ps      = area_map[area]
        avg_cit = sum(p["citations"] for p in ps) / len(ps) if ps else 0
        years   = [int(p["year"]) for p in ps if str(p.get("year", "")).isdigit()]
        avg_yr  = sum(years) / len(years) if years else 0
        print(f"    {area:<16} {len(ps):>5} papers  avg_citations={avg_cit:.0f}  avg_year={avg_yr:.0f}")

    print(f"\n  Total PWC sampled : {len(papers):,}")
    return papers


def reconstruct_abstract(inv: dict) -> str:
    if not inv:
        return ""
    word_pos = []
    for word, positions in inv.items():
        for pos in positions:
            word_pos.append((pos, word))
    return " ".join(w for _, w in sorted(word_pos))


def fetch_openalex_domain(label: str, concept_id: str, year: int, limit: int) -> list:
    papers   = []
    page     = 1
    per_page = min(200, limit)

    while len(papers) < limit:
        batch = min(per_page, limit - len(papers))
        try:
            r = requests.get(OA_BASE, headers=OA_HEADERS, params={
                "filter":   (
                    f"concepts.id:{concept_id},"
                    f"publication_year:{year},"
                    f"has_abstract:true,"
                    f"type:article"
                ),
                "sort":     "cited_by_count:desc",
                "per_page": batch,
                "page":     page,
                "select":   OA_SELECT,
            }, timeout=30)

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                print(f"    Rate limited — sleeping {wait}s")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                print(f"    HTTP {r.status_code} — stopping")
                break

            results = r.json().get("results", [])
            if not results:
                break

            for w in results:
                abstract = reconstruct_abstract(w.get("abstract_inverted_index") or {})
                if not abstract:
                    continue
                primary = w.get("primary_location") or {}
                source  = primary.get("source") or {}
                journal = source.get("display_name", "")
                doi     = (w.get("doi") or "").replace("https://doi.org/", "")

                arxiv_id = ""
                if "arxiv." in doi.lower():
                    arxiv_id = doi.split("rXiv.")[-1].split("rxiv.")[-1].strip()

                authors, authors_enriched = [], []
                for a in w.get("authorships", []):
                    name    = (a.get("author") or {}).get("display_name", "")
                    insts   = a.get("institutions", [])
                    affs    = [i.get("display_name", "") for i in insts if i.get("display_name")]
                    country = next(
                        (i.get("country_code", "") for i in insts if i.get("country_code")), ""
                    )
                    if name:
                        authors.append(name)
                        authors_enriched.append({"name": name, "affiliations": affs, "country": country})

                fields = [
                    c["display_name"]
                    for c in w.get("concepts", [])
                    if c.get("level", 99) <= 1
                ]

                papers.append({
                    "id":               arxiv_id or doi or w.get("id", "").split("/")[-1],
                    "arxiv_id":         arxiv_id,
                    "title":            w.get("title", ""),
                    "authors":          authors,
                    "authors_enriched": authors_enriched,
                    "summary":          abstract,
                    "published":        w.get("publication_date", ""),
                    "year":             w.get("publication_year", ""),
                    "pdf_url":          primary.get("pdf_url", ""),
                    "category":         label.lower(),
                    "journal":          journal,
                    "doi":              doi,
                    "citations":        w.get("cited_by_count", 0),
                    "fields_of_study":  fields,
                    "source":           "openalex",
                    "github_repos":     [],
                    "has_code":         False,
                })

            page += 1
            time.sleep(OA_DELAY)

            if len(results) < batch:
                break

        except requests.RequestException as e:
            print(f"    Network error: {e} — retrying in 10s")
            time.sleep(10)

    return papers


def main(test: bool):
    done = load_progress()

    all_papers = []
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding="utf-8") as f:
            all_papers = json.load(f)
        print(f"Loaded {len(all_papers)} existing papers\n")

    print("=" * 60)
    print(f"PHASE 1 — PWC bulk  (target: {PWC_TARGET:,} papers)")
    print("=" * 60)

    if not test and "pwc_bulk" in done:
        print("  PWC bulk — skipping (done)\n")
    else:
        pwc_papers = fetch_pwc_bulk(PWC_TARGET, test)
        all_papers.extend(pwc_papers)
        deduped = save(all_papers)
        print(f"  Total unique after PWC: {len(deduped)}\n")
        if not test:
            done.add("pwc_bulk")
            save_progress(done)

    total_oa = len(OA_DOMAINS) * len(OA_YEARS) * OA_PER_YEAR
    print("=" * 60)
    print(f"PHASE 2 — OpenAlex  ({len(OA_DOMAINS)} domains × {len(OA_YEARS)} years × {OA_PER_YEAR} = ~{total_oa:,})")
    print("=" * 60)

    bucket_count = 0
    for label, concept_id in OA_DOMAINS:
        for year in OA_YEARS:
            key = f"oa_{label.lower().replace(' ', '_')}_{year}"
            if not test and key in done:
                continue

            limit = 1 if test else OA_PER_YEAR
            print(f"  [OpenAlex] {label} {year} ...", flush=True)
            papers = fetch_openalex_domain(label, concept_id, year, limit)
            all_papers.extend(papers)
            print(f"    -> {len(papers)} papers")

            if not test:
                done.add(key)
                bucket_count += 1
                if bucket_count % 10 == 0:
                    save_progress(done)
                    deduped = save(all_papers)
                    print(f"    [checkpoint] {len(deduped):,} unique papers saved\n")

            time.sleep(0.5)

    save_progress(done)
    deduped = save(all_papers)
    print(f"  Total unique after OpenAlex: {len(deduped):,}\n")

    final     = dedup(all_papers)
    pwc_count = sum(1 for p in final if p.get("source") == "pwc")
    oa_count  = sum(1 for p in final if p.get("source") == "openalex")

    print(f"\n{'=' * 60}")
    print(f"DONE — {len(final):,} unique papers saved to {DATA_PATH}")
    print(f"  PWC papers      : {pwc_count:,}")
    print(f"  OpenAlex papers : {oa_count:,}")
    print(f"  With abstract   : {sum(1 for p in final if p.get('summary')):,}")
    print(f"  With citations  : {sum(1 for p in final if p.get('citations', 0) > 0):,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    main(args.test)
