"""Composition-only feature construction; fixed sources and explicit dependencies."""
from itertools import product
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from mendeleev.econf import ElectronicConfiguration
from common import ROOT, OUT, X_ORDER, dump, sha

STOICH = {'O3': {'O': 3}, 'NO2': {'N': 1, 'O': 2}, 'FO2': {'F': 1, 'O': 2},
          'N2O': {'N': 2, 'O': 1}, 'N3': {'N': 3}, 'O2S': {'O': 2, 'S': 1},
          'FNO': {'F': 1, 'N': 1, 'O': 1}}
CHARGE = {'O': -2, 'N': -3, 'F': -1, 'S': -2}
ION_RADII = {'O': 1.40, 'F': 1.33, 'S': 1.84, 'N': 1.46}
DB = Path('/home/mary/.local/lib/python3.10/site-packages/mendeleev/elements.db')
ZUNGER = ROOT / '01_参考学习/量子知识补充（forD题）/02_GitHub开源/perovskite-tutorial/zungervalenceradius.csv'
ORB = [f'N{s}{kind}' for kind in ('Valence', 'Unfilled') for s in 'spdf']
BASIC = ['Z', 'mass', 'group', 'period', 'en', 'ie1', 'ie2', 'ie3', 'ea', 'nvalence', 'arad', 'covalent', 'Rs', 'Rp', 'Rd']
ELECTRONIC = {'en', 'ie1', 'ie2', 'ie3', 'ea', 'nvalence', 'Rs', 'Rp', 'Rd', 'pettifor', 'mb_en', 'rs_plus_rp', *ORB}
GEOMETRIC = {'arad', 'covalent', 'irad'}
X_PROPS = ['en', 'ie1', 'ea', 'nvalence', 'arad', 'covalent']


class Features:
    def __init__(self, elements):
        self.elements = sorted(set(elements) | {'O', 'N', 'F', 'S'})
        con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
        e = pd.read_sql_query('select * from elements', con).set_index('symbol')
        ions = pd.read_sql_query('select * from ionicradii', con)
        ox = pd.read_sql_query('select * from oxidationstates', con)
        ie = pd.read_sql_query('select atomic_number,ion_charge,ionization_energy from ionizationenergies', con)
        con.close()
        zunger = pd.read_csv(ZUNGER).set_index('Element')
        magpie = {p: np.array([float(x.strip()) for x in (OUT / 'sources/magpie' / (p + '.table')).read_text().splitlines()]) for p in ORB}
        self.table, self.states, self.radii = {}, {}, {}
        provenance = []
        for sym in self.elements:
            row = e.loc[sym]; Z = int(row.atomic_number)
            ec = ElectronicConfiguration(row.electronic_configuration)
            ies = ie[ie.atomic_number == Z].set_index('ion_charge').ionization_energy.to_dict()
            ir = ions[ions.atomic_number == Z]
            nv = ec.nvalence(row.block, int(row.period))
            simple = ec.nvalence(row.block, int(row.period), method='simple')
            energies = [ies.get(i, np.nan) for i in range(simple)]
            vals = dict(Z=Z, mass=row.atomic_weight, group=row.group_id, period=row.period,
                        en=row.en_pauling, ea=row.electron_affinity, arad=row.atomic_radius / 100,
                        covalent=row.covalent_radius_pyykko / 100, nvalence=nv,
                        irad=float(ir.ionic_radius.median()) if len(ir) else np.nan,
                        pettifor=row.pettifor_number, mb_en=float(np.sqrt(np.mean(energies))) if energies else np.nan)
            vals.update({f'ie{k}': ies.get(k - 1, np.nan) for k in (1, 2, 3)})
            vals.update({p: float(zunger.loc[sym, p]) if sym in zunger.index else np.nan for p in ('Rs', 'Rp', 'Rd')})
            vals['rs_plus_rp'] = vals['Rs'] + vals['Rp']
            vals.update({p: magpie[p][Z - 1] for p in ORB})
            self.table[sym] = vals
            state_rows = ox[(ox.atomic_number == Z) & (ox.oxidation_state > 0)]
            self.states[sym] = [(int(r.oxidation_state), r.category == 'main') for r in state_rows.itertuples()]
            for r in ir.itertuples():
                key = (sym, int(r.charge), r.coordination)
                self.radii.setdefault(key, []).append(float(r.ionic_radius) / 100)
            for prop, val in vals.items():
                src = 'magpie-v0.9.3' if prop in ORB else 'zunger-local' if prop in ('Rs','Rp','Rd','rs_plus_rp') else 'mendeleev-1.3.0'
                provenance.append(dict(element=sym, property=prop, value=val, source=src,
                    is_missing=not np.isfinite(val), is_source_imputed=None, source_interpolation_unknown=True,
                    definition='mendeleev nvalence(simple); sqrt(mean(IE[1:n]))' if prop == 'mb_en' else 'fixed source convention'))
        self.tags = {}
        self.geometry_cache = {}
        OUT.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(provenance).to_csv(OUT / 'element_provenance.csv', index=False)
        dump(OUT / 'element_sources.json', {'db_sha256': sha(DB), 'zunger_sha256': sha(ZUNGER),
             'radii_angstrom': ION_RADII, 'N_CN': 4, 'S_radius_origin': 'Pauling 1960 in local database',
             'Zunger_unit': 'source-native; not mixed into ionic geometry'})

    def geometry(self, a, b, x):
        key = (a,b,x)
        if key in self.geometry_cache: return self.geometry_cache[key]
        target = -sum(CHARGE[s]*n for s,n in STOICH[x].items())
        balanced = [(qa,qb,ma,mb) for (qa,ma),(qb,mb) in product(self.states[a], self.states[b]) if qa+qb == target]
        residues = [abs(qa+qb-target) for (qa,_),(qb,_) in product(self.states[a], self.states[b])]
        out = {'geo_charge_pairs': len(balanced), 'geo_main_charge_pairs': sum(ma and mb for _,_,ma,mb in balanced),
               'geo_min_charge_residual': min(residues) if residues else np.nan}
        rx = sum(ION_RADII[s]*n for s,n in STOICH[x].items()) / 3
        for mode in ('strict', 'proxy'):
            metric = {k: [] for k in ('rA','rB','t','mu','tau')}
            approximate = 0
            for qa,qb,ma,mb in balanced:
                ar = self.radii.get((a,qa,'XII'), [])
                if not ar and mode == 'proxy':
                    ar = self.radii.get((a,qa,'VIII'), []) or self.radii.get((a,qa,'VI'), [])
                    approximate += bool(ar)
                br = self.radii.get((b,qb,'VI'), [])
                if 'N' in STOICH[x] and mode == 'strict': continue
                for ra,rb in product(ar,br):
                    if min(ra,rb,rx) <= 0: continue
                    ratio = ra/rb
                    metric['rA'].append(ra); metric['rB'].append(rb)
                    metric['t'].append((ra+rx)/(np.sqrt(2)*(rb+rx)))
                    metric['mu'].append(rb/rx)
                    if ratio > 1+1e-6:
                        metric['tau'].append(rx/rb-qa*(qa-ratio/np.log(ratio)))
            for name, values in metric.items():
                for agg, func in [('mean',np.mean),('std',np.std),('min',np.min),('max',np.max)]:
                    out[f'geo_{mode}_{name}_{agg}'] = float(func(values)) if values else np.nan
            out[f'geo_{mode}_count'] = len(metric['t'])
            out[f'geo_{mode}_tau_count'] = len(metric['tau'])
            out[f'geo_{mode}_A_proxy_count'] = approximate
        out['geo_X_radius_mean'] = rx
        out['geo_X_N_CN4_proxy'] = int('N' in STOICH[x])
        self.geometry_cache[key] = out
        return out

    def row(self, a, b, x, legacy=False):
        f = {}
        def add(name, value, tags=()):
            f[name] = float(value)
            if not legacy:
                self.tags[name] = sorted(tags)
                f[name+'__missing'] = float(not np.isfinite(value))
                self.tags[name+'__missing'] = sorted(tags)
        if legacy:
            props = ['Z','mass','en','group','period','ie1','ea','irad','arad','covalent','nvalence','Rs','Rp','Rd']
            for site,sym in [('A',a),('B',b)]:
                for p in props:
                    # Preserve old F0 native pm convention, while repairing zeros.
                    v = self.table[sym][p] * (100 if p in ('arad','covalent') else 1)
                    add(site+'_'+p,v)
            for name,v in [('d_en',abs(f['A_en']-f['B_en'])),('d_irad',abs(f['A_irad']-f['B_irad'])),
                           ('d_Z',abs(f['A_Z']-f['B_Z'])),('sum_ie1',f['A_ie1']+f['B_ie1'])]: add(name,v)
        else:
            for site,sym in [('A',a),('B',b)]:
                for p in BASIC + ORB + ['pettifor','mb_en','rs_plus_rp']:
                    tags = ({'electronic'} if p in ELECTRONIC else set()) | ({'geometry'} if p in GEOMETRIC else set())
                    if p in ORB + ['pettifor','mb_en','rs_plus_rp']: tags |= {'E1'}
                    add(site+'_'+p,self.table[sym][p],tags)
            for p in ['en','ie1','ea','nvalence','arad','covalent','Rs','Rp']:
                tags = {'electronic'} if p in ELECTRONIC else {'geometry'}
                dv = self.table[a][p]-self.table[b][p]
                add('AB_diff_'+p,dv,tags);add('AB_abs_'+p,abs(dv),tags)
            for p in X_PROPS:
                v = np.array([self.table[s][p] for s,n in STOICH[x].items() for _ in range(n)])
                tags = {'xstats'} | ({'electronic'} if p in ELECTRONIC else {'geometry'})
                for agg,fun in [('mean',np.mean),('std',np.std),('min',np.min),('max',np.max)]:
                    add('X_'+p+'_'+agg,fun(v),tags)
                for site,sym in [('A',a),('B',b)]: add(site+'X_'+p,self.table[sym][p]-np.mean(v),tags)
            for name,v in self.geometry(a,b,x).items():
                tags = {'geometry'}
                if 'charge' not in name: tags |= {'xstats'} # effective X-radius descendants
                if '_tau_' in name: tags |= {'tau'}
                add(name,v,tags)
            for s in ('O','N','F','S'): add('X_count_'+s,STOICH[x].get(s,0))
            add('X_formal_charge',sum(CHARGE[s]*n for s,n in STOICH[x].items()))
        add('a_eq_b',a==b)
        for fam in X_ORDER: add('X_is_'+fam,x==fam)
        return f

    def transform(self, d, feature_set='F4'):
        legacy = feature_set == 'F0'
        F = pd.DataFrame([self.row(r.A,r.B,r.X,legacy) for r in d.itertuples()], index=d.index)
        if not legacy:
            exclude = {'F3':'E1', 'minus_electronic':'electronic', 'minus_geometry':'geometry', 'minus_xstats':'xstats'}.get(feature_set)
            if exclude: F = F[[c for c in F if exclude not in self.tags[c]]]
        assert not np.isinf(F.to_numpy()).any()
        if legacy: assert F.shape[1] == 40
        return F

    def save_schema(self):
        dump(OUT / 'feature_schema.json', self.tags)
