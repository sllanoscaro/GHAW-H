# GitHub Agentic Workflows Challenge

The 2027 GitHub Agentic Workflows Challenge invites researchers to investigate
how developers specify, configure, and evolve natural-language-based agentic
workflows in real-world GitHub repositories.

[GitHub Agentic Workflows](https://github.github.com/gh-aw/) (GH-AW) are an
emerging form of repository automation in which developers define agentic
workflows in Markdown and execute them through GitHub Actions. These workflows
combine natural-language instructions with structured configuration, allowing AI
agents to interact with repositories and support software engineering tasks.

The challenge focuses on the empirical study of these artifacts and their
evolution, with particular attention to the role of natural language in
software engineering automation.

## Dataset

We release GHAW-H, a dataset of GitHub Agentic Workflow Histories. GHAW-H covers
262 public GitHub repositories that used GH-AW between February 13 and June 6,
2026. The dataset connects agentic workflow specifications with their compiled
representations and version histories.

GHAW-H includes 604 source histories, 2,820 source Markdown file snapshots,
2,820 source-version records, and 2,820 lock-file snapshots. The dataset
contains natural-language instructions written in Markdown, structured
frontmatter declarations, compiled GitHub Actions workflow definitions in YAML,
and historical versions of these artifacts.

- `Ready-made dataset`: GHAW-H provides repository-level and file-level artifacts
  for studying GitHub Agentic Workflows and their histories.
- `Source specifications`: Markdown files contain natural-language instructions
  and structured frontmatter used to define agentic workflows.
- `Compiled workflows`: Lock-file snapshots provide the compiled GitHub Actions
  workflow definitions associated with the source specifications.
- `Histories`: Source-version records allow researchers to study how workflow
  specifications and compiled representations evolve over time.

The dataset and documentation can be found on the
[GHAW-H website](https://pavt.github.io/GHAW-H/),
[GitHub repository](https://github.com/pavt/GHAW-H),
[Hugging Face](https://huggingface.co/datasets/pavtch/GHAW-H), and
[Zenodo](https://zenodo.org/records/22084012).

## Additional Data Usage

Participants are allowed to use additional public data beyond what is included
in GHAW-H. For example, participants may use GitHub APIs to collect repository
metadata, workflow execution information, issue or pull request data, source
code context, or other public project information relevant to their study.

Any additional data sources must be clearly documented, including the collection
or extraction procedure, the date of collection, and how the additional data was
linked to GHAW-H. Participants should also clearly identify the version of
GHAW-H used in their study.

## Baselines

This challenge is an open research challenge and does not prescribe a single
baseline model or ranking metric. Participants may define baselines appropriate
to their research question, such as keyword-based analyses, repository mining
heuristics, NLP pipelines, machine-learning models, LLM-based methods, or manual
coding protocols.

Submissions should justify the selected baseline or comparison point and explain
how it supports the research question being investigated.

## Goal

Use GHAW-H to investigate a research question related to natural language and
agentic workflows in software engineering. The goal is to produce reproducible
research that improves our understanding of how developers specify, configure,
analyze, or evolve agentic workflows in practice.

Example research directions include, but are not limited to:

- How do developers express software engineering tasks and goals in natural
  language when defining agentic workflows?
- How are GH-AW capabilities, permissions, triggers, tools, and execution
  options configured in practice?
- What characteristics distinguish different types of agentic workflow
  specifications?
- How are Markdown specifications reflected in their compiled GitHub Actions
  workflow definitions?
- How do natural-language instructions, frontmatter configurations, and compiled
  workflows change over time?
- How do changes to natural-language instructions relate to changes in
  structured configuration and compiled workflow definitions?
- How do GH-AW specifications differ from other forms of agent or software
  automation configuration?
- How can NLP, machine learning, LLM-based, or other analysis techniques support
  the study, understanding, or development of agentic workflows?

## Challenge Organizers

The GitHub Agentic Workflows Challenge is organized by:

- [Pablo Valenzuela-Toledo](https://pavt.github.io/), University of Bern and
  Universidad de La Frontera
- [Timo Kehrer](https://seg.inf.unibe.ch/team/timo-kehrer/), University of Bern
- [Sebastiano Panichella](https://spanichella.github.io/), University of Bern
  and AI4I

## Participation Requirements

To participate in the challenge, authors must write a paper describing a study,
method, tool, or empirical analysis based on GHAW-H.

The paper should describe:

- The software engineering problem or research question being investigated.
- The role of natural language in the investigated problem.
- The GHAW-H artifacts used in the study.
- The version of GHAW-H used.
- Any additional data sources and how they were collected.
- The study design, methods, tools, and analysis protocol.
- The main findings or resulting contribution.
- The implications of the results for Natural Language-based Software
  Engineering.
- A link to code, data, notebooks, tools, or other artifacts with documentation
  on how to reproduce the results, whenever possible.

Submit the paper by the deadline using the
[NLBSE 2027 submission site](https://icse2027-nlbse.hotcrp.com/). All
submissions must conform to the NLBSE 2027 submission requirements and the
[ICSE 2027 formatting and submission instructions](https://conf.researchr.org/home/icse-2027).

Important dates:

- Paper submission: November 13, 2026
- Author notification: December 11, 2026
- Camera-ready: January 29, 2027
- Deadlines: Anywhere on Earth (AoE)

## Submission Acceptance & Challenge

Submissions will be evaluated and accepted based on relevance, correctness,
clarity, and reproducibility.

Submissions will be judged on:

- Clarity and completeness of the paper.
- Relevance of the research question to Natural Language-based Software
  Engineering.
- Appropriate and well-documented use of GHAW-H.
- Soundness of the study design, method, or tool.
- Correct documentation of additional data sources, when used.
- Clear reporting of findings, limitations, and implications.
- Availability and reproducibility of code, data, notebooks, or tools whenever
  possible.
- Quality of artifact documentation.

Accepted papers will appear in the NLBSE '27 proceedings.

## Ranking Details

The GitHub Agentic Workflows Challenge is not ranked by a single quantitative
metric. Submissions will be assessed according to the relevance of the research
question, the soundness of the method, the appropriateness of the use of
GHAW-H, and the reproducibility of the reported results.

## Paper / Reference Publication

The reference paper,
[GHAW-H: A Dataset of GitHub Agentic Workflow Histories](https://pavt.github.io/GHAW-H/assets/GHAW-H.pdf?v=420906b),
describes the construction, structure, and intended research uses of GHAW-H.
Participants should consult the paper when designing studies and cite it
together with the archived dataset release; please see BibTeX entries below.

## Citing Relevant Work

Please cite the archived dataset release if participating in the GitHub Agentic
Workflows Challenge:

```bibtex
@dataset{valenzuela_toledo_ghaw_h_2026,
  author    = {Pablo Valenzuela{-}Toledo and Timo Kehrer and Sebastiano Panichella},
  title     = {{GHAW-H}: A Dataset of GitHub Agentic Workflow Histories},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v0.1.2},
  doi       = {10.5281/zenodo.22084012},
  url       = {https://doi.org/10.5281/zenodo.22084012}
}
```

Please also cite the reference paper when available:

```bibtex
@inproceedings{valenzuela_toledo_ghaw_h_2027,
  author    = {Pablo Valenzuela{-}Toledo and Timo Kehrer and Sebastiano Panichella},
  title     = {{GHAW-H}: A Dataset of GitHub Agentic Workflow Histories},
  booktitle = {{IEEE/ACM} International Workshop on Natural Language-Based Software
               Engineering, NLBSE@ICSE 2027, Dublin, Ireland},
  year      = {2027},
  url       = {https://pavt.github.io/GHAW-H/assets/GHAW-H.pdf?v=420906b},
  note      = {Publication metadata to be updated}
}
```

## Resources

- Challenge call: https://pavt.github.io/GHAW-H/calls/nlbse-2027-ghaw-challenge/
- Dataset website: https://pavt.github.io/GHAW-H/
- GitHub repository: https://github.com/pavt/GHAW-H
- Hugging Face dataset: https://huggingface.co/datasets/pavtch/GHAW-H
- Zenodo record: https://zenodo.org/records/22084012
- DOI: https://doi.org/10.5281/zenodo.22084012
- Reference paper: https://pavt.github.io/GHAW-H/assets/GHAW-H.pdf?v=420906b
