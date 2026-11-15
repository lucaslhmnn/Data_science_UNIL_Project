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

Write content in the section files; `report.qmd` holds the header, the structure, the AI statement and
the appendices. No gap is left to fill (no `TO FILL BY TEAM` marker remains).

## Requirements

- [Quarto CLI](https://quarto.org/docs/get-started/) (`quarto --version` to check).
- Python 3 with Jupyter, so Quarto can run the Python chunks: `pip install jupyter`.
  These are not in the repo `requirements.txt` yet.
- Internet access at render time: the citation style (`csl`) is downloaded from GitHub.

## Render

From this folder:

```bash
quarto render report.qmd          # writes update_Groupe_L.html next to report.qmd
quarto preview report.qmd         # live preview in the browser, re-renders on save
```

Only HTML is enabled. The `pdf` and `docx` formats are commented out in the YAML header of
`report.qmd`; uncomment them to render those formats.

`update_Groupe_L.html` (name set by `output-file` in the YAML header, as required for the Moodle upload) is
self-contained (`self-contained: true`), so it can be shared as a single file.

## Open the HTML report

After rendering, open `update_Groupe_L.html` in any web browser:

```bash
xdg-open update_Groupe_L.html     # Linux
open update_Groupe_L.html         # macOS
start update_Groupe_L.html        # Windows (Command Prompt or PowerShell)
```

You can also double-click `update_Groupe_L.html` in your file manager, or drag it into a browser window.
`quarto preview report.qmd` opens the report in the browser automatically and refreshes it on save.

## Good to know

- The setup chunk takes as project root the first folder, from `report.qmd` upwards, that contains
  `src/`. That is `quarto_report/` itself, not the repo root. Data at the repo root is therefore
  reached with `project_root.parent`, e.g. `project_root.parent / "data" / "processed" / ...`.
- Rendering creates an empty `quarto_report/data/processed/` folder (done by `src/project_setup.py`).
- The code cells read only versioned files (`Data_cleaning/clean/*.parquet`, `EDA/ds_clean.csv`,
  `EDA/ds_clean_roles.json`, the figures and key numbers in `EDA/figures/`, and the model results in
  `Modeles/resultats/`), so the report renders
  after a plain `git pull`, without the raw files. They need `pandas`, `pyarrow` and `scipy`. If
  `EDA/ds_clean.csv` changes, run `python3 EDA/eda.py` before rendering so that the figures and
  `EDA/figures/eda_key_numbers.json` match, then `bash Modeles/run_all.sh` so that the model results
  match too.
- Cite with `@key`, where `key` is an entry of `references.bib`. The list is generated under References.
