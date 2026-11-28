"""Export six VESTA scenes from the archived supercell, with native VESTA 3.5.8 under X11."""
from pathlib import Path
import subprocess, sys, re, shutil, json, hashlib, time, os, tempfile
import numpy as np
from scipy.spatial.transform import Rotation

here = Path(__file__).resolve().parent
repo = here.parents[3]
scratch = Path(tempfile.mkdtemp(prefix='p2-vesta-'))
exe = Path(os.environ['VESTA_BIN']).resolve()
env = dict(os.environ, LIBGL_ALWAYS_SOFTWARE='1')
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
scratch.mkdir(parents=True,exist_ok=True)
source=repo/'figures/shared/crystal_structure/source/LaTiNO2_2x2x1.cif'
shutil.copyfile(source,scratch/'input.cif')
base=scratch/'base.vesta'
if not base.exists():
    subprocess.run([str(exe),'-nogui','-i',str(scratch/'input.cif'),'-o',str(base)],cwd=exe.parent)
native=base.read_text()
# Verify the periodic first coordination shell in the supplied orthorhombic cell.
rows=[a.split() for a in source.read_text().splitlines() if re.match(r'^  (?:La|Ti|O|N)\s',a)]
length=np.array([float(re.search('_cell_length_'+k+r'\s+(\S+)',source.read_text()).group(1)) for k in 'abc'])
xyz=np.array([r[3:6] for r in rows],float)
el=np.array([r[0] for r in rows])
for ti in xyz[el=='Ti']:
    d=xyz-ti
    ds=np.linalg.norm((d-np.rint(d))*length,axis=1)
    shell=el[((el=='O') | (el=='N')) & (ds<2.36)]
    assert sorted(shell)==['N','N','O','O','O','O']
bonds='SBOND\n'+'\n'.join(f'  {i} Ti {atom} 0.00000 2.36000 0 1 1 0 1 0.130 2.000 125 135 145' for i,atom in [(1,'O'),(2,'N')])+'\n  0 0 0 0\n'
native=re.sub(r'SBOND\n.*?(?=SITET)',bonds,native,flags=re.S)
# Muted element colours and smaller La radii retain the octahedral interiors.
palette={'La':(.82,[178,190,126]),'Ti':(.62,[70,119,159]),'O':(.46,[213,146,117]),'N':(.47,[84,65,120])}
for section,stop in [('SITET','VECTR'),('ATOMT','SCENE')]:
    start=native.index(section+'\n')+len(section)+1
    end=native.index('\n  0 0',start)
    lines=[]
    for line in native[start:end].splitlines():
        tok=line.split()
        atom=re.match('[A-Za-z]+',tok[1]).group()
        rad,rgb=palette[atom]
        tok[2:10]=[f'{rad:.3f}',*map(str,rgb),*map(str,rgb),'175']
        lines.append('  '+' '.join(tok))
    native=native[:start]+'\n'.join(lines)+native[end:]
views={'c':np.eye(3),'a':Rotation.from_euler('y',-90,degrees=True).as_matrix(),
       'oblique':Rotation.from_euler('yx',[36,24],degrees=True).as_matrix()}
out=[]
for mode,number in [('poly',2),('stick',0)]:
    for view,rot in views.items():
        name=f'{mode}_{view}'
        scene=scratch/(name+'.vesta')
        mat=np.eye(4); mat[:3,:3]=rot
        config=re.sub(r'(?<=SCENE\n)(?:[^\n]*\n){4}', ''.join(' '+' '.join(f'{x:.7f}' for x in row)+'\n' for row in mat),native)
        config=re.sub(r'MODEL\s+0  1  0',f'MODEL   {number}  1  0',config)
        scene.write_text(config)
        shutil.copy2(scene,here/scene.name)
        png=scratch/(name+'.png')
        if not png.is_file():
            log=open(scratch/(name+'.log'),'wb')
            proc=subprocess.Popen([str(exe),'-open',str(scene),'-scale_width_to','28','-flush','-export_img','scale=3',str(png),'-close',str(scene)],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
            for attempt in range(120):
                if png.exists() and png.stat().st_size>1000:
                    time.sleep(1); break
                time.sleep(.5)
            if not png.exists(): raise SystemExit(f'Verify native VESTA export of {name}: {scratch}')
        shutil.copy2(png,here/png.name)
        out.append(dict(scene=name,png_sha256=digest(png),scene_sha256=digest(scene),width_A=28))
(here/'exports.json').write_text(json.dumps(dict(source_sha256=digest(source),shell='4 O and 2 N at each of 16 Ti sites',cutoff_A=2.36,images=out),indent=2)+'\n')
