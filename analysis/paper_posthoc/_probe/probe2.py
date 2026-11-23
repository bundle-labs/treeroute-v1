import numpy as np, pandas as pd, pyarrow.parquet as pq
R={"pm25":"D:/treeroute/runs/pm25/headline/20261007_74e67609","ndvi":"D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
   "fire":"D:/treeroute/runs/fire/headline/20261017_869d1f38","defo":"D:/treeroute/runs/defo/headline/20261017_d71c61f4"}
for k,v in R.items():
    t=pq.read_table(v+"/test_preds.parquet",columns=["y","normal","arm__identity_trees_off_unweighted","base__guess_normal","legal_min","legal_max"]).to_pandas()
    lab=np.isfinite(t.y.values)
    a=t["arm__identity_trees_off_unweighted"].values; g=t["base__guess_normal"].values; n=t["normal"].values
    clipn=np.clip(n,t.legal_min.iloc[0],t.legal_max.iloc[0])
    print(k,"rows",len(t),"lab",lab.sum(),"max|tof-gn| all %.3e"%np.nanmax(np.abs(a-g)),"lab %.3e"%np.max(np.abs(a-g)[lab]),
          "gn==clip(normal) %s"%np.allclose(g,clipn,rtol=0,atol=0),
          "MAE tof %.12g gn %.12g diff %.3e"%(np.mean(np.abs(t.y.values[lab]-a[lab])),np.mean(np.abs(t.y.values[lab]-g[lab])),
           np.mean(np.abs(t.y.values[lab]-a[lab]))-np.mean(np.abs(t.y.values[lab]-g[lab]))))
# coral more strata
c=pq.read_table("D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet",columns=["unit","time","lead","y","arm__arcsine_corrector_gls"]).to_pandas()
p=pq.read_table("D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_hgb_l1.parquet",columns=["unit","time","lead","arm__rival_hgb_l1"]).to_pandas()
c=c.merge(p,on=["unit","time","lead"],validate="one_to_one")
o,r="arm__arcsine_corrector_gls","arm__rival_hgb_l1"
for cuts in ([0,10,50],[0,20,50],[0,5,20,50],[0,1,10,50],[0,2.5,10,50]):
    out=[]
    edges=cuts+[1e9]
    for lo,hi in zip(edges[:-1],edges[1:]):
        s=c[(c.y>lo)&(c.y<=hi)] if lo==0 else c[(c.y>lo)&(c.y<=hi)]
        out.append("(%g,%g] n%d ours %.2f L1 %.2f"%(lo,hi,len(s),(s.y-s[o]).abs().mean(),(s.y-s[r]).abs().mean()))
    print(" | ".join(out))
