import json, numpy as np, pandas as pd
from pathlib import Path
RUN=Path(r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"); OUT=Path(r"D:\treeroute\analysis\coral_choice\drift\out")
m=pd.read_parquet(OUT/"rows.parquet"); key={r:i for i,r in enumerate(m.row_id)}
names=json.loads((OUT/"fold_names.json").read_text()); fidx={g:i for i,g in enumerate(names)}; wF=np.load(OUT/"w_folds.npy")
d=pd.read_parquet(OUT/"donor_fit.parquet"); y=np.full(len(m),np.nan); y[d.key.values]=d.y.values
ip=pd.read_parquet(RUN/"inner_preds.parquet",columns=["unit","y"]); 
for r,v in zip(ip.unit,ip.y): y[key[r]]=v
tp=pd.read_parquet(RUN/"test_preds.parquet"); ty=dict(zip(tp.unit,tp.y))
per=np.where(m.day<=734868,"<=2012","2013-15")
out=[]
def collect(pools, wget, yget, tag):
    for r in pools.itertuples():
        ids=json.loads(r.pool_row_ids)
        if not ids or yget[r.row_id]<=50: continue
        kk=np.array([key[x] for x in ids]); w=wget(r)[kk]; w=w/w.mean()
        for k_,wi in zip(kk,w):
            out.append((tag,r.row_id,y[k_],per[k_],m.s_programme[k_],wi,m.f_dhw_84[k_]))
collect(pd.read_parquet(RUN/"pools_test_pass.parquet"), lambda r: m.w_T.values, ty, "test")
sy=dict(zip(ip.unit,ip.y))
collect(pd.read_parquet(RUN/"pools_decision_surface.parquet"), lambda r: wF[fidx[r.part]], sy, "surface")
D=pd.DataFrame(out,columns=["pass","row","y","period","prog","w_rel","dhw84"])
D["ybin"]=pd.cut(D.y,[-0.001,0,20,50,101],labels=["0","(0,20]","(20,50]",">50"])
print("pool members of SEVERE (y>50) scored rows; w_rel = weight / pool mean weight (unweighted = 1)")
print(D.groupby(["pass","ybin"],observed=True).agg(members=("y","size"),w_rel=("w_rel","mean")).round(3).to_string())
print(D[D.ybin==">50"].groupby(["pass","period","prog"],observed=True).agg(members=("y","size"),ymean=("y","mean"),dhw84=("dhw84","mean"),w_rel=("w_rel","mean")).round(3).to_string())
# surface severe rows programme
ps=pd.read_parquet(RUN/"pools_decision_surface.parquet"); sev=[r for r in ps.row_id if sy[r]>50]
print("surface severe rows by programme:", m.set_index("row_id").loc[sev].s_programme.value_counts().to_dict())
t_sev=[r for r in tp.unit if ty[r]>50]; print("test severe rows by programme:", tp.set_index("unit").loc[t_sev].programme.value_counts().to_dict())
