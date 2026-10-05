import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.utils import read_parquet_table, has_create_pull_request
import json

def main():
    # Cargar tablas
    repo_df = read_parquet_table("repository")
    snap_df = read_parquet_table("source_markdown_file_snapshot")
    ver_df = read_parquet_table("source_markdown_file_version")
    lock_df = read_parquet_table("lock_file_snapshot")

    # Mapas de búsqueda
    repo_map = repo_df.set_index("repository_id")
    snap_map = snap_df.set_index("source_markdown_file_snapshot_id")
    ver_map = ver_df.set_index("source_markdown_file_version_id")

    # Diccionario clave: (repo_full_name, md_path, lock_path) => (committed_at, pair)
    latest_pairs = dict()
    for lock in lock_df.itertuples():
        lock_path = lock.path
        ver_id = lock.source_markdown_file_version_id
        if ver_id not in ver_map.index:
            continue
        snap_id = ver_map.at[ver_id, "source_markdown_file_snapshot_id"]
        if snap_id not in snap_map.index:
            continue
        md_path = snap_map.at[snap_id, "path"]
        repo_id = snap_map.at[snap_id, "repository_id"]
        repo_full_name = repo_map.at[repo_id, "repo_full_name"] if repo_id in repo_map.index else str(repo_id)
        committed_at = ver_map.at[ver_id, "committed_at"]
        # Filtro: solo workflows cuyo Markdown declare safe-outputs.create-pull-request
        frontmatter = snap_map.at[snap_id, "frontmatter"]
        if not has_create_pull_request(frontmatter):
            continue
        key = (repo_full_name, md_path, lock_path)
        # Si ya existe la clave, conservamos el commit MÁS RECIENTE
        if key not in latest_pairs or committed_at > latest_pairs[key][0]:
            latest_pairs[key] = (committed_at, {"markdown_file": md_path, "lock_file": lock_path, "committed_at": committed_at})

    # Reorganizar a dict por repo
    pairs_per_repo = dict()
    for (repo_full_name, _, _), (_, pair) in latest_pairs.items():
        repo_entry = pairs_per_repo.setdefault(repo_full_name, [])
        repo_entry.append(pair)

    # Por cada repo, quedarnos SOLO con el par con el commit más reciente si hay varios pares
    result_per_repo = dict()
    for repo_full_name, entries in pairs_per_repo.items():
        if len(entries) == 1:
            result_per_repo[repo_full_name] = [
                {"markdown_file": entries[0]["markdown_file"], "lock_file": entries[0]["lock_file"]}
            ]
        else:
            # Elegir solo el de commit más reciente
            last = max(entries, key=lambda x: x["committed_at"])
            result_per_repo[repo_full_name] = [
                {"markdown_file": last["markdown_file"], "lock_file": last["lock_file"]}
            ]

    # Exportar
    output_path = os.path.join(os.path.dirname(__file__), "..", "output", "repo_markdown_lock_pairs.json")
    with open(output_path, "w") as f:
        json.dump(result_per_repo, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
