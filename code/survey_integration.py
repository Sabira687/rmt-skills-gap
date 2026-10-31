"""Rank comparison for the integration paragraph (Assignment 4, Table 11).
Run from the repository root after code/survey_analysis.py and code/analyze.py:
python3 code/survey_integration.py
Reads data/processed/analysis_s1-s2/survey_skill_mapping.csv (D_pooled per survey skill) and data/survey/tables/skill_gap_table.csv.
Writes data/survey/tables/integration_ranks.csv"""
import pandas as pd
from scipy import stats
m = pd.read_csv('data/processed/analysis_s1-s2/survey_skill_mapping.csv'); s = pd.read_csv('data/survey/tables/skill_gap_table.csv')
t = m[['survey_skill','D_pooled']].merge(s[['skill','q7_often_always','q8_well_extremely','gap_mean']], left_on='survey_skill', right_on='skill')
t['survey_share_often_always'] = (t.q7_often_always/32).round(3)
t['rank_vacancies'] = t.D_pooled.rank(ascending=False); t['rank_survey'] = t.q7_often_always.rank(ascending=False)
r = stats.spearmanr(t.D_pooled, t.q7_often_always)
t.drop(columns='skill').to_csv('data/survey/tables/integration_ranks.csv', index=False)
print(t.drop(columns='skill').to_string()); print('Spearman rho =', round(float(r.statistic),2), 'p =', round(float(r.pvalue),3), 'n = 6')
