import os
import json
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

from github_config import GITHUB_REPOS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(
    BASE_DIR,
    "github_docs"
)

os.makedirs(DOCS_DIR, exist_ok=True)

repo_metadata = []

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

for repo in GITHUB_REPOS:
    print(f"Fetching {repo}...")
    filename = None
    readme_text = ""

    try:
        repo_url = f"https://api.github.com/repos/{repo}"
        repo_response = requests.get(
            repo_url,
            headers=headers,
            timeout=10
        )

        if repo_response.status_code != 200:
            print(
                f"Failed metadata for {repo}: "
                f"{repo_response.status_code}"
            )
            continue

        repo_data = repo_response.json()

        readme_url = (
            f"https://api.github.com/repos/"
            f"{repo}/readme"
        )

        readme_response = requests.get(
            readme_url,
            headers=headers,
            timeout=10
        )

        if readme_response.status_code == 200:
            readme_data = readme_response.json()
            encoded_content = readme_data.get(
                "content",
                ""
            )
            readme_text = base64.b64decode(
                encoded_content
            ).decode(
                "utf-8",
                errors="ignore"
            )
            filename = (repo.replace("/", "_")+ "_README.md")
            filepath = os.path.join(DOCS_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(readme_text)

        repo_metadata.append(
            {
                "name": repo_data.get(
                    "full_name"
                ),
                "description": repo_data.get(
                    "description"
                ),
                "stars": repo_data.get(
                    "stargazers_count"
                ),
                "forks": repo_data.get(
                    "forks_count"
                ),
                "language": repo_data.get(
                    "language"
                ),
                "topics": repo_data.get(
                    "topics",
                    []
                ),
                "url": repo_data.get(
                    "html_url"
                ),
                "readme_file": filename
            }
        )

        print(f"Saved {repo}")

    except Exception as e:

        print(
            f"Error processing {repo}: {e}"
        )


metadata_file = os.path.join(
    DOCS_DIR,
    "github_repos.json"
)

with open(
    metadata_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        repo_metadata,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\nDone!")
print(
    f"Metadata saved to {metadata_file}"
)
