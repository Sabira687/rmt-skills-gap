# Data quality report

Generated: 2026-10-30 14:09 · rules: `v1-frozen-2026-10-25`

Inputs: data/raw/vacancies/session2_2026-10-30/hh_cards_2026-10-30-08-37.json, _private/session1_2026-10-23/hh_full_2026-10-25-11-14.json, _private/session1_2026-10-23/hh_full_2026-10-25-11-00.json, _private/session2_2026-10-30/hh_full_2026-10-30-09-07.json

## T10 data-quality shares

| measure | definition | count | base | observed | expected | verdict |
|---|---|---|---|---|---|---|
| not_entry_level_1_3 | 1-3 year candidates excluded on full text as not entry level (experience_unclear, experience_too_high) / 1-3 year candidates whose full text reached the experience check | 210 | 284 | 73.9% | 70%-85% | within expected range |
| no_requirements | collected candidates with a description under 300 characters / collected candidates | 4 | 342 | 1.2% | 0%-5% | within expected range |
| closed_before_full_text | collected candidates archived or skipped / collected candidates | 4 | 342 | 1.2% | 0%-5% | within expected range |
| duplicates | duplicates removed / included before deduplication | 12 | 80 | 15.0% | 5%-10% | above expected range |
| empty_key_skills | final vacancies with an empty 'Key skills' field / final vacancies | 22 | 68 | 32.4% | 25%-35% | within expected range |
| unassigned_proxy | collected candidates whose programme could not be assigned / collected candidates (proxy for role mismatch, no expectation declared) | 47 | 342 | 13.7% | - | - |
| role_mismatch | accuracy-check candidates (included or excluded on full text) where the hh role does not match the text / judged candidates | 0 | 20 | 0.0% | 10%-15% | below expected range |
| role_mismatch_all_checked | all accuracy-check vacancies where the hh role does not match the text / all judged (stratified sample, not representative; no expectation declared) | 4 | 30 | 13.3% | - | - |

## Cleaning log (E.3)

| step | rule | rows_before | rows_after | revealed |
|---|---|---|---|---|
| Duplicates removed (same ID) | cards merged by hh vacancy ID across export files | 771 | 771 | 0 repeated IDs |
| Impossible values handled (cards) | empty title or experience bucket not recognised -> reported, card kept | 771 | 771 | 0 empty titles, 0 unknown buckets |
| Missing values handled (description) | description shorter than 300 characters -> excluded (no_requirements) | 342 | 338 | 4 vacancies without requirements text |
| Impossible values handled (vacancies) | experience on the page differs from the search bucket; publication date after saving date -> reported, vacancy kept | 80 | 80 | 0 experience mismatches, 0 dates in the future |
| Duplicates removed (same company, title and text) | same company and title, word-set overlap (Jaccard) >= 0.8 -> later one excluded | 80 | 68 | 12 duplicates |
| Missing values handled (key skills) | empty 'Key skills' field -> kept, skills are coded from the description text | 68 | 68 | 22 vacancies with an empty field |

## Data dictionary (E.2): final dataset, 68 rows

| field | type | unit | meaning | values_or_range | missing_n | missing_pct |
|---|---|---|---|---|---|---|
| id | nominal | - | hh vacancy ID | 68 distinct values | 0 | 0.0% |
| group | nominal | - | programme the vacancy is assigned to | se (38), cyber (19), bda (11) | 0 | 0.0% |
| assign_basis | nominal | - | assigned by title or by full-text markers | title (58), text (10) | 0 | 0.0% |
| borderline | nominal | - | soft exclusion word overridden by a programme position (empty = not borderline) | поддержк (3), support (1) | 64 | 94.1% |
| bucket | ordinal | experience bucket | hh experience filter of the search | between1And3 (45), noExperience (23) | 0 | 0.0% |
| title | nominal | - | vacancy title | 61 distinct values | 0 | 0.0% |
| company | nominal | - | employer name | 52 distinct values | 0 | 0.0% |
| location | nominal | - | address on the vacancy page | 51 distinct values | 6 | 8.8% |
| city | nominal | - | city on the search card | 33 distinct values | 0 | 0.0% |
| experience | ordinal | experience bucket | experience label on the vacancy page | 1–3 года (45), не требуется (23) | 0 | 0.0% |
| employment | nominal | - | employment type / schedule | Тип занятости
Полная занятость (48), Тип занятости
Полная занятость
Стажировка (16), Тип занятости
Подработка
Стажировка (3), Тип занятости
Проект или разовое задание (1) | 0 | 0.0% |
| salary | nominal | text, KZT or other | salary as displayed (not parsed) | 21 distinct values | 38 | 55.9% |
| published | interval | date | publication date (JSON-LD datePosted) | 2026-09-28 to 2026-10-30 | 0 | 0.0% |
| key_skills | nominal | list of tags | hh 'Key skills' field | 1-19 tags per vacancy, 242 distinct | 22 | 32.4% |
| description | ratio | characters (length) | full vacancy text, contacts masked (private copy only) | 320-6386 characters | 0 | 0.0% |
| url | nominal | - | vacancy URL | 68 distinct values | 0 | 0.0% |
| search_url | nominal | - | search page the card came from | 12 distinct values | 0 | 0.0% |
| saved_at | interval | timestamp, UTC | time the full text was saved | 2026-10-25 to 2026-10-30 | 0 | 0.0% |

## Accuracy check

Judged rows: 30 of 30

| Stage | Agree | Judged | Agreement |
|---|---|---|---|
| excluded_card | 10 | 10 | 100% |
| excluded_full_text | 7 | 10 | 70% |
| included | 9 | 10 | 90% |
| **all** | **26** | **30** | **87%** |

Threshold 70%: passed
