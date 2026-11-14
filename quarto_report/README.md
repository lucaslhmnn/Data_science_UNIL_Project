# Quarto report

Project Update report, built from the course template.

## Structure

```
quarto_report/
├── report.qmd          main file: YAML header, setup chunk, includes, AI statement, references, appendices
├── references.bib      bibliography (BibTeX)
├── sections/           one file per section, included by report.qmd in this order:
│   ├── _introduction.qmd
│   ├── _data.qmd
│   ├── _eda.qmd
│   ├── _analysis.qmd
│   └── _conclusion.qmd
└── src/project_setup.py   environment setup, called by the setup chunk (do not edit)
```

Write content in the section files; `report.qmd` only holds the header and the structure. Every gap
still to fill is marked `**[TO FILL BY TEAM: ...]**`: search for `TO FILL BY TEAM` to list them.

## Requirements

- [Quarto CLI](https://quarto.org/docs/get-started/) (`quarto --version` to check).
- Python 3 with Jupyter, so Quarto can run the Python chunks: `pip install jupyter`.
  These are not in the repo `requirements.txt` yet.
- Internet access at render time: the citation style (`csl`) is downloaded from GitHub.

## Render

From this folder:

```bash
quarto render report.qmd          # writes report.html next to report.qmd
quarto preview report.qmd         # live preview in the browser, re-renders on save
```

Only HTML is enabled. The `pdf` and `docx` formats are commented out in the YAML header of
`report.qmd`; uncomment them to render those formats.

`report.html` is self-contained (`self-contained: true`), so it can be shared as a single file.

## Good to know

- The setup chunk takes as project root the first folder, from `report.qmd` upwards, that contains
  `src/`. That is `quarto_report/` itself, not the repo root. Data at the repo root is therefore
  reached with `project_root.parent`, e.g. `project_root.parent / "data" / "processed" / ...`.
- Rendering creates an empty `quarto_report/data/processed/` folder (done by `src/project_setup.py`).
- Code cells that need data not yet built use `#| eval: false`, so the report renders without data.
- Cite with `@key`, where `key` is an entry of `references.bib`. The list is generated under References.
