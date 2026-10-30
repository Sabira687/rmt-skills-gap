#!/usr/bin/env python3
"""Vacancy and programme side of the six survey skills (integration table of A4).

    python3 code/survey_mapping.py --full _private/combined_s1-s2/final_dataset_full.csv \
        --cycles data/processed/programmes/cycles_se.csv data/processed/programmes/cycles_cyber.csv data/processed/programmes/cycles_bda.csv \
        --out data/processed/analysis_s1-s2/survey_skill_mapping.csv

The mapping of each survey skill to rows of code/skills_dictionary_v1.csv is code/survey_skill_mapping.csv.
For every skill: D = share of vacancies that mention it (pooled and per programme), C strict / soft = mentioned in the English
text of mandatory cycles / of any cycle, G = D x (1 - C). Vacancy texts are read from _private/ and only counts are written.
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coding import load_dictionary  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROG = {"se": "Software Engineering", "cyber": "Cybersecurity", "bda": "Big Data Analysis"}


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", required=True)
    ap.add_argument("--cycles", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    entries = load_dictionary()
    mapping = read(os.path.join(HERE, "survey_skill_mapping.csv"))
    vac = read(a.full)
    cyc = [r for p in a.cycles for r in read(p)]
    out = []
    for m in mapping:
        rows = {tuple(x.split(":", 1)) for x in m["dictionary_rows"].split("|")}
        rx = [e[2] for e in entries if (str(e[0]), e[1]) in rows]
        assert rx, m["survey_skill"]
        hit = lambda text: any(r.search(text) for r in rx)
        row = {"survey_skill": m["survey_skill"], "taxonomy_category": m["taxonomy_category"]}
        flags = []
        for v in vac:
            text = " \n".join([v["title"], v["key_skills"], v["description"]])
            flags.append((v["group"], hit(text)))
        row["D_pooled"] = round(sum(f for _, f in flags) / len(flags), 4)
        row["n_pooled"] = len(flags)
        for key, name in PROG.items():
            g = [f for k, f in flags if k == key]
            d = sum(g) / len(g)
            c_rows = [r for r in cyc if r["programme"] == name]
            strict = int(any(hit(r["text_en"]) for r in c_rows if r["status"] == "mandatory"))
            soft = int(any(hit(r["text_en"]) for r in c_rows))
            row.update({f"D_{key}": round(d, 4), f"C_strict_{key}": strict, f"C_soft_{key}": soft,
                        f"G_strict_{key}": round(d * (1 - strict), 4)})
        out.append(row)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(r["survey_skill"], "D pooled", r["D_pooled"], {k: (r[f"D_{k}"], r[f"C_strict_{k}"], r[f"C_soft_{k}"]) for k in PROG})


if __name__ == "__main__":
    main()
