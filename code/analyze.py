#!/usr/bin/env python3
"""Analysis A4: demand D, coverage C, gap G, unmet demand U, bootstrap intervals, verdicts for ER1-ER6.

    python3 code/analyze.py --vacancies data/processed/combined_s1-s2/vacancy_skills.csv \
        --cycles data/processed/programmes/cycle_skills.csv --out data/processed/analysis_s1-s2/

Definitions (A3, Table 3 and Table 14):
  D_c      share of the programme's vacancies that mention category c (Wilson 95% interval)
  C_c      1 if category c is mentioned in the English text of the programme (strict: mandatory cycles only,
           soft: mandatory and elective cycles), otherwise 0
  G_c      D_c * (1 - C_c)
  U        sum_c D_c (1 - C_c) / sum_c D_c   (demand-weighted share of demand that is not covered)
  bootstrap: vacancies of a programme are resampled with replacement B times (fixed seed), percentile 95% interval
  H1       confirmed for a programme if the lower bound of the strict-U interval is above 0.30
Only the standard library is used.
"""
import argparse
import csv
import math
import os
import random
import statistics
import sys

B = 2000
SEED = 20261030
PROGRAMMES = [("se", "Software Engineering"), ("cyber", "Cybersecurity"), ("bda", "Big Data Analysis")]
RAPID = {2, 3, 4, 7, 8, 9, 14}  # "Rapidly Evolving Categories" of code/taxonomy_categories_v1.md
COLS = [f"c{i:02d}" for i in range(1, 20)]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coding import CATEGORIES  # noqa: E402


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def demand(rows):
    n = len(rows)
    return [sum(int(r[c]) for r in rows) / n if n else 0.0 for c in COLS]


def u_index(d, cov):
    tot = sum(d)
    return sum(x * (1 - c) for x, c in zip(d, cov)) / tot if tot else float("nan")


def percentile(xs, q):
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def coverage(cycles, programme):
    rows = [r for r in cycles if r["programme"] == programme]
    strict = [1 if any(int(r[c]) for r in rows if r["status"] == "mandatory") else 0 for c in COLS]
    soft = [1 if any(int(r[c]) for r in rows) else 0 for c in COLS]
    return strict, soft


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vacancies", required=True)
    ap.add_argument("--cycles", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    vac = read(args.vacancies)
    cyc = read(args.cycles)
    rng = random.Random(SEED)
    numbers = []  # registry of reported numbers

    def reg(key, value, unit, source, note=""):
        numbers.append({"id": key, "value": value, "unit": unit, "source_file": source, "note": note})

    d_rows, c_rows, g_rows, u_rows, rank_rows, v_rows, t10_rows, sens_rows = [], [], [], [], [], [], [], []
    U = {}
    prog_data = {}
    for key, name in PROGRAMMES:
        rows = [r for r in vac if r["group"] == key]
        n = len(rows)
        d = demand(rows)
        strict, soft = coverage(cyc, name)
        prog_data[key] = (rows, d, strict, soft)
        reg(f"n_vacancies_{key}", n, "vacancies", "vacancy_skills.csv")
        for i, c in enumerate(COLS):
            k = round(d[i] * n)
            lo, hi = wilson(k, n)
            d_rows.append({"programme": key, "category_id": i + 1, "category": CATEGORIES[i + 1], "n": n, "k": k,
                           "D": round(d[i], 4), "wilson_lo": round(lo, 4), "wilson_hi": round(hi, 4)})
            c_rows.append({"programme": key, "category_id": i + 1, "category": CATEGORIES[i + 1],
                           "C_strict": strict[i], "C_soft": soft[i]})
            g_rows.append({"programme": key, "category_id": i + 1, "category": CATEGORIES[i + 1],
                           "D": round(d[i], 4), "C_strict": strict[i], "G_strict": round(d[i] * (1 - strict[i]), 4),
                           "C_soft": soft[i], "G_soft": round(d[i] * (1 - soft[i]), 4)})
        # bootstrap
        boots = {"strict": [], "soft": []}
        top3 = {c: 0 for c in COLS}
        for _ in range(B):
            sample = [rows[rng.randrange(n)] for _ in range(n)]
            db = demand(sample)
            boots["strict"].append(u_index(db, strict))
            boots["soft"].append(u_index(db, soft))
            gs = sorted(range(19), key=lambda i: (-(db[i] * (1 - strict[i])), i))[:3]
            for i in gs:
                top3[COLS[i]] += 1
        for scen, cov in (("strict", strict), ("soft", soft)):
            u = u_index(d, cov)
            xs = [x for x in boots[scen] if not math.isnan(x)]
            lo, hi = percentile(xs, 0.025), percentile(xs, 0.975)
            U[(key, scen)] = (u, lo, hi)
            u_rows.append({"programme": key, "scenario": scen, "n": n, "U": round(u, 4), "ci_lo": round(lo, 4),
                           "ci_hi": round(hi, 4), "H1_lower_gt_0.30": "yes" if lo > 0.30 else "no",
                           "covered_categories": sum(cov), "bootstrap_B": B, "seed": SEED})
            reg(f"U_{scen}_{key}", round(u, 4), "share", "U.csv")
            reg(f"U_{scen}_{key}_ci", f"{lo:.4f}-{hi:.4f}", "95% bootstrap interval", "U.csv")
        for i, c in enumerate(COLS):
            rank_rows.append({"programme": key, "category_id": i + 1, "category": CATEGORIES[i + 1],
                              "G_strict": round(d[i] * (1 - strict[i]), 4), "top3_frequency": round(top3[c] / B, 4)})
        # vacancy-level coverage (strict and soft)
        for scen, cov in (("strict", strict), ("soft", soft)):
            shares, full = [], 0
            for r in rows:
                cats = [i for i, c in enumerate(COLS) if int(r[c])]
                if not cats:
                    continue
                share = sum(cov[i] for i in cats) / len(cats)
                shares.append(share)
                full += share == 1.0
            v_rows.append({"programme": key, "scenario": scen, "vacancies_with_categories": len(shares),
                           "median_share_covered": round(statistics.median(shares), 4) if shares else "",
                           "fully_covered": full,
                           "share_fully_covered": round(full / len(shares), 4) if shares else ""})
        # T10 patterns
        ncat = [int(r["n_categories"]) for r in rows]
        t10_rows.append({"programme": key, "n": n, "mean_categories_per_vacancy": round(statistics.mean(ncat), 3),
                         "median_categories_per_vacancy": statistics.median(ncat),
                         "top3_D": "; ".join(f"{CATEGORIES[i + 1]} ({d[i]:.2f})"
                                             for i in sorted(range(19), key=lambda j: -d[j])[:3])})
        # sensitivity of U (strict) to inclusion decisions
        variants = {"all": rows,
                    "without_borderline": [r for r in rows if not r["borderline"]],
                    "no_experience_only": [r for r in rows if r["bucket"] == "noExperience"],
                    "one_to_three_years_only": [r for r in rows if r["bucket"] == "between1And3"]}
        for vname, vrows in variants.items():
            if len(vrows) >= 3:
                sens_rows.append({"programme": key, "variant": vname, "n": len(vrows),
                                  "U_strict": round(u_index(demand(vrows), strict), 4),
                                  "U_soft": round(u_index(demand(vrows), soft), 4)})
            else:
                sens_rows.append({"programme": key, "variant": vname, "n": len(vrows), "U_strict": "", "U_soft": ""})

    # ER verdicts (conditions copied from A3, Table 11)
    n_of = {k: len(prog_data[k][0]) for k, _ in PROGRAMMES}
    er = []
    er1 = n_of["se"] > max(n_of["cyber"], n_of["bda"])
    er.append(("ER1", "SE has the largest number of vacancies", f"SE {n_of['se']}, Cyber {n_of['cyber']}, BDA {n_of['bda']}",
               "confirmed" if er1 else "not confirmed"))
    ok = [U[(k, "strict")][0] <= 0.50 for k, _ in PROGRAMMES]
    er.append(("ER2", "U strict <= 50% for every programme",
               "; ".join(f"{k} {U[(k, 'strict')][0]:.3f}" for k, _ in PROGRAMMES),
               "confirmed" if all(ok) else ("partly" if any(ok) else "not confirmed")))
    ok = [U[(k, "strict")][1] > 0.30 for k, _ in PROGRAMMES]
    er.append(("ER3", "lower bound of 95% bootstrap interval of U strict > 30% for every programme",
               "; ".join(f"{k} [{U[(k, 'strict')][1]:.3f}, {U[(k, 'strict')][2]:.3f}]" for k, _ in PROGRAMMES),
               "confirmed" if all(ok) else ("partly" if any(ok) else "not confirmed")))
    keys = [k for k, _ in PROGRAMMES]
    diffs = {(a, b): abs(U[(a, "strict")][0] - U[(b, "strict")][0]) for i, a in enumerate(keys) for b in keys[i + 1:]}
    er.append(("ER4", "|U strict| differs by more than 10 pp for at least one pair",
               "; ".join(f"{a}-{b} {v * 100:.1f} pp" for (a, b), v in diffs.items()),
               "confirmed" if any(v > 0.10 for v in diffs.values()) else "not confirmed"))
    gaps = {k: (U[(k, "strict")][0] - U[(k, "soft")][0]) for k in keys}
    ok = [v >= 0.10 for v in gaps.values()]
    er.append(("ER5", "U strict is at least 10 pp higher than U soft for every programme",
               "; ".join(f"{k} {v * 100:.1f} pp" for k, v in gaps.items()),
               "confirmed" if all(ok) else ("partly" if any(ok) else "not confirmed")))
    se_g = sorted(range(19), key=lambda i: (-(prog_data["se"][1][i] * (1 - prog_data["se"][2][i])), i))[:3]
    n_rapid = sum((i + 1) in RAPID for i in se_g)
    er.append(("ER6", "at least two of the top-3 SE gap categories are rapidly evolving",
               "top-3: " + "; ".join(f"{CATEGORIES[i + 1]}{' [rapid]' if (i + 1) in RAPID else ''}" for i in se_g),
               "confirmed" if n_rapid >= 2 else "not confirmed"))
    write(os.path.join(args.out, "er_verdicts.csv"),
          [{"er": a, "condition": b, "observed": c, "verdict_computed": d} for a, b, c, d in er])

    write(os.path.join(args.out, "D.csv"), d_rows)
    write(os.path.join(args.out, "C.csv"), c_rows)
    write(os.path.join(args.out, "G.csv"), g_rows)
    write(os.path.join(args.out, "U.csv"), u_rows)
    write(os.path.join(args.out, "rank_stability.csv"), rank_rows)
    write(os.path.join(args.out, "vacancy_level_coverage.csv"), v_rows)
    write(os.path.join(args.out, "t10_patterns.csv"), t10_rows)
    write(os.path.join(args.out, "sensitivity.csv"), sens_rows)
    for a, _, c, d in er:
        reg(f"verdict_{a}", d, "verdict", "er_verdicts.csv", c)
    write(os.path.join(args.out, "results_numbers.csv"), numbers)
    for r in u_rows:
        print(r)
    for a, b, c, d in er:
        print(a, d, "|", c)


if __name__ == "__main__":
    main()
