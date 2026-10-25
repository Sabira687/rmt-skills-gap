"""
Screening and assignment rules for hh.kz vacancies (RMT study).

This file is the screening protocol. Workflow:
  1. The rules are tuned on the first collection session (pilot).
  2. RULES_VERSION is then set to "v1-frozen-YYYY-MM-DD" and the file is not edited again.
  3. Any change after freezing creates a new version and an entry in CHANGELOG with the reason.

All patterns are regular expressions, matched against lower-case text in which
the letter "ё" is replaced by "е". Patterns contain Russian and Kazakh words because
hh.kz vacancies are published mostly in Russian; they are data patterns, not comments.

Source of the positions: the "List of a specialist's positions" section of each programme document
(Cybersecurity p.9, Big Data Analysis p.5, Software Engineering p.6; see
data/processed/programmes/graduate_positions.csv). The "Atlas of new professions" section of the documents
is not used as a source of positions.
"""

RULES_VERSION = "v1-frozen-2026-10-25"

CHANGELOG = [
    # ("2026-10-23", "v1-draft", "first version"),
    ("2026-10-25", "v1-draft",
     "Latin look-alike letters inside Cyrillic words are mapped to Cyrillic before matching "
     "(7 cards titled 'Cистемный администратор' with a Latin 'C' were missed as no_role_match)"),
    ("2026-10-25", "v1-draft",
     "'тестовик' (colloquial 'tester') added to SE positions; 'системотехник' (systems technician) "
     "added to generic titles, so its group is decided by the full text"),
    ("2026-10-25", "v1-draft",
     "support / helpdesk / DevOps / SRE moved to EXCLUDE_TITLE_SOFT: they no longer exclude a title "
     "that also names a programme position explicitly (POSITION_OVERRIDE), e.g. 'Support Backend Developer', "
     "'DevOps / SysAdmin'. Such vacancies are flagged in the 'borderline' column"),
    ("2026-10-25", "v1-draft",
     "entry-level check of the '1-3 years' bucket removed from the card stage and left to the full-text stage "
     "(experience_unclear): the card snippet is cut at about 150 characters, so a statement such as "
     "'experience from 1 year' is often not visible on the card. Removed reason: not_entry_level_card"),
    ("2026-10-25", "v1-draft",
     "positions from the programme documents checked against the rules (data/processed/programmes/"
     "graduate_positions.csv): 'больших данных' (big data analyst / engineer, BDA p.5) and 'security tester of "
     "networks and systems' (Cyber p.9) were not assigned to their programme; patterns added to BDA and Cyber"),
    ("2026-10-25", "v1-draft",
     "documentation only, no pattern changed: positions are taken from the 'List of a specialist's positions' "
     "only, not from the 'Atlas of new professions'; managers and architects listed for SE are excluded as "
     "not entry level"),
    ("2026-10-25", "v1-draft",
     "after the first full-text run (session 1): (1) duplicates are compared by word-set overlap (Jaccard >= 0.80) "
     "instead of order-sensitive similarity of the first 1500 characters (>= 0.90): the same Andersen traineeships "
     "re-posted for Almaty and Astana with re-ordered paragraphs scored 0.78-0.86 and were not caught; "
     "(2) 'quality assurance' added to SE (2 'Quality Assurance Trainee Program' vacancies were unassigned); "
     "(3) testing titles go to SE before BDA topic words (TESTING_TITLE): 'Software QA Engineer/Intern (AI-Powered)' "
     "was assigned to BDA because of 'AI'; (4) 'game dev' added to SE"),
    ("2026-10-25", "v1-frozen-2026-10-25",
     "rules frozen after the accuracy check of session 1 (logs/accuracy_check_session1.csv): agreement with the "
     "manual decision 25 of 29 (86%), threshold 70%. No pattern changed at freezing. Sessions 2 and 3 are "
     "screened with this version; any later change gets a new version and an entry here"),
]

# ---------------------------------------------------------------------------
# 1. Title exclusions (checked FIRST)
# ---------------------------------------------------------------------------

# Roles that do not appear in any programme's list of graduate positions:
# 1C, technical writer, product/scrum roles, sales,
# operators/call centre, designers, marketing/SMM/SEO/content, HR/recruiting,
# business/system analysts, teachers/mentors, low-voltage/CCTV installers, cashiers.
# Managers: the SE list names "manager of IT systems and projects", but it is a management role
# that is not entry level, so managers are excluded on the same ground as seniority (see EXCLUDE_SENIOR,
# which also covers "architect of IT systems and projects" and the BDA "head of ..." positions).
# DevOps appears only in the SE "Atlas of new professions", which is not a source of positions.
EXCLUDE_TITLE = [
    r"\b1\s?[сc]\b", r"1с[- ]", r"технич\w* писател", r"technical writer",
    r"менеджер", r"manager", r"product owner", r"scrum", r"проджект",
    r"продаж", r"\bsales\b",
    r"оператор", r"колл-?центр", r"call[- ]?(center|центр)",
    r"дизайнер", r"designer", r"ui/ux", r"ux/ui",
    r"маркетолог", r"маркетинг", r"marketing", r"\bsmm\b", r"\bseo\b", r"контент", r"content",
    r"рекрутер", r"recruit", r"\bhr\b",
    r"бизнес-?аналит", r"business analyst", r"системн\w* аналит", r"system analyst",
    r"преподават", r"учител", r"teacher", r"tutor", r"ментор", r"mentor", r"куратор",
    r"слаботоч", r"видеонаблюд", r"монтаж", r"электрик", r"кассир",
]

# Support/helpdesk and DevOps/SRE describe the work context rather than a different occupation.
# They exclude a title only when it does not also name a programme position from POSITION_OVERRIDE:
# "Technical support specialist" is excluded, "Support Backend Developer" and "DevOps / SysAdmin" are not.
EXCLUDE_TITLE_SOFT = [
    r"поддержк", r"support", r"help ?desk", r"хелпдеск", r"devops", r"\bsre\b",
]

# Explicit graduate positions (job nouns, not topics such as "AI" or "mobile")
POSITION_OVERRIDE = [
    r"разработчик", r"developer", r"программист", r"programmer",
    r"data (engineer|scientist|analyst)", r"инженер\w* данн", r"аналитик\w* данн",
    r"\bqa\b", r"тестировщик", r"тестовик", r"tester",
    r"системн\w* администратор", r"сисадмин", r"sysadmin", r"system administrator",
    r"сетев\w* (инженер|администратор)", r"network (engineer|administrator)",
    r"специалист\w* (по )?(информационн\w* |кибер)безопасн", r"security (engineer|analyst|specialist)",
]

# Seniority above entry level - always excluded
# (senior, lead, head, director, architect, "leading/senior/chief" in Russian)
EXCLUDE_SENIOR = [
    r"senior", r"сеньор", r"\blead\b", r"тимлид", r"team ?lead", r"\bhead\b",
    r"руководител", r"директор", r"director", r"архитектор", r"architect",
    r"\bведущ(ий|его|ая|ей)\b", r"\bстарш(ий|его|ая|ей)\b", r"\bглавн(ый|ого|ая|ой)\b",
]

# Middle level - excluded UNLESS the title also contains a junior marker
MIDDLE = [r"middle", r"мидл"]

# ---------------------------------------------------------------------------
# 2. Graduate positions from the programme documents (matched in the title).
#    Dictionary order = assignment priority.
# ---------------------------------------------------------------------------

ROLE_TITLE = {
    # Cybersecurity: SOC, information protection, forensics, security testing,
    # security engineering, audit, DB / network / infrastructure administration
    "cyber": [
        r"информационн\w* безопасн", r"кибербезопасн", r"cyber ?security", r"\bsecurity\b",
        r"secops", r"\bsoc\b", r"pentest", r"пентест", r"penetration", r"forensic", r"криминалист",
        r"\bиб\b", r"защит\w* информац", r"\bsiem\b", r"\bdlp\b",
        r"тестировщик\w* безопасн", r"безопасност\w* (компьютерн\w* )?(сет|систем|сервис|приложен|инфраструктур)",
        r"системн\w* администратор", r"сисадмин", r"system administrator", r"sysadmin",
        r"сетев\w* (инженер|администратор)", r"network (engineer|administrator)",
        r"администратор (баз|бд|сет|инфраструкт)", r"\bdba\b", r"database administrator",
        r"инфраструктур",
    ],
    # Big Data Analysis: data analyst, data scientist, big data analyst / engineer, ML / AI, BI
    # (ML / AI / NLP / computer vision titles are data-science roles, covered by "Data Scientist")
    "bda": [
        r"\bdata\b", r"big ?data", r"больш\w* данн", r"аналитик\w* данн", r"инженер\w* данн",
        r"дата[- ]?(сайентист|аналитик|инженер)", r"machine learning", r"машинн\w* обучен",
        r"\bml\b", r"\bai\b", r"\bии\b", r"искусственн\w* интеллект", r"\bnlp\b",
        r"computer vision", r"компьютерн\w* зрени", r"deep learning",
        r"\bbi\b", r"power ?bi", r"tableau", r"analytics",
    ],
    # Software Engineering: software engineer / developer, backend, frontend, mobile, tester
    "se": [
        r"разработчик", r"developer", r"программист", r"programmer", r"software",
        r"frontend", r"front-end", r"фронтенд", r"backend", r"back-end", r"бэкенд", r"бекенд",
        r"full ?-?stack", r"фулстек", r"mobile", r"мобильн", r"\bios\b", r"android", r"flutter",
        r"react", r"\bjava\b", r"python", r"golang", r"\.net", r"c#", r"\bphp\b", r"node",
        r"\bqa\b", r"quality assurance", r"тестировщик", r"тестовик", r"тестирован", r"tester", r"test engineer",
        r"sdet", r"\bweb\b", r"\bвеб\b", r"game ?dev", r"геймдев",
    ],
}
ROLE_PRIORITY = ["cyber", "bda", "se"]

# Testing roles go to SE before the BDA topic words are checked:
# "Software QA Engineer (AI-Powered)" is a tester, not a data-science role.
# Cybersecurity is still checked first ("security tester" stays in Cybersecurity).
TESTING_TITLE = [
    r"\bqa\b", r"quality assurance", r"тестировщик", r"тестовик", r"tester", r"test engineer", r"sdet",
]

# Generic titles (intern, IT specialist, engineer, analyst, junior):
# the role is unclear from the title and is decided from the full text in step 4
GENERIC_TITLE = [
    r"стаж[её]р", r"стажировк", r"intern", r"trainee", r"\bit\b", r"айти",
    r"инженер", r"engineer", r"специалист", r"аналитик", r"analyst", r"младш", r"junior",
    r"системотехник",
]

# ---------------------------------------------------------------------------
# 3. Entry level
# ---------------------------------------------------------------------------

# Junior / intern / trainee / beginner / graduate / student / "no experience"
JUNIOR_MARKERS = [
    r"junior", r"джун", r"стаж[её]р", r"стажировк", r"intern", r"trainee", r"младш",
    r"начинающ", r"выпускник", r"graduate", r"студент", r"entry[- ]level", r"без опыта",
]

# For the "1-3 years" bucket: signs that up to one year of experience is enough
# ("no experience", "experience not required", "from 6 months", "from 1 year", "up to 1 year")
EXPERIENCE_OK_TEXT = [
    r"без опыта", r"опыт\w* (работы )?не (обязател|требует|нужен)",
    r"(от|не менее) (6|шести) месяц",
    r"(от|не менее) (1|одного)(-го)? года", r"опыт\w* (работы )?от года",
    r"\b1\+? ?(year|год)", r"до (1|одного) года",
]

# A requirement of 2+ years of experience - exclusion for any bucket
# ("from / at least / minimum / more than 2-5 years", "2+ years", "N years of experience")
EXPERIENCE_TOO_HIGH = [
    r"(от|не менее|минимум|более)\s*(2|3|4|5|двух|тр[её]х|четыр\w*|пят\w*)[\s-]*(х\s*)?(лет|года)",
    r"(at least|minimum|min\.?)\s*(2|3|4|5|two|three)\+?\s*years?",
    r"\b[2-9]\+\s*(years?|лет|года)",
    r"\b[2-9]\s*years? of (commercial |professional |relevant )?experience",
]

# ---------------------------------------------------------------------------
# 4. Assignment by full text (only for generic titles)
# ---------------------------------------------------------------------------

TEXT_MARKERS = {
    # information security, SIEM, SOC, pentest, vulnerabilities, incidents, firewalls, network equipment
    "cyber": [
        r"информационн\w* безопасн", r"\bsiem\b", r"\bsoc\b", r"pentest", r"пентест", r"уязвим",
        r"vulnerab", r"инцидент", r"firewall", r"межсетев", r"kali", r"wireshark",
        r"active directory", r"сетев\w* оборудован", r"cisco", r"mikrotik",
    ],
    # machine learning, data science, data analysis, BI, ETL, big data tools
    "bda": [
        r"машинн\w* обучен", r"machine learning", r"data science", r"pandas", r"numpy",
        r"scikit", r"pytorch", r"tensorflow", r"power ?bi", r"tableau", r"анализ\w* данн",
        r"\betl\b", r"spark", r"hadoop", r"airflow",
    ],
    # software / web / application development, APIs, frameworks, software testing, Git, OOP
    "se": [
        r"разработк\w* (по|программ|приложен|веб|web|backend|frontend|сайт)", r"\bapi\b", r"\brest\b",
        r"frontend", r"backend", r"фронтенд", r"бэкенд", r"react", r"\bvue\b", r"angular",
        r"spring", r"django", r"fastapi", r"laravel", r"\.net", r"тестирован\w* (по|программ|приложен)",
        r"\bgit\b", r"\bооп\b", r"\boop\b",
    ],
}
TEXT_MIN_HITS = 2  # minimum number of matches; the winning group must be unique

# ---------------------------------------------------------------------------
# 5. Other settings
# ---------------------------------------------------------------------------

MIN_DESCRIPTION_CHARS = 300  # shorter descriptions are treated as having no requirements text
DEDUP_SIMILARITY = 0.80      # word-set overlap (Jaccard) threshold for duplicates (same company and title)
SMALL_GROUP_N = 30           # minimum group size for full analysis
