#!/usr/bin/env python3
"""Audit the compiled skeleton and render the requested visual checks."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf as fitz

WORK = Path(__file__).resolve().parents[1]
REPO = WORK.parents[2]
OUT = WORK / "verification"
TEAM = "Dapmcm26301618"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_state(relative: str) -> dict:
    folder = REPO / relative
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    h = hashlib.sha256()
    size = 0
    for p in files:
        h.update(str(p.relative_to(REPO)).encode() + b"\0" + bytes.fromhex(sha(p)))
        size += p.stat().st_size
    return {"path": relative, "files": len(files), "bytes": size, "sha256": h.hexdigest()}


def spans(page):
    return [s for b in page.get_text("dict")["blocks"] if "lines" in b
            for line in b["lines"] for s in line["spans"] if s["text"].strip()]


def main():
    checks = {}
    document = fitz.open(WORK / "main.pdf")
    texts = [p.get_text() for p in document]
    joined = "\n".join(texts)
    checks["summary_first_physical_page"] = "2026 APMCM Summary Sheet" in texts[0]
    checks["contents_second_physical_page"] = "Contents" in texts[1]
    checks["body_starts_third_physical_page"] = "Introduction" in texts[2] and "Problem 1:" in texts[2]
    checks["contents_fits_one_page"] = "Layout Smoke Test" in texts[1] and "Problem 1:" in texts[2]
    checks["a4_all_pages"] = all(abs(p.rect.width - 595.276) < .1 and abs(p.rect.height - 841.89) < .1 for p in document)
    checks["english_no_cjk"] = not re.search(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]", joined)
    checks["no_identity_metadata"] = not document.metadata.get("author") and not document.metadata.get("keywords")
    checks["no_control_sheet"] = not any(t in joined for t in ("School Name", "Supervisor Name", "Member Name", "Control Sheet"))
    headers = []
    for i, page in enumerate(document):
        header = " ".join(page.get_text(clip=fitz.Rect(0, 0, page.rect.width, 65)).split())
        page_no = i + 1 if i < 2 else i - 1
        expected = f"Team {TEAM} Page {page_no} of 25"
        headers.append({"physical_page": i + 1, "expected": expected, "observed": header})
        checks[f"header_page_{i+1}"] = header == expected
    aux = (WORK / "build/main.aux").read_text()
    last = re.search(r"\\newlabel\{main:last\}\{\{[^}]*\}\{(\d+)\}", aux)
    body_pages = int(last.group(1)) if last else None
    checks["body_at_most_25_pages"] = body_pages is not None and body_pages <= 25
    checks["adjacent_square_citations"] = "[1][2]" in joined
    checks["journal_marker_rendered"] = "[J]" in joined
    checks["article_number_not_fake_page_range"] = "Article 5." in joined
    checks["reference_examples_marked"] = joined.count("verification pending") >= 2
    checks["empty_approved_reference_library"] = not re.search(r"^\s*@", (WORK / "references.bib").read_text(), re.M)
    fonts = {}
    for page in document:
        for row in page.get_fonts(full=True):
            xref = row[0]
            if xref not in fonts:
                name, extension, kind, payload = document.extract_font(xref)
                fonts[xref] = {"name": name, "type": kind, "extension": extension, "embedded": bool(payload)}
    checks["all_pdf_fonts_embedded"] = all(f["embedded"] for f in fonts.values())
    checks["times_family_body"] = any("Termes" in f["name"] for f in fonts.values())
    checks["original_f1_times_new_roman"] = any("TimesNewRoman" in f["name"].replace("-", "") for f in fonts.values())
    body_placeholder = [s for p in list(document)[2:] for s in spans(p)
                        if s["text"].startswith("[Placeholder:")]
    checks["body_font_12_tex_pt"] = bool(body_placeholder) and all(abs(s["size"] - 12*72/72.27) < .02 for s in body_placeholder)
    smoke_index = next(i for i in range(2, len(document)) if "Check the unchanged F1" in texts[i])
    smoke = document[smoke_index]
    forms = [{"xref": x[0], "name": x[1], "invoker": x[2], "bbox": list(x[3])} for x in smoke.get_xobjects()]
    target_forms = [x for x in forms if abs((x["bbox"][2]-x["bbox"][0])*25.4/72 - 170) < .1]
    checks["f1_included_at_170mm"] = bool(target_forms)
    smoke_spans = spans(smoke)
    source_fonts = [s for s in smoke_spans if "TimesNewRoman" in s["font"].replace("-", "")]
    f1_min_size = min((s["size"] for s in source_fonts), default=0)
    checks["f1_final_font_at_least_8pt"] = f1_min_size >= 8
    checks["f1_caption_same_page"] = "Data audit and grouped split (layout smoke test)" in texts[smoke_index]
    checks["framework_on_first_body_page"] = "Stage 1 placeholder" in texts[2] and "Three-stage framework" in texts[2]
    if checks["framework_on_first_body_page"]:
        frame_caption = next(s for s in spans(document[2]) if "Three-stage framework" in s["text"])
        checks["framework_at_page_bottom"] = frame_caption["bbox"][1] > document[2].rect.height*.80
    log_checks = {}
    for name in ("main", "style_smoke"):
        logfile = WORK / f"build/{name}.log"
        log = logfile.read_text(errors="replace") if logfile.exists() else "MISSING"
        issues = re.findall(r"(?im)^.*(?:Overfull|undefined|Missing character|Font Warning|LaTeX Error|MISSING).*$", log)
        biblio_log = WORK / f"build/{name}.blg"
        bib_text = biblio_log.read_text(errors="replace") if biblio_log.exists() else "MISSING"
        bib_issues = re.findall(r"(?im)^.*(?:Warning--|error message|MISSING).*$", bib_text)
        log_checks[name] = {"layout_issues": issues, "bibliography_issues": bib_issues}
        checks[f"{name}_clean_layout_log"] = not issues
        checks[f"{name}_clean_bibtex_log"] = not bib_issues
    fixture = fitz.open(WORK / "build/style_smoke.pdf")
    fixture_text = "\n".join(p.get_text() for p in fixture)
    checks["book_publisher_and_pages"] = all(x in fixture_text for x in ("[M]", "Publisher placeholder", "1–2"))
    checks["web_access_date"] = "Accessed 2026-11-27" in fixture_text
    checks["subfigure_labels_a_b"] = "(a) Condition A" in fixture_text and "(b) Condition B" in fixture_text
    checks["all_eight_table_templates_rendered"] = all(f"Table {i}." in fixture_text for i in range(1, 9))
    before = json.loads((OUT / "protected_before.json").read_text())
    after = {k: tree_state(v["path"]) for k, v in before.items() if isinstance(v, dict)}
    after["F1_sha256"] = sha(REPO / "figures/F1/F1_data_audit_v3.pdf")
    checks["protected_sources_unchanged"] = before == after
    (OUT / "protected_after.json").write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
    manifest = json.loads((OUT / "official_copy_manifest.json").read_text())
    checks["official_copies_byte_identical"] = all(sha(WORK / "upstream/official" / name) == value for name, value in manifest.items())
    screenshots = {}
    for name, index in (("01_summary", 0), ("02_contents", 1), ("03_first_body_page", 2), ("04_f1_smoke", smoke_index)):
        path = OUT / f"{name}.png"
        document[index].get_pixmap(dpi=150, alpha=False).save(path)
        screenshots[name] = {"physical_page": index+1, "file": str(path.relative_to(WORK))}
    document[2].get_pixmap(dpi=250, alpha=False, clip=fitz.Rect(50, 28, 545, 65)).save(OUT / "05_header_detail.png")
    fixture[0].get_pixmap(dpi=150, alpha=False).save(OUT / "06_booktabs_fixture.png")
    fixture[-1].get_pixmap(dpi=150, alpha=False).save(OUT / "07_citation_subfigure_fixture.png")
    report = {"checks": checks, "all_pass": all(checks.values()), "physical_pages": len(document),
              "body_pages_including_references": body_pages, "header_denominator": 25,
              "headers": headers, "fonts": list(fonts.values()), "metadata": document.metadata,
              "f1_smoke_physical_page": smoke_index+1, "f1_min_font_pt": f1_min_size,
              "f1_forms": forms, "log_checks": log_checks, "screenshots": screenshots,
              "main_pdf_sha256": sha(WORK / "main.pdf")}
    (OUT / "layout_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"all_pass": report["all_pass"], "physical_pages": len(document),
                      "body_pages": body_pages, "failed_checks": [k for k,v in checks.items() if not v]}, indent=2))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
