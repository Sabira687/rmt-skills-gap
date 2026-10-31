"""Survey analysis for Assignment 4 (Block A). Run from the repository root:
python3 code/survey_analysis.py
Reads  data/survey/survey_responses_raw.csv (Google Forms export, 37 rows)
Writes data/survey/survey_eligible_recoded.csv, data/survey/tables/*.csv, data/survey/numbers.json, figures/a4/A4_Fig11-13*.png
"""
import json, re, collections, os, warnings
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')
os.makedirs('data/survey/tables', exist_ok=True); os.makedirs('figures/a4', exist_ok=True)
rng = np.random.default_rng(20261030)
SK = {'P':'Programming Fundamentals','D':'Databases/SQL','G':'Git/Version Control','A':'REST APIs','F':'Frameworks','K':'Docker/DevOps'}
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
C5 = ['#b2182b','#ef8a62','#d9d9d9','#67a9cf','#2166ac']
raw = pd.read_csv('data/survey/survey_responses_raw.csv'); raw.columns = [c.strip() for c in raw.columns]
raw.columns = ['ts','consent','q2','q3','q4','q5','q6']+['r_'+s for s in SK]+['t_'+s for s in SK]+['m_'+s for s in SK]+['q10','q11','q12','q13','q14','q15']
R = {'never asked':1,'rarely':2,'sometimes':3,'often':4,'always required':5}
T = {'not taught at all':1,'poorly / basic theory only':2,'moderately well':3,'well taught':4,'extremely well / hands-on practice':5}
N = {'submissions':len(raw), 'first_ts':str(raw.ts.min()), 'last_ts':str(raw.ts.max())}
e = raw[raw.q2!='No'].copy(); N['eligible'] = len(e); N['q2'] = raw.q2.value_counts().to_dict()
for s in SK:
    e['R'+s] = e['r_'+s].str.lower().map(R); e['T'+s] = e['t_'+s].str.lower().map(T); e['G'+s] = e['R'+s]-e['T'+s]
assert e[[x+s for s in SK for x in 'RT']].notna().all().all()
e['Gmean'] = e[['G'+s for s in SK]].mean(axis=1); e['same8'] = e[['T'+s for s in SK]].nunique(axis=1)==1
N['straightline_q8'] = int(e.same8.sum()); N['dup_rows'] = int(e.drop(columns=['ts']).duplicated().sum())
e.drop(columns=['q6','q10','q15']).to_csv('data/survey/survey_eligible_recoded.csv', index=False)
rows = []
for s,nm in SK.items():
    r,t,g = e['R'+s],e['T'+s],e['G'+s]; w = stats.wilcoxon(r,t); bs = [rng.choice(g.values,len(g)).mean() for _ in range(10000)]
    rows.append(dict(skill=nm, q7_median=float(r.median()), q7_often_always=int((r>=4).sum()), q8_median=float(t.median()), q8_well_extremely=int((t>=4).sum()),
        gap_mean=round(float(g.mean()),2), ci_lo=round(float(np.percentile(bs,2.5)),2), ci_hi=round(float(np.percentile(bs,97.5)),2), gap_median=float(g.median()),
        gap_pos=int((g>0).sum()), gap_zero=int((g==0).sum()), gap_neg=int((g<0).sum()), wilcoxon_p=round(float(w.pvalue),3)))
sk = pd.DataFrame(rows); sk.to_csv('data/survey/tables/skill_gap_table.csv', index=False); N['skills'] = rows
d7 = pd.DataFrame({SK[s]: e['R'+s].value_counts().reindex(range(1,6),fill_value=0) for s in SK}).T; d7.columns = ['Never asked','Rarely','Sometimes','Often','Always required']
d8 = pd.DataFrame({SK[s]: e['T'+s].value_counts().reindex(range(1,6),fill_value=0) for s in SK}).T; d8.columns = ['Not taught','Poorly','Moderately','Well','Extremely well']
d7.to_csv('data/survey/tables/q7_distribution.csv'); d8.to_csv('data/survey/tables/q8_distribution.csv'); N['d7'] = d7.to_dict('index'); N['d8'] = d8.to_dict('index')
N['q3'] = {int(k):int(v) for k,v in e.q3.value_counts().sort_index().items()}; N['q3_median'] = float(e.q3.median())
N['q4'] = e.q4.value_counts().to_dict(); N['q5'] = e.q5.value_counts().to_dict()
N['q14'] = {int(k):int(v) for k,v in e.q14.value_counts().sort_index().items()}; N['q14_median'] = float(e.q14.median())
for c in ['q11','q12','q13']: N[c] = e[c].value_counts().to_dict()
N['valid_missing'] = {c:[int(e[c].notna().sum()), int(e[c].isna().sum())] for c in ['q2','q3','q4','q5','q11','q12','q13','q14','q6','q10','q15']+['r_'+s for s in SK]+['t_'+s for s in SK]}
N['valid_missing_q2_all37'] = [int(raw.q2.notna().sum()), int(raw.q2.isna().sum())]
ct = pd.crosstab(e.q2, e.q12); ct.to_csv('data/survey/tables/q2_by_q12.csv'); N['q2_by_q12'] = ct.to_dict('index')
N['q12_working'] = int((e.q12!='Not employed yet').sum()); N['q2_working'] = int(e.q2.str.contains('currently').sum())
N['q2_work_but_q12_not'] = int((e.q2.str.contains('currently') & (e.q12=='Not employed yet')).sum()); N['q2_nothired_but_q12_work'] = int((e.q2.str.contains('interviewed') & (e.q12!='Not employed yet')).sum())
N['q7_same_label_all_rows'] = int((e[['R'+s for s in SK]].nunique(axis=1)==1).sum())
N['q8_extremely_two_skills'] = {SK[s]:int((e['T'+s]==5).sum()) for s in 'PD'}
N['q9_resp_multi'] = int(e[['m_'+s for s in SK]].apply(lambda r: any(';' in str(x) for x in r), axis=1).sum())
# merged year groups (cells under three respondents merged, as declared in A3)
e['yr'] = e.q11.map({'1':'Years 1-2','2':'Years 1-2','3':'Year 3','4':'Year 4 + graduates','Graduate':'Year 4 + graduates'})
N['yr_groups'] = {g:dict(n=len(s), gap_mean=round(float(s.Gmean.mean()),2), gap_median=round(float(s.Gmean.median()),2), q3_median=float(s.q3.median())) for g,s in e.groupby('yr')}
N['yr_kruskal_p'] = round(float(stats.kruskal(*[s.Gmean for _,s in e.groupby('yr')]).pvalue),3)
a = e[e.yr=='Year 3'].Gmean; b = e[e.yr=='Year 4 + graduates'].Gmean; N['yr3_vs_grad_p'] = round(float(stats.mannwhitneyu(a,b).pvalue),3)
fe = e[e.q13=='Frontend']; ot = e[e.q13!='Frontend']
N['spec'] = {g:dict(n=len(s), q3_median=float(s.q3.median()), q3_45=int((s.q3>=4).sum()), gap_mean=round(float(s.Gmean.mean()),2)) for g,s in e.groupby('q13')}
N['front_vs_rest'] = dict(front_n=len(fe), rest_n=len(ot), front_median=float(fe.q3.median()), rest_median=float(ot.q3.median()), front_45=int((fe.q3>=4).sum()), rest_45=int((ot.q3>=4).sum()), p=float(stats.mannwhitneyu(fe.q3,ot.q3).pvalue))
w_ = e[e.q2.str.contains('currently')]; nh = e[e.q2.str.contains('interviewed')]
N['status'] = dict(work_n=len(w_), nh_n=len(nh), work_q3_median=float(w_.q3.median()), nh_q3_median=float(nh.q3.median()), p=float(stats.mannwhitneyu(w_.q3,nh.q3).pvalue), work_gap=round(float(w_.Gmean.mean()),2), nh_gap=round(float(nh.Gmean.mean()),2))
ee = e[~e.same8]; N['sens'] = dict(n=len(ee), items=[dict(skill=SK[s], gap=round(float(ee['G'+s].mean()),2), p=round(float(stats.wilcoxon(ee['R'+s],ee['T'+s]).pvalue),3)) for s in SK])
N['overall_gap'] = round(float(e.Gmean.mean()),2)
def code(t):
    t = str(t).lower(); o = []
    if re.search(r'practic|real project|real-world|hands-on|real compan|internship|work experience', t): o.append('practice / real projects')
    if re.search(r'\bgit|docker|framework|\bapi|database|tools|technolog|backend|testing|version control', t): o.append('named technology / tool')
    if re.search(r'team|communicat|collaborat|problem-solving|problem solving|solve', t): o.append('teamwork / communication / problem solving')
    return o
oc = []; ans = []
for col,nm in [('q6','Q6'),('q10','Q10'),('q15','Q15')]:
    sub = e[col].dropna(); cnt = collections.Counter()
    for t in sub:
        cs = code(t); ans.append(dict(item=nm, answer=t, themes='; '.join(cs)))
        for c in cs: cnt[c]+=1
    for c in ['practice / real projects','named technology / tool','teamwork / communication / problem solving']: oc.append(dict(item=nm, n_answers=len(sub), theme=c, n=cnt[c]))
pd.DataFrame(oc).to_csv('data/survey/tables/open_coding_summary.csv', index=False); pd.DataFrame(ans).to_csv('data/survey/tables/open_coding_answers.csv', index=False); N['open'] = oc
json.dump(N, open('data/survey/numbers.json','w'), ensure_ascii=False, indent=1, default=str)
def save(fig,name): fig.tight_layout(); fig.savefig('figures/a4/'+name, dpi=200); plt.close(fig)
# Fig 11: Q3, Q4, Q5
fig, axs = plt.subplots(1,3, figsize=(10,3.1))
c3 = [N['q3'].get(i,0) for i in range(1,6)]; axs[0].bar(range(1,6), c3, color='#2166ac'); axs[0].set_xlabel('Q3 difficulty (1 easy - 5 hard)', fontsize=8); axs[0].set_ylabel('Respondents (n = 32)')
for i,v in enumerate(c3): axs[0].text(i+1, v+.2, str(v), ha='center')
for ax,col,tt in [(axs[1],'q4','Q4 search duration'),(axs[2],'q5','Q5 main obstacle')]:
    vc = e[col].value_counts(); ax.barh([x[:28] for x in vc.index[::-1]], vc.values[::-1], color='#67a9cf'); ax.set_title(tt, fontsize=9); ax.tick_params(axis='y', labelsize=7)
    for i,v in enumerate(vc.values[::-1]): ax.text(v+.2, i, str(v), va='center', fontsize=8)
save(fig,'A4_Fig11_survey_difficulty_duration_obstacle.png')
# Fig 12: Q7 and Q8 full distributions
def stacked(ax, dist, title):
    pct = dist.div(dist.sum(axis=1),axis=0)*100; order = list(dist.index)[::-1]; base = np.zeros(len(order))
    for c,col in zip(dist.columns,C5):
        w = pct[c].reindex(order).values; ax.barh(order, w, left=base, color=col, label=c)
        for i_,(x0,wi,cnt) in enumerate(zip(base,w,dist[c].reindex(order).values)):
            if cnt>0: ax.text(x0+wi/2, i_, str(int(cnt)), ha='center', va='center', color='white' if col in (C5[0],C5[4]) else 'black', fontsize=8)
        base += w
    ax.set_xlim(0,100); ax.set_title(title, fontsize=9); ax.legend(ncol=5, fontsize=7, loc='upper center', bbox_to_anchor=(.5,-.12), frameon=False)
fig, axs = plt.subplots(2,1, figsize=(7.2,7)); stacked(axs[0], d7, 'Q7: how often each skill was required (n = 32, counts in bars)'); stacked(axs[1], d8, 'Q8: how well each skill was taught at AITU (n = 32, counts in bars)'); axs[1].set_xlabel('% of respondents'); fig.subplots_adjust(hspace=.5); fig.savefig('figures/a4/A4_Fig12_survey_requirement_teaching.png', dpi=200, bbox_inches='tight'); plt.close(fig)
# Fig 13: subgroup comparison
fig, axs = plt.subplots(1,2, figsize=(8,3.2)); order = ['Frontend','Backend','Fullstack','Data / ML','DevOps / Cloud']; lab = ['Frontend','Backend','Fullstack','Data/ML','DevOps/\nCloud']
sh = [100*N['spec'][g]['q3_45']/N['spec'][g]['n'] for g in order]; axs[0].bar(range(5), sh, color='#67a9cf'); axs[0].set_xticks(range(5)); axs[0].set_xticklabels([f"{l}\n(n={N['spec'][g]['n']})" for l,g in zip(lab,order)], fontsize=7); axs[0].set_ylabel('% rating search difficulty 4-5'); axs[0].set_ylim(0,100)
for i,g in enumerate(order): axs[0].text(i, sh[i]+2, f"{N['spec'][g]['q3_45']}/{N['spec'][g]['n']}", ha='center', fontsize=8)
yo = ['Years 1-2','Year 3','Year 4 + graduates']; ym = [N['yr_groups'][g]['gap_mean'] for g in yo]
axs[1].bar(range(3), ym, color=['#ef8a62' if v<0 else '#2166ac' for v in ym]); axs[1].axhline(0,color='k',lw=.8); axs[1].set_ylim(-.7,.5); axs[1].set_xticks(range(3)); axs[1].set_xticklabels([f"{g}\n(n={N['yr_groups'][g]['n']})" for g in yo], fontsize=7); axs[1].set_ylabel('Mean gap over six skills (scale points)')
for i,v in enumerate(ym): axs[1].text(i, v+(.03 if v>=0 else -.05), f'{v:+.2f}'.replace('-','\u2212'), ha='center', va='bottom' if v>=0 else 'top', fontsize=8)
save(fig,'A4_Fig13_survey_subgroups.png')
# Appendix B figures
fig, ax = plt.subplots(figsize=(6.2,2.6)); lab2 = ['Invited','Submitted','Eligible (analysed)','Excluded (Q2 = No)']; val = [78,37,32,5]
b = ax.barh(lab2[::-1], val[::-1], color=['#b2182b','#2166ac','#67a9cf','#bdbdbd'])
for r_,v in zip(b,val[::-1]): ax.text(v+1, r_.get_y()+r_.get_height()/2, str(v), va='center')
ax.set_xlabel('Number of people'); save(fig,'A4_FigB1_survey_response_funnel.png')
fig, ax = plt.subplots(figsize=(6.4,3)); o = sk.sort_values('gap_mean'); y = np.arange(len(o))
ax.errorbar(o.gap_mean, y, xerr=[o.gap_mean-o.ci_lo, o.ci_hi-o.gap_mean], fmt='o', color='#2166ac', capsize=3); ax.axvline(0,color='k',lw=.8); ax.axvline(.3,color='#b2182b',ls='--',lw=.8); ax.axvline(-.3,color='#b2182b',ls='--',lw=.8)
ax.set_yticks(y); ax.set_yticklabels(o.skill); ax.set_xlabel('Mean paired gap (Q7 - Q8), scale points; 95% bootstrap CI', fontsize=8); save(fig,'A4_FigB2_survey_gap_per_skill.png')
print(json.dumps({k:N[k] for k in ['submissions','first_ts','last_ts','eligible','q4','q5','q11','q12','q13','q14','q14_median','q2_by_q12','q12_working','q2_working','q2_work_but_q12_not','q2_nothired_but_q12_work','q7_same_label_all_rows','q8_extremely_two_skills','straightline_q8','dup_rows','yr_groups','yr_kruskal_p','yr3_vs_grad_p','spec','front_vs_rest','status','sens','overall_gap','open','valid_missing_q2_all37']}, ensure_ascii=False, indent=0, default=str))
print(sk.to_string())
