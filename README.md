# GHAW-H: GitHub Agentic Workflow Histories

[![Paper](https://img.shields.io/badge/paper-PDF-B31B1B?logo=adobeacrobatreader&logoColor=white)](docs/assets/GHAW-H.pdf?v=420906b)
[![Dataset](https://img.shields.io/badge/dataset-Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/datasets/pavtch/GHAW-H)
[![Website](https://img.shields.io/badge/project-website-162A46)](https://pavt.github.io/GHAW-H/)
[![License: CC BY 4.0](https://img.shields.io/badge/license-CC%20BY%204.0-2D7F75)](LICENSE)

GHAW-H is a research dataset describing the observable evolution of GitHub Agentic Workflows (GH-AW) in early-adopter open-source repositories. It connects repository metadata with versioned workflow Markdown specifications and their aligned lock-file snapshots.

This public repository is the dataset companion package. It contains documentation, schema material, figures, and executable notebooks. The Parquet tables are hosted on [Hugging Face](https://huggingface.co/datasets/pavtch/GHAW-H).

## Dataset at a glance

| Repositories | Source histories | Markdown versions | Lock snapshots |
| ---: | ---: | ---: | ---: |
| 262 | 604 | 2,820 | 2,820 |

The published `source_history` profile contains five relational tables:

| Table | Rows | Description |
| --- | ---: | --- |
| `repository` | 262 | GitHub repository metadata observed from the repository API. |
| `source_markdown_file_history` | 604 | Longitudinal grouping for versions of the same GH-AW Markdown file. |
| `source_markdown_file_snapshot` | 2,820 | Immutable observed Markdown states. |
| `source_markdown_file_version` | 2,820 | Ordered positions linking snapshots to commits and histories. |
| `lock_file_snapshot` | 2,820 | Matching `.lock.yml` states recovered at the same commits. |

## GitHub Agentic Workflows Challenge at NLBSE 2027

GHAW-H is the dataset for the GitHub Agentic Workflows Challenge hosted at [NLBSE 2027](https://nlbse2027.github.io/), the 6th International Workshop on Natural Language-based Software Engineering, co-located with [ICSE 2027](https://conf.researchr.org/home/icse-2027) in Dublin, Ireland.

| Milestone | Date |
| --- | --- |
| Paper submission | November 13, 2026 |
| Author notification | December 11, 2026 |
| Camera-ready | January 29, 2027 |

All deadlines are Anywhere on Earth (AoE). [Read the full challenge call](https://pavt.github.io/GHAW-H/calls/nlbse-2027-ghaw-challenge/).

## Example notebooks

The notebooks download the current dataset directly from `pavtch/GHAW-H`. No GitHub authorization is required.

| Description | Notebook | Open in Colab |
| --- | --- | --- |
| Basic loading and joins | [load_GAWD.ipynb](notebooks/load_GAWD.ipynb) | [Open in Colab](https://colab.research.google.com/github/pavt/GHAW-H/blob/main/notebooks/load_GAWD.ipynb) |
| Dataset overview | [dataset_overview.ipynb](notebooks/dataset_overview.ipynb) | [Open in Colab](https://colab.research.google.com/github/pavt/GHAW-H/blob/main/notebooks/dataset_overview.ipynb) |
| Repository language usage | [language_usage.ipynb](notebooks/language_usage.ipynb) | [Open in Colab](https://colab.research.google.com/github/pavt/GHAW-H/blob/main/notebooks/language_usage.ipynb) |
| File-version histories | [history_data.ipynb](notebooks/history_data.ipynb) | [Open in Colab](https://colab.research.google.com/github/pavt/GHAW-H/blob/main/notebooks/history_data.ipynb) |

## Load a table

```python
import pandas as pd

base = "https://huggingface.co/datasets/pavtch/GHAW-H/resolve/main/data"
repository = pd.read_parquet(f"{base}/repository.parquet")
versions = pd.read_parquet(f"{base}/source_markdown_file_version.parquet")
```

## Schema

![GHAW-H entity-relationship diagram](schema/gh-aw-er-v0.1.svg)

The detailed [table dictionary](schema/table_dictionary.md) documents every public field.

## License

The release metadata declares CC BY 4.0. Content originating from source repositories remains subject to the copyright and license terms of those repositories. Users are responsible for checking source-specific terms before redistributing extracted artifacts.

## Citation

Please cite the archived GHAW-H v0.1.2 dataset release. Machine-readable metadata is provided in [`CITATION.cff`](CITATION.cff).

> Valenzuela-Toledo, P., Kehrer, T., & Panichella, S. (2026). *GHAW-H: A Dataset of GitHub Agentic Workflow Histories* (Version v0.1.2) [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.22084012

```bibtex
@dataset{valenzuela_toledo_ghaw_h_2026,
  author    = {Valenzuela-Toledo, Pablo and Kehrer, Timo and Panichella, Sebastiano},
  title     = {{GHAW-H}: A Dataset of GitHub Agentic Workflow Histories},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v0.1.2},
  doi       = {10.5281/zenodo.22084012},
  url       = {https://doi.org/10.5281/zenodo.22084012}
}
```
