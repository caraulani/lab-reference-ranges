---
license: cc-by-4.0
pretty_name: Lab Reference Ranges
language:
- en
- de
- no
tags:
- reference-intervals
- laboratory-medicine
- clinical-chemistry
- haematology
- harmonisation
size_categories:
- n<1K
configs:
- config_name: ranges
  data_files: data/ranges.csv
- config_name: sources
  data_files: data/sources.csv
- config_name: variation_summary
  data_files: data/variation_summary.csv
- config_name: discordance_examples
  data_files: data/discordance_examples.csv
---

# Lab Reference Ranges

Interactive version: https://lifefrom.ai/research/open-data/lab-ranges

How much do the reference intervals printed on lab reports differ between laboratories for the same test? This dataset is an open, sourced snapshot that lets you check.

It holds 510 adult intervals for 52 blood analytes. They come from public documents of 10 hospital laboratories in the United Kingdom, Germany, New Zealand and the United States, and from two harmonisation bodies: the UK Pathology Harmony group (2011) and the Nordic Reference Interval Project (NORIP, as published in 2004). Every row says where it came from: document, page, URL and access date (2026-11-25). Each source file was archived with its SHA-256.

Version 1.0.0, released 2026-11-25, by LifeFrom (https://lifefrom.ai).

## What it shows

For a 40-year-old adult, the lowest and highest printed limits across the laboratories in this snapshot were:

| Analyte | Sex | Labs | Lower limits | Upper limits |
|---|---|---|---|---|
| Ferritin | women | 9 | 9 to 30 µg/L | 112 to 337 µg/L |
| Ferritin | men | 9 | 15 to 34 µg/L | 200 to 400 µg/L |
| TSH | both | 8 | 0.2 to 0.4 mIU/L | 3.0 to 4.94 mIU/L |
| Free T4 | both | 7 | 9 to 12.8 pmol/L | 19 to 22.7 pmol/L |
| Vitamin B12 | both | 6 | 182 to 232 ng/L | 692 to 1245 ng/L |
| HbA1c | both | 4 | 20 to 29 mmol/mol | 38 to 42 mmol/mol |
| Total testosterone | men | 7 | 5.72 to 11.4 nmol/L | 26.14 to 32 nmol/L |
| ALT | men | 9 | (most labs print no lower limit) | 35 to 50 U/L |
| GGT | men | 8 | (several print no lower limit) | 38 to 71 U/L |
| Potassium | both | 8 | 3.4 to 3.7 mmol/L | 4.5 to 5.3 mmol/L |
| Sodium | both | 8 | 133 to 136 mmol/L | 145 to 146 mmol/L |

Full figures are in `data/variation_summary.csv`.

Concrete examples, taken from `data/discordance_examples.csv`:

- Ferritin 20 µg/L in a woman is below the printed interval at Leeds Teaching Hospitals (30–337 µg/L) and inside it at Universitätsklinikum Essen (9–145 µg/L).
- TSH 4.0 mIU/L is above the printed interval at Universitätsklinikum Essen (0.3–3.0) and inside it at Oxford University Hospitals (0.35–4.94).
- Vitamin B12 200 ng/L is below the printed interval at the University of Iowa (232–1245 ng/L) and inside it at Synnovis, London (182–692 ng/L).
- Total testosterone 10 nmol/L in a man is below the printed interval at Maidstone and Tunbridge Wells NHS Trust (11.4–27.9) and inside it at Universitätsklinikum Essen (5.72–26.14).

Read these with the limitations below. Some differences come from the specimen (serum or plasma), the assay, the document's age, or how the interval was derived, not only from local choice.

## Who it is for

- Researchers working on harmonisation of reference intervals (Pathology Harmony, AACB, NORIP and similar efforts).
- Laboratory scientists comparing their intervals with peers.
- Educators showing why the same number can be flagged in one report and not another.
- Developers who display reference intervals and need to know they are local.

It records what laboratories print. It does not propose intervals or rank them.

## Files

| File | What it is |
|---|---|
| `data/ranges.csv` | One row per printed interval (510 rows). |
| `data/sources.csv` | One row per archived source file (54 files from 12 sources), with URL, Wayback capture, SHA-256 and the terms-of-use finding. |
| `data/variation_summary.csv` | Per analyte and sex: number of labs, minimum and maximum lower and upper limits, spread, ratio, and the harmonised intervals beside them. |
| `data/discordance_examples.csv` | Values that are outside one lab's printed interval and inside another's (176 rows). |
| `web/lab-ranges.json` | Compact JSON for the lifefrom.ai website. |
| `transcriptions/` | The hand transcriptions the build reads, one CSV per source, plus `_interval_kinds.csv`. |
| `sources/` | `registry.csv` (lab, document, terms), `files.csv` (archived files), `excluded_sources.csv`. |
| `scripts/` | `build.sh` regenerates everything from the archive and runs the tests. |
| `tests/` | Checks (pytest). |

### `data/ranges.csv` columns

| Column | Meaning |
|---|---|
| `row_id` | `<source_id>-<n>`; stable within this version. |
| `source_id`, `lab`, `country`, `organisation_type` | Who published the interval. `organisation_type` is hospital laboratory, hospital laboratory network or harmonisation body. |
| `analyte_printed` | Test name as printed. |
| `marker_slug`, `marker_name` | LifeFrom marker key and name (from LifeFrom release 1 `markers.csv`). |
| `specimen` | Specimen as printed, or `not stated`. |
| `sex` | `M`, `F` or `all` (one interval for both). |
| `age_printed`, `age_min_years`, `age_max_years` | Age band as printed, and its bounds in years where the document gives them (blank = open). |
| `range_as_printed` | The interval text as it appears in the document. Decimal commas are kept. |
| `low`, `high` | Limits as numbers in the printed unit. Blank when the document prints only one side (for example `<35`). |
| `unit_printed`, `unit_normalised` | Unit as printed, and a normalised spelling. |
| `method_or_platform` | Method or analyser when the document states it. |
| `interval_kind` | `reference_interval`, `decision_limit` (clinical cut-off such as NICE PSA thresholds) or `target` (for example ESC lipid targets). `kind_note` says why. |
| `unit_common`, `low_common`, `high_common` | Limits in one unit per analyte. Blank when no factor exists (HbA1c % vs mmol/mol, prolactin ng/mL vs mIU/L). |
| `conversion_factor`, `conversion_basis` | Factor applied and where it came from. |
| `applies_at_age_40` | Whether the row applies to a 40-year-old. The summary uses only these rows. |
| `source_url`, `source_location` | Original URL and page (or file and page). |
| `document_title`, `document_version` | As printed. |
| `accessed` | 2026-11-25 for every row. |
| `archive_path`, `archive_sha256`, `wayback_url` Path of the archived copy relative to the folder that contains this repository (the archive is not included), its SHA-256, and an existing Wayback Machine capture if one was found. |

### `data/variation_summary.csv` columns

`marker_slug`, `marker_name`, `sex`, `unit_common`, `n_labs`, `n_countries`, `labs`; for each side (`lower_`, `upper_`): `n_with_`, `min`, `max`, `spread` (max minus min), `max_over_min`, and which labs hold the minimum and maximum; `harmonised_intervals_for_comparison` (Pathology Harmony and NORIP values, not counted in the lab figures).

### `data/discordance_examples.csv` columns

`marker_slug`, `marker_name`, `sex`, `direction`, `value`, `unit`, the flagged lab (name, country, interval as printed, unit, value in that unit), the lab where the value is inside the interval (same fields), `limit_gap_percent`, a plain `statement`, the two `row_id`s and the two source URLs.

## How it was built

1. Public documents were found by web search, downloaded with robots.txt respected, and archived under `../_raw/ranges/<source>/` (outside this repository) with SHA-256. Three were read from existing Wayback Machine captures because the live file had moved or blocked our client. No new captures were requested.
2. Each site's terms of use were read where they could be. Six sources were excluded because their terms forbid reuse (see `sources/excluded_sources.csv`).
3. Adult rows for the analytes in scope were copied by hand into `transcriptions/<source>.csv`, with the page each row came from. PDF tables that the text layer garbled were checked against a rendered page image.
4. The build checks every row against the archived text: the printed interval and both limits must appear on the cited page.
5. Units are converted only with factors from LifeFrom release 1 `units.csv` or by pure unit arithmetic (for example g/dL to g/L).
6. The comparison uses reference intervals only (not decision limits or targets), from laboratories only, for rows that apply to a 40-year-old. An interval printed for both sexes counts for each sex.

`METHODS.md` has the details needed to rebuild the numbers.

## Limitations

- **Small, non-random sample.** 10 laboratories and 2 harmonisation bodies, chosen because their documents were public and their terms allowed reuse. UK and German labs make up most rows. Six further sources were left out because their terms forbid reuse.
- **Specimen and method differ.** Some labs report serum, others lithium-heparin plasma, and many documents do not say. Plasma potassium, for example, runs lower than serum potassium. Assays differ (for example Jaffe vs enzymatic creatinine; Roche vs Siemens immunoassays). A difference in printed limits is not always a difference in what a result means.
- **Document dates differ.** Essen's list is from October 2022; Pathology Harmony from 2011; NORIP from 2004; Maidstone and Tunbridge Wells from January 2025. A lab may have changed its intervals since.
- **Derivation differs.** Some intervals are manufacturer ranges, some local studies, some literature values, and some lower limits are set by clinical guidance (for example ferritin 30 µg/L at Leeds and Vermont). The dataset records what is printed, not how it was derived, except where the document says.
- **Age choice.** The summary uses rows that apply at age 40. Other ages can give other spreads.
- **One-sided intervals.** Where a lab prints `<35`, it has no lower limit, and the summary counts it only on the upper side.
- **Transcription.** Rows were copied by hand. The build checks that each printed interval and its limits appear on the cited page; it does not check that a row is assigned to the right analyte or sex.

## How to cite

LifeFrom; Caraulani J. Lab Reference Ranges: a sourced snapshot of published adult reference intervals from hospital laboratories and harmonisation bodies. Version 1.0.0. 2026-11-25. https://github.com/caraulani/lab-reference-ranges

Please also cite the source documents listed in `data/sources.csv`.

## Licence

Data under CC BY 4.0 and code under MIT (see `LICENSE`). The limits are facts copied from documents published by the laboratories and bodies named in `data/sources.csv`. Those documents are not redistributed here. Canterbury Health Laboratories rows are Crown copyright (Health New Zealand | Te Whatu Ora), reproduced under its terms with acknowledgement.
