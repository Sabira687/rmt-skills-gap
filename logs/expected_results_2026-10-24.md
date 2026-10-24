
# T9. Expected Results

| No. | Expected result                                                                                                                                                                                   | Connected objective | What would falsify it                                                                                                                  | Confidence and why                                                                                                                                                                                                                                                                                          |
|---|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---|----------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ER1 | After data collection and filtering, the largest number of vacancies in the sample will be in Software Engineering                                                                                | O1 | The number of SE vacancies will be less than or equal to the number of vacancies in at least one of the other two educational programs | High: SE encompasses the full spectrum of development and testing roles, which constitutes the largest segment of IT vacancies                                                                                                                                                                              |
| ER2 | The share of unmet demand U in the strict scenario will not exceed 50% for any of the three educational programs                                                                                  | O3 | For at least one educational program, U will be higher than 50% in the strict scenario                                                 | Medium: The mandatory portion of the programs includes core categories (programming languages, databases, networks) that are in demand for most vacancies, so the program likely covers most of the demand. However, the brevity of the program descriptions may underestimate the measured coverage        |
| ER3 | The lower bound of the 95% bootstrap interval for U in the strict scenario will be above 30% for all three educational programs                                                                   | O3 | For at least one educational program, the lower bound of the interval will be 30% or lower                                             | Low: Austria (2025) shows that the gap is most pronounced for entry-level positions, while Ashimkhanova et al. (2025) find that young people in Kazakhstan consider IT programs to be outdated, but the Cybersecurity and Big Data Analysis groups are likely to be small, and their intervals will be wide |
| ER4 | In the strict scenario, U will differ by more than 10 percentage points for at least one pair of educational programs                                                                             | O3 | In the strict scenario, the difference in U between each pair of educational programs will not exceed 10 percentage points             | Medium: Programs differ in terms of specialization and course composition, so their alignment with their respective market segments varies |
| ER5 | For each of the three educational programs, U in the strict scenario will be at least 10 percentage points higher than in the soft scenario                                                       | O3 | For at least one educational program, the difference between the strict and soft scenarios will be less than 10 percentage points.     | Medium: Electives define specializations within the program and introduce categories not covered in the required curriculum, but some electives provide more in-depth coverage of categories already covered |
| ER6 | At least two of the three categories with the largest gaps in the strict scenario for the SE educational program will be from the list of rapidly changing categories | O4 | For the SE educational program, fewer than two categories from the list will be among the top 3 by gap | Low: Curricula are updated more slowly than market instruments, but a high rate of change does not in itself guarantee high demand. |

---

## Six Scenarios

**Bad 1.** After the selection process, no educational program reaches the threshold of 30 openings. It is not possible to compare the programs or test the H1 hypothesis, so the study is limited to a description and an overview of the selection process, and data collection is extended.

**Bad 2.** An accuracy check shows that the automatic selection and allocation by program match the manual decision in less than 70% of cases. The results cannot be considered reliable until the rules are revised and the main analysis is postponed, and the selection rules are being revised using a pilot sample.

**Medium 1.** There are enough vacancies for software engineers, but the numbers for cybersecurity and big data analysis remain below 30. H1 is fully tested only for SE; small groups are described without statistical conclusions, and comparisons of programs are made with reservations.

**Medium 2.** There is sufficient data in all groups, but the bootstrap U-intervals cross the 30% threshold for at least two treatment groups. H1 is neither confirmed nor refuted for these groups, therefore, the result is described as borderline, with an indication of the sample size needed for a definitive answer.

**Good 1.** All three groups have at least 30 vacancies, and the gap rankings are stable in the bootstrap. The study provides a complete answer to the research question.

**Good 2.** There is sufficient data across all groups, and H1 is rejected for all three programs (the lower bound of the U-interval is below 30%). The program documentation covers most of the employers’ stated requirements, and the notion of a significant gap is not supported.

---

# T10. Methodological Expectations (Data Analytics)

### Expected Patterns Across Groups and Categories

Programming languages, databases and SQL, and version control will be in demand across all three job categories. Incident monitoring and response, penetration testing, digital forensics, and information security standards will be found almost exclusively in Cybersecurity job postings. Big data processing, machine learning, and BI will be featured in Big Data Analysis job openings. On average, SE job openings will require more skill categories per position than job openings in the other two groups. The ranking of skill gaps will be stable in the top three positions and less stable further down the list.

### Expected Data Quality Issues

| Issue                                                                | Expected Proportion                     | Why It Matters |
|----------------------------------------------------------------------|-----------------------------------------|---|
| Job postings from the “1-3 years” category that are not entry-level  | 70-85% of the listings in this category | Determines how many job postings will actually be included in the sample |
| The role listed on hh does not match the job description             | 10-15% of candidates                    | Affects the assignment of job postings to education programs |
| Duplicates                                                           | 5-10% of included job postings          | If not removed, they inflate the demand for certain categories |
| Empty “Key Skills” field on hh                                       | 25-35% of job postings                  | Skills are extracted only from the job description text, and some may be omitted |
| Job postings closed between card extraction and full-text collection | less than 5% of candidates              | Data loss between selection stages |
| Job postings without requirement text                                | less than 5% of candidates              | Such job postings cannot be coded |

Each issue will be counted and recorded in the cleaning log.

### What the data cannot reveal

- graduates’ actual knowledge and skills
- the depth and quality of instruction in various subjects
- the actual minimum hiring requirements, as opposed to those stated in job postings
- demand in the job market outside of hh.kz

---

**Expectations recorded: October 24, 2026**

