#!/usr/bin/env python3
"""Coding of vacancies and programme disciplines with the level-2 skills dictionary.

    python3 code/coding.py vacancies --full _private/<session>/final_dataset_full.csv --out data/processed/<session>/
    python3 code/coding.py disciplines --disciplines data/processed/programmes/disciplines.csv --out data/processed/programmes/

Both commands use code/skills_dictionary_v1.csv and the 19 categories of code/taxonomy_categories_v1.md.
Vacancy texts are read from _private/ and never written to the public output; only 0/1 values are written.
"""
import argparse
import csv
import os
import re
import sys

# CHANGELOG of skills_dictionary_v1.csv (changes after the freeze must be listed here with a reason)
# 2026-10-30  draft written; precision checked on 8 random session-1 vacancies (matched terms in _private/*/vacancy_skill_hits.csv)
# 2026-10-30  before the freeze, after reading the English programme text: generic "testing" removed from category 11 (it matched
#             "hypothesis testing"), "front end" / "back end" added to categories 2 and 3 (programme titles "WEB Technologies (Front End)")
# 2026-10-30  FROZEN. Note: coverage C (cycle_skills.csv) had been looked at once before these two fixes; U was not computed.
DICT_VERSION = "v1-frozen-2026-10-30"
HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, "skills_dictionary_v1.csv")

CATEGORIES = {
    1: "Programming Languages",
    2: "Frontend Development",
    3: "Backend Frameworks and APIs",
    4: "Mobile Development",
    5: "Databases and SQL",
    6: "Big Data Processing",
    7: "Machine Learning and Deep Learning",
    8: "Data Visualization and BI",
    9: "Cloud, Containers, and CI/CD",
    10: "Version Control",
    11: "Testing and QA",
    12: "Operating Systems and Linux",
    13: "Computer Networks",
    14: "Monitoring and Incident Response (SOC, SIEM)",
    15: "Penetration Testing",
    16: "Digital Forensics and Malware Analysis",
    17: "Information Security Standards, Auditing, and Risk Management",
    18: "Cryptography",
    19: "Software Architecture and Design",
}
COLS = [f"c{i:02d}" for i in CATEGORIES]


def load_dictionary(path=DICT_PATH):
    entries = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            tail = r"(?!\w)" if row["match"] == "word" else ""
            rx = re.compile(r"(?<!\w)(?:" + row["pattern"] + r")" + tail, re.IGNORECASE)
            entries.append((int(row["category_id"]), row["skill"], rx))
    return entries


def code_text(text, entries):
    """Return {category_id: [matched strings]} for one text."""
    hits = {}
    for cat, _skill, rx in entries:
        found = [m.group(0).lower() for m in rx.finditer(text)]
        if found:
            hits.setdefault(cat, []).extend(found)
    return hits


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def cmd_vacancies(args):
    entries = load_dictionary()
    with open(args.full, encoding="utf-8-sig", newline="") as f:
        vacancies = list(csv.DictReader(f))
    rows, hit_rows = [], []
    for v in vacancies:
        text = " \n".join([v.get("title", ""), v.get("key_skills", ""), v.get("description", "")])
        hits = code_text(text, entries)
        row = {"id": v["id"], "group": v["group"], "bucket": v["bucket"], "borderline": v.get("borderline", "")}
        for cat, col in zip(CATEGORIES, COLS):
            row[col] = 1 if cat in hits else 0
        row["n_categories"] = len(hits)
        rows.append(row)
        for cat, found in hits.items():
            hit_rows.append({"id": v["id"], "category": cat, "terms": "; ".join(sorted(set(found)))})
    fields = ["id", "group", "bucket", "borderline"] + COLS + ["n_categories"]
    write_csv(os.path.join(args.out, "vacancy_skills.csv"), rows, fields)
    # matched terms are kept next to the full texts (private) for the manual check
    private = args.private or os.path.dirname(args.full)
    write_csv(os.path.join(private, "vacancy_skill_hits.csv"), hit_rows, ["id", "category", "terms"])
    print(f"{len(rows)} vacancies coded with dictionary {DICT_VERSION} -> {args.out}/vacancy_skills.csv")


def cmd_disciplines(args):
    entries = load_dictionary()
    with open(args.disciplines, encoding="utf-8-sig", newline="") as f:
        disciplines = list(csv.DictReader(f))
    rows = []
    for d in disciplines:
        text = " \n".join([d.get("discipline", ""), d.get("description_en", "")])
        hits = code_text(text, entries)
        row = {k: d[k] for k in ("programme", "discipline", "status", "credits", "semester")}
        for cat, col in zip(CATEGORIES, COLS):
            row[col] = 1 if cat in hits else 0
        row["n_categories"] = len(hits)
        rows.append(row)
    fields = ["programme", "discipline", "status", "credits", "semester"] + COLS + ["n_categories"]
    write_csv(os.path.join(args.out, "discipline_skills.csv"), rows, fields)
    print(f"{len(rows)} disciplines coded with dictionary {DICT_VERSION} -> {args.out}/discipline_skills.csv")


def cmd_cycles(args):
    """Programme side: one row per cycle of disciplines (English text of the cycle), 0/1 per category."""
    entries = load_dictionary()
    rows = []
    for path in args.cycles:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for u in csv.DictReader(f):
                hits = code_text(u["text_en"], entries)
                row = {"programme": u["programme"], "cycle": u["cycle"], "status": u["status"],
                       "source_pages": u["source_pages"], "words": u["words"]}
                for cat, col in zip(CATEGORIES, COLS):
                    row[col] = 1 if cat in hits else 0
                row["n_categories"] = len(hits)
                rows.append(row)
    fields = ["programme", "cycle", "status", "source_pages", "words"] + COLS + ["n_categories"]
    write_csv(os.path.join(args.out, "cycle_skills.csv"), rows, fields)
    print(f"{len(rows)} cycle units coded with dictionary {DICT_VERSION} -> {args.out}/cycle_skills.csv")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("vacancies")
    a.add_argument("--full", required=True, help="final_dataset_full.csv (private)")
    a.add_argument("--out", required=True)
    a.add_argument("--private", help="folder for the hits file (default: folder of --full)")
    b = sub.add_parser("disciplines")
    b.add_argument("--disciplines", required=True)
    b.add_argument("--out", required=True)
    c = sub.add_parser("cycles")
    c.add_argument("--cycles", nargs="+", required=True, help="cycles_*.csv from programmes_extract.py --union")
    c.add_argument("--out", required=True)
    args = p.parse_args()
    {"vacancies": cmd_vacancies, "disciplines": cmd_disciplines, "cycles": cmd_cycles}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
