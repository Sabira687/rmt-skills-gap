# rmt-skills-gap

Research Methods and Tools, Astana IT University, group SE-2424.
Team: Fariza Arstanbek, Sabira Kurbankhozha.

Comparative content analysis of entry-level IT vacancies on hh.kz (Kazakhstan) and the public
Educational Programme documents of three AITU bachelor programmes: Software Engineering,
Cybersecurity, Big Data Analysis. Unit of analysis: one vacancy.

## Folder structure

| Path | Contents | Status |
|---|---|---|
| `code/hh_collector_v2.user.js` | Tampermonkey userscript: harvests search-result cards, saves full vacancy texts, exports JSON | instrument |
| `code/rules.py` | Screening and assignment protocol (patterns, thresholds, `CHANGELOG` of every rule change) | instrument |
| `code/pipeline.py` | Screening, assignment, deduplication, contact masking, data-quality report, accuracy-check sample | instrument |
| `code/taxonomy_categories_v1.md` | 19 level-1 skill categories (coding scheme) | instrument |
| `code/skills_dictionary_v1.csv` | Level-2 skills dictionary (skill and synonym patterns per category), frozen as `v1-frozen-2026-10-30` | instrument |
| `code/coding.py` | Codes vacancies and programme text with the dictionary (0/1 per category); `CHANGELOG` of the dictionary | instrument |
| `code/programmes_extract.py`, `code/ocr_pdf.swift` | Extract the English text of each cycle of disciplines from the programme PDFs (text layer, or macOS Vision OCR for the scanned SE document) | instrument |
| `code/analyze.py` | D, C, G, U, Wilson and bootstrap intervals, verdicts for ER1-ER6, sensitivity, registry of reported numbers | analysis |
| `code/figures.py` | Draws the A4 figures from the files written by `analyze.py` and `pipeline.py` | analysis |
| `data/raw/programmes/` | Programme documents (PDF) as downloaded + `access_log.txt` (source URLs, access dates) | **raw, never edited** |
| `data/raw/vacancies/sessionN_*/` | `hh_cards_*.json`: search-result cards exactly as exported by the userscript | **raw, never edited** |
| `data/processed/sessionN_*/` | Everything produced by `pipeline.py` from the raw files (see below) | working copy, reproducible |
| `data/processed/programmes/` | Data extracted from the programme documents: graduate positions, English text per cycle of disciplines (`cycles_*.csv`), coding (`cycle_skills.csv`), OCR text of the scanned SE document | working copy |
| `data/processed/combined_s1-s2/` | Final dataset of sessions 1 and 2 together (68 vacancies), its quality files and the 0/1 skill coding (`vacancy_skills.csv`) | **analysed in Assignment 4** |
| `data/processed/analysis_s1-s2/` | Output of `analyze.py`: `D.csv`, `C.csv`, `G.csv`, `U.csv`, `er_verdicts.csv`, `rank_stability.csv`, `sensitivity.csv`, `results_numbers.csv` | results |
| `data/survey/` | Student survey (run by the team partner) | separate instrument |
| `logs/research_log.csv` | Dated research diary: what was done, by whom, problems, changes | log |
| `logs/expected_results_2026-10-24.md` | Expected results (T9) and method-related expectations (T10), fixed before data collection | fixed, never edited |
| `logs/searches_session1.txt`, `logs/searches_session2.txt` | hh.kz search URLs and result counts per session | log |
| `logs/accuracy_check_session1.csv` | Manual check of 30 sampled screening decisions (session 1) | log |
| `logs/coding_check_sample.csv`, `logs/coding_check_summary.csv` | Manual check of the skills dictionary on 20 vacancies and its result | log |
| `logs/pilot/` | Pilot harvest (1 page, 99 cards) | log |
| `figures/` | Screenshots of the study used in the report (`FigNN_*.png`) | evidence |
| `figures/a4/` | Charts of the results drawn by `code/figures.py` (`A4_FigNN_*.png`) | results |
| `_private/` | Full vacancy texts as exported (may contain recruiter contacts). Not published, excluded by `.gitignore` | private |

### Files in `data/processed/sessionN_*/`

| File | Produced by | What it is |
|---|---|---|
| `cards_raw.csv` | `export-csv` | Readable copy of the raw cards JSON, one row per card, no changes |
| `cards_screened.csv` | `candidates` | Every card with the card-stage decision and reason |
| `candidates.txt` | `candidates` | IDs whose full text is collected |
| `final_dataset.csv` / `.json` | `final` | **The dataset analysed in Assignment 4**: included vacancies with programme, metadata, hh key skills and link; vacancy texts are not published (their copy with masked contacts is `_private/sessionN_*/final_dataset_full.*`) |
| `screening_log.csv` | `final` | Full-text-stage decision and reason for every candidate |
| `report.md` | `final` | Screening flow and distribution by programme |
| `quality.md`, `data_dictionary.csv`, `cleaning_log.csv`, `t10_quality_shares.csv` | `quality` | Data dictionary, cleaning log, data-quality shares compared with T10 |

## Reproducing the processing

Python 3.9+, standard library only. Run from the repository root.

```bash
python3 code/pipeline.py candidates --cards data/raw/vacancies/session1_2026-10-23/hh_cards_*.json --out data/processed/session1_2026-10-23/
python3 code/pipeline.py final --cards data/raw/vacancies/session1_2026-10-23/hh_cards_*.json --full _private/session1_2026-10-23/hh_full_*.json --out data/processed/session1_2026-10-23/
python3 code/pipeline.py quality --cards data/raw/vacancies/session1_2026-10-23/hh_cards_*.json --full _private/session1_2026-10-23/hh_full_*.json --out data/processed/session1_2026-10-23/
python3 code/pipeline.py export-csv --json data/raw/vacancies/session1_2026-10-23/hh_cards_*.json --out data/processed/session1_2026-10-23/cards_raw.csv
```

Collection steps in the browser (userscript): on a search page **N** harvests the page and opens the next one,
**E** exports the cards; on a vacancy page **I** imports the IDs from `candidates.txt`, **G** starts the queue,
**S** saves the vacancy and opens the next one, **X** skips it, **E** exports the full texts.

## Analysis (Assignment 4)

Sessions 1 and 2 are merged by passing the files of both sessions to the same commands (cards and full texts are merged by
vacancy ID). `pipeline.py` and `coding.py` use the standard library only; `figures.py` needs matplotlib (`python3 -m venv .venv2 && .venv2/bin/pip install matplotlib pypdf`).
`ocr_pdf.swift` needs macOS (Vision framework, no installation). Run from the repository root.

```bash
# 1. merged dataset of sessions 1 and 2 (cards of session 2 contain all cards of session 1)
python3 code/pipeline.py final --cards data/raw/vacancies/session2_2026-10-30/hh_cards_*.json --full _private/session1_2026-10-23/hh_full_*.json _private/session2_2026-10-30/hh_full_*.json --out data/processed/combined_s1-s2/
python3 code/pipeline.py quality --cards data/raw/vacancies/session2_2026-10-30/hh_cards_*.json --full _private/session1_2026-10-23/hh_full_*.json _private/session2_2026-10-30/hh_full_*.json --check logs/accuracy_check_session1.csv --out data/processed/combined_s1-s2/
# 2. programme documents: English text per cycle of disciplines (SE is a scan: OCR first)
swift code/ocr_pdf.swift data/raw/programmes/OP_SoftwareEngineering_2026-2029.pdf 1 101 0 data/processed/programmes/ocr/OP_SoftwareEngineering_ocr.txt
python3 code/programmes_extract.py --programme "Software Engineering" --text data/processed/programmes/ocr/OP_SoftwareEngineering_ocr.txt --first 14 --last 47 --union --out data/processed/programmes/cycles_se.csv
python3 code/programmes_extract.py --programme "Cybersecurity" --pdf data/raw/programmes/OP_Cybersecurity_2026.pdf --first 17 --last 84 --union --out data/processed/programmes/cycles_cyber.csv
python3 code/programmes_extract.py --programme "Big Data Analysis" --pdf data/raw/programmes/OP_BigDataAnalysis_2025-2028.pdf --first 14 --last 58 --union --out data/processed/programmes/cycles_bda.csv
# 3. coding with the skills dictionary
python3 code/coding.py cycles --cycles data/processed/programmes/cycles_se.csv data/processed/programmes/cycles_cyber.csv data/processed/programmes/cycles_bda.csv --out data/processed/programmes
python3 code/coding.py vacancies --full _private/combined_s1-s2/final_dataset_full.csv --out data/processed/combined_s1-s2
# 4. results and figures (fixed seed, 2000 bootstrap repetitions)
python3 code/analyze.py --vacancies data/processed/combined_s1-s2/vacancy_skills.csv --cycles data/processed/programmes/cycle_skills.csv --out data/processed/analysis_s1-s2
.venv2/bin/python code/figures.py --an data/processed/analysis_s1-s2 --sessions data/processed/session1_2026-10-23 data/processed/session2_2026-10-30 --combined data/processed/combined_s1-s2 --vacancies data/processed/combined_s1-s2/vacancy_skills.csv --t10 data/processed/combined_s1-s2/t10_quality_shares.csv --out figures/a4
```

Definitions used by `analyze.py` (also in its docstring): D_c is the share of a programme's vacancies that mention category c;
C_c is 1 if c is mentioned in the English text of the programme (strict: mandatory cycles only; soft: mandatory and elective cycles);
G_c = D_c x (1 - C_c); U = sum D_c (1 - C_c) / sum D_c. Coverage is computed per cycle of disciplines, not per discipline,
because discipline boundaries are not reliable in the PDFs.

## Data handling

- Raw files are never edited; every derived file is regenerated by the commands above.
- Full vacancy texts are not published (hh.kz user agreement restricts copying and reuse of site content);
  they stay in `_private/`, where phone numbers, e-mails, messenger links and names after contact labels are
  masked as `[contact]` in every derived file. Each published vacancy keeps its hh.kz link.
- No applicant data or résumés are collected.

## Environment

macOS 14.6.1 (arm64), Python 3.14.5, matplotlib 3.11.2 (figures only), git 2.39.5, Google Chrome 155.0.8059.86 with Tampermonkey 5.5.1, userscript v2.2.
