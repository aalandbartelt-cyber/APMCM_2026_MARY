#!/usr/bin/env python3
"""Compare the skeleton against the official PDF without changing its layout."""
from pathlib import Path
import hashlib
import json
import re
import pymupdf as fitz

WORK = Path(__file__).resolve().parents[1]
REPO = WORK.parents[2]
OUT = WORK / "verification"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def spans(page):
    return [s for b in page.get_text("dict")["blocks"] if "lines" in b
            for line in b["lines"] for s in line["spans"] if s["text"].strip()]


def tree_state(relative):
    files = sorted(p for p in (REPO / relative).rglob("*") if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(REPO)).encode() + b"\0" + bytes.fromhex(sha(p)))
    return {"path": relative, "files": len(files),
            "bytes": sum(p.stat().st_size for p in files), "sha256": h.hexdigest()}


def main():
    doc = fitz.open(WORK / "main.pdf")
    official = fitz.open(WORK / "upstream/official/main.pdf")
    smoke = fitz.open(OUT / "f1_inclusion_smoke.pdf")
    fixture = fitz.open(WORK / "build/style_smoke.pdf")
    checks = {}
    texts = [p.get_text() for p in doc]
    alltext = "\n".join(texts)
    checks["official_class_byte_identical"] = sha(WORK/"apmcmthesis.cls") == sha(WORK/"upstream/official/apmcmthesis.cls")
    checks["official_cfg_byte_identical"] = sha(WORK/"apmcmthesis.cfg") == sha(WORK/"upstream/official/apmcmthesis.cfg")
    layout = (WORK/"config/layout.sty").read_text()
    forbidden = (r"\geometry", r"\linespread", r"\titleformat", r"\titlespacing",
                 r"\titlecontents", r"\fontsize", r"\renewenvironment{abstract}",
                 r"\captionsetup", r"\setlength{\parindent}")
    checks["no_visual_style_overrides"] = not any(x in layout for x in forbidden)
    checks["summary_first"] = "2026 APMCM summary sheet" in texts[0]
    checks["contents_second_single_page"] = "Contents" in texts[1] and "AI Tool Disclosure" in texts[1]
    checks["body_starts_third"] = "I. Introduction" in texts[2] and "Problem 1:" in texts[2]
    checks["a4"] = all(abs(p.rect.width-595.276)<.1 and abs(p.rect.height-841.89)<.1 for p in doc)
    headers = []
    for i,p in enumerate(doc):
        observed = " ".join(p.get_text(clip=fitz.Rect(0,0,p.rect.width,65)).split())
        expected = f"Team Dapmcm26301618 Page {i+1 if i<2 else i-1} of 25"
        headers.append({"physical_page":i+1,"observed":observed,"expected":expected})
        checks[f"header_{i+1}"] = observed == expected
    comparisons = []
    for page_no, phrase in ((0,"Team Number:"),(0,"Problem Chosen:"),
                           (0,"2026 APMCM summary sheet"),(1,"Contents"),
                           (2,"I."),(2,"Introduction"),(2,"1 . 1")):
        a = next(s for s in spans(official[page_no]) if s["text"].strip()==phrase)
        b = next(s for s in spans(doc[page_no]) if s["text"].strip()==phrase)
        delta = max(abs(x-y) for x,y in zip(a["bbox"],b["bbox"]))
        same = a["font"]==b["font"] and abs(a["size"]-b["size"])<.01 and delta<.02
        comparisons.append({"text":phrase,"physical_page":page_no+1,
                            "official_font":a["font"],"current_font":b["font"],
                            "official_size_pt":a["size"],"current_size_pt":b["size"],
                            "max_position_difference_pt":delta,"pass":same})
    checks["official_font_size_position_match"] = all(c["pass"] for c in comparisons)
    body = next(s for s in spans(doc[2]) if s["text"].startswith("[Placeholder:"))
    checks["official_body_font"] = body["font"]=="TimesNewRomanPSMT" and abs(body["size"]-10.5)<.01
    checks["all_main_text_is_times_new_roman"] = all("TimesNewRoman" in s["font"] for p in doc for s in spans(p))
    checks["no_chinese_in_pdf"] = not re.search(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]",alltext)
    checks["no_identity_metadata"] = not doc.metadata.get("author") and not doc.metadata.get("keywords")
    checks["no_control_sheet"] = all(x not in alltext for x in ("School Name","Supervisor Name","Control Sheet"))
    font_info = []
    for source,pdf in (("main",doc),("f1_smoke",smoke)):
        seen = set()
        for page in pdf:
            for row in page.get_fonts(full=True):
                if row[0] not in seen:
                    seen.add(row[0])
                    name,ext,kind,payload = pdf.extract_font(row[0])
                    font_info.append({"source":source,"name":name,"embedded":bool(payload)})
    checks["fonts_embedded"] = all(f["embedded"] for f in font_info)
    aux = (WORK/"build/main.aux").read_text()
    match = re.search(r"\\newlabel\{main:last\}\{\{[^}]*\}\{(\d+)\}",aux)
    body_pages = int(match.group(1)) if match else None
    checks["body_within_25_pages"] = body_pages is not None and body_pages<=25
    checks["adjacent_square_citations"] = "[1][2]" in alltext
    checks["journal_examples_marked"] = "[J]" in alltext and alltext.count("verification pending")>=2
    checks["approved_reference_library_empty"] = not re.search(r"^\s*@",(WORK/"references.bib").read_text(),re.M)
    checks["lucas_article_number"] = "Article 5." in alltext
    stext = " ".join(" ".join(p.get_text().split()) for p in fixture)
    checks["book_publisher_page_range"] = all(x in stext for x in ("[M]","Publisher placeholder","1–2"))
    checks["web_access_date"] = "Accessed 2026-11-27" in stext
    checks["eight_table_templates_rendered"] = all(re.search(rf"Table\s+{i}\b",stext) for i in range(1,9))
    checks["subfigure_labels"] = "(a) Condition A" in stext and "(b) Condition B" in stext
    checks["source_listing_macro"] = "Source listing style" in stext
    f1_spans = [s for p in smoke for s in spans(p) if "TimesNewRoman" in s["font"]]
    f1_font_min = min(s["size"] for s in f1_spans)
    forms = smoke[0].get_xobjects()
    widths = [(x[3][2]-x[3][0])*25.4/72 for x in forms]
    checks["f1_170mm"] = any(abs(w-170)<.01 for w in widths)
    checks["f1_minimum_8pt"] = f1_font_min>=8
    checks["f1_caption_same_page"] = len(smoke)==1 and "Data audit and grouped split" in smoke[0].get_text()
    checks["framework_slot_on_first_body_page"] = "Three-stage framework placeholder" in texts[2]
    logs = {}
    for job in ("main","f1_smoke","style_smoke"):
        log = (WORK/f"build/{job}.log").read_text(errors="replace")
        errors = re.findall(r"(?im)^.*(?:Overfull|undefined|Missing character|Font Warning|LaTeX Error).*$",log)
        warnings = re.findall(r"(?im)^.*Warning:.*$",log)
        checks[f"{job}_no_errors_or_overflow"] = not errors
        logs[job] = {"issues":errors,"warnings":warnings}
        if job!="f1_smoke":
            blg = (WORK/f"build/{job}.blg").read_text(errors="replace")
            checks[f"{job}_bibtex_clean"] = not re.search(r"Warning--|\(\d+ error message",blg)
    before = json.loads((OUT/"protected_before.json").read_text())
    after = {k:tree_state(v["path"]) for k,v in before.items() if isinstance(v,dict)}
    after["F1_sha256"] = sha(REPO/"figures/F1/F1_data_audit_v3.pdf")
    checks["protected_sources_unchanged"] = before==after
    (OUT/"protected_after.json").write_text(json.dumps(after,ensure_ascii=False,indent=2)+"\n")
    manifest = json.loads((OUT/"official_copy_manifest.json").read_text())
    checks["upstream_copies_unchanged"] = all(sha(WORK/"upstream/official"/n)==h for n,h in manifest.items())
    for i in range(len(doc)):
        doc[i].get_pixmap(dpi=150).save(OUT/f"current_page_{i+1}.png")
    smoke[0].get_pixmap(dpi=150).save(OUT/"f1_smoke.png")
    fixture[0].get_pixmap(dpi=150).save(OUT/"booktabs_smoke.png")
    fixture[-1].get_pixmap(dpi=150).save(OUT/"citation_subfigure_smoke.png")
    report = {"all_pass":all(checks.values()),"checks":checks,"physical_pages":len(doc),
              "body_pages_including_references":body_pages,"headers":headers,
              "official_comparison":comparisons,"fonts":font_info,"logs":logs,
              "f1_min_font_pt":f1_font_min,"metadata":doc.metadata,"main_pdf_sha256":sha(WORK/"main.pdf"),
              "precedence_note":"Latest user instruction: reproduce official PDF. Its actual body font is Times New Roman 10.5 pt, with XeTeX provenance. Earlier 11/12 pt and pdfLaTeX-only requirements are not claimed as passed."}
    (OUT/"layout_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"all_pass":report["all_pass"],"physical_pages":len(doc),
                      "body_pages":body_pages,"failed_checks":[k for k,v in checks.items() if not v]},indent=2))
    return 0 if report["all_pass"] else 1


if __name__=="__main__":
    raise SystemExit(main())
