import numpy as np, pandas as pd, glob, scipy
from scipy import stats
print("scipy", scipy.__version__, "pandas", pd.__version__, "numpy", np.__version__)
def tag(m, se, n, band, z):
    if se == 0 and m == 0: return "identical?"
    lo, hi = m - z*se, m + z*se
    if -band <= lo and hi <= band: return "equivalent"
    if lo > 0 and m >= band: return "helps"
    if hi < 0 and m <= -band: return "hurts"
    return "cannot_tell"
rows=[]
for f in ["D:/treeroute/runs/_headline_tables/verdicts_9abcea419ce2.csv"]+glob.glob("D:/treeroute/runs/_headline_tables/*/verdicts_*.csv"):
    t=pd.read_csv(f); t=t[t.rows=="common"]
    for _,r in t.iterrows():
        rows.append(("ours",r.package,int(r.lead),"own verdict",r.tag,r.contrast_mean,r.contrast_se,int(r.n_groups),r.band))
for f in glob.glob("D:/treeroute/rivals/*/*/board_lead_*.csv"):
    t=pd.read_csv(f); t=t[t.decides==True]
    pkg=f.replace("\\","/").split("/")[3]
    for _,r in t.iterrows():
        rows.append(("common",pkg,int(r.lead),r.learner,r.tag,r.d_mean,r.d_se,int(r.n_groups),r.band))
for f in glob.glob("D:/treeroute/rivals_human/*/*/human_board_lead_*.csv"):
    t=pd.read_csv(f); t=t[t.decides==True]
    pkg=f.replace("\\","/").split("/")[3]
    for _,r in t.iterrows():
        rows.append(("human",pkg,int(r.lead),r.rival,r.tag,r.d_mean,r.d_se,int(r.n_groups) if r.n_groups==r.n_groups else -1,r.band))
d=pd.DataFrame(rows,columns=["src","pkg","lead","who","tag","mean","se","G","band"])
out=[]
for _,r in d.iterrows():
    if r.tag in ("declined","identical"):
        out.append((r.tag,r.tag,np.nan,np.nan)); continue
    tz=tag(r["mean"],r.se,r.G,r.band,1.959963984540054)
    tt=tag(r["mean"],r.se,r.G,r.band,stats.t.ppf(0.975,r.G-1))
    pz=2*stats.norm.sf(abs(r["mean"]/r.se)); pt=2*stats.t.sf(abs(r["mean"]/r.se),r.G-1)
    out.append((tz,tt,pz,pt))
d[["tag_z","tag_t","p_z","p_t"]]=pd.DataFrame(out)
pd.set_option("display.width",250)
print(d.to_string())
print("rows",len(d),"changed",(d.tag_z!=d.tag_t).sum())
print(d[d.tag_z!=d.tag_t])
print("tag_z != recorded:", d[(d.tag_z!=d.tag)][["src","pkg","lead","who","tag","tag_z"]])
