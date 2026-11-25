"""Build every output of the lab-reference-ranges release from the transcriptions and the archived sources.

Inputs
  transcriptions/<source_id>.csv     one row per printed interval, copied by hand from the archived document
  transcriptions/_interval_kinds.csv rows that are decision limits or targets rather than reference intervals
  sources/registry.csv               one row per source (lab, country, document, terms finding)
  sources/files.csv                  one row per archived file (URL, SHA-256, Wayback capture)
  ../_raw/lifefrom-release-1/        markers.csv, units.csv (LifeFrom marker list and unit factors)
  ../_raw/ranges/                    the archived files (checked against files.csv SHA-256)
  ../_raw/ranges_text/               text layer made by scripts/extract_text.py

Outputs
  data/ranges.csv, data/sources.csv, data/variation_summary.csv, data/discordance_examples.csv
  web/lab-ranges.json

usage: python -I scripts/build.py
"""
import csv, hashlib, json, math, pathlib, re, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPEN = ROOT.parent
RAW = OPEN / "_raw" / "ranges"
TXT = OPEN / "_raw" / "ranges_text"
LF = OPEN / "_raw" / "lifefrom-release-1"
ACCESSED = "2026-11-25"
VERSION = "1.0.0"
REFERENCE_AGE = 40  # comparison rows are those that apply to a 40-year-old adult
MIN_GAP = 0.02      # limits closer than 2 % of the larger limit are not used for examples (unit-conversion rounding)

sys.path.insert(0, str(ROOT / "scripts"))
from check_transcription import check as check_source  # noqa: E402


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


# ---------------------------------------------------------------- units
CANON = {
    "u/l": "U/L", "iu/l": "U/L",
    "umol/l": "µmol/L", "µmol/l": "µmol/L", "μmol/l": "µmol/L",
    "mmol/l": "mmol/L", "mmol/mol": "mmol/mol", "mmol/mol hb": "mmol/mol",
    "g/l": "g/L", "g/dl": "g/dL", "mg/dl": "mg/dL", "mg/l": "mg/L",
    "µg/dl": "µg/dL", "ug/dl": "µg/dL", "μg/dl": "µg/dL",
    "ng/l": "ng/L", "pg/ml": "pg/mL", "pmol/l": "pmol/L", "nmol/l": "nmol/L",
    "µg/l": "µg/L", "ug/l": "µg/L", "μg/l": "µg/L", "ng/ml": "ng/mL",
    "mu/l": "mIU/L", "miu/l": "mIU/L", "µiu/ml": "µIU/mL", "uiu/ml": "µIU/mL",
    "%": "%", "fl": "fL",
    "x109/l": "10^9/L", "109/l": "10^9/L", "/nl": "10^9/L", "giga/l": "10^9/L", "tsd./µl": "10^9/L",
    "x1012/l": "10^12/L", "1012/l": "10^12/L", "/pl": "10^12/L", "tera/l": "10^12/L", "mio./µl": "10^12/L",
    "(no units)": "L/L", "l/l": "L/L", "ll": "L/L",
}


def canon_unit(printed):
    u = re.sub(r"\s*\(µ lost in text layer\)", "", printed).strip()
    key = u.lower()
    if key not in CANON:
        raise ValueError(f"unit not mapped: {printed!r}")
    return CANON[key]


# Pure unit arithmetic that units.csv does not list for a marker (factor to the marker's preferred unit).
ARITHMETIC = {
    ("testosterone-total", "ng/mL"): (100.0, "unit arithmetic (1 ng/mL = 100 ng/dL)"),
    ("testosterone-total", "µg/L"): (100.0, "unit arithmetic (1 µg/L = 100 ng/dL)"),
    ("total-protein", "g/dL"): (1.0, "same unit"),
    ("ldh", "U/L"): (1.0, "same unit"),
    ("ck-total", "U/L"): (1.0, "same unit"),
    ("tsh", "mIU/L"): (1.0, "same unit"),
    ("mcv", "fL"): (1.0, "same unit"),
    ("transferrin-saturation", "%"): (1.0, "same unit"),
}


def unit_factors():
    """(marker_slug, unit) -> (factor to preferred unit, basis); only rows with a numeric factor."""
    out = {}
    for r in read(LF / "units.csv"):
        if not r["factor_to_preferred"]:
            continue
        f = float(r["factor_to_preferred"])
        forms = [r["unit"]] + [x.strip() for x in r["equivalent_forms"].split("|") if x.strip()]
        for u in forms:
            for cu in {u, CANON.get(u.lower(), u)}:
                out.setdefault((r["marker_slug"], cu), (f, r["factor_basis"]))
    for k, v in ARITHMETIC.items():
        out.setdefault(k, v)
    # SI prefix arithmetic: mmol/L <-> µmol/L, mg/L <-> µg/L etc., derived from a listed unit
    prefix = {"m": 1e-3, "µ": 1e-6, "n": 1e-9, "p": 1e-12}
    for (slug, u), (f, b) in list(out.items()):
        m = re.fullmatch(r"([mµnp])(mol|g)/(L|dL)", u)
        if not m:
            continue
        for p2, scale in prefix.items():
            u2 = f"{p2}{m.group(2)}/{m.group(3)}"
            if (slug, u2) not in out:
                out[(slug, u2)] = (f * scale / prefix[m.group(1)], f"unit arithmetic from {u} ({b})")
    return out


def sig(x, n=4):
    if x is None:
        return ""
    if x == 0:
        return "0"
    d = n - int(math.floor(math.log10(abs(x)))) - 1
    v = round(x, d)
    s = f"{v:.{max(d, 0)}f}" if d > 0 else str(int(round(v)))
    return s.rstrip("0").rstrip(".") if "." in s else s


def num(s):
    return float(s) if s not in ("", None) else None


# ---------------------------------------------------------------- load
def load():
    markers = {r["marker_slug"]: r for r in read(LF / "markers.csv")}
    registry = {r["source_id"]: r for r in read(ROOT / "sources" / "registry.csv")}
    files = read(ROOT / "sources" / "files.csv")
    kinds = {(r["source_id"], r["marker_slug"]): r for r in read(ROOT / "transcriptions" / "_interval_kinds.csv")}
    rows = []
    for sid in registry:
        for i, r in enumerate(read(ROOT / "transcriptions" / f"{sid}.csv"), 1):
            r = dict(r)
            r["source_id"] = sid
            r["order"] = i
            rows.append(r)
    return markers, registry, files, kinds, rows


def file_for(sid, page, files, layout):
    fs = [f for f in files if f["source_id"] == sid]
    if len(fs) == 1:
        return fs[0]
    if layout == "pdf-multi":
        stem = page.rsplit("-", 1)[0]
        hits = [f for f in fs if pathlib.Path(f["local_path"]).stem.split("_FB-PA")[0] == stem]
    else:
        hits = [f for f in fs if pathlib.Path(f["local_path"]).stem == page]
    if len(hits) != 1:
        raise ValueError(f"cannot map page {page!r} of {sid} to one file")
    return hits[0]


def covers_reference_age(r):
    lo, hi = num(r["age_min_y"]), num(r["age_max_y"])
    return (lo is None or lo <= REFERENCE_AGE) and (hi is None or hi >= REFERENCE_AGE)


# ---------------------------------------------------------------- build
def build():
    markers, registry, files, kinds, rows = load()

    # 1. archived files must match their recorded SHA-256
    for f in files:
        p = RAW / f["local_path"]
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != f["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {p}")

    # 2. every transcribed row must be found on its cited page of the archived text
    failures = sum(check_source(sid) for sid in registry)
    if failures:
        raise SystemExit(f"{failures} transcription rows not found in source text")

    factors = unit_factors()

    # 3. common unit per marker: the most frequent printed unit that converts, ties -> preferred unit
    by_marker = defaultdict(list)
    for r in rows:
        r["unit_canonical"] = canon_unit(r["unit_printed"])
        by_marker[r["marker_slug"]].append(r)
    common = {}
    for slug, rs in by_marker.items():
        if slug not in markers:
            raise SystemExit(f"marker_slug not in markers.csv: {slug}")
        pref = markers[slug]["preferred_unit"]
        counts = defaultdict(int)
        for r in rs:
            counts[r["unit_canonical"]] += 1
        common[slug] = sorted(counts, key=lambda u: (-counts[u], u != pref, u))[0]

    out = []
    for n, r in enumerate(rows, 1):
        reg = registry[r["source_id"]]
        f = file_for(r["source_id"], r["page"], files, reg["text_layout"])
        slug, u, cu = r["marker_slug"], r["unit_canonical"], common[r["marker_slug"]]
        k = kinds.get((r["source_id"], slug))
        lo, hi = num(r["low"]), num(r["high"])
        if u == cu:
            fac, basis = 1.0, "same unit"
        elif (slug, u) in factors and (slug, cu) in factors:
            (fu, bu), (fc, bc) = factors[(slug, u)], factors[(slug, cu)]
            fac = fu / fc
            pref = markers[slug]["preferred_unit"]
            pow10 = abs(math.log10(fac) - round(math.log10(fac))) < 1e-9
            kind = "unit arithmetic" if pow10 or "reader factor" not in (bu + bc) else "LifeFrom reader factor"
            basis = f"{kind}: 1 {u} = {sig(fu, 6)} {pref}; 1 {cu} = {sig(fc, 6)} {pref} (units.csv)"
        else:
            fac, basis = None, "not converted (no factor in units.csv and not pure unit arithmetic)"
        out.append({
            "row_id": f"{r['source_id']}-{r['order']:03d}",
            "source_id": r["source_id"],
            "lab": reg["lab"],
            "country": reg["country"],
            "organisation_type": reg["organisation_type"],
            "analyte_printed": r["analyte_printed"],
            "marker_slug": slug,
            "marker_name": markers[slug]["canonical_name"],
            "specimen": r["specimen"],
            "sex": r["sex"],
            "age_printed": r["age_printed"],
            "age_min_years": r["age_min_y"],
            "age_max_years": r["age_max_y"],
            "range_as_printed": r["range_as_printed"],
            "low": r["low"],
            "high": r["high"],
            "unit_printed": r["unit_printed"],
            "unit_normalised": u,
            "method_or_platform": r["method"],
            "interval_kind": k["interval_kind"] if k else "reference_interval",
            "kind_note": k["note"] if k else "",
            "unit_common": cu if fac is not None else "",
            "low_common": sig(lo * fac) if (lo is not None and fac is not None) else "",
            "high_common": sig(hi * fac) if (hi is not None and fac is not None) else "",
            "conversion_factor": sig(fac, 6) if fac is not None else "",
            "conversion_basis": basis,
            "applies_at_age_40": "yes" if covers_reference_age(r) else "no",
            "source_url": f["original_url"],
            "source_location": f"page {r['page']}" if reg["text_layout"] == "pdf" else (f"{pathlib.Path(f['local_path']).name}, page {r['page'].rsplit('-', 1)[-1]}" if reg["text_layout"] == "pdf-multi" else (pathlib.Path(f["local_path"]).name if reg["text_layout"] == "html-multi" else "Table 1")),
            "document_title": reg["document_title"],
            "document_version": reg["document_version_or_date"],
            "accessed": ACCESSED,
            "archive_path": f"_raw/ranges/{f['local_path']}",
            "archive_sha256": f["sha256"],
            "wayback_url": f["wayback_url"],
        })

    ranges_fields = list(out[0].keys())
    write(ROOT / "data" / "ranges.csv", out, ranges_fields)

    # sources.csv: one row per archived file
    nrows = defaultdict(int)
    for r in out:
        nrows[r["archive_path"]] += 1
    src = []
    for f in files:
        reg = registry[f["source_id"]]
        src.append({
            "source_id": f["source_id"], "lab": reg["lab"], "organisation_type": reg["organisation_type"],
            "country": reg["country"], "city_or_region": reg["city_or_region"],
            "document_title": reg["document_title"], "document_version": reg["document_version_or_date"],
            "original_url": f["original_url"], "retrieved_url": f["retrieved_url"],
            "wayback_url": f["wayback_url"], "wayback_timestamp": f["wayback_timestamp"],
            "accessed": ACCESSED, "archive_path": f"_raw/ranges/{f['local_path']}",
            "sha256": f["sha256"], "bytes": f["bytes"], "rows_in_ranges_csv": nrows[f"_raw/ranges/{f['local_path']}"],
            "terms_url": reg["terms_url"], "terms_finding": reg["terms_finding"], "terms_decision": reg["terms_decision"],
        })
    write(ROOT / "data" / "sources.csv", src, list(src[0].keys()))

    # 4. comparison set: reference intervals that apply to a 40-year-old, one row per lab x marker x sex
    comp = {}
    for r in out:
        if r["interval_kind"] != "reference_interval" or r["applies_at_age_40"] != "yes" or not r["unit_common"]:
            continue
        if "laboratory" not in r["organisation_type"]:  # harmonisation bodies are reported beside, not inside, the lab comparison
            continue
        if r["low_common"] == "" and r["high_common"] == "":
            continue
        for sex in (["M", "F"] if r["sex"] == "all" else [r["sex"]]):
            key = (r["marker_slug"], sex, r["source_id"])
            prev = comp.get(key)
            specific = r["sex"] != "all"
            if prev is None or (specific and prev["sex"] == "all"):
                comp[key] = r
    groups = defaultdict(list)
    for (slug, sex, sid), r in comp.items():
        groups[(slug, sex)].append(r)

    summary, examples = [], []
    harmonised = defaultdict(list)
    for r in out:
        if "harmonisation" in r["organisation_type"] and r["interval_kind"] == "reference_interval" and r["applies_at_age_40"] == "yes":
            for sex in (["M", "F"] if r["sex"] == "all" else [r["sex"]]):
                harmonised[(r["marker_slug"], sex)].append(f"{r['source_id']}: {fmt(r)}")
    for (slug, sex), rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: r["source_id"])
        if len(rs) < 2:
            continue
        lows = [(num(r["low_common"]), r) for r in rs if r["low_common"] != ""]
        highs = [(num(r["high_common"]), r) for r in rs if r["high_common"] != ""]
        def stat(vals):
            if not vals:
                return "", "", "", "", ""
            mn = min(vals, key=lambda t: t[0]); mx = max(vals, key=lambda t: t[0])
            ratio = sig(mx[0] / mn[0], 3) if mn[0] > 0 else ""
            return sig(mn[0]), sig(mx[0]), sig(mx[0] - mn[0]), ratio, f"{mn[1]['source_id']}|{mx[1]['source_id']}"
        lmin, lmax, lspread, lratio, lwho = stat(lows)
        hmin, hmax, hspread, hratio, hwho = stat(highs)
        summary.append({
            "marker_slug": slug, "marker_name": markers[slug]["canonical_name"], "sex": sex,
            "unit_common": rs[0]["unit_common"], "n_labs": len(rs),
            "n_countries": len({r["country"] for r in rs}),
            "labs": "|".join(r["source_id"] for r in rs),
            "n_with_lower": len(lows), "lower_min": lmin, "lower_max": lmax, "lower_spread": lspread,
            "lower_max_over_min": lratio, "lower_min_lab|lower_max_lab": lwho,
            "n_with_upper": len(highs), "upper_min": hmin, "upper_max": hmax, "upper_spread": hspread,
            "upper_max_over_min": hratio, "upper_min_lab|upper_max_lab": hwho,
            "harmonised_intervals_for_comparison": "; ".join(harmonised.get((slug, sex), [])),
        })
        examples += discordances(slug, sex, rs, markers)

    sfields = list(summary[0].keys())
    write(ROOT / "data" / "variation_summary.csv", summary, sfields)
    efields = ["marker_slug", "marker_name", "sex", "direction", "value", "unit", "flagged_lab", "flagged_lab_country",
               "flagged_lab_interval_printed", "flagged_lab_unit_printed", "value_in_flagged_lab_unit",
               "normal_lab", "normal_lab_country", "normal_lab_interval_printed", "normal_lab_unit_printed",
               "value_in_normal_lab_unit", "limit_gap_percent", "statement", "flagged_lab_row_id", "normal_lab_row_id",
               "flagged_lab_url", "normal_lab_url"]
    write(ROOT / "data" / "discordance_examples.csv", examples, efields)

    # 5. web JSON: every row, grouped by marker
    analytes = []
    for slug in sorted(by_marker):
        labs = [{
            "lab": r["lab"], "country": r["country"], "sex": r["sex"], "age": r["age_printed"],
            "low": num(r["low"]), "high": num(r["high"]), "unit_printed": r["unit_printed"],
            "low_common": num(r["low_common"]), "high_common": num(r["high_common"]),
            "interval_kind": r["interval_kind"], "url": r["source_url"], "accessed": r["accessed"],
        } for r in out if r["marker_slug"] == slug]
        analytes.append({"marker_slug": slug, "name": markers[slug]["canonical_name"],
                         "unit_common": common[slug], "labs": labs})
    (ROOT / "web").mkdir(exist_ok=True)
    with open(ROOT / "web" / "lab-ranges.json", "w", encoding="utf-8") as fh:
        json.dump({"version": VERSION, "analytes": analytes}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(f"rows {len(out)}; sources {len(registry)}; files {len(files)}; markers {len(by_marker)}; "
          f"summary groups {len(summary)}; discordance examples {len(examples)}")


def nice_between(lo, hi):
    """A round number strictly between lo and hi, closest to the midpoint."""
    mid = (lo + hi) / 2
    for step in (1000, 500, 100, 50, 10, 5, 1, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001):
        eps = step * 1e-6
        k0, k1 = math.floor(lo / step) - 1, math.ceil(hi / step) + 1
        cands = [round(k * step, 10) for k in range(k0, k1 + 1)]
        cands = [c for c in cands if lo + eps < c < hi - eps]
        if cands:
            return min(cands, key=lambda c: abs(c - mid))
    return mid


def in_lab_unit(value, r):
    fac = num(r["conversion_factor"])
    return sig(value / fac) if fac else ""


def discordances(slug, sex, rs, markers):
    out = []
    lows = [r for r in rs if r["low_common"] != ""]
    highs = [r for r in rs if r["high_common"] != ""]
    name = markers[slug]["canonical_name"]
    sexword = {"M": "men", "F": "women"}[sex]
    # low side: flagged low at the lab with the highest lower limit, inside the interval at the lab with the lowest
    if len(lows) >= 2:
        a = max(lows, key=lambda r: num(r["low_common"]))
        b = min(lows, key=lambda r: num(r["low_common"]))
        alo, blo = num(a["low_common"]), num(b["low_common"])
        bhi = num(b["high_common"]) if b["high_common"] != "" else math.inf
        if blo < alo and (alo - blo) / alo >= MIN_GAP:
            x = nice_between(blo, min(alo, bhi))
            if blo < x < alo and x < bhi and float(sig(x)) != alo:
                out.append(example(slug, name, sex, sexword, "below lower limit", x, a, b))
    if len(highs) >= 2:
        a = min(highs, key=lambda r: num(r["high_common"]))
        b = max(highs, key=lambda r: num(r["high_common"]))
        ahi, bhi = num(a["high_common"]), num(b["high_common"])
        blo = num(b["low_common"]) if b["low_common"] != "" else -math.inf
        if ahi < bhi and (bhi - ahi) / bhi >= MIN_GAP:
            x = nice_between(max(ahi, blo), bhi)
            if ahi < x < bhi and x > blo:
                out.append(example(slug, name, sex, sexword, "above upper limit", x, a, b))
    return out


def example(slug, name, sex, sexword, direction, x, a, b):
    word = "low" if direction.startswith("below") else "high"
    xs = sig(x)
    return {
        "marker_slug": slug, "marker_name": name, "sex": sex, "direction": direction, "value": xs,
        "unit": a["unit_common"],
        "flagged_lab": a["lab"], "flagged_lab_country": a["country"],
        "flagged_lab_interval_printed": a["range_as_printed"], "flagged_lab_unit_printed": a["unit_printed"],
        "value_in_flagged_lab_unit": in_lab_unit(x, a),
        "normal_lab": b["lab"], "normal_lab_country": b["country"],
        "normal_lab_interval_printed": b["range_as_printed"], "normal_lab_unit_printed": b["unit_printed"],
        "value_in_normal_lab_unit": in_lab_unit(x, b),
        "limit_gap_percent": sig(abs(num(a["low_common" if word == "low" else "high_common"]) - num(b["low_common" if word == "low" else "high_common"])) / max(num(a["low_common" if word == "low" else "high_common"]), num(b["low_common" if word == "low" else "high_common"])) * 100, 3),
        "statement": (f"{name}, {sexword}: {xs} {a['unit_common']} is {'below' if word == 'low' else 'above'} the printed "
                      f"interval at {a['lab']}, {a['country']} ({fmt(a)}) and inside the printed interval at "
                      f"{b['lab']}, {b['country']} ({fmt(b)})."),
        "flagged_lab_row_id": a["row_id"], "normal_lab_row_id": b["row_id"],
        "flagged_lab_url": a["source_url"], "normal_lab_url": b["source_url"],
    }


def fmt(r):
    lo, hi, u = r["low_common"], r["high_common"], r["unit_common"]
    if lo and hi:
        return f"{lo}–{hi} {u}"
    return f"<{hi} {u}" if hi else f">{lo} {u}"


if __name__ == "__main__":
    build()
