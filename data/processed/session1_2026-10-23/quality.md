# Data quality report

Generated: 2026-10-30 16:55 · rules: `v1-frozen-2026-10-25`

Inputs: data/raw/vacancies/session1_2026-10-23/hh_cards_2026-10-25-09-39.json, _private/session1_2026-10-23/hh_full_2026-10-25-11-14.json, _private/session1_2026-10-23/hh_full_2026-10-25-11-00.json

## T10 data-quality shares

| measure | definition | count | base | observed | expected | verdict |
|---|---|---|---|---|---|---|
| not_entry_level_1_3 | 1-3 year candidates excluded on full text as not entry level (experience_unclear, experience_too_high) / 1-3 year candidates whose full text reached the experience check | 177 | 238 | 74.4% | 70%-85% | within expected range |
| no_requirements | collected candidates with a description under 300 characters / collected candidates | 4 | 287 | 1.4% | 0%-5% | within expected range |
| closed_before_full_text | collected candidates archived or skipped / collected candidates | 4 | 287 | 1.4% | 0%-5% | within expected range |
| duplicates | duplicates removed / included before deduplication | 9 | 68 | 13.2% | 5%-10% | above expected range |
| empty_key_skills | final vacancies with an empty 'Key skills' field / final vacancies | 18 | 59 | 30.5% | 25%-35% | within expected range |
| unassigned_proxy | collected candidates whose programme could not be assigned / collected candidates (proxy for role mismatch, no expectation declared) | 37 | 287 | 12.9% | - | - |
| role_mismatch | accuracy-check candidates (included or excluded on full text) where the hh role does not match the text / judged candidates | 0 | 20 | 0.0% | 10%-15% | below expected range |
| role_mismatch_all_checked | all accuracy-check vacancies where the hh role does not match the text / all judged (stratified sample, not representative; no expectation declared) | 4 | 30 | 13.3% | - | - |

## Cleaning log (E.3)

| step | rule | rows_before | rows_after | revealed |
|---|---|---|---|---|
| Duplicates removed (same ID) | cards merged by hh vacancy ID across export files | 654 | 654 | 0 repeated IDs |
| Impossible values handled (cards) | empty title or experience bucket not recognised -> reported, card kept | 654 | 654 | 0 empty titles, 0 unknown buckets |
| Missing values handled (description) | description shorter than 300 characters -> excluded (no_requirements) | 287 | 283 | 4 vacancies without requirements text |
| Impossible values handled (vacancies) | experience on the page differs from the search bucket; publication date after saving date -> reported, vacancy kept | 68 | 68 | 0 experience mismatches, 0 dates in the future |
| Duplicates removed (same company, title and text) | same company and title, word-set overlap (Jaccard) >= 0.8 -> later one excluded | 68 | 59 | 9 duplicates |
| Missing values handled (key skills) | empty 'Key skills' field -> kept, skills are coded from the description text | 59 | 59 | 18 vacancies with an empty field |

## Data dictionary (E.2): final dataset, 59 rows

| field | type | unit | meaning | values_or_range | missing_n | missing_pct |
|---|---|---|---|---|---|---|
| id | nominal | - | hh vacancy ID | 59 distinct values | 0 | 0.0% |
| group | nominal | - | programme the vacancy is assigned to | se (33), cyber (16), bda (10) | 0 | 0.0% |
| assign_basis | nominal | - | assigned by title or by full-text markers | title (50), text (9) | 0 | 0.0% |
| borderline | nominal | - | soft exclusion word overridden by a programme position (empty = not borderline) | поддержк (2), support (1) | 56 | 94.9% |
| bucket | ordinal | experience bucket | hh experience filter of the search | between1And3 (38), noExperience (21) | 0 | 0.0% |
| title | nominal | - | vacancy title | 52 distinct values | 0 | 0.0% |
| company | nominal | - | employer name | 46 distinct values | 0 | 0.0% |
| location | nominal | - | address on the vacancy page | 44 distinct values | 6 | 10.2% |
| city | nominal | - | city on the search card | 29 distinct values | 0 | 0.0% |
| experience | ordinal | experience bucket | experience label on the vacancy page | 1–3 года (38), не требуется (21) | 0 | 0.0% |
| employment | nominal | - | employment type / schedule | Тип занятости
Полная занятость (41), Тип занятости
Полная занятость
Стажировка (14), Тип занятости
Подработка
Стажировка (3), Тип занятости
Проект или разовое задание (1) | 0 | 0.0% |
| salary | nominal | text, KZT or other | salary as displayed (not parsed) | 20 distinct values | 33 | 55.9% |
| published | interval | date | publication date (JSON-LD datePosted) | 2026-09-28 to 2026-10-25 | 0 | 0.0% |
| key_skills | nominal | list of tags | hh 'Key skills' field | 1-31 tags per vacancy, 236 distinct | 18 | 30.5% |
| description | ratio | characters (length) | full vacancy text, contacts masked (private copy only) | 320-6386 characters | 0 | 0.0% |
| url | nominal | - | vacancy URL | 59 distinct values | 0 | 0.0% |
| search_url | nominal | - | search page the card came from | https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&experience=noExperience&ored_clusters=true&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&items_on_page=100&search_session_id=f7133d74-d28c-4875-8dbd-e16260577857&hhtmFromLabel=search_order_button&hhtmFrom=vacancy_search_list (21), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSourceLabel=vacancy_search_list&page=2&search_session_id=ae55fb38-3389-4cb7-8630-d5b4f58f8e7e (10), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSourceLabel=vacancy_search_list&page=1&search_session_id=ae55fb38-3389-4cb7-8630-d5b4f58f8e7e (10), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&hhtmFromLabel=drawer_filter&hhtmFrom=vacancy_search_list&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSource=vacancy_search_list&hhtmSourceLabel=vacancy_search_list (7), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSourceLabel=vacancy_search_list&page=5&search_session_id=ae55fb38-3389-4cb7-8630-d5b4f58f8e7e (5), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSourceLabel=vacancy_search_list&page=3&search_session_id=ae55fb38-3389-4cb7-8630-d5b4f58f8e7e (4), https://astana.hh.kz/search/vacancy?area=40&enable_snippets=true&ored_clusters=true&items_on_page=100&experience=between1And3&professional_role=156&professional_role=160&professional_role=10&professional_role=25&professional_role=165&professional_role=73&professional_role=96&professional_role=104&professional_role=157&professional_role=107&professional_role=112&professional_role=113&professional_role=114&professional_role=116&professional_role=121&professional_role=124&professional_role=125&professional_role=164&search_field=name&search_field=company_name&search_field=description&hhtmSourceLabel=vacancy_search_list&page=4&search_session_id=ae55fb38-3389-4cb7-8630-d5b4f58f8e7e (2) | 0 | 0.0% |
| saved_at | interval | timestamp, UTC | time the full text was saved | 2026-10-25 to 2026-10-25 | 0 | 0.0% |

## Accuracy check

Judged rows: 30 of 30

| Stage | Agree | Judged | Agreement |
|---|---|---|---|
| excluded_card | 10 | 10 | 100% |
| excluded_full_text | 7 | 10 | 70% |
| included | 9 | 10 | 90% |
| **all** | **26** | **30** | **87%** |

Threshold 70%: passed
