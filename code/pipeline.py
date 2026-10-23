#!/usr/bin/env python3
"""
Processing pipeline for hh.kz vacancies (RMT study).

Step 2 (candidates):
    python3 03_code/pipeline.py candidates --cards <hh_cards_*.json> --out <folder>

Steps 4-5 (final screening and assignment to programmes):
    python3 03_code/pipeline.py final --cards <hh_cards_*.json> --full <hh_full_*.json> --out <folder>

Several files from different sessions can be passed; they are merged by vacancy ID.
Standard library only, Python 3.9+.
"""
import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse

import rules as R


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def norm(s):
    # Lower-case, replace the Russian letter "yo" with "ye", collapse whitespace
    s = (s or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", s).strip()


def compile_list(patterns):
    return [re.compile(p.replace("ё", "е"), re.I) for p in patterns]


EXCL = compile_list(R.EXCLUDE_TITLE)
SENIOR = compile_list(R.EXCLUDE_SENIOR)
MIDDLE = compile_list(R.MIDDLE)
ROLE = {g: compile_list(p) for g, p in R.ROLE_TITLE.items()}
GENERIC = compile_list(R.GENERIC_TITLE)
JUNIOR = compile_list(R.JUNIOR_MARKERS)
EXP_OK = compile_list(R.EXPERIENCE_OK_TEXT)
EXP_HIGH = compile_list(R.EXPERIENCE_TOO_HIGH)
TEXT = {g: compile_list(p) for g, p in R.TEXT_MARKERS.items()}


def first_hit(pats, text):
    for p in pats:
        m = p.search(text)
        if m:
            return m.group(0)
    return None


def count_hits(pats, text):
    return sum(1 for p in pats if p.search(text))


def load_many(paths, key):
    merged = {}
    extra = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get(key, data) if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = list(items.values())
        for it in items:
            merged[str(it["id"])] = {**merged.get(str(it["id"]), {}), **it}
        if isinstance(data, dict) and "searches" in data:
            extra.update(data["searches"])
    return merged, extra


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("; ".join(v) if isinstance(v, list) else v) for k, v in r.items()})


# ---------------------------------------------------------------------------
# Step 2. Screening of search cards
# ---------------------------------------------------------------------------

def bucket_of(card):
    # Experience labels on hh.kz cards are in Russian: "no experience", "1-3 years", "3-6 years", "over 6"
    exp = norm(card.get("experience")) or norm(card.get("raw"))
    if re.search(r"без опыта|опыт не нужен|no experience", exp):
        return "noExperience"
    if re.search(r"1\s*[–-]\s*3", exp):
        return "between1And3"
    if re.search(r"3\s*[–-]\s*6|более 6|6\+", exp):
        return "more"
    q = parse_qs(urlparse(card.get("search_url", "")).query)
    vals = q.get("experience", [])
    return vals[0] if len(vals) == 1 else "unknown"


def title_role(title):
    for g in R.ROLE_PRIORITY:
        hit = first_hit(ROLE[g], title)
        if hit:
            return g, hit
    return None, None


def screen_card(card):
    """Returns (decision, reason, detail)."""
    title = norm(card.get("title"))
    snippet = norm(card.get("snippet")) or norm(card.get("raw"))
    bucket = bucket_of(card)
    junior_title = first_hit(JUNIOR, title)

    if bucket not in ("noExperience", "between1And3"):
        return "out", "experience_bucket", bucket
    hit = first_hit(EXCL, title)
    if hit:
        return "out", "excluded_role", hit
    hit = first_hit(SENIOR, title)
    if hit:
        return "out", "senior_title", hit
    hit = first_hit(MIDDLE, title)
    if hit and not junior_title:
        return "out", "senior_title", hit

    role, hit = title_role(title)
    generic = first_hit(GENERIC, title)
    if not role and not generic:
        return "out", "no_role_match", ""

    if bucket == "between1And3":
        if not (junior_title or first_hit(JUNIOR, snippet) or first_hit(EXP_OK, snippet)):
            return "out", "not_entry_level_card", ""

    return "candidate", "", role or "generic"


def cmd_candidates(args):
    cards, searches = load_many(args.cards, "cards")
    os.makedirs(args.out, exist_ok=True)
    rows, reasons, cand = [], Counter(), []
    for c in cards.values():
        dec, reason, det = screen_card(c)
        rows.append({**c, "bucket": bucket_of(c), "decision": dec, "reason": reason, "detail": det})
        if dec == "candidate":
            cand.append(c["id"])
        else:
            reasons[reason] += 1

    write_csv(os.path.join(args.out, "cards_screened.csv"), rows,
              ["id", "decision", "reason", "detail", "bucket", "title", "company", "city", "experience", "snippet", "search_url"])
    with open(os.path.join(args.out, "candidates.txt"), "w", encoding="utf-8") as f:
        f.write(" ".join(cand))

    print(f"Rules: {R.RULES_VERSION}")
    print(f"Cards in total (unique): {len(cards)}")
    print("By experience bucket:", dict(Counter(r["bucket"] for r in rows)))
    print("Excluded at card stage:", dict(reasons))
    print(f"Candidates: {len(cand)}  ->  {os.path.join(args.out, 'candidates.txt')}")
    if searches:
        print("\nSearches (as reported by hh):")
        for url, s in searches.items():
            print(f"  {s.get('header', '')[:80]} | pages harvested: {len(s.get('pages', []))}")


# ---------------------------------------------------------------------------
# Steps 4-5. Final screening and assignment
# ---------------------------------------------------------------------------

def assign_group(title, text):
    role, hit = title_role(title)
    if role:
        return role, "title", hit
    scores = {g: count_hits(TEXT[g], text) for g in R.ROLE_PRIORITY}
    best = max(scores.values())
    winners = [g for g, s in scores.items() if s == best]
    if best >= R.TEXT_MIN_HITS and len(winners) == 1:
        return winners[0], "text", json.dumps(scores)
    return None, "unassigned", json.dumps(scores)


def cmd_final(args):
    cards, searches = load_many(args.cards, "cards")
    full, _ = load_many(args.full, "vacancies")
    os.makedirs(args.out, exist_ok=True)

    stage1 = Counter()
    candidates = []
    for c in cards.values():
        dec, reason, _ = screen_card(c)
        if dec == "candidate":
            candidates.append(c)
        else:
            stage1[reason] += 1

    log, included, stage2 = [], [], Counter()
    for c in candidates:
        v = full.get(c["id"])
        row = {"id": c["id"], "title": c.get("title"), "company": c.get("company"), "bucket": bucket_of(c)}
        if not v:
            reason = "not_collected"
        elif v.get("status") == "skipped":
            reason = "skipped_manual"
        else:
            title = norm(v.get("title") or c.get("title"))
            text = norm(v.get("description"))
            if len(text) < R.MIN_DESCRIPTION_CHARS:
                reason = "no_requirements"
            elif first_hit(EXP_HIGH, text):
                reason = "experience_too_high"
                row["detail"] = first_hit(EXP_HIGH, text)
            elif row["bucket"] == "between1And3" and not (first_hit(JUNIOR, title) or first_hit(EXP_OK, text) or first_hit(JUNIOR, text)):
                reason = "experience_unclear"
            else:
                group, basis, det = assign_group(title, text)
                if not group:
                    reason = "unassigned_role"
                    row["detail"] = det
                else:
                    reason = ""
                    rec = {**c, **v, "bucket": row["bucket"], "group": group, "assign_basis": basis, "assign_detail": det}
                    included.append(rec)
        if reason:
            stage2[reason] += 1
        row.update({"decision": "included" if not reason else "excluded", "reason": reason})
        log.append(row)

    # Deduplication: same company + same title + similar text
    by_key = defaultdict(list)
    for r in included:
        by_key[(norm(r.get("company")), norm(r.get("title")))].append(r)
    dup_ids = set()
    for group in by_key.values():
        group.sort(key=lambda r: (r.get("published") or "", r["id"]))
        for i, a in enumerate(group):
            if a["id"] in dup_ids:
                continue
            for b in group[i + 1:]:
                if b["id"] in dup_ids:
                    continue
                sim = SequenceMatcher(None, norm(a.get("description"))[:1500], norm(b.get("description"))[:1500]).ratio()
                if sim >= R.DEDUP_SIMILARITY:
                    dup_ids.add(b["id"])
    for row in log:
        if row["id"] in dup_ids:
            row.update({"decision": "excluded", "reason": "duplicate"})
            stage2["duplicate"] += 1
    final = [r for r in included if r["id"] not in dup_ids]

    # Output
    fields = ["id", "group", "assign_basis", "bucket", "title", "company", "location", "city", "experience",
              "employment", "salary", "published", "key_skills", "description", "url", "search_url", "saved_at"]
    write_csv(os.path.join(args.out, "final_dataset.csv"), final, fields)
    with open(os.path.join(args.out, "final_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)
    write_csv(os.path.join(args.out, "screening_log.csv"), log, ["id", "decision", "reason", "detail", "bucket", "title", "company"])

    write_report(args.out, cards, stage1, candidates, stage2, final, searches)
    print(open(os.path.join(args.out, "report.md"), encoding="utf-8").read())


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

REASON_TEXT = {
    "experience_bucket": "experience bucket 3+ years / unknown",
    "excluded_role": "role not in any programme's list of positions",
    "senior_title": "seniority above entry level (title)",
    "no_role_match": "title does not match programme positions",
    "not_entry_level_card": "1-3 years without junior/intern markers",
    "not_collected": "full text not collected",
    "skipped_manual": "skipped manually (X)",
    "no_requirements": "no requirements text",
    "experience_too_high": "text requires 2+ years of experience",
    "experience_unclear": "1-3 years, no sign of <=1 year in text",
    "unassigned_role": "role could not be assigned to a programme",
    "duplicate": "duplicate",
}
GROUP_NAME = {"se": "Software Engineering", "cyber": "Cybersecurity", "bda": "Big Data Analysis"}


def write_report(out, cards, stage1, candidates, stage2, final, searches):
    L = []
    L.append("# Preliminary vacancy collection report\n")
    L.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M} · rules: `{R.RULES_VERSION}`\n")
    L.append("> Preliminary data: screening rules are not frozen yet and the skill taxonomy is not built. "
             "The top skills below come from the hh \"Key skills\" field, not from the final taxonomy.\n")

    L.append("## Screening flow\n")
    L.append("| Stage | Count |\n|---|---|")
    L.append(f"| Cards harvested (unique) | {len(cards)} |")
    for k, n in stage1.most_common():
        L.append(f"| - {REASON_TEXT.get(k, k)} | {n} |")
    L.append(f"| **Candidates** | **{len(candidates)}** |")
    for k, n in stage2.most_common():
        L.append(f"| - {REASON_TEXT.get(k, k)} | {n} |")
    L.append(f"| **Included in the sample** | **{len(final)}** |\n")

    L.append("## Distribution by programme\n")
    L.append("| Programme | Vacancies | of which \"no experience\" | Assigned by text | Status |\n|---|---|---|---|---|")
    for g in R.ROLE_PRIORITY:
        rows = [r for r in final if r["group"] == g]
        noexp = sum(r["bucket"] == "noExperience" for r in rows)
        bytext = sum(r["assign_basis"] == "text" for r in rows)
        status = "sufficient" if len(rows) >= R.SMALL_GROUP_N else f"small (< {R.SMALL_GROUP_N})"
        L.append(f"| {GROUP_NAME[g]} | {len(rows)} | {noexp} | {bytext} | {status} |")
    L.append("")

    for g in R.ROLE_PRIORITY:
        rows = [r for r in final if r["group"] == g]
        if not rows:
            continue
        cnt = Counter(norm(s) for r in rows for s in set(r.get("key_skills") or []))
        with_skills = sum(1 for r in rows if r.get("key_skills"))
        L.append(f"## {GROUP_NAME[g]}: top 20 hh key skills\n")
        L.append(f"Vacancies with the key skills field filled: {with_skills} of {len(rows)}\n")
        L.append("| Skill | Vacancies | Share |\n|---|---|---|")
        for s, n in cnt.most_common(20):
            L.append(f"| {s} | {n} | {n / len(rows):.0%} |")
        L.append("")

    cities = Counter((r.get("city") or r.get("location") or "—").split(",")[0].strip() for r in final)
    L.append("## Cities\n")
    L.append("| City | Vacancies |\n|---|---|")
    for c, n in cities.most_common(8):
        L.append(f"| {c} | {n} |")
    L.append("")

    if searches:
        L.append("## hh searches\n")
        L.append("| Search result header | Pages harvested |\n|---|---|")
        for s in searches.values():
            L.append(f"| {s.get('header', '')[:90]} | {len(s.get('pages', []))} |")

    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="RMT: processing of hh.kz vacancies")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("candidates", help="Step 2: select candidates from search cards")
    a.add_argument("--cards", nargs="+", required=True)
    a.add_argument("--out", default="out")
    b = sub.add_parser("final", help="Steps 4-5: final screening and assignment to programmes")
    b.add_argument("--cards", nargs="+", required=True)
    b.add_argument("--full", nargs="+", required=True)
    b.add_argument("--out", default="out")
    args = ap.parse_args()
    {"candidates": cmd_candidates, "final": cmd_final}[args.cmd](args)


if __name__ == "__main__":
    main()
