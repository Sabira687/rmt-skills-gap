#!/usr/bin/env python3
"""
Processing pipeline for hh.kz vacancies (RMT study).

Step 2 (candidates):
    python3 code/pipeline.py candidates --cards <hh_cards_*.json> --out <folder>

Steps 4-5 (final screening and assignment to programmes):
    python3 code/pipeline.py final --cards <hh_cards_*.json> --full <hh_full_*.json> --out <folder>

Readable copy of a raw export (contacts in full texts are masked):
    python3 code/pipeline.py export-csv --json <hh_cards_*.json | hh_full_*.json> --out <file.csv>

Data dictionary, cleaning log and data-quality shares (T10):
    python3 code/pipeline.py quality --cards ... [--full ...] [--check <accuracy_check.csv>] --out <folder>

Sample for the accuracy check (10 included, 10 excluded on full text, 10 excluded on card):
    python3 code/pipeline.py sample-check --cards ... --full ... --out logs/accuracy_check_session1.csv

Several files from different sessions can be passed; they are merged by vacancy ID.
Standard library only, Python 3.9+.
"""
import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse

import rules as R


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

# Latin and Cyrillic letters that look the same. Employers sometimes type a Latin "C" in a
# Russian word ("Cистемный"), which breaks every Cyrillic pattern.
LAT2CYR = str.maketrans("aceopxykmthb", "асеорхукмтнв")
CYR2LAT = str.maketrans("асеорхукмтнв", "aceopxykmthb")
LETTER_RUN = re.compile(r"[^\W\d_]+")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
LATIN = re.compile(r"[a-z]")


def fix_mixed_script(word):
    # A word that mixes scripts is converted to the script of the majority of its letters
    cyr, lat = len(CYRILLIC.findall(word)), len(LATIN.findall(word))
    if not cyr or not lat:
        return word
    return word.translate(LAT2CYR if cyr >= lat else CYR2LAT)


def norm(s):
    # Lower-case, replace the Russian letter "yo" with "ye", fix mixed-script words, collapse whitespace
    s = (s or "").lower().replace("ё", "е")
    s = LETTER_RUN.sub(lambda m: fix_mixed_script(m.group(0)), s)
    return re.sub(r"\s+", " ", s).strip()


def compile_list(patterns):
    return [re.compile(p.replace("ё", "е"), re.I) for p in patterns]


EXCL = compile_list(R.EXCLUDE_TITLE)
EXCL_SOFT = compile_list(R.EXCLUDE_TITLE_SOFT)
OVERRIDE = compile_list(R.POSITION_OVERRIDE)
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
# Masking of contacts in published texts
# ---------------------------------------------------------------------------

CONTACT = "[contact]"
MASKS = [
    # e-mail
    ("email", re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")),
    # messenger links
    ("link", re.compile(r"(https?://)?(t\.me|telegram\.me|wa\.me|api\.whatsapp\.com)/\S+", re.I)),
    # Kazakhstan phone numbers: +7 or 8 followed by 10 digits with any separators
    ("phone", re.compile(r"(?<![\d+])(\+\s?7|8)([\s\-()]*\d){10}(?!\d)")),
    # Telegram user names
    ("handle", re.compile(r"(?<![\w.@])@[a-z][\w]{3,}", re.I)),
    # One to three capitalised words after a contact label ("Контактное лицо: <name>", "HR: <name>",
    # "обращаться к <name>"). The labels are Russian/English words found in hh.kz vacancy texts.
    ("name", re.compile(r"((?i:\b(контактное лицо|контакты|контакт|contact person|contacts?|hr|рекрутер|recruiter)"
                        r"\s*[:\-–—]\s*|\b(?i:обращаться к)\s+))"
                        r"[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ][\w'-]*(\s+[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ][\w'-]*){0,2}")),
]


def mask_contacts(text):
    """Returns (masked text, Counter of masked items by kind)."""
    counts = Counter()
    for kind, pat in MASKS:
        if kind == "name":
            text, n = pat.subn(lambda m: m.group(1) + CONTACT, text or "")
        else:
            text, n = pat.subn(CONTACT, text or "")
        counts[kind] += n
    return text, counts


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
    """Returns (decision, reason, detail, borderline).
    borderline is the soft exclusion word that a programme position overrode, or ""."""
    title = norm(card.get("title"))
    bucket = bucket_of(card)
    junior_title = first_hit(JUNIOR, title)

    if bucket not in ("noExperience", "between1And3"):
        return "out", "experience_bucket", bucket, ""
    hit = first_hit(EXCL, title)
    if hit:
        return "out", "excluded_role", hit, ""
    soft = first_hit(EXCL_SOFT, title) or ""
    if soft and not first_hit(OVERRIDE, title):
        return "out", "excluded_role", soft, ""
    hit = first_hit(SENIOR, title)
    if hit:
        return "out", "senior_title", hit, ""
    hit = first_hit(MIDDLE, title)
    if hit and not junior_title:
        return "out", "senior_title", hit, ""

    role, hit = title_role(title)
    generic = first_hit(GENERIC, title)
    if not role and not generic:
        return "out", "no_role_match", "", ""

    # Entry level of "1-3 years" vacancies is decided on the full text (experience_unclear),
    # because the card snippet is cut at about 150 characters
    return "candidate", "", role or "generic", soft


def cmd_candidates(args):
    cards, searches = load_many(args.cards, "cards")
    os.makedirs(args.out, exist_ok=True)
    rows, reasons, cand = [], Counter(), []
    for c in cards.values():
        dec, reason, det, soft = screen_card(c)
        rows.append({**c, "bucket": bucket_of(c), "decision": dec, "reason": reason, "detail": det, "borderline": soft})
        if dec == "candidate":
            cand.append(c["id"])
        else:
            reasons[reason] += 1

    write_csv(os.path.join(args.out, "cards_screened.csv"), rows,
              ["id", "decision", "reason", "detail", "borderline", "bucket", "title", "company", "city", "experience",
               "snippet", "search_url"])
    with open(os.path.join(args.out, "candidates.txt"), "w", encoding="utf-8") as f:
        f.write(" ".join(cand))

    print(f"Rules: {R.RULES_VERSION}")
    print(f"Cards in total (unique): {len(cards)}")
    print("By experience bucket:", dict(Counter(r["bucket"] for r in rows)))
    print("Excluded at card stage:", dict(reasons))
    print("Candidates by title group:", dict(Counter(r["detail"] for r in rows if r["decision"] == "candidate")))
    print(f"  of which borderline (soft exclusion overridden): {sum(1 for r in rows if r['borderline'])}")
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


def screen_all(cards, full):
    """Runs both screening stages and deduplication. Returns a dict with every intermediate result."""
    stage1 = Counter()
    candidates, card_rows = [], []
    for c in cards.values():
        dec, reason, det, soft = screen_card(c)
        card_rows.append({"id": c["id"], "decision": dec, "reason": reason, "detail": det, "title": c.get("title"),
                          "company": c.get("company"), "bucket": bucket_of(c)})
        if dec == "candidate":
            candidates.append({**c, "borderline": soft})
        else:
            stage1[reason] += 1

    log, included, stage2 = [], [], Counter()
    for c in candidates:
        v = full.get(c["id"])
        row = {"id": c["id"], "title": c.get("title"), "company": c.get("company"), "bucket": bucket_of(c),
               "borderline": c["borderline"]}
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
                    row["group"] = group
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
    return {"stage1": stage1, "card_rows": card_rows, "candidates": candidates, "log": log,
            "included": included, "dup_ids": dup_ids, "stage2": stage2, "final": final}


FINAL_FIELDS = ["id", "group", "assign_basis", "borderline", "bucket", "title", "company", "location", "city",
                "experience", "employment", "salary", "published", "key_skills", "description", "url", "search_url",
                "saved_at"]


def publishable(rec):
    # Copy of a vacancy that is safe to publish: contacts masked, raw HTML dropped
    out = {k: v for k, v in rec.items() if k != "description_html"}
    out["description"], _ = mask_contacts(rec.get("description"))
    return out


def cmd_final(args):
    cards, searches = load_many(args.cards, "cards")
    full, _ = load_many(args.full, "vacancies")
    os.makedirs(args.out, exist_ok=True)
    s = screen_all(cards, full)
    final = [publishable(r) for r in s["final"]]

    write_csv(os.path.join(args.out, "final_dataset.csv"), final, FINAL_FIELDS)
    with open(os.path.join(args.out, "final_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)
    write_csv(os.path.join(args.out, "screening_log.csv"), s["log"],
              ["id", "decision", "reason", "detail", "group", "borderline", "bucket", "title", "company"])

    write_report(args.out, cards, s["stage1"], s["candidates"], s["stage2"], final, searches)
    print(open(os.path.join(args.out, "report.md"), encoding="utf-8").read())


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

REASON_TEXT = {
    "experience_bucket": "experience bucket 3+ years / unknown",
    "excluded_role": "role not in any programme's list of positions",
    "senior_title": "seniority above entry level (title)",
    "no_role_match": "title does not match programme positions",
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
    L.append("| Programme | Vacancies | of which \"no experience\" | Assigned by text | Borderline titles | Status |\n"
             "|---|---|---|---|---|---|")
    for g in R.ROLE_PRIORITY:
        rows = [r for r in final if r["group"] == g]
        noexp = sum(r["bucket"] == "noExperience" for r in rows)
        bytext = sum(r["assign_basis"] == "text" for r in rows)
        border = sum(1 for r in rows if r.get("borderline"))
        status = "sufficient" if len(rows) >= R.SMALL_GROUP_N else f"small (< {R.SMALL_GROUP_N})"
        L.append(f"| {GROUP_NAME[g]} | {len(rows)} | {noexp} | {bytext} | {border} | {status} |")
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
# Readable CSV copy of a raw export
# ---------------------------------------------------------------------------

CARD_FIELDS = ["id", "title", "company", "city", "experience", "salary", "snippet", "raw", "search_url",
               "harvested_at", "first_seen"]
FULL_FIELDS = ["id", "url", "status", "title", "company", "location", "experience", "employment", "salary",
               "published", "archived", "key_skills", "description", "saved_at"]


def cmd_export_csv(args):
    with open(args.json, encoding="utf-8") as f:
        data = json.load(f)
    if "vacancies" in data:
        items, _ = load_many([args.json], "vacancies")
        rows, masked = [], Counter()
        for v in items.values():
            out = publishable(v)
            masked += mask_contacts(v.get("description"))[1]
            rows.append(out)
        write_csv(args.out, rows, FULL_FIELDS)
        print(f"Full vacancies: {len(rows)} -> {args.out}")
        print(f"Masked: {dict(masked)} (description_html dropped)")
    else:
        items, _ = load_many([args.json], "cards")
        write_csv(args.out, list(items.values()), CARD_FIELDS)
        print(f"Cards: {len(items)} -> {args.out}")


# ---------------------------------------------------------------------------
# Data quality: data dictionary, cleaning log, T10 shares, accuracy check
# ---------------------------------------------------------------------------

# Level of measurement, unit and meaning of every field of the final dataset (E.2)
FIELD_INFO = {
    "id": ("nominal", "-", "hh vacancy ID"),
    "group": ("nominal", "-", "programme the vacancy is assigned to"),
    "assign_basis": ("nominal", "-", "assigned by title or by full-text markers"),
    "borderline": ("nominal", "-", "soft exclusion word overridden by a programme position (empty = not borderline)"),
    "bucket": ("ordinal", "experience bucket", "hh experience filter of the search"),
    "title": ("nominal", "-", "vacancy title"),
    "company": ("nominal", "-", "employer name"),
    "location": ("nominal", "-", "address on the vacancy page"),
    "city": ("nominal", "-", "city on the search card"),
    "experience": ("ordinal", "experience bucket", "experience label on the vacancy page"),
    "employment": ("nominal", "-", "employment type / schedule"),
    "salary": ("nominal", "text, KZT or other", "salary as displayed (not parsed)"),
    "published": ("interval", "date", "publication date (JSON-LD datePosted)"),
    "key_skills": ("nominal", "list of tags", "hh 'Key skills' field"),
    "description": ("ratio", "characters (length)", "full vacancy text, contacts masked"),
    "url": ("nominal", "-", "vacancy URL"),
    "search_url": ("nominal", "-", "search page the card came from"),
    "saved_at": ("interval", "timestamp, UTC", "time the full text was saved"),
    "snippet": ("nominal", "text", "requirement and responsibility snippets on the search card"),
    "raw": ("nominal", "text", "whole text of the search card (fallback)"),
    "harvested_at": ("interval", "timestamp, UTC", "time the card was last harvested"),
    "first_seen": ("interval", "timestamp, UTC", "time the card was first harvested"),
}

# T10 data-quality expectations, copied from logs/expected_results_2026-10-24.md (low, high, as shares)
T10_EXPECTED = {
    "not_entry_level_1_3": (0.70, 0.85),
    "role_mismatch": (0.10, 0.15),
    "duplicates": (0.05, 0.10),
    "empty_key_skills": (0.25, 0.35),
    "closed_before_full_text": (0.0, 0.05),
    "no_requirements": (0.0, 0.05),
}


def is_missing(v):
    return v is None or v == "" or v == [] or (isinstance(v, str) and not v.strip())


def describe_values(field, values):
    present = [v for v in values if not is_missing(v)]
    if not present:
        return "-"
    if field == "description":
        lens = [len(v) for v in present]
        return f"{min(lens)}-{max(lens)} characters"
    if field == "key_skills":
        n = [len(v) for v in present]
        return f"{min(n)}-{max(n)} tags per vacancy, {len({s for v in present for s in v})} distinct"
    if field in ("published", "saved_at", "harvested_at", "first_seen"):
        return f"{min(present)[:10]} to {max(present)[:10]}"
    distinct = Counter(present)
    if len(distinct) <= 8:
        return ", ".join(f"{k} ({n})" for k, n in distinct.most_common())
    return f"{len(distinct)} distinct values"


def data_dictionary(rows, fields):
    out = []
    for f in fields:
        values = [r.get(f) for r in rows]
        miss = sum(1 for v in values if is_missing(v))
        level, unit, meaning = FIELD_INFO.get(f, ("nominal", "-", ""))
        out.append({"field": f, "type": level, "unit": unit, "meaning": meaning,
                    "values_or_range": describe_values(f, values), "missing_n": miss,
                    "missing_pct": f"{miss / len(rows):.1%}" if rows else "-"})
    return out


def share(n, d):
    return (n, d, n / d if d else None)


def t10_shares(cards, full, s, check_rows):
    """Each value is (numerator, denominator, share) with the definition in T10_DEFINITION."""
    res = {}
    if full:
        # 1-3 years candidates whose full text reached the experience check but are not entry level
        reached = [r for r in s["log"] if r["bucket"] == "between1And3"
                   and r["reason"] not in ("not_collected", "skipped_manual", "no_requirements")]
        not_entry = sum(1 for r in reached if r["reason"] in ("experience_unclear", "experience_too_high"))
        res["not_entry_level_1_3"] = share(not_entry, len(reached))
        collected = [r for r in s["log"] if r["reason"] not in ("not_collected",)]
        res["no_requirements"] = share(sum(1 for r in collected if r["reason"] == "no_requirements"), len(collected))
        closed = sum(1 for r in collected if full.get(r["id"], {}).get("archived") or r["reason"] == "skipped_manual")
        res["closed_before_full_text"] = share(closed, len(collected))
        res["duplicates"] = share(len(s["dup_ids"]), len(s["included"]))
        res["empty_key_skills"] = share(sum(1 for r in s["final"] if is_missing(r.get("key_skills"))), len(s["final"]))
        res["unassigned_proxy"] = share(sum(1 for r in collected if r["reason"] == "unassigned_role"), len(collected))
    judged = [r for r in check_rows if (r.get("hh_role_matches") or "").strip()]
    if judged:
        no = sum(1 for r in judged if r["hh_role_matches"].strip().lower() in ("no", "0", "false", "n"))
        res["role_mismatch"] = share(no, len(judged))
    return res


T10_DEFINITION = {
    "not_entry_level_1_3": "1-3 year candidates excluded on full text as not entry level (experience_unclear, "
                           "experience_too_high) / 1-3 year candidates whose full text reached the experience check",
    "role_mismatch": "accuracy-check vacancies where the hh role does not match the text / judged vacancies",
    "duplicates": "duplicates removed / included before deduplication",
    "empty_key_skills": "final vacancies with an empty 'Key skills' field / final vacancies",
    "closed_before_full_text": "collected candidates archived or skipped / collected candidates",
    "no_requirements": "collected candidates with a description under "
                       f"{R.MIN_DESCRIPTION_CHARS} characters / collected candidates",
    "unassigned_proxy": "collected candidates whose programme could not be assigned / collected candidates "
                        "(proxy for role mismatch, no expectation declared)",
}


def verdict(key, value):
    if key not in T10_EXPECTED or value is None:
        return "-"
    lo, hi = T10_EXPECTED[key]
    if value < lo:
        return "below expected range"
    if value > hi:
        return "above expected range"
    return "within expected range"


def agreement(check_rows):
    # A row agrees when the manual decision matches the code, and for included vacancies the group as well
    rows = [r for r in check_rows if (r.get("my_decision") or "").strip()]
    by_stage = defaultdict(lambda: [0, 0])
    for r in rows:
        ok = r["my_decision"].strip().lower() == r["code_decision"].strip().lower()
        if ok and r["code_decision"] == "included":
            ok = r.get("my_group", "").strip().lower() == r["code_group"].strip().lower()
        by_stage[r["stage"]][0] += ok
        by_stage[r["stage"]][1] += 1
    return rows, dict(by_stage)


def cleaning_log(cards, card_files, full, s):
    rows = []
    n_raw = 0
    for path in card_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        n_raw += len(data.get("cards", data) if isinstance(data, dict) else data)
    rows.append({"step": "Duplicates removed (same ID)", "rule": "cards merged by hh vacancy ID across export files",
                 "rows_before": n_raw, "rows_after": len(cards),
                 "revealed": f"{n_raw - len(cards)} repeated IDs"})
    empty_title = sum(1 for c in cards.values() if is_missing(c.get("title")))
    no_bucket = sum(1 for c in cards.values() if bucket_of(c) == "unknown")
    rows.append({"step": "Impossible values handled (cards)",
                 "rule": "empty title or experience bucket not recognised -> reported, card kept",
                 "rows_before": len(cards), "rows_after": len(cards),
                 "revealed": f"{empty_title} empty titles, {no_bucket} unknown buckets"})
    if not full:
        return rows
    collected = [r for r in s["log"] if r["reason"] != "not_collected"]
    no_req = sum(1 for r in collected if r["reason"] == "no_requirements")
    rows.append({"step": "Missing values handled (description)",
                 "rule": f"description shorter than {R.MIN_DESCRIPTION_CHARS} characters -> excluded (no_requirements)",
                 "rows_before": len(collected), "rows_after": len(collected) - no_req,
                 "revealed": f"{no_req} vacancies without requirements text"})
    mismatch, future = 0, 0
    for r in s["included"]:
        page_bucket = bucket_of({"experience": r.get("experience")})
        if page_bucket in ("noExperience", "between1And3", "more") and page_bucket != r["bucket"]:
            mismatch += 1
        if r.get("published") and r.get("saved_at") and r["published"][:10] > r["saved_at"][:10]:
            future += 1
    rows.append({"step": "Impossible values handled (vacancies)",
                 "rule": "experience on the page differs from the search bucket; publication date after saving date "
                         "-> reported, vacancy kept",
                 "rows_before": len(s["included"]), "rows_after": len(s["included"]),
                 "revealed": f"{mismatch} experience mismatches, {future} dates in the future"})
    rows.append({"step": "Duplicates removed (same company, title and text)",
                 "rule": f"same company and title, text similarity >= {R.DEDUP_SIMILARITY} -> later one excluded",
                 "rows_before": len(s["included"]), "rows_after": len(s["final"]),
                 "revealed": f"{len(s['dup_ids'])} duplicates"})
    empty_skills = sum(1 for r in s["final"] if is_missing(r.get("key_skills")))
    rows.append({"step": "Missing values handled (key skills)",
                 "rule": "empty 'Key skills' field -> kept, skills are coded from the description text",
                 "rows_before": len(s["final"]), "rows_after": len(s["final"]),
                 "revealed": f"{empty_skills} vacancies with an empty field"})
    return rows


def md_table(rows, fields):
    L = ["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    for r in rows:
        L.append("| " + " | ".join(str(r.get(f, "")).replace("|", "/") for f in fields) + " |")
    return L


def cmd_quality(args):
    cards, _ = load_many(args.cards, "cards")
    full, _ = load_many(args.full, "vacancies") if args.full else ({}, {})
    check_rows = []
    if args.check and os.path.exists(args.check):
        with open(args.check, encoding="utf-8-sig") as f:
            check_rows = list(csv.DictReader(f))
    os.makedirs(args.out, exist_ok=True)
    s = screen_all(cards, full)

    if full:
        dd_rows, dd_fields, dd_name = [publishable(r) for r in s["final"]], FINAL_FIELDS, "final dataset"
    else:
        dd_rows, dd_fields, dd_name = list(cards.values()), CARD_FIELDS, "search cards"
    dd = data_dictionary(dd_rows, dd_fields)
    dd_cols = ["field", "type", "unit", "meaning", "values_or_range", "missing_n", "missing_pct"]
    write_csv(os.path.join(args.out, "data_dictionary.csv"), dd, dd_cols)

    cl = cleaning_log(cards, args.cards, full, s)
    cl_cols = ["step", "rule", "rows_before", "rows_after", "revealed"]
    write_csv(os.path.join(args.out, "cleaning_log.csv"), cl, cl_cols)

    shares = t10_shares(cards, full, s, check_rows)
    t10 = []
    for k, (n, d, v) in shares.items():
        lo_hi = T10_EXPECTED.get(k)
        t10.append({"measure": k, "definition": T10_DEFINITION[k], "count": n, "base": d,
                    "observed": f"{v:.1%}" if v is not None else "-",
                    "expected": f"{lo_hi[0]:.0%}-{lo_hi[1]:.0%}" if lo_hi else "-", "verdict": verdict(k, v)})
    t10_cols = ["measure", "definition", "count", "base", "observed", "expected", "verdict"]
    write_csv(os.path.join(args.out, "t10_quality_shares.csv"), t10, t10_cols)

    L = ["# Data quality report\n",
         f"Generated: {datetime.now():%Y-%m-%d %H:%M} · rules: `{R.RULES_VERSION}`\n",
         f"Inputs: {', '.join(args.cards + (args.full or []))}\n",
         "## T10 data-quality shares\n"]
    if not full:
        L.append("> Card stage only: the T10 shares need full texts and are not computed yet.\n")
    L += md_table(t10, t10_cols) + [""]
    L += ["## Cleaning log (E.3)\n"] + md_table(cl, cl_cols) + [""]
    L += [f"## Data dictionary (E.2): {dd_name}, {len(dd_rows)} rows\n"] + md_table(dd, dd_cols) + [""]
    if check_rows:
        judged, by_stage = agreement(check_rows)
        L.append("## Accuracy check\n")
        L.append(f"Judged rows: {len(judged)} of {len(check_rows)}\n")
        L.append("| Stage | Agree | Judged | Agreement |\n|---|---|---|---|")
        tot_a = tot_n = 0
        for st, (a, n) in sorted(by_stage.items()):
            L.append(f"| {st} | {a} | {n} | {a / n:.0%} |")
            tot_a, tot_n = tot_a + a, tot_n + n
        if tot_n:
            L.append(f"| **all** | **{tot_a}** | **{tot_n}** | **{tot_a / tot_n:.0%}** |")
            L.append(f"\nThreshold 70%: {'passed' if tot_a / tot_n >= 0.70 else 'NOT passed - rules must be reworked'}")
    with open(os.path.join(args.out, "quality.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


# ---------------------------------------------------------------------------
# Sample for the accuracy check
# ---------------------------------------------------------------------------

CHECK_FIELDS = ["id", "stage", "code_decision", "code_group", "my_decision", "my_group", "agree",
                "hh_role_matches", "comment", "code_reason", "title", "url"]


def cmd_sample_check(args):
    if os.path.exists(args.out) and not args.force:
        sys.exit(f"{args.out} already exists (it may contain manual decisions). Use --force to overwrite.")
    cards, _ = load_many(args.cards, "cards")
    full, _ = load_many(args.full, "vacancies")
    s = screen_all(cards, full)

    strata = {
        "included": [{"id": r["id"], "code_decision": "included", "code_group": r["group"], "code_reason": "",
                      "title": r.get("title")} for r in s["final"]],
        "excluded_full_text": [{"id": r["id"], "code_decision": "excluded", "code_group": "",
                                "code_reason": r["reason"], "title": r.get("title")}
                               for r in s["log"] if r["decision"] == "excluded"
                               and r["reason"] not in ("not_collected", "skipped_manual")],
        "excluded_card": [{"id": r["id"], "code_decision": "excluded", "code_group": "",
                           "code_reason": r["reason"], "title": r.get("title")}
                          for r in s["card_rows"] if r["decision"] == "out"],
    }
    rng = random.Random(args.seed)
    rows = []
    for stage, pool in strata.items():
        pool = sorted(pool, key=lambda r: r["id"])
        pick = rng.sample(pool, min(args.n, len(pool)))
        if len(pick) < args.n:
            print(f"Warning: only {len(pick)} vacancies available for stage '{stage}'")
        for r in sorted(pick, key=lambda r: r["id"]):
            rows.append({**r, "stage": stage, "url": f"https://hh.kz/vacancy/{r['id']}"})
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    write_csv(args.out, rows, CHECK_FIELDS)
    print(f"Seed {args.seed}: {len(rows)} vacancies -> {args.out}")
    print("Fill in my_decision (included/excluded), my_group (se/cyber/bda), hh_role_matches (yes/no), comment.")


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
    c = sub.add_parser("export-csv", help="Readable CSV copy of a raw JSON export (contacts masked)")
    c.add_argument("--json", required=True)
    c.add_argument("--out", required=True)
    d = sub.add_parser("quality", help="Data dictionary, cleaning log, T10 shares, accuracy check agreement")
    d.add_argument("--cards", nargs="+", required=True)
    d.add_argument("--full", nargs="+")
    d.add_argument("--check", help="filled accuracy check CSV")
    d.add_argument("--out", default="out")
    e = sub.add_parser("sample-check", help="Stratified random sample for the accuracy check")
    e.add_argument("--cards", nargs="+", required=True)
    e.add_argument("--full", nargs="+", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--n", type=int, default=10, help="vacancies per stage")
    e.add_argument("--seed", type=int, default=20261025)
    e.add_argument("--force", action="store_true")
    args = ap.parse_args()
    {"candidates": cmd_candidates, "final": cmd_final, "export-csv": cmd_export_csv,
     "quality": cmd_quality, "sample-check": cmd_sample_check}[args.cmd](args)


if __name__ == "__main__":
    main()
