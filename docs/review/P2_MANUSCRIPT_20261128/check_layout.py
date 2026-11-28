"""Check the compiled paper, approved figure placements and frozen numeric sources."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pymupdf as pdf

review = Path(__file__).resolve().parent
root = review.parents[2]
paper = next((root / '00_赛题与规则/官方发布/2026论文规范与模板').glob('*/main.tex')).parent
before = review / 'before'
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows(p):
    with p.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def require(condition, description):
    if not condition:
        raise ValueError(description)

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

doc = pdf.open(paper / 'main.pdf')
names = doc.resolve_names()
pages = [p.get_text() for p in doc]
outline = doc.get_toc(False)
body_start = next(page for _,title,page,_ in outline if title=='1 Introduction')
links = [(p.number,link) for p in doc for link in p.get_links()]
internal = [(p,l) for p,l in links if l['kind'] in (pdf.LINK_GOTO,pdf.LINK_NAMED)]
require(all(0 <= l.get('page',-1) < len(doc) for _,l in internal), 'Unresolved internal link')
toc_links = Counter(l.get('nameddest') for p,l in internal if 1 <= p < body_start-1)
for level, title, page, dest in outline:
    key = dest['nameddest']
    printed = level <= 2 and not re.match(r'subsection\.[ABC]\.',key)
    require(toc_links[key] == (2 if printed else 0) and names[key]['page']==page-1, 'TOC target: '+title)
    heading = re.sub(r'^\d+(?:\.\d+)*\s+','',title)
    require(norm(heading) in norm(pages[page-1]), 'Missing heading on linked page: '+title)
require(body_start==3 and all(toc_links[dest['nameddest']]==2 for _,t,_,dest in outline if t.startswith('Appendix ')), 'one printed contents page with three appendix entries')
require('summary sheet' in pages[0].lower() and 'Contents' in pages[1], 'Front matter')
for i,p in enumerate(doc):
    require(abs(p.rect.width-595.28)<.1 and abs(p.rect.height-841.89)<.1, 'A4')
    if i>=body_start-1:
        require('Team Dapmcm26301618' in pages[i] and f'Page {i-body_start+2} of 25' in pages[i], 'Header')
require(not re.search(r'[\u3400-\u9fff]|\ufffd|\?\?', ''.join(pages)), 'CJK, missing glyph or unresolved reference')
require(not any(doc.metadata[k] for k in ('author','subject','keywords')), 'Identifying PDF metadata')

aux = (paper/'main.aux').read_text()
labels = {k:(number,int(logical),dest) for k,number,logical,dest in
          re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{(\d+)\}\{.*?\}\{([^{}]+)\}\{\}\}',aux)}
plate_rows = rows(root/'figures/P2/audit/spec_out.csv')
figlabels = ['pipeline','crystal','coupling','margin','cloud','graph','energy','attain','time','cost','precision','tail','budget','ablation']
lookup = dict(zip(['F1','A1','F2','F3','F5','A2','A3','A4','A5','A6','A7','A8','F4','A12'],figlabels))
p2start=next(page for _,t,page,_ in outline if t.startswith('5 Problem 2:'))
p2end=next(page for _,t,page,_ in outline if t.startswith('5.6 Direct answer'))
allfig=[]
for row in plate_rows:
    ident=row['id']; short=ident.split('-')[-1]; lab='fig:p2'+lookup[short]
    number,logical,dest=labels[lab]; page=names[dest]['page']; page_obj=doc[page]
    original=next((root/'figures/P2/plates').glob(ident+'_*.pdf'))
    require(digest(original)==row['pdf_sha256'],ident+' hash')
    require(logical==page-body_start+2,lab+' page')
    drawing=doc[page].read_contents()
    # Each approved plate is a PDF Form XObject (with exactly its original media box).
    with pdf.open(original) as source:
        w=source[0].rect.width; h=source[0].rect.height
    number_pattern=rb'[+\-\d.]+'
    candidates=[]
    for xref,form,invoker,rect in page_obj.get_xobjects():
        if invoker or abs(rect[2]-w)>.05 or abs(rect[3]-h)>.05: continue
        m=re.search(rb'q ('+number_pattern+rb') 0 0 ('+number_pattern+rb') '+number_pattern+rb' '+number_pattern+rb' cm q 1 0 0 1 '+number_pattern+rb' '+number_pattern+rb' cm /'+form.encode()+rb' Do', drawing)
        if m: candidates.append(float(m[1]))
    require(candidates and max(candidates)-min(candidates)<.001, ident+' scale')
    scale=candidates[0]
    min_pt=scale*float(row['minimum_print_pt'])
    require(min_pt>=7.0, ident+' type')
    cites=[(pg,l['from']) for pg,l in internal if l.get('nameddest')==dest]
    local=[pg for pg,rect in cites if page-1<=pg<=page]
    require(local, 'No nearby callout: '+lab)
    require(any(p2start-1<=pg<=p2end-1 for pg,_ in cites), 'No main-text guide: '+lab)
    allfig.append(dict(id=ident,figure=number,pdf_page=page+1,logical_page=logical,
                       local_callout_pdf_page=min(local)+1,scaled_min_pt=round(min_pt,3)))
workflow = root/'figures/P2/solver_workflow/kaiwu_solver_workflow.pdf'
with pdf.open(workflow) as flow:
    source_span = [s for b in flow[0].get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
    expected = ['Enumerate','Exact reference','Solve in Kaiwu','SA / cloud optimizer','Check returns','Legality and regret']
    require(sorted(s['text'].strip() for s in source_span)==sorted(expected), 'workflow labels')
    require(all('TimesNewRoman' in s['font'] for s in source_span), 'workflow font')
fig_no, _, key=labels['fig:p2workflow']
flow_page=names[key]['page']
flow_text = [s for b in doc[flow_page].get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans'] if s['text'].strip() in expected]
require(len(flow_text)==6 and min(s['size'] for s in flow_text)>=8, 'workflow print size')
require(any(pg==flow_page and l.get('nameddest')==key for pg,l in internal),'workflow same-page introduction')
allfig.append(dict(id='P2-workflow',figure=fig_no,pdf_page=flow_page+1,logical_page=flow_page-body_start+2,local_callout_pdf_page=flow_page+1,scaled_min_pt=round(min(s['size'] for s in flow_text),3)))
for fig in allfig:
    page = doc[fig['pdf_page']-1]
    prefix = 'Figure '+fig['figure']+' '
    matches = [''.join(span['text'] for span in line['spans']).strip()
               for block in page.get_text('dict')['blocks'] if block['type']==0
               for line in block['lines'] if any('Bold' in span['font'] for span in line['spans'])
               and ''.join(span['text'] for span in line['spans']).strip().startswith(prefix)]
    require(len(matches)==1, 'missing caption line: '+fig['id'])
    caption = matches[0][len(prefix):]
    # Compare the single physical PDF line to the complete title recorded by TeX.
    label='fig:p2'+(lookup[fig['id'][3:]] if fig['id']!='P2-workflow' else 'workflow')
    prefix_aux=r'\\newlabel\{'+re.escape(label)+r'\}\{\{[^}]+\}\{\d+\}\{(.*?)\}\{figure\.caption'
    title = re.search(prefix_aux,aux).group(1)
    require(norm(caption)==norm(title), 'caption wraps: '+fig['id'])
    fig['caption']=caption
require('cim.CIMOptimizer' in pages[flow_page] and 'SimulatedAnnealingOptimizer' in ''.join(pages[flow_page].split()), 'Kaiwu solvers separated from workflow')
for key in ['tab:p2service','tab:p2pools','prop:p2onehot','prop:p2ground','prop:p2margin']:
    d=labels[key][2]
    require(any(l.get('nameddest')==d for _,l in internal),key+' no internal reference')
for key in ['kasahara2002','mp1222738','chancellor2019','kaiwu144','wei2026']:
    require(any(l.get('nameddest')=='cite.'+key for _,l in internal),'uncited '+key)
for f in (before/'sections').glob('*.tex'):
    if f.name not in ('frontmatter.tex','references.tex'):
        require(digest(f)==digest(paper/'sections'/f.name), f.name)
for f in list(before.glob('*.cls'))+list(before.glob('*.cfg'))+list((before/'tables').glob('*.tex')):
    require(digest(f)==digest(paper/f.relative_to(before)),f.name)
for p,n,runner,gap in [('07',2704,'Sc|Ti|NO2',.416697),('11',529,'Sr|Ta|NO2',.465139)]:
    vals=rows(root/f'artifacts/p2_v2/enumeration_{p}.csv')
    require(len(vals)==n and vals[0]['key']=='La|Ti|NO2' and round(float(vals[0]['vhat']),6)==1.839047
            and vals[1]['key']==runner and round(float(vals[1]['regret']),6)==gap,'enumeration '+p)
formal=[r for r in rows(root/'figures/P2/data/task_margin.csv') if r['stage']=='formal']
require(len(formal)==20 and all(int(r['returns'])==10 for r in formal),'formal tasks')
require(min(int(r['min_residual']) for r in formal)==84 and max(int(r['min_residual']) for r in formal)==176 and max(int(r['max_residual']) for r in formal)==188,'residual range')
require([(r['slot'],r['selected_margin']) for r in formal if int(r['selected_margin'])<=20]==[('F03','20')] and any(r['slot']=='F14' and r['set_min_margin']=='8' for r in formal),'nearest margins')
for name,energy,regret in [('raw',-10822,21.65085),('rc',-10994,13.55685)]:
    path=root/f'artifacts/p2_v2/representations/11-{name}-N8.certificate.json'
    c=json.loads(path.read_text()); r=json.loads(path.with_name(path.name.replace('.certificate','')).read_text())
    require(c['best_allowed_energy']==c['witness_energy']==energy and c['status']=='COUNTEREXAMPLE' and round(r['worst_ground_regret'],5)==regret,'witness '+name)
proof = subprocess.check_output([sys.executable,'-I','-B',str(root/'evidence/p2/verify.py')],text=True)
build=(paper/'main.log').read_text()
require(not re.search('Overfull|Underfull|Missing character|undefined references|LaTeX Warning:|destination with the same identifier', build),'TeX warnings')
result=dict(pdf_sha256=digest(paper/'main.pdf'),pages=len(doc),body_pdf_page=body_start,
            p2_main_pdf_pages=[p2start,p2end],bookmarks=len(outline),printed_toc_entries=len(toc_links),toc_links=sum(toc_links.values()),
            internal_links=len(internal),fonts_audit_baseline='Native minimum from signed-off plates times XeTeX PDF placement scale',
            figures=allfig, offline_certificate=proof.strip().splitlines())
(review/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(len(allfig),'plates,',len(toc_links),'printed TOC entries,',len(outline),'bookmarks,',len(internal),'internal links verified.')
