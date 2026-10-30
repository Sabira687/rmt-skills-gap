#!/usr/bin/env python3
"""Extract discipline names, status and English descriptions from the programme documents (ОП).

    python3 code/programmes_extract.py --programme "Big Data Analysis" --pdf data/raw/programmes/OP_BigDataAnalysis_2025-2028.pdf --out data/processed/programmes/disciplines_bda.csv
    python3 code/programmes_extract.py --programme "Software Engineering" --text <ocr.txt> --out ...

Input is either a PDF with a text layer (read with pypdf) or a text file with "=====PAGE n=====" markers
(OCR output of code/ocr_pdf.swift). The descriptions are written in three columns (KZ / RU / EN); only lines
without Cyrillic letters are kept, which gives the English column. Status comes from the cycle header above
each discipline: "Elective component" without "Compulsory" -> elective, everything else -> mandatory.
"""
import argparse
import csv
import os
import re
import sys

CYR = re.compile(r"[Ѐ-ӿ]")
PAGE = re.compile(r"^=====PAGE (\d+)=====")
START = re.compile(r"^\s*(\d{1,3})\.?\s+(?=\S)")
MARKS = re.compile(r"^[\s\dVv+\-–•.]*$")
CYCLE = re.compile(r"^\s*Cycle of (.+)$", re.IGNORECASE)


def read_pages(args):
    if args.pdf:
        import pypdf
        reader = pypdf.PdfReader(args.pdf)
        return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)
                if args.first <= i + 1 <= args.last]
    pages, cur, buf = [], None, []
    for line in open(args.text, encoding="utf-8"):
        m = PAGE.match(line.strip())
        if m:
            if cur is not None:
                pages.append((cur, "".join(buf)))
            cur, buf = int(m.group(1)), []
        else:
            buf.append(line)
    if cur is not None:
        pages.append((cur, "".join(buf)))
    return [(n, t) for n, t in pages if args.first <= n <= args.last]


def status_of(cycle):
    c = cycle.lower()
    return "elective" if "elective" in c and "compulsory" not in c else "mandatory"


def parse(pages):
    entries, cycle, status, cur = [], "", "mandatory", None
    for page_no, text in pages:
        for line in text.split("\n"):
            s = line.strip()
            m = CYCLE.match(s)
            if m:
                cycle, status = s, status_of(s)
                cur = None
                continue
            if not s or MARKS.match(s):
                continue
            if cycle and START.match(s) and re.match(r"^\s*\d{1,3}\.?\s+[^\W\d_]", s):
                cur = {"no": int(START.match(s).group(1)), "cycle": cycle, "status": status, "page": page_no, "lines": [s]}
                entries.append(cur)
                continue
            if cur is not None:
                cur["lines"].append(s)
    return entries


def parse_blocks(pages):
    """OCR layout: consecutive Latin-only lines form one unit; short Latin lines before it are its title."""
    entries, cycle, status, run, last_short = [], "", "mandatory", [], ""
    def flush(page_no):
        nonlocal run
        text = " ".join(run)
        if len(text.split()) >= 25:
            entries.append({"no": len(entries) + 1, "cycle": cycle, "status": status, "page": page_no,
                            "lines": ["", last_short, text.replace(".", ". ", 0)], "block": True})
        run = []
    for page_no, text in pages:
        for line in text.split("\n"):
            s = line.strip()
            m = CYCLE.match(s)
            if m:
                flush(page_no)
                cycle, status = s, status_of(s)
                continue
            if not s or MARKS.match(s):
                continue
            if CYR.search(s):
                flush(page_no)
            else:
                if len(s.split()) <= 6 and not run:
                    last_short = s
                else:
                    run.append(s)
        flush(page_no)
    return entries


def is_english(line):
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    latin = sum(c.isascii() for c in letters)
    return latin / len(letters) >= 0.85 and len(CYR.findall(line)) <= 2


def parse_union(pages):
    """One unit per cycle header: all English lines of the cycle (discipline boundaries are not reliable in the PDFs)."""
    units, cycle, status, lines, first_page = [], "", "mandatory", [], 0
    def flush(page_no):
        nonlocal lines
        if cycle and lines:
            units.append({"cycle": cycle, "status": status, "page": f"{first_page}-{page_no}", "text": " ".join(lines)})
        lines = []
    page_no = 0
    for page_no, text in pages:
        for line in text.split("\n"):
            s = line.strip()
            m = CYCLE.match(s)
            if m:
                flush(page_no)
                cycle, status, first_page = s, status_of(s), page_no
                continue
            if cycle and s and not MARKS.match(s) and is_english(s):
                lines.append(s)
    flush(page_no)
    return units


def english(entry):
    if entry.get("block"):
        return entry["lines"][1], entry["lines"][2]
    """Return (English title, English description) of one entry."""
    title, desc, state = [], [], "skip"
    head = START.sub("", entry["lines"][0], count=1)
    for s in [head] + entry["lines"][1:]:
        latin = CYR.search(s) is None
        if state == "skip":
            if latin:
                state = "title"
                title.append(s)
        elif state == "title":
            if latin and len(title) < 4 and len(s.split()) <= 6 and not s.endswith("."):
                title.append(s)
            else:
                state = "desc"
                if latin:
                    desc.append(s)
        else:
            if latin:
                desc.append(s)
    t = re.sub(r"\s+", " ", " ".join(title)).strip(" /")
    return t, re.sub(r"\s+", " ", " ".join(desc)).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--programme", required=True)
    p.add_argument("--pdf")
    p.add_argument("--text")
    p.add_argument("--first", type=int, default=1, help="first page of the description section")
    p.add_argument("--last", type=int, default=10000, help="last page of the description section")
    p.add_argument("--union", action="store_true", help="one unit per cycle header with all English lines (used for coverage)")
    p.add_argument("--blocks", action="store_true", help="OCR layout: one unit per English paragraph (titles not reliable)")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    rows = []
    if args.union:
        for u in parse_union(read_pages(args)):
            rows.append({"programme": args.programme, "cycle": u["cycle"], "status": u["status"],
                         "source_pages": u["page"], "text_en": re.sub(r"\s+", " ", u["text"]),
                         "words": len(u["text"].split())})
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} cycle units -> {args.out}")
        return
    entries = parse_blocks(read_pages(args)) if args.blocks else parse(read_pages(args))
    for e in entries:
        title, desc = english(e)
        if not title or len(desc.split()) < 15:
            continue
        rows.append({"programme": args.programme, "no": e["no"], "discipline": title, "status": e["status"],
                     "cycle": e["cycle"], "source_page": e["page"], "description_en": desc,
                     "description_words": len(desc.split())})
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} disciplines -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
