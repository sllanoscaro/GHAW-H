import time
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

# Dataset HuggingFace params
data_params = {
    'DATASET_ID': 'pavtch/GHAW-H',
    'DATASET_REVISION': 'main'
}

# Cache local para no depender de la red en cada ejecución
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def remote_parquet_url(table_name: str) -> str:
    return (
        f"https://huggingface.co/datasets/{data_params['DATASET_ID']}/resolve/"
        f"{data_params['DATASET_REVISION']}/data/{table_name}.parquet"
    )


def read_parquet_table(table_name: str, use_cache: bool = True) -> pd.DataFrame:
    """Read a dataset table from Hugging Face, caching it locally on first use."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{table_name}.parquet"

    if use_cache and cache_path.exists() and cache_path.stat().st_size > 0:
        return pd.read_parquet(cache_path)

    url = remote_parquet_url(table_name)
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(url, timeout=120) as response:
                payload = response.read()
            cache_path.write_bytes(payload)
            return pd.read_parquet(BytesIO(payload))
        except Exception as error:  # red inestable: reintentar con backoff
            last_error = error
            time.sleep(2 * (attempt + 1))

    if cache_path.exists():
        return pd.read_parquet(cache_path)
    raise last_error


def has_create_pull_request(frontmatter: str) -> bool:
    """Return True if the YAML frontmatter declares safe-outputs.create-pull-request."""
    if not frontmatter:
        return False
    in_safe_outputs = False
    for raw_line in frontmatter.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if not in_safe_outputs:
            if indent == 0 and stripped.startswith("safe-outputs:"):
                in_safe_outputs = True
                inline = stripped[len("safe-outputs:"):].strip()
                if "create-pull-request:" in inline:
                    return True
            continue
        # Inside the safe-outputs block: a new top-level key closes it.
        if indent == 0:
            in_safe_outputs = False
            continue
        if stripped.startswith("create-pull-request:"):
            return True
    return False
