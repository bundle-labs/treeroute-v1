# Third-party notices

The archive's own code is under the MIT licence (`LICENSE`), and its own data files are under CC BY 4.0
(`LICENSE-DATA`). Some of its files hold values from third-party data sets, and some of its predictions and figures
were made with third-party data. This file gives, for each, the licence or terms and the credit that the provider
asks for. Supplement S9 of the paper lists every input with its provider, version, citation and licence, as read
on the provider's page. Raw third-party layers are not redistributed (`KEPT_OUT.md`).

## 1. Third-party values inside the archive's files

| Values | Where in the archive | Licence or terms | Credit |
|---|---|---|---|
| PM2.5 labels: SatPM2.5 V5.GL.06 of the Atmospheric Composition Analysis Group (ACAG) | the labels inside the row-level predictions of the PM2.5 run (`runs/pm25/`) and its rival boards (`rival_boards/`) | CC BY 4.0 | Atmospheric Composition Analysis Group, Washington University in St. Louis; van Donkelaar et al. (2021); Hammer et al. (2023) |
| Forest-loss labels: Global Forest Change 2000-2025, version GFC-2025-v1.13 | the labels inside the row-level predictions of the forest-loss run (`runs/defo/`) and its rival boards | CC BY 4.0, with the display credit | "Source: Hansen/UMD/Google/USGS/NASA"; Hansen et al. (2013) |
| Burned-fraction labels: MODIS MCD64A1.061 | the labels inside the row-level predictions of the burned-fraction run (`runs/fire/`) and its rival boards | NASA: cite the data and acknowledge NASA | Giglio et al. (2021), https://doi.org/10.5067/MODIS/MCD64A1.061; Giglio et al. (2018) |
| NDVI labels: MODIS MOD13C2.061 | the labels inside the row-level predictions of the NDVI run (`runs/ndvi/`) and its rival boards | NASA: cite the data and acknowledge NASA | Didan (2021), https://doi.org/10.5067/MODIS/MOD13C2.061 |
| MERRA-2 | the PM2.5 published rivals' index tables (`rival_boards/human_index/pm25/`), answers and calibration maps (`rival_boards/rivals_human/pm25/20261007_74e67609/`), and the post hoc re-score inputs and answers (`analysis/paper_posthoc/merra2_formula/`) | cite GMAO, acknowledge NASA | Global Modeling and Assimilation Office (GMAO) (2015), https://doi.org/10.5067/FH9A0MLJPC7N; Gelaro et al. (2017) |
| Global Coral Bleaching Database | the sample events in `rebuild/inputs/coral/events_dated.parquet` (its project-made columns are under CC BY 4.0) | CC0 1.0; credited as a courtesy | van Woesik and Kratochwill (2022a, 2022b), https://doi.org/10.6084/m9.figshare.17076290.v1 |
| MODIS MOD44B tree cover | per-region statistics (columns `tc_mean`, `tc_p90`, `frac_tc30`, `frac_tc10`) in `records/earlier_runs/forest_census.csv` | NASA: cite the data and acknowledge NASA (NASA LP DAAC) | DiMiceli et al. (2022), https://doi.org/10.5067/MODIS/MOD44B.061 |
| LUH2-GCB2025 forest | per-region statistics (column `luh2_forest`) in the same census | CC BY 4.0, with attribution | Chini and Hurtt (2025), https://doi.org/10.5281/zenodo.15557904; Hurtt et al. (2020) |

The author acknowledges NASA for the MODIS products (NASA LP DAAC) and for MERRA-2 (GES DISC), whose values
these files hold.

## 2. Works produced with third-party data

### SPEIbase v2.9 (Open Database License 1.0)

No per-location SPEIbase value is in this archive, but some tree inputs of the runs were derived from SPEIbase v2.9 (Beguería
et al. 2010, 2014; data set: Beguería et al. 2023, https://doi.org/10.20350/digitalCSIC/15470). The predictions
and figures made with those inputs are produced works under section 4.3 of the ODbL, so they carry this notice:

> The predictions and figures of this archive that were made with SPEIbase-derived inputs contain information from
> SPEIbase, which is made available under the Open Database License (ODbL) 1.0:
> https://opendatacommons.org/licenses/odbl/1-0/

### ERA5-Land, AgERA5 and FireCCI (Copernicus Climate Change Service)

Some tree inputs of the runs were derived from ERA5-Land (Copernicus Climate Change Service 2019b,
https://doi.org/10.24381/cds.68d2bb30; Muñoz-Sabater et al. 2021) and AgERA5 (Copernicus Climate Change Service
2019a, https://doi.org/10.24381/cds.6c68c9bb), both CC BY 4.0, and from the FireCCI burned area (Copernicus Climate
Change Service 2019c, https://doi.org/10.24381/cds.f333cf85; Lizundia-Loiola et al. 2020). No per-location value
of these data sets is in this archive.

> The ERA5-Land and AgERA5 data and the FireCCI burned area come from the Copernicus Climate Change Service Climate Data Store. Contains modified Copernicus Climate Change Service information 2026. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains. The FireCCI burned area from 2020 on contains modified Copernicus Sentinel data 2020–2023; the author acknowledges the ESA Climate Change Initiative and its Fire CCI project, with the individual data providers, for the FireCCI burned area.

### GSHHG 2.3.7 (GNU Lesser General Public License, version 3 or later)

The region map, Figure 1 of the paper (`analysis/paper/figures/fig_map/fig_map.pdf` and `fig_map.png`), draws the
level-1 coastlines of GSHHG 2.3.7 (Wessel and Smith 1996). GSHHG is distributed under the GNU Lesser General Public
License, version 3 or later. No GSHHG file is in this archive: the figure is a rendering of the coastlines, not a
copy of the data. The distribution's `LICENSE.TXT`, reproduced word for word:

```
$LastChangedDate: 2013-11-24 09:26:07 -1000 (Sun, 24 Nov 2013) $
$Revision: 594 $

As of GSHHG 2.2.2, GSHHG is distributed under the GNU Lesser General Public
License (LGPL) version 3 or later. Copies of the The GNU General Public
License (GPL) and the GNU Lesser General Public License (LGPL) are
distributed along with the sources. Refer to the files COPYINGv3 and
COPYING.LESSERv3.

Permission to use, copy, modify, and distribute (with no more than a
reasonable redistribution fee) this data and its documentation for
any purpose is hereby granted, provided that the above copyright notice
appear in all copies, that both that copyright notice and this
permission notice appear in supporting documentation, and that the name
of GSHHG not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior permission.
 The GSHHG package may be included in a bundled distribution of software
for which a fee may be charged. The University of Hawaii (UH) and the
National Oceanic and Atmospheric Administration (NOAA) make no
representations about the suitability of this software for any purpose. 
It is provided "as is" without expressed or implied warranty.  It is
provided with no support and without obligation on the part of UH or
NOAA, to assist in its use, correction, modification, or enhancement.
```

The distribution carries no separate copyright line: the "above copyright notice" of
`LICENSE.TXT` has none above it, and the only copyright line in the distribution is the Free Software Foundation's,
in its copy of the GNU Lesser General Public License, version 3 (`COPYING.LESSERv3`). The text of that licence is
`COPYING.LESSERv3` in the GSHHG distribution, and https://www.gnu.org/licenses/lgpl-3.0.html.
This archive names GSHHG only in this notice, the figure's credit and the paper's reference.

## 3. No third-party code

The archive includes no third-party code. The two published methods that the rival tool runs, the LSTM of Kraft et
al. (2019) and the BARDL model of Salakpi et al. (2022), are re-implemented in the tool
(`rivals_code/human_rivals_build/human/adapters/ndvi_kraft.py` and `ndvi_bardl.py`).

## 4. Libraries

The Python libraries that the code imports (`environment/` lists their versions) are not redistributed; each keeps
its own licence.

## References

- Atmospheric Composition Analysis Group (n.d.). SatPM2.5 V5.GL.06: global monthly surface PM2.5, 1998–2024 [data set]. Washington University in St. Louis. CC BY 4.0. https://www.satpm.org/v5-gl-06 (accessed 23 September 2026)
- Beguería, S., Vicente-Serrano, S. M., & Angulo-Martínez, M. (2010). A multiscalar global drought dataset: The SPEIbase: A new gridded product for the analysis of drought variability and impacts. *Bulletin of the American Meteorological Society*, 91(10), 1351–1356. https://doi.org/10.1175/2010BAMS2988.1
- Beguería, S., Vicente-Serrano, S. M., Reig, F., & Latorre, B. (2014). Standardized precipitation evapotranspiration index (SPEI) revisited: Parameter fitting, evapotranspiration models, tools, datasets and drought monitoring. *International Journal of Climatology*, 34(10), 3001–3023. https://doi.org/10.1002/joc.3887
- Beguería, S., Vicente-Serrano, S. M., Reig-Gracia, F., & Latorre Garcés, B. (2023). SPEIbase v.2.9 [Data set]. DIGITAL.CSIC. https://doi.org/10.20350/digitalCSIC/15470
- Chini, L., & Hurtt, G. (2025). Land-Use Harmonization 2 for Global Carbon Budget 2025 (LUH2-GCB2025) [data set]. Zenodo. CC BY 4.0. https://doi.org/10.5281/zenodo.15557904
- Copernicus Climate Change Service (2019a). Agrometeorological indicators from 1979 to present derived from reanalysis (AgERA5) [data set]. C3S Climate Data Store. CC-BY-4.0. https://doi.org/10.24381/cds.6c68c9bb
- Copernicus Climate Change Service (2019b). ERA5-Land monthly averaged data from 1950 to present [data set]. C3S Climate Data Store. CC-BY. https://doi.org/10.24381/cds.68d2bb30
- Copernicus Climate Change Service (2019c). Fire burned area from 2001 to present derived from satellite observations [data set]. C3S Climate Data Store. https://doi.org/10.24381/cds.f333cf85
- Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG V061 [data set]. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13C2.061
- DiMiceli, C., Sohlberg, R., & Townshend, J. (2022). MODIS/Terra Vegetation Continuous Fields Yearly L3 Global 250m SIN Grid V061 [data set]. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD44B.061
- Gelaro, R., McCarty, W., Suárez, M. J., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications, Version 2 (MERRA-2). *Journal of Climate*, 30(14), 5419–5454. https://doi.org/10.1175/JCLI-D-16-0758.1
- Giglio, L., Boschetti, L., Roy, D. P., Humber, M. L., & Justice, C. O. (2018). The Collection 6 MODIS burned area mapping algorithm and product. *Remote Sensing of Environment*, 217, 72–85. https://doi.org/10.1016/j.rse.2018.08.005
- Giglio, L., Justice, C., Boschetti, L., & Roy, D. (2021). MODIS/Terra+Aqua Burned Area Monthly L3 Global 500m SIN Grid V061 [data set]. NASA LP DAAC. https://doi.org/10.5067/MODIS/MCD64A1.061
- Global Modeling and Assimilation Office (GMAO) (2015). MERRA-2 tavgM_2d_aer_Nx: 2d, Monthly mean, Time-averaged, Single-Level, Assimilation, Aerosol Diagnostics V5.12.4 [data set]. Greenbelt, MD: GES DISC. https://doi.org/10.5067/FH9A0MLJPC7N
- Hammer, M. S., van Donkelaar, A., Bindle, L., et al. (2023). Assessment of the impact of discontinuity in satellite instruments and retrievals on global PM2.5 estimates. *Remote Sensing of Environment*, 294, 113624. https://doi.org/10.1016/j.rse.2023.113624
- Hansen, M. C., Potapov, P. V., Moore, R., Hancher, M., Turubanova, S. A., Tyukavina, A., Thau, D., Stehman, S. V., Goetz, S. J., Loveland, T. R., Kommareddy, A., Egorov, A., Chini, L., Justice, C. O., & Townshend, J. R. G. (2013). High-resolution global maps of 21st-century forest cover change. *Science*, 342(6160), 850–853. https://doi.org/10.1126/science.1244693
- Hurtt, G. C., Chini, L., Sahajpal, R., Frolking, S., Bodirsky, B. L., et al. (2020). Harmonization of global land use change and management for the period 850–2100 (LUH2) for CMIP6. *Geoscientific Model Development*, 13(11), 5425–5464. https://doi.org/10.5194/gmd-13-5425-2020
- Kraft, B., Jung, M., Körner, M., Requena Mesa, C., Cortés, J., & Reichstein, M. (2019). Identifying dynamic memory effects on vegetation state using recurrent neural networks. *Frontiers in Big Data*, 2, 31. https://doi.org/10.3389/fdata.2019.00031
- Lizundia-Loiola, J., Otón, G., Ramo, R., & Chuvieco, E. (2020). A spatio-temporal active-fire clustering approach for global burned area mapping at 250 m from MODIS data. *Remote Sensing of Environment*, 236, 111493. https://doi.org/10.1016/j.rse.2019.111493
- Muñoz-Sabater, J., Dutra, E., Agustí-Panareda, A., et al. (2021). ERA5-Land: A state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data*, 13(9), 4349–4383. https://doi.org/10.5194/essd-13-4349-2021
- Salakpi, E. E., Hurley, P. D., Muthoka, J. M., Barrett, A. B., Bowell, A., Oliver, S., & Rowhani, P. (2022). Forecasting vegetation condition with a Bayesian auto-regressive distributed lags (BARDL) model. *Natural Hazards and Earth System Sciences*, 22(8), 2703–2723. https://doi.org/10.5194/nhess-22-2703-2022
- van Donkelaar, A., Hammer, M. S., Bindle, L., Brauer, M., Brook, J. R., Garay, M. J., Hsu, N. C., Kalashnikova, O. V., Kahn, R. A., Lee, C., Levy, R. C., Lyapustin, A., Sayer, A. M., & Martin, R. V. (2021). Monthly global estimates of fine particulate matter and their uncertainty. *Environmental Science & Technology*, 55(22), 15287–15300. https://doi.org/10.1021/acs.est.1c05309
- van Woesik, R., & Kratochwill, C. (2022a). A global coral-bleaching database, 1980–2020. *Scientific Data*, 9, 20. https://doi.org/10.1038/s41597-022-01121-y
- van Woesik, R., & Kratochwill, C. (2022b). Global Coral Bleaching Database [data set]. figshare. CC0 1.0. https://doi.org/10.6084/m9.figshare.17076290.v1
- Wessel, P., & Smith, W. H. F. (1996). A global, self-consistent, hierarchical, high-resolution shoreline database. *Journal of Geophysical Research: Solid Earth*, 101(B4), 8741–8743. https://doi.org/10.1029/96JB00104
