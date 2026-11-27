"""Check the compiled draft, source references, numbers and protected assets."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import numpy as np
import pandas as pd
import pymupdf
from scipy.stats import hypergeom

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).parent
PAPER = ROOT / '00_赛题与规则/官方发布/2026论文规范与模板/APMCM LaTeX 模板'
RESULTS = ROOT / 'artifacts/p1_v21/results'
checks = {}

def check(name, condition):
    checks[name] = bool(condition)

before = json.loads((AUDIT/'protected_before.json').read_text())
changed = [name for name,digest in before.items()
           if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
check('protected_assets_unchanged', not changed)

tex_paths = [PAPER/'main.tex', *sorted((PAPER/'sections').glob('*.tex')), *sorted((PAPER/'tables').glob('*.tex'))]
source = '\n'.join(p.read_text() for p in tex_paths)
labels = [v for v in re.findall(r'\\label\{([^}]+)\}',source) if not v.startswith('#')]
# The inclusion macro receives its label as its fourth argument.
labels += re.findall(r'\\paperfigure(?:\[[^\]]+\])?\{.*?\}\{(fig:[^{}]+)\}',source,re.S)
refs = re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',source)
bibs = re.findall(r'\\bibitem\{([^}]+)\}',source)
cites = re.findall(r'\\cite\{([^}]+)\}',source)
check('unique_labels',len(labels)==len(set(labels)))
check('all_source_references_defined',set(refs)<=set(labels))
check('four_references_all_cited',len(bibs)==4 and set(bibs)==set(cites))
check('two_propositions_and_proofs',source.count(r'\begin{proposition}')==2 and source.count(r'\begin{p1proof}')==2)
equations = re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',source,re.S)
check('every_equation_followed_by_flush_left_explanation',len(equations)==9 and
      len(re.findall(r'\\end\{equation\}\s*\\noindent',source))==9)
check('all_nine_figures_referenced',sum('fig:' in v for v in labels)==9 and
      all(v in refs for v in labels if v.startswith('fig:')))
table_blocks = re.findall(r'\\begin\{tabularx?\}.*?\\end\{tabularx?\}',source,re.S)
check('tables_have_three_booktabs_rules',all(all(b.count(rule)==1 for rule in [r'\toprule',r'\midrule',r'\bottomrule']) for b in table_blocks))
check('all_populated_tables_referenced',all(v in refs for v in labels if v.startswith('tab:')))
check('no_layout_font_redefinition',not re.search(r'\\(?:geometry|setmainfont|titleformat|titlespacing|captionsetup)\b',source))

main = pd.read_csv(RESULTS/'P1_final_experiment_table.csv').set_index('route')
h = main.loc['H-soft']; n=np.array(json.loads(h.N_per_fold));m=np.array(json.loads(h.M_per_fold));hit=np.array(json.loads(h.h_per_fold))
check('grouped_EF_reconstructed',np.isclose(np.mean((hit/20)/(m/n)),h['EF_{V<=2}@20_mean']))
check('hits_denominator_100',sum(hit)==68 and h.total_screen_budget==100)
check('MSE_contributions_sum_correctly',np.isclose(h.RMSE**2,h.metal_MSE_contribution+h.nonmetal_MSE_contribution))
d=pd.read_csv(RESULTS/'03_development_results.csv').set_index('route');p=hypergeom.sf(12,3969,41,20)
check('development_EF_reconstructed',np.isclose((13/20)/(41/3969),d.loc['H-soft','EF_{V<=2}@20']))
check('development_hypergeometric_reconstructed',np.isclose(p,d.loc['H-soft','p_uniform@20'],rtol=1e-10,atol=0))
check('development_Holm_reconstructed',np.isclose(2*p,d.loc['H-soft','p_uniform_holm'],rtol=1e-10,atol=0))
check('development_NDCG_tie_break',d.loc['H-soft','NDCG@20']>d.loc['B-eps','NDCG@20'])
paired=pd.read_csv(RESULTS/'paired_AB_bootstrap_5000.csv')
pair=paired[(paired.model=='H-soft') & (paired.reference=='R-log')].set_index('metric')
check('screening_interval_crosses_zero',pair.loc['EF_macro@20','delta_p025']<0<pair.loc['EF_macro@20','delta_p975'])
check('regression_interval_below_zero',pair.loc['RMSE','delta_p975']<0)
check('paired_resamples_all_valid',all(paired.n_valid==5000) and all(paired.n_undefined==0))

pdf=pymupdf.open(PAPER/'main.pdf'); texts=[p.get_text() for p in pdf];text='\n'.join(texts)
check('summary_then_contents','2026 APMCM summary sheet' in texts[0] and 'Contents' in texts[1] and 'I. Introduction' in texts[2])
check('english_only_pdf',not re.search(r'[\u3400-\u9fff，。；：（）【】]',text))
check('no_unresolved_pdf_references','??' not in text)
check('anonymous_metadata',all(not pdf.metadata.get(k) for k in ['author','title','subject','keywords']))
check('no_personal_paths_or_email',not re.search(r'/home/|/mnt/|[A-Za-z]:\\|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text))
check('header_text',all('Team Dapmcm26301618' in t for t in texts) and all(f'Page {i-1} of 25' in texts[i] for i in range(2,len(texts))))
check('A4_all_pages',all(abs(p.rect.width-595.276)<.1 and abs(p.rect.height-841.89)<.1 for p in pdf))
log=(PAPER/'main.log').read_text()
check('clean_compile',not any(k in log for k in ['Overfull','Underfull','LaTeX Warning:','Missing character:']))

def spans(page):
    return [s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
original=pymupdf.open(AUDIT/'official_original/main.pdf')
old_head=next(s for s in spans(original[2]) if s['text'].startswith('Team'))
new_head=next(s for s in spans(pdf[2]) if s['text'].startswith('Team'))
check('official_header_font_and_position',old_head['font']==new_head['font'] and abs(old_head['size']-new_head['size'])<.01 and np.allclose(old_head['origin'],new_head['origin'],atol=.1))
old_title=next(s for s in spans(original[2]) if 'Introduction' in s['text'])
new_title=next(s for s in spans(pdf[2]) if 'Introduction' in s['text'])
check('official_section_font_size',old_title['font']==new_title['font'] and abs(old_title['size']-new_title['size'])<.01)
old_body=Counter(round(s['size'],2) for s in spans(original[2]) if s['font']=='TimesNewRomanPSMT').most_common(1)[0][0]
new_body=Counter(round(s['size'],2) for p in pdf for s in spans(p) if s['font']=='TimesNewRomanPSMT').most_common(1)[0][0]
check('official_body_font_size',old_body==new_body)

body_start=2
appendix_index=next(i for i in range(2,len(texts)) if 'Appendix A Supporting Materials' in texts[i])
figure_callouts={}
for num in ['1','2','3','B.1','B.2','B.3','B.4','B.5','B.6']:
    occurrences=[]
    for i,p in enumerate(pdf):
        for s in spans(p):
            if re.match(r'Figure\s+'+re.escape(num)+r'\b',s['text']):
                occurrences.append({'physical_page':i+1,'caption':'Bold' in s['font'],'text':s['text']})
    captions=[o for o in occurrences if o['caption']]
    prose=[o for o in occurrences if not o['caption']]
    figure_callouts[num]={'caption':captions,'paragraphs':prose}
fonts=sorted(set(s['font'] for p in pdf for s in spans(p)))
check('no_sans_serif_fallback',not any('DejaVu' in f or 'Arial' in f for f in fonts))
check('rules_synced',all((Path(base)/'references/31_逐问撰稿与官方模板保真规范.md').read_bytes()==(ROOT/'02_口径与约定/逐问撰稿规则_用户确认.md').read_bytes() for base in ['/home/mary/.codex/skills/mary-modeling-contest-pipeline-apmcm','/mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm']))

report={'checks':checks,'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v],
        'physical_pages':len(pdf),'main_body_through_references':appendix_index-body_start,
        'protected_files':len(before),'changed_protected_files':changed,'font_names':fonts,
        'body_font_pt':new_body,'figure_callouts':figure_callouts,
        'figure_scaling_exception':'User selected intact figures within official 146.4 mm text width; some plot labels are about 7.3 pt.',
        'header_exception':'User-confirmed literal of 25 retained; draft is not a final page-count certification.',
        'pdf_sha256':hashlib.sha256((PAPER/'main.pdf').read_bytes()).hexdigest()}
(AUDIT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['passed','failed','physical_pages','main_body_through_references','protected_files','body_font_pt']},ensure_ascii=False,indent=2))
if report['failed']:raise SystemExit(1)
