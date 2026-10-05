import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))

def run_script(script_name, extra_args=None):
    src = os.path.join(HERE, "scripts", script_name)
    args = [sys.executable, src, *(extra_args or [])]
    print(f"Ejecutando {script_name}...")
    subprocess.run(args, check=True)

def main():
    run_script("extract_repo_info.py")
    run_script("pair_markdown_locks.py")
    run_script(
        "fetch_prs_from_artifacts.py",
        ["--reuse-runs", "--all-runs"],
    )
    print("Extracción finalizada. Verifique la carpeta output.")

if __name__ == "__main__":
    main()
