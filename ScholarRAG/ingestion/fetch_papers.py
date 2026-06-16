import arxiv
import json
import os
import time
from ingestion.config import FIELDS, MAX_PER_FIELD

DATA_PATH = "ingestion/papers.json"
client = arxiv.Client()

DATE_FROM = "20220101"   # papers from 2022
DATE_TO   = "20241231"   # to end of 2024


def fetch_field(category, limit):
    print(f"Searching category: {category}")

    search = arxiv.Search(
        query=f"cat:{category} AND submittedDate:[{DATE_FROM} TO {DATE_TO}]",
        max_results=limit,
        sort_by=arxiv.SortCriterion.Relevance
    )

    papers = []

    results = list(client.results(search))

    print(f"    Found {len(results)} raw results")

    for result in results:
        papers.append({
            "id": result.entry_id.split("/")[-1],
            "title": result.title,
            "authors": [a.name for a in result.authors],
            "summary": result.summary,
            "published": str(result.published),
            "pdf_url": result.pdf_url,
            "category": category
        })

    print(f"    Processed {len(papers)} papers")

    return papers


def run():
    print("\n Starting ingestion pipeline...\n")

    all_papers = []

    for field, category in FIELDS.items():
        print(f"\n FIELD: {field}")

        try:
            papers = fetch_field(category, MAX_PER_FIELD)
            all_papers.extend(papers)

            time.sleep(1)

        except Exception as e:
            print(f"Error in {field}: {e}")

    print(f"\n Saving {len(all_papers)} papers...")

    os.makedirs("ingestion", exist_ok=True)

    with open(DATA_PATH, "w") as f:
        json.dump(all_papers, f, indent=2)

    print("DONE! Saved to ingestion/papers.json")


if __name__ == "__main__":
    run()
