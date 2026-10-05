import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.utils import read_parquet_table
import json

def main():
    df = read_parquet_table("repository")
    repos = [
        {"repo_full_name": row["repo_full_name"], "url": row["url"]}
        for row in df.to_dict(orient="records")
    ]
    output_path = os.path.join(os.path.dirname(__file__), "..", "output", "repositories.json")
    with open(output_path, "w") as f:
        json.dump(repos, f, indent=2)

if __name__ == "__main__":
    main()
