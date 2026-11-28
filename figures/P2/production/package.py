"""Assemble the review PDF and measure the final deliverables at their native print size."""
import csv, hashlib, json, re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pymupdf as pdf
from PIL import Image,ImageOps,ImageDraw
from render import P2,ROOT,specs,SPEC,basename,src

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_csv(path,rows):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def check(ok,label):
    if not ok: raise ValueError(label)
def spans(p):
    return [s for b in p.get_text('dict',flags=pdf.TEXT_PRESERVE_WHITESPACE)['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
def tnr(p):p.insert_font(fontname='TNR',fontfile='/mnt/c/Windows/Fonts/times.ttf')
def wrap(text,font,width,size):
    out=['']
    for word in text.split():
        nxt=(out[-1]+' '+word).strip()
        if font.text_length(nxt,fontsize=size)>width and out[-1]:out.append(word)
        else:out[-1]=nxt
    return out
def crop_compare():
    # Full native screenshots with original axes; this is a source-comparison sheet.
    doc=pdf.open();pg=doc.new_page(width=1100,height=520);tnr(pg)
    for k in range(6):
        x=12+363*(k%3);y=13+253*(k//3);f=src('A11',k)
        pg.insert_text((x+3,y+12),f.stem[:3],fontname='TNR',fontsize=12)
        pg.insert_image(pdf.Rect(x,y+16,x+350,y+222),filename=str(f),keep_proportion=True)
    doc.save(P2/'audit/A11_original_screenshots.pdf',garbage=4,deflate=True);doc.close()
def main():
    review=pdf.open(); audit=P2/'audit';gray=audit/'grayscale';gray.mkdir(parents=True,exist_ok=True)
    captions=json.loads((P2/'captions/captions.json').read_text());assert set(captions)==set(specs)
    for f,h in SPEC['input_sha256'].items():check(sha(ROOT/f)==h,'Changed spec source: '+f)
    with open(P2/'data/figure_data_manifest.csv') as f:
        records=list(csv.DictReader(f));check(len(records)==17,'data manifest')
        for r in records:check(sha(ROOT/r['file'])==r['sha256'],r['file'])
    auditrows=[];index=[];toc=[];font=pdf.Font(fontfile='/mnt/c/Windows/Fonts/times.ttf')
    for number,(i,spec) in enumerate(specs.items(),1):
        dest=P2/'plates'/basename(i); img=dest.with_suffix('.png');vector=dest.with_suffix('.pdf')
        d=pdf.open(vector);page=d[0]; ss=spans(page);text=' '.join(s['text'] for s in ss)
        fontnames=sorted(set(s['font'] for s in ss));smallest=min(s['size'] for s in ss)
        check(all('TimesNewRoman' in v for v in fontnames),i+' font');check(smallest>=8.45,i+' font size')
        check(not re.search(r'[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]',text),i+' non-English text')
        check(all(page.rect.contains(pdf.Rect(s['bbox'])) for s in ss),i+' text clipping')
        with Image.open(img) as im:
            dpi=round(im.info['dpi'][0]);check(dpi>=450 and abs(im.width*72/dpi-page.rect.width)<1,i+' dpi')
            ImageOps.grayscale(im).save(gray/(basename(i)+'.png'),dpi=(dpi,dpi),optimize=True)
        cp=P2/'captions'/(i+'.md');cp.write_text(f"# P2-{i} · {spec['title']}\n\n{captions[i]}\n")
        width=535.;left=24.;fig_y=48.;lines=wrap(captions[i],font,width-2*left,10)
        h=fig_y+page.rect.height+19+len(lines)*13+18
        out=review.new_page(width=width,height=h);tnr(out)
        kind='Main figure' if number<6 else 'Appendix figure'
        out.insert_text((left,19),f'{kind}   /   P2-{i}',fontname='TNR',fontsize=9,color=(.32,.37,.42))
        out.insert_text((left,37),spec['title'],fontname='TNR',fontsize=13)
        near=(width-page.rect.width)/2
        out.show_pdf_page(pdf.Rect(near,fig_y,near+page.rect.width,fig_y+page.rect.height),d,0)
        y=fig_y+page.rect.height+16
        for line in lines:
            out.insert_text((left,y),line,fontname='TNR',fontsize=10,color=(.12,.14,.16));y+=13
        if i=='A1':
            for rect in out.search_for('10.17188/1745405'):out.insert_link({'kind':pdf.LINK_URI,'from':rect,'uri':'https://doi.org/10.17188/1745405'})
        if number in [1,6]:toc.append([1,kind+'s',number])
        toc.append([2,f'P2-{i}   {spec["title"]}',number])
        row=dict(id='P2-'+i,page=number,placement=kind,width_mm=round(page.rect.width*25.4/72,1),
              height_mm=round(page.rect.height*25.4/72,1),dpi=dpi,minimum_print_pt=round(smallest,2),
              fonts=' / '.join(fontnames),english='PASS',font='PASS',bounds='PASS',grayscale='Reviewed',
              palette='Reviewed',no_suptitle='Reviewed',no_table='Reviewed',labels_and_legends='Reviewed',
              units_and_denominators='Reviewed',three_second_internal_readout=spec['readout'],
              vector_marks='Native scene rasters + vector labels/arrows' if i=='A1' else
              'Original illustration + vector label' if i=='A10' else
              'Vector paths from original screenshot ink and calibrated axes' if i=='A11' else 'Vector chart',
              pdf_sha256=sha(vector),png_sha256=sha(img))
        auditrows.append(row)
        index.append(dict(id='P2-'+i,review_page=number,placement=kind,title=spec['title'],purpose=spec['readout'],
                  pdf=str(vector.relative_to(P2)),png=str(img.relative_to(P2)),spec=f'specs/{i}.md',
                  caption=f'captions/{i}.md',sources=' | '.join(spec['files'])))
        d.close()
    review.set_toc(toc);review.set_metadata({'title':'P2 figure review','subject':'Sixteen plates and working captions','creator':'P2 figure archive'})
    review.save(P2/'P2_figures_review.pdf',garbage=4,deflate=True);review.close()
    crop_compare()
    write_csv(audit/'spec_out.csv',auditrows);write_csv(P2/'delivery_inventory.csv',index)
    (P2/'captions/README.md').write_text('# Figure captions\n\n'+'\n'.join(f"- [P2-{i} · {s['title']}]({i}.md)" for i,s in specs.items())+'\n')
    print('Verified input digests:',len(SPEC['input_sha256']),'and',len(records),'manifest records. Review pages:',len(auditrows))
if __name__=='__main__':main()
