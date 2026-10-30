#!/usr/bin/env python3
"""Figures for A4, drawn from the files written by analyze.py and pipeline.py (nothing is typed in by hand).

    .venv2/bin/python code/figures.py --an data/processed/analysis_s1-s2 \
        --sessions data/processed/session1_2026-10-23 data/processed/session2_2026-10-30 \
        --combined data/processed/combined_s1-s2 --out figures/a4

Requires matplotlib (see README, section Analysis).
"""
import argparse
import csv
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coding import CATEGORIES  # noqa: E402

COLOR = {"se": "#0072B2", "cyber": "#D55E00", "bda": "#009E73"}
LABEL = {"se": "Software Engineering", "cyber": "Cybersecurity", "bda": "Big Data Analysis"}
KEYS = ["se", "cyber", "bda"]
SHORT = {i: re.sub(r" \(.*\)", "", n).replace("Information Security Standards, Auditing, and Risk Management", "InfoSec standards, audit, risk")
         for i, n in CATEGORIES.items()}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100})


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name), dpi=200)
    plt.close(fig)
    print("saved", name)


def fig_funnel(sessions, combined, out):
    labels, cards, cands = [], [], []
    for s in sessions:
        rows = read(os.path.join(s, "cards_screened.csv"))
        labels.append(os.path.basename(s).split("_")[0].replace("session", "Session "))
        cards.append(len(rows))
        cands.append(sum(r["decision"] == "candidate" for r in rows))
    final = len(read(os.path.join(combined, "final_dataset.csv")))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], cards, 0.4, label="Search cards", color="#9AA5B1")
    ax.bar([i + 0.2 for i in x], cands, 0.4, label="Candidates after card screening", color="#0072B2")
    for i in x:
        ax.text(i - 0.2, cards[i], cards[i], ha="center", va="bottom")
        ax.text(i + 0.2, cands[i], cands[i], ha="center", va="bottom")
    ax.bar(len(labels), final, 0.4, color="#D55E00", label="Final dataset (sessions combined)")
    ax.text(len(labels), final, final, ha="center", va="bottom")
    ax.set_xticks(list(x) + [len(labels)])
    ax.set_xticklabels(labels + ["Combined"])
    ax.set_ylabel("Vacancies")
    ax.legend(frameon=False)
    save(fig, out, "A4_Fig01_selection_funnel.png")


def fig_counts(an, out, vac):
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    for j, b in enumerate(["noExperience", "between1And3"]):
        vals = [sum(1 for r in vac if r["group"] == k and r["bucket"] == b) for k in KEYS]
        bottoms = [sum(1 for r in vac if r["group"] == k and r["bucket"] == "noExperience") if j else 0 for k in KEYS]
        ax.bar([LABEL[k] for k in KEYS], vals, bottom=bottoms, color=["#56B4E9", "#E69F00"][j],
               label=["No experience", "1-3 years"][j])
    for i, k in enumerate(KEYS):
        ax.text(i, sum(1 for r in vac if r["group"] == k) + 0.5, sum(1 for r in vac if r["group"] == k), ha="center")
    ax.axhline(30, color="#555", ls="--", lw=1)
    ax.text(2.45, 30.5, "threshold 30", ha="right", color="#555")
    ax.set_ylabel("Vacancies")
    ax.legend(frameon=False)
    save(fig, out, "A4_Fig02_vacancies_by_programme.png")


def heat(ax, matrix, rows, cols, fmt, cmap="Blues", vmax=1.0):
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    for i, row in enumerate(matrix):
        for j, v in enumerate(row):
            ax.text(j, i, fmt(v), ha="center", va="center", color="white" if v > 0.6 * vmax else "black", fontsize=7)
    return im


def fig_demand(an, out):
    d = read(os.path.join(an, "D.csv"))
    n = {k: int(next(r["n"] for r in d if r["programme"] == k)) for k in KEYS}
    m = [[float(next(r["D"] for r in d if r["programme"] == k and int(r["category_id"]) == i)) for k in KEYS] for i in CATEGORIES]
    fig, ax = plt.subplots(figsize=(5.6, 6.2))
    im = heat(ax, m, [SHORT[i] for i in CATEGORIES], [f"{k.upper()}\n(n={n[k]})" for k in KEYS], lambda v: f"{v:.2f}")
    fig.colorbar(im, ax=ax, label="D_c (share of vacancies)")
    save(fig, out, "A4_Fig03_demand_by_category.png")


def fig_coverage(an, out):
    c = read(os.path.join(an, "C.csv"))
    fig, ax = plt.subplots(figsize=(6.4, 6.2))
    cols = [f"{k.upper()}\nstrict" if s == "C_strict" else f"{k.upper()}\nsoft" for k in KEYS for s in ("C_strict", "C_soft")]
    m = [[int(next(r[s] for r in c if r["programme"] == k and int(r["category_id"]) == i)) for k in KEYS for s in ("C_strict", "C_soft")]
         for i in CATEGORIES]
    heat(ax, m, [SHORT[i] for i in CATEGORIES], cols, lambda v: "covered" if v else "-", cmap="Greens", vmax=1.6)
    save(fig, out, "A4_Fig04_coverage_matrix.png")


def fig_u(an, out):
    u = read(os.path.join(an, "U.csv"))
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    for j, scen in enumerate(("strict", "soft")):
        for i, k in enumerate(KEYS):
            r = next(x for x in u if x["programme"] == k and x["scenario"] == scen)
            v, lo, hi = float(r["U"]), float(r["ci_lo"]), float(r["ci_hi"])
            xpos = i + (j - 0.5) * 0.3
            ax.errorbar(xpos, v, yerr=[[v - lo], [hi - v]], fmt="o" if scen == "strict" else "s", color=COLOR[k],
                        mfc=COLOR[k] if scen == "strict" else "white", capsize=3)
            ax.text(xpos + 0.05, hi + 0.01, f"{v:.2f}", fontsize=7)
    ax.axhline(0.30, color="#555", ls="--", lw=1)
    ax.text(-0.45, 0.31, "H1 threshold 0.30", ha="left", color="#555")
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{LABEL[k]}\n(n={next(x['n'] for x in u if x['programme'] == k)})" for k in KEYS])
    ax.set_ylabel("U (unmet share of demand)")
    ax.set_ylim(0, 0.7)
    ax.set_title("filled = strict, open = soft; bars = 95% bootstrap interval", fontsize=8)
    save(fig, out, "A4_Fig05_unmet_demand_U.png")


def fig_gaps(an, out):
    g = read(os.path.join(an, "G.csv"))
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.8), sharex=True)
    for ax, k in zip(axes, KEYS):
        rows = sorted([r for r in g if r["programme"] == k], key=lambda r: -float(r["G_strict"]))[:8]
        ax.barh([SHORT[int(r["category_id"])] for r in rows][::-1], [float(r["G_strict"]) for r in rows][::-1], color=COLOR[k])
        ax.set_title(LABEL[k], fontsize=9)
        ax.set_xlabel("G_c (strict)")
    save(fig, out, "A4_Fig06_largest_gaps.png")


def fig_stability(an, out):
    s = read(os.path.join(an, "rank_stability.csv"))
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.8), sharex=True)
    for ax, k in zip(axes, KEYS):
        rows = sorted([r for r in s if r["programme"] == k], key=lambda r: -float(r["top3_frequency"]))[:6]
        ax.barh([SHORT[int(r["category_id"])] for r in rows][::-1], [float(r["top3_frequency"]) for r in rows][::-1], color=COLOR[k])
        ax.set_xlim(0, 1)
        ax.set_title(LABEL[k], fontsize=9)
        ax.set_xlabel("Share of 2000 bootstrap samples in top-3 by G_c")
    save(fig, out, "A4_Fig07_ranking_stability.png")


def fig_t10(t10_files, out):
    rows = []
    for f in t10_files:
        rows += [(os.path.basename(os.path.dirname(f)), r) for r in read(f)]
    if not rows:
        return
    measures = []
    for tag, r in rows:
        if r["expected"] in ("-", ""):
            continue
        m = re.match(r"\s*(?:<)?(\d+(?:\.\d+)?)%?\s*-\s*(\d+(?:\.\d+)?)%", r["expected"])
        lo, hi = (float(m.group(1)), float(m.group(2))) if m else (0.0, float(re.findall(r"[\d.]+", r["expected"])[0]))
        measures.append((tag.split("_")[0] if len(rows) > 8 else "", r["measure"], float(r["observed"].strip("%")), lo, hi))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for i, (tag, name, obs, lo, hi) in enumerate(measures):
        ax.plot([lo, hi], [i, i], color="#9AA5B1", lw=6, solid_capstyle="butt")
        ax.plot(obs, i, "o", color="#D55E00" if not lo <= obs <= hi else "#009E73")
    ax.set_yticks(range(len(measures)))
    ax.set_yticklabels([f"{t} {n[:38]}".strip() for t, n, *_ in measures], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("% (grey = range expected in A3; dot = observed; green inside, orange outside)")
    save(fig, out, "A4_Fig08_expected_vs_observed_quality.png")


def fig_sensitivity(an, out):
    s = read(os.path.join(an, "sensitivity.csv"))
    variants = ["all", "without_borderline", "no_experience_only", "one_to_three_years_only"]
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    for i, k in enumerate(KEYS):
        for j, v in enumerate(variants):
            r = next((x for x in s if x["programme"] == k and x["variant"] == v), None)
            if r and r["U_strict"] != "":
                ax.bar(i + (j - 1.5) * 0.2, float(r["U_strict"]), 0.2, color=COLOR[k], alpha=0.4 + 0.2 * j)
                ax.text(i + (j - 1.5) * 0.2, float(r["U_strict"]) + 0.005, f"n={r['n']}", ha="center", fontsize=6, rotation=90)
    ax.set_xticks(range(3))
    ax.set_xticklabels([LABEL[k] for k in KEYS])
    ax.set_ylabel("U (strict)")
    ax.set_title("bars left to right: all; without borderline; 'no experience' only; '1-3 years' only", fontsize=8)
    save(fig, out, "A4_Fig09_sensitivity.png")


def fig_vacancy_cov(an, out, vac):
    import statistics  # noqa: F401
    g = read(os.path.join(an, "C.csv"))
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    from coding import CATEGORIES as CATS  # noqa: F401
    cols = [f"c{i:02d}" for i in range(1, 20)]
    for i, k in enumerate(KEYS):
        cov = [int(next(r["C_strict"] for r in g if r["programme"] == k and int(r["category_id"]) == c + 1)) for c in range(19)]
        shares = []
        for r in vac:
            if r["group"] != k:
                continue
            cats = [c for c, col in enumerate(cols) if int(r[col])]
            if cats:
                shares.append(sum(cov[c] for c in cats) / len(cats))
        ax.boxplot(shares, positions=[i], widths=0.5, patch_artist=True, boxprops={"facecolor": COLOR[k], "alpha": 0.5},
                   medianprops={"color": "black"})
    ax.set_xticks(range(3))
    ax.set_xticklabels([LABEL[k] for k in KEYS])
    ax.set_ylabel("Share of a vacancy's categories\ncovered by the programme (strict)")
    save(fig, out, "A4_Fig10_vacancy_level_coverage.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--an", required=True)
    ap.add_argument("--sessions", nargs="+", required=True)
    ap.add_argument("--combined", required=True)
    ap.add_argument("--vacancies", required=True, help="vacancy_skills.csv of the combined dataset")
    ap.add_argument("--t10", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    vac = read(a.vacancies)
    fig_funnel(a.sessions, a.combined, a.out)
    fig_counts(a.an, a.out, vac)
    fig_demand(a.an, a.out)
    fig_coverage(a.an, a.out)
    fig_u(a.an, a.out)
    fig_gaps(a.an, a.out)
    fig_stability(a.an, a.out)
    fig_t10(a.t10, a.out)
    fig_sensitivity(a.an, a.out)
    fig_vacancy_cov(a.an, a.out, vac)


if __name__ == "__main__":
    main()
