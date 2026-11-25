"""Checks for the lab-reference-ranges release. Run: uv run --with pytest --with pdfplumber pytest -q"""
import csv, hashlib, json, math, pathlib, re, subprocess, sys
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "_raw"
DATA = ROOT / "data"


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


RANGES = read(DATA / "ranges.csv")
SOURCES = read(DATA / "sources.csv")
SUMMARY = read(DATA / "variation_summary.csv")
EXAMPLES = read(DATA / "discordance_examples.csv")
WEB = json.loads((ROOT / "web" / "lab-ranges.json").read_text(encoding="utf-8"))
EXCLUDED = {r["source_id"] for r in read(ROOT / "sources" / "excluded_sources.csv")}
num = lambda s: float(s) if s not in ("", None) else None


def test_counts_are_reported():
    assert len(RANGES) > 400
    assert len({r["source_id"] for r in RANGES}) == 12
    assert len({r["marker_slug"] for r in RANGES}) >= 40


def test_ranges_columns_and_values():
    slugs = {r["marker_slug"] for r in read(RAW / "lifefrom-release-1" / "markers.csv")} if (RAW / "lifefrom-release-1").exists() else None
    for r in RANGES:
        assert r["sex"] in {"M", "F", "all"}, r["row_id"]
        assert r["interval_kind"] in {"reference_interval", "decision_limit", "target"}
        assert r["accessed"] == "2026-11-25"
        assert r["source_url"].startswith(("https://", "http://"))
        assert re.fullmatch(r"[0-9a-f]{64}", r["archive_sha256"])
        assert r["range_as_printed"]
        lo, hi = num(r["low"]), num(r["high"])
        assert lo is not None or hi is not None, r["row_id"]
        if lo is not None and hi is not None:
            assert lo <= hi, r["row_id"]
        if slugs is not None:
            assert r["marker_slug"] in slugs


def test_row_ids_unique():
    ids = [r["row_id"] for r in RANGES]
    assert len(ids) == len(set(ids))


def test_conversions_match_factor():
    for r in RANGES:
        f = num(r["conversion_factor"])
        for a, b in (("low", "low_common"), ("high", "high_common")):
            if f is None:
                assert r[b] == ""
            elif r[a] != "":
                assert math.isclose(num(r[b]), num(r[a]) * f, rel_tol=1e-3, abs_tol=1e-9), r["row_id"]


def test_known_conversions():
    # spot checks against hand arithmetic
    fac = {(r["marker_slug"], r["unit_normalised"]): num(r["conversion_factor"]) for r in RANGES if r["conversion_factor"]}
    assert math.isclose(fac[("albumin-serum", "g/dL")], 10)
    assert math.isclose(fac[("testosterone-total", "ng/mL")], 100 / 28.8184, rel_tol=1e-4)
    assert math.isclose(fac[("vitamin-b12", "pmol/L")], 1.35501, rel_tol=1e-4)
    assert math.isclose(fac[("uric-acid", "mmol/L")], 1000, rel_tol=1e-6)
    assert ("hba1c", "%") not in fac  # % <-> mmol/mol is a formula, not a factor


def test_no_excluded_source_shipped():
    shipped = {r["source_id"] for r in RANGES} | {r["source_id"] for r in SOURCES}
    assert not shipped & EXCLUDED
    assert not list((ROOT / "transcriptions").glob("nswhp*"))


def test_sources_cover_every_row():
    paths = {r["archive_path"] for r in SOURCES}
    for r in RANGES:
        assert r["archive_path"] in paths


@pytest.mark.skipif(not (RAW / "ranges").exists(), reason="raw archive not present")
def test_archive_hashes():
    for s in SOURCES:
        p = ROOT.parent / s["archive_path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == s["sha256"], p


@pytest.mark.skipif(not (RAW / "ranges_text").exists(), reason="text layer not present")
def test_transcriptions_found_in_source_text():
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_transcription import check
    assert sum(check(s) for s in {r["source_id"] for r in RANGES}) == 0


def test_summary_consistent():
    for s in SUMMARY:
        assert int(s["n_labs"]) >= 2
        assert int(s["n_labs"]) == len(s["labs"].split("|"))
        if s["lower_min"]:
            assert num(s["lower_min"]) <= num(s["lower_max"])
        if s["upper_min"]:
            assert num(s["upper_min"]) <= num(s["upper_max"])


def test_discordance_examples_hold():
    by_id = {r["row_id"]: r for r in RANGES}
    assert EXAMPLES
    for e in EXAMPLES:
        x = num(e["value"])
        a, b = by_id[e["flagged_lab_row_id"]], by_id[e["normal_lab_row_id"]]
        assert a["unit_common"] == b["unit_common"] == e["unit"]
        for r in (a, b):
            assert r["interval_kind"] == "reference_interval" and r["applies_at_age_40"] == "yes"
            assert "laboratory" in r["organisation_type"]
        alo, ahi, blo, bhi = (num(a["low_common"]), num(a["high_common"]), num(b["low_common"]), num(b["high_common"]))
        if e["direction"].startswith("below"):
            assert x < alo
        else:
            assert x > ahi
        assert (blo is None or x > blo) and (bhi is None or x < bhi)


def test_web_json_schema():
    assert set(WEB) == {"version", "analytes"}
    n = 0
    for a in WEB["analytes"]:
        assert {"marker_slug", "name", "unit_common", "labs"} <= set(a)
        for l in a["labs"]:
            assert {"lab", "country", "sex", "age", "low", "high", "unit_printed", "low_common", "high_common", "url", "accessed"} <= set(l)
            n += 1
    assert n == len(RANGES)


@pytest.mark.skipif(not (RAW / "ranges_text").exists(), reason="raw archive not present")
def test_build_is_reproducible(tmp_path):
    before = {p.name: p.read_bytes() for p in list(DATA.glob("*.csv")) + [ROOT / "web" / "lab-ranges.json"]}
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "build.py")], check=True, capture_output=True)
    after = {p.name: p.read_bytes() for p in list(DATA.glob("*.csv")) + [ROOT / "web" / "lab-ranges.json"]}
    assert before == after
