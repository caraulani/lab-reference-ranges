# Methods

This file gives enough detail to rebuild every number in the release from the archived sources.

The scripts expect the raw archive in a folder named `_raw` next to this repository (`../_raw/`, relative to the repository root). It holds the downloaded documents (`../_raw/ranges/`), their text layer (`../_raw/ranges_text/`), the terms-of-use pages read (`../_raw/terms/`) and the LifeFrom release 1 marker and unit tables (`../_raw/lifefrom-release-1/markers.csv`, `units.csv`). The archive is not distributed; `sources/files.csv` lists every file with its URL and SHA-256 so it can be re-downloaded and checked.

## 1. Scope

- Adults only. Paediatric rows were not transcribed.
- Blood analytes common on routine reports: ferritin, TSH, free T4, B12, folate, 25-OH vitamin D, HbA1c, glucose, lipids, creatinine, ALT, AST, GGT, ALP, bilirubin, albumin, total protein, CRP, sodium, potassium, chloride, bicarbonate, calcium, phosphate, magnesium, urea, urate, CK, LDH, lipase, amylase, iron, TIBC, transferrin, transferrin saturation, prolactin, SHBG, total testosterone, PSA, morning cortisol, haemoglobin, haematocrit, red and white cell counts, platelets, MCV, neutrophils and lymphocytes. A source contributed only the analytes it prints.
- eGFR was not transcribed: the sources that list it give no reference interval.

## 2. Finding sources

Sources were found by web search on 2026-11-25 for laboratory handbooks and reference-range documents (English, German, Dutch, Norwegian and Romanian queries), and for harmonisation bodies. Only public pages and PDFs were used. No logins, no forms. robots.txt was read for every host before downloading. Two hosts were not fetched because their robots.txt rules excluded us: `pmc.ncbi.nlm.nih.gov` (disallows all crawlers) and `hse.ie` (disallows the crawler class used for this work). One request was made to `path.uiowa.edu/path_handbook/api/` before its robots.txt (`Disallow: /`) was read; its response was not used.

## 3. Archiving

`scripts/fetch.sh <source_id> <url> [name]` downloads one file with curl into `../_raw/ranges/<source_id>/`, makes it read-only, and appends the URL, HTTP status, SHA-256 and UTC time to `../_raw/ranges/fetch_log.tsv`. Failed downloads (404, HTML error pages, a Wayback copy truncated at 1 MiB) were deleted and are not used.

Three documents were read from existing Wayback Machine captures because the live file had moved or refused our client: Synnovis (capture 2026-04-19), Maidstone and Tunbridge Wells (2025-10-28) and the NORIP article in Tidsskriftet (2024-06-05). The raw capture was fetched with the `id_` URL form so the file is byte-identical to what the Archive stored.

`scripts/make_files_table.py` writes `sources/files.csv`: one row per archived file with original URL, URL actually fetched, SHA-256, size, and the closest existing Wayback capture from `https://archive.org/wayback/available` (looked up, never requested). A capture listed there is a pointer; its content may differ from the file we archived.

The archive itself (`../_raw/`) is not part of this repository. The SHA-256 values let anyone who obtains the same files confirm they match.

## 4. Text layer

`scripts/extract_text.py` turns each archived file into `../_raw/ranges_text/<source_id>.txt`:

- PDF: `pdfplumber` (`extract_text(layout=True)`), one block per page headed `===== PAGE <n>/<N> =====`.
- Several PDFs for one source (Ulm publishes one PDF per test): page id `<file stem>-<n>`.
- HTML: tags stripped, table cells joined with ` | `, one block per file (page id `1`, or the file stem when a source has several files).

## 5. Transcription

Rows were copied by hand into `transcriptions/<source_id>.csv` with these fields: `analyte_printed`, `marker_slug`, `specimen`, `sex`, `age_printed`, `age_min_y`, `age_max_y`, `range_as_printed`, `low`, `high`, `unit_printed`, `method`, `page`.

Rules:

- `range_as_printed` is copied from the text layer, including decimal commas and any sex or age label printed on the same line. `low` and `high` use a decimal point.
- One-sided limits (`<35`, `≤ 40`, `>75`) fill only one of `low`/`high`. `<` and `≤` are not distinguished in `low`/`high`; `range_as_printed` keeps the symbol.
- Where a document gives several adult age bands, each band is a row. `age_min_y`/`age_max_y` are filled from the band; a bare "adult" or "Erwachsene" is left open (blank) unless the document gives a lower age.
- Where a PDF table's text layer was ambiguous (multi-column tables at Synnovis; table cells split across lines), the page was rendered to an image with `scripts/render_page.py` and read visually before transcribing. A value spanning both sex columns applies to both sexes.
- `marker_slug` is the LifeFrom release 1 key. Names were matched by meaning (aliases in `aliases.csv` cover most printed names; German, Dutch and Norwegian names were matched by hand).
- `transcriptions/_interval_kinds.csv` marks rows that the document presents as a clinical decision limit (for example NICE PSA referral thresholds, WHO glucose bands) or a target (for example ESC lipid targets, Ulm's vitamin D "Zielbereich"). All other rows are `reference_interval`.

## 6. Verification against the source

`scripts/check_transcription.py` normalises whitespace and dashes and requires that, on the cited page of the text layer, `range_as_printed` occurs and each of `low` and `high` occurs (with either decimal point or decimal comma). The build stops if any row fails. All 510 rows pass.

This check proves the strings are on the page; it does not prove the row is assigned to the right analyte or sex. That assignment was done by reading the document, and for the tables listed in section 5 by reading a rendered page image.

## 7. Units

- `unit_printed` is normalised by a fixed table in `scripts/build.py` (`CANON`), for example `U/l`, `IU/L` → `U/L`; `x109/L`, `/nl`, `Giga/l`, `Tsd./µl` → `10^9/L`; `(no units)`, `l/l` → `L/L` for haematocrit. Where the PDF text layer dropped the µ sign (Oxford), the unit is recorded as `µmol/L (µ lost in text layer)`.
- For each marker, `unit_common` is the most frequent normalised unit among its rows (ties go to the marker's preferred unit).
- A row is converted when both its unit and `unit_common` have a numeric `factor_to_preferred` in LifeFrom release 1 `units.csv` (matching `unit` or `equivalent_forms`), or when the change is pure unit arithmetic: SI prefixes (mmol/L ↔ µmol/L) and the listed exceptions in `ARITHMETIC` (ng/mL or µg/L testosterone to ng/dL, factor 100). The factor is `f(printed unit → preferred) / f(common unit → preferred)`.
- Not converted: HbA1c % ↔ mmol/mol (`units.csv` gives a formula, not a factor) and prolactin ng/mL ↔ mIU/L (no factor). Those rows have blank `*_common` columns.
- Converted values are rounded to 4 significant figures.

## 8. Comparison set

A row enters `variation_summary.csv` and `discordance_examples.csv` when all hold:

1. `interval_kind` is `reference_interval`;
2. the organisation is a hospital laboratory or laboratory network (Pathology Harmony and NORIP are shown beside the lab figures, not counted in them);
3. the row applies at age 40 (`age_min ≤ 40 ≤ age_max`, blanks open);
4. at least one limit could be put in `unit_common`.

For each laboratory, marker and sex, one row is kept: a sex-specific row beats an `all` row; otherwise the first row in transcription order wins (this picks Essen serum glucose over its plasma row). An `all` row counts for both sexes. Groups with fewer than two laboratories are dropped.

Summary statistics per marker and sex: number of labs and countries; for lower and upper limits separately, the minimum, maximum, spread (maximum minus minimum) and ratio (maximum over minimum), and which lab holds each extreme.

## 9. Discordance examples

For each marker and sex, and separately for each side:

- Lower side: lab A has the highest lower limit, lab B the lowest. If B's limit is below A's by at least 2 % of A's limit, a value x is chosen strictly between them (and below B's upper limit). x is below A's interval and inside B's.
- Upper side: lab A has the lowest upper limit, lab B the highest, with the same 2 % rule; x lies strictly between them and above B's lower limit.
- x is the round number closest to the midpoint, trying steps of 1000, 500, 100, 50, 10, 5, 1, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001.
- The 2 % rule stops unit-conversion rounding (for example cortisol 535 nmol/L = 19.39 µg/dL vs 19.5 µg/dL) from producing false examples.
- Only labs with an explicit limit on that side are used.

The test suite re-checks each example against `ranges.csv`.

## 10. Terms of use

Each site's terms were looked for and read where possible (copies in `../_raw/terms/`). Decision rule:

- **Exclude** when the terms forbid reuse of the information or data itself, for example "no portion of the Content may be reproduced in any form", "not to modify the Information" where Information includes data, or database rights with a ban on commercial reuse that a CC BY release would breach.
- **Include, flagged** when the terms cover copying of documents, texts or graphics but do not mention data or facts. Individual reference limits are facts; the documents themselves are not redistributed.
- **Include, terms not read** when no terms page could be found or read.

`data/sources.csv` records the finding and decision per source; `sources/excluded_sources.csv` lists the six excluded sources with the clause that excluded them.

## 11. Rebuild

```sh
./scripts/build.sh
```

This regenerates the text layer, checks SHA-256 of every archived file, checks every transcription, writes all outputs, runs the tests and rewrites `SHA256SUMS`. Without `../_raw/`, `pytest tests` still runs the checks on the shipped files and skips the archive, text-layer and rebuild checks. The build itself makes no network requests. Python 3.10+ and `uv` are needed; pdfplumber is the only non-standard dependency for the build.
