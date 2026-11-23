
### test: by year  (rows 2312; MAE gls 6.6980, unw 6.1475, gap gls-unw +0.5505)

| year | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| 2016 | 873 | 17.081 | 12.406 | 10.652 | 8.785 | 11.993 | 0.662 | 1.203 |
| 2017 | 565 | 2.808 | 3.569 | 3.798 | 1.839 | 2.189 | -0.056 | -0.101 |
| 2018 | 443 | 0.844 | 1.280 | 1.290 | 0.806 | 0.821 | -0.002 | -0.003 |
| 2019 | 431 | 4.304 | 4.806 | 5.096 | 2.048 | 2.407 | -0.054 | -0.098 |

### test: by programme  (rows 2312; MAE gls 6.6980, unw 6.1475, gap gls-unw +0.5505)

| programme | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| AGRRA | 1 | 11.111 | 5.541 | 0.869 | 5.570 | 10.242 | 0.002 | 0.004 |
| FRRP | 190 | 11.735 | 7.660 | 7.736 | 10.202 | 10.486 | -0.006 | -0.011 |
| McClanahan | 189 | 54.819 | 35.060 | 26.299 | 21.668 | 33.128 | 0.716 | 1.301 |
| Reef_Check | 1932 | 3.170 | 3.829 | 4.023 | 2.023 | 2.507 | -0.161 | -0.293 |

### test: by band  (rows 2312; MAE gls 6.6980, unw 6.1475, gap gls-unw +0.5505)

| band | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| a:0 | 1288 | 0.000 | 1.393 | 1.625 | 1.393 | 1.625 | -0.129 | -0.235 |
| b:(0,10) | 590 | 2.944 | 3.601 | 4.191 | 4.037 | 4.725 | -0.150 | -0.273 |
| c:[10,50) | 294 | 22.246 | 14.043 | 13.572 | 9.385 | 11.520 | 0.060 | 0.109 |
| d:>=50 | 140 | 74.640 | 53.125 | 40.404 | 21.515 | 34.569 | 0.770 | 1.399 |

### test: by pool_sev_q  (rows 2312; MAE gls 6.6980, unw 6.1475, gap gls-unw +0.5505)

| pool_sev_q | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| <=2% | 1832 | 3.628 | 3.826 | 3.874 | 1.766 | 1.912 | -0.038 | -0.070 |
| (2,5]% | 186 | 20.027 | 15.970 | 14.815 | 7.874 | 10.979 | 0.093 | 0.169 |
| (5,10]% | 121 | 19.314 | 14.973 | 14.089 | 11.901 | 15.947 | 0.046 | 0.084 |
| >10% | 173 | 34.789 | 21.358 | 15.347 | 22.013 | 32.565 | 0.450 | 0.817 |

### test: by group (ecoregion)  (rows 2312; MAE gls 6.6980, unw 6.1475, gap gls-unw +0.5505)

| group | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| Andaman Islands | 8 | 72.915 | 47.358 | 20.062 | 25.557 | 52.853 | 0.094 | 0.172 |
| Andaman Sea | 63 | 3.317 | 3.240 | 3.227 | 1.091 | 2.752 | 0.000 | 0.001 |
| Bahamas and Florida Keys | 206 | 11.326 | 7.569 | 7.632 | 9.888 | 10.156 | -0.006 | -0.010 |
| Banda Sea and Molucca Islands | 71 | 0.848 | 1.486 | 1.975 | 1.547 | 2.442 | -0.015 | -0.027 |
| Belize and west Caribbean | 22 | 5.641 | 6.068 | 6.027 | 2.639 | 2.714 | 0.000 | 0.001 |
| Celebes Sea | 25 | 1.810 | 1.867 | 1.862 | 0.188 | 0.173 | 0.000 | 0.000 |
| Central and northern Great Barrier Reef | 48 | 21.596 | 23.876 | 25.091 | 10.602 | 12.553 | -0.025 | -0.046 |
| Eastern Hawaii | 1 | 0.000 | 1.856 | 1.018 | 1.856 | 1.018 | 0.000 | 0.001 |
| Fiji | 73 | 3.915 | 3.645 | 4.417 | 2.035 | 3.038 | -0.024 | -0.044 |
| Gulf of Oman | 13 | 0.308 | 0.635 | 0.720 | 0.369 | 0.453 | -0.000 | -0.001 |
| Hispaniola, Puerto Rico and Lesser Antilles | 171 | 1.128 | 2.387 | 2.551 | 2.089 | 2.247 | -0.012 | -0.022 |
| Jamaica | 49 | 0.946 | 3.303 | 4.708 | 3.528 | 5.231 | -0.030 | -0.054 |
| Java Sea | 18 | 42.457 | 33.971 | 29.220 | 8.485 | 14.144 | 0.037 | 0.067 |
| Kenya and Tanzania coast | 35 | 49.485 | 21.445 | 17.820 | 33.271 | 44.895 | 0.055 | 0.100 |
| Lakshadweep Islands | 14 | 85.494 | 48.069 | 30.995 | 37.424 | 54.499 | 0.103 | 0.188 |
| Lesser Sunda Islands and Savu Sea | 164 | 9.218 | 8.024 | 7.019 | 4.149 | 6.180 | 0.071 | 0.130 |
| Makassar Strait, Indonesia | 2 | 8.800 | 3.782 | 2.889 | 5.018 | 8.577 | 0.001 | 0.001 |
| Maldive Islands | 81 | 5.396 | 5.103 | 5.675 | 5.971 | 7.762 | -0.020 | -0.036 |
| Mascarene Islands | 14 | 46.735 | 42.018 | 41.421 | 6.560 | 7.517 | 0.004 | 0.007 |
| Mayotte and Comoros | 7 | 0.536 | 2.421 | 3.253 | 2.957 | 3.789 | -0.003 | -0.005 |
| Moreton Bay, eastern Australia | 75 | 6.578 | 6.018 | 5.899 | 1.514 | 1.891 | 0.004 | 0.007 |
| Netherlands Antilles and south Caribbean | 10 | 1.600 | 4.856 | 4.370 | 5.684 | 5.156 | 0.002 | 0.004 |
| Ningaloo Reef and coastal north-west Australia | 16 | 7.659 | 5.644 | 5.609 | 2.324 | 2.377 | 0.000 | 0.000 |
| North Madagascar | 28 | 59.346 | 43.128 | 34.458 | 18.891 | 29.311 | 0.105 | 0.191 |
| North Philippines | 19 | 7.342 | 3.540 | 3.619 | 8.243 | 8.148 | -0.001 | -0.001 |
| North Ryukyu Islands, Japan | 4 | 78.475 | 65.440 | 56.512 | 13.035 | 21.963 | 0.015 | 0.028 |
| North and central Red Sea | 49 | 0.135 | 0.139 | 0.138 | 0.005 | 0.005 | 0.000 | 0.000 |
| Persian Gulf | 11 | 3.750 | 4.397 | 4.791 | 1.148 | 1.844 | -0.002 | -0.003 |
| Society Islands, French Polynesia | 113 | 1.732 | 2.055 | 2.099 | 0.875 | 0.920 | -0.002 | -0.004 |
| Solomon Islands and Bougainville | 16 | 30.196 | 12.135 | 11.944 | 24.083 | 28.560 | 0.001 | 0.002 |
| South Madagascar | 12 | 74.871 | 56.871 | 54.371 | 19.944 | 22.843 | 0.013 | 0.024 |
| South-east Philippines | 16 | 0.445 | 1.505 | 1.816 | 1.631 | 1.930 | -0.002 | -0.004 |
| Southern Great Barrier Reef | 32 | 6.578 | 6.239 | 6.275 | 0.394 | 0.342 | -0.001 | -0.001 |
| Strait of Malacca | 14 | 84.579 | 54.264 | 16.518 | 30.315 | 70.365 | 0.229 | 0.415 |
| Sulu Sea | 263 | 0.712 | 1.450 | 1.526 | 0.966 | 1.061 | -0.009 | -0.016 |
| Sunda Shelf, south-east Asia | 445 | 3.321 | 4.222 | 4.420 | 1.409 | 1.719 | -0.038 | -0.069 |
| Taiwan and coastal China | 104 | 0.475 | 1.481 | 1.400 | 1.129 | 1.045 | 0.004 | 0.007 |

### surface: by year  (rows 2046; MAE gls 7.2101, unw 7.2872, gap gls-unw -0.0771)

| year | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| 2013 | 642 | 2.436 | 2.803 | 2.929 | 2.028 | 2.236 | -0.040 | 0.513 |
| 2014 | 641 | 12.980 | 9.284 | 9.336 | 4.772 | 4.887 | -0.016 | 0.212 |
| 2015 | 763 | 12.432 | 9.176 | 9.233 | 5.189 | 5.262 | -0.021 | 0.275 |

### surface: by programme  (rows 2046; MAE gls 7.2101, unw 7.2872, gap gls-unw -0.0771)

| programme | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| AGRRA | 51 | 1.761 | 2.020 | 2.043 | 1.890 | 1.993 | -0.001 | 0.008 |
| FRRP | 546 | 30.040 | 20.303 | 20.297 | 11.752 | 11.759 | 0.001 | -0.019 |
| Reef_Check | 1449 | 1.986 | 2.459 | 2.569 | 1.247 | 1.422 | -0.078 | 1.011 |

### surface: by band  (rows 2046; MAE gls 7.2101, unw 7.2872, gap gls-unw -0.0771)

| band | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| a:0 | 929 | 0.000 | 1.247 | 1.388 | 1.247 | 1.388 | -0.064 | 0.829 |
| b:(0,10) | 606 | 2.642 | 2.368 | 2.479 | 2.349 | 2.506 | -0.033 | 0.428 |
| c:[10,50) | 389 | 26.114 | 16.198 | 16.082 | 10.244 | 10.351 | 0.022 | -0.287 |
| d:>=50 | 122 | 62.380 | 48.010 | 48.048 | 14.371 | 14.332 | -0.002 | 0.030 |

### surface: by pool_sev_q  (rows 2046; MAE gls 7.2101, unw 7.2872, gap gls-unw -0.0771)

| pool_sev_q | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| <=2% | 1806 | 9.294 | 7.172 | 7.211 | 3.564 | 3.703 | -0.034 | 0.445 |
| (2,5]% | 149 | 15.112 | 8.678 | 9.212 | 9.602 | 9.411 | -0.039 | 0.504 |
| (5,10]% | 66 | 3.565 | 5.394 | 5.535 | 4.087 | 4.756 | -0.005 | 0.059 |
| >10% | 25 | 3.930 | 6.027 | 5.975 | 7.349 | 7.159 | 0.001 | -0.008 |

### surface: by group (ecoregion)  (rows 2046; MAE gls 7.2101, unw 7.2872, gap gls-unw -0.0771)

| group | n | y_mean | mae_gls | mae_unw | pred_gls | pred_unw | gap_contrib | share_of_gap |
|---|---|---|---|---|---|---|---|---|
| Andaman Sea | 40 | 0.175 | 1.388 | 1.541 | 1.396 | 1.545 | -0.003 | 0.039 |
| Bahamas and Florida Keys | 621 | 26.793 | 18.529 | 18.535 | 10.924 | 10.947 | -0.002 | 0.023 |
| Banda Sea and Molucca Islands | 6 | 0.729 | 0.770 | 0.773 | 0.264 | 0.272 | -0.000 | 0.000 |
| Belize and west Caribbean | 3 | 0.667 | 0.742 | 0.680 | 1.409 | 1.347 | 0.000 | -0.001 |
| Celebes Sea | 16 | 1.080 | 1.259 | 1.275 | 0.294 | 0.327 | -0.000 | 0.002 |
| Central and northern Great Barrier Reef | 41 | 8.095 | 7.253 | 7.251 | 1.247 | 1.310 | 0.000 | -0.001 |
| Fiji | 29 | 2.112 | 1.904 | 2.371 | 2.554 | 2.945 | -0.007 | 0.086 |
| Gulf of Oman | 25 | 0.415 | 0.583 | 0.632 | 0.306 | 0.364 | -0.001 | 0.008 |
| Gulf of Thailand | 39 | 0.173 | 2.783 | 2.859 | 2.836 | 2.883 | -0.001 | 0.019 |
| Hispaniola, Puerto Rico and Lesser Antilles | 98 | 1.605 | 2.013 | 2.102 | 1.810 | 1.922 | -0.004 | 0.055 |
| Honshu, Japan | 2 | 0.250 | 0.250 | 0.250 | 0.000 | 0.000 | 0.000 | -0.000 |
| Jamaica | 77 | 1.741 | 2.454 | 2.488 | 1.893 | 1.929 | -0.001 | 0.016 |
| Lesser Sunda Islands and Savu Sea | 33 | 5.658 | 5.378 | 6.145 | 1.177 | 3.014 | -0.012 | 0.161 |
| Maldive Islands | 17 | 1.193 | 0.887 | 1.003 | 0.918 | 1.285 | -0.001 | 0.013 |
| Marshall Islands | 6 | 1.333 | 1.226 | 1.224 | 0.209 | 0.204 | 0.000 | -0.000 |
| Mascarene Islands | 40 | 0.125 | 0.454 | 0.659 | 0.488 | 0.642 | -0.004 | 0.052 |
| Mayotte and Comoros | 17 | 0.059 | 0.877 | 1.056 | 0.915 | 1.093 | -0.001 | 0.019 |
| Moreton Bay, eastern Australia | 84 | 5.869 | 5.494 | 5.493 | 1.367 | 1.384 | 0.000 | -0.001 |
| Netherlands Antilles and south Caribbean | 17 | 3.890 | 3.954 | 3.976 | 0.650 | 0.649 | -0.000 | 0.002 |
| Ningaloo Reef and coastal north-west Australia | 5 | 1.900 | 2.287 | 2.560 | 3.968 | 4.460 | -0.001 | 0.009 |
| North Philippines | 24 | 0.964 | 1.135 | 1.121 | 0.860 | 0.818 | 0.000 | -0.002 |
| North and central Red Sea | 49 | 0.349 | 0.354 | 0.353 | 0.005 | 0.004 | 0.000 | -0.000 |
| Samoa, Tuvalu and Tonga | 1 | 5.500 | 4.516 | 4.810 | 0.984 | 0.690 | -0.000 | 0.002 |
| Shikoku, Japan | 4 | 0.000 | 0.012 | 0.006 | 0.012 | 0.006 | 0.000 | -0.000 |
| Society Islands, French Polynesia | 62 | 0.339 | 1.057 | 0.917 | 0.917 | 0.751 | 0.004 | -0.055 |
| South Ryukyu Islands, Japan | 5 | 0.000 | 0.580 | 0.537 | 0.580 | 0.537 | 0.000 | -0.001 |
| South-east Philippines | 20 | 9.156 | 8.132 | 7.790 | 1.869 | 2.180 | 0.003 | -0.043 |
| Southern Great Barrier Reef | 42 | 3.857 | 3.466 | 3.500 | 0.460 | 0.442 | -0.001 | 0.009 |
| Sulu Sea | 213 | 2.278 | 2.914 | 2.854 | 1.206 | 1.261 | 0.006 | -0.080 |
| Sunda Shelf, south-east Asia | 320 | 0.817 | 1.322 | 1.655 | 0.825 | 1.220 | -0.052 | 0.677 |
| Taiwan and coastal China | 36 | 0.097 | 0.269 | 0.251 | 0.183 | 0.177 | 0.000 | -0.004 |
| Vanuatu | 53 | 0.750 | 0.760 | 0.758 | 0.023 | 0.019 | 0.000 | -0.001 |
| Western Tuamotu Archipelago, central Pacific | 1 | 7.500 | 7.472 | 7.465 | 0.028 | 0.035 | 0.000 | -0.000 |

### Severe rows (y>=50) side by side

| index | surface | test |
|---|---|---|
| rows | 122.000 | 140.000 |
| y mean | 62.380 | 74.640 |
| pred gls | 14.371 | 21.515 |
| pred unw | 14.332 | 34.569 |
| MAE gls | 48.010 | 53.125 |
| MAE unw | 48.048 | 40.404 |
| unw-gls pred | -0.038 | 13.054 |
| share unw>gls+5 | 0.000 | 0.664 |
| pool severe share | 0.010 | 0.085 |

surface severe rows by programme/year/group:

| year | programme | group | n | y | gls | unw | mae_g | mae_u |
|---|---|---|---|---|---|---|---|---|
| 2013 | Reef_Check | Moreton Bay, eastern Australia | 1 | 52.50 | 2.25 | 2.19 | 50.25 | 50.31 |
| 2013 | Reef_Check | South-east Philippines | 1 | 72.00 | 0.51 | 1.11 | 71.49 | 70.89 |
| 2014 | FRRP | Bahamas and Florida Keys | 72 | 62.51 | 15.86 | 15.86 | 46.65 | 46.65 |
| 2015 | FRRP | Bahamas and Florida Keys | 46 | 62.21 | 13.03 | 12.92 | 49.18 | 49.29 |
| 2015 | Reef_Check | Central and northern Great Barrier Reef | 1 | 67.50 | 0.60 | 0.57 | 66.90 | 66.93 |
| 2015 | Reef_Check | Moreton Bay, eastern Australia | 1 | 56.25 | 8.61 | 8.73 | 47.64 | 47.52 |

### How far apart the two arms predict (|unw-gls|, mean) by band

| band | surface | test | surface signed | test signed |
|---|---|---|---|---|
| a:0 | 0.246 | 0.325 | 0.141 | 0.232 |
| b:(0,10) | 0.264 | 0.806 | 0.157 | 0.688 |
| c:[10,50) | 0.604 | 2.230 | 0.106 | 2.135 |
| d:>=50 | 0.600 | 13.067 | -0.038 | 13.054 |

### Composition: surface vs test

| programme | surface_n | test_n | surface_share | test_share |
|---|---|---|---|---|
| AGRRA | 51.000 | 1 | 0.025 | 0.000 |
| FRRP | 546.000 | 190 | 0.267 | 0.082 |
| McClanahan | 0.000 | 189 | 0.000 | 0.082 |
| Reef_Check | 1449.000 | 1932 | 0.708 | 0.836 |

| year | surface_n | test_n | surface_share | test_share |
|---|---|---|---|---|
| 2013 | 642.000 | 0.000 | 0.314 | 0.000 |
| 2014 | 641.000 | 0.000 | 0.313 | 0.000 |
| 2015 | 763.000 | 0.000 | 0.373 | 0.000 |
| 2016 | 0.000 | 873.000 | 0.000 | 0.378 |
| 2017 | 0.000 | 565.000 | 0.000 | 0.244 |
| 2018 | 0.000 | 443.000 | 0.000 | 0.192 |
| 2019 | 0.000 | 431.000 | 0.000 | 0.186 |

| band | surface_n | test_n | surface_share | test_share |
|---|---|---|---|---|
| a:0 | 929 | 1288 | 0.454 | 0.557 |
| b:(0,10) | 606 | 590 | 0.296 | 0.255 |
| c:[10,50) | 389 | 294 | 0.190 | 0.127 |
| d:>=50 | 122 | 140 | 0.060 | 0.061 |

pool composition (mean over rows):

| index | surface | test |
|---|---|---|
| pool_n | 50.000 | 50.000 |
| pool_ymean | 5.266 | 4.715 |
| pool_sev_share | 0.010 | 0.022 |
| pool_zero_share | 0.493 | 0.555 |
| pool_maxyear | 2011.589 | 2014.623 |
| pool_share_2013plus | 0.000 | 0.476 |

McClanahan test groups: Andaman Islands, Fiji, Java Sea, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Mascarene Islands, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Ryukyu Islands, Japan, Solomon Islands and Bougainville, South Madagascar, Strait of Malacca
those groups on the surface: {"Fiji": 29, "Lesser Sunda Islands and Savu Sea": 33, "Maldive Islands": 17, "Mascarene Islands": 40, "Ningaloo Reef and coastal north-west Australia": 5}
McClanahan rows on surface: 0

### Test severe rows: gap by pool severe-share

| pool_sev_q | n | y | gls | unw | d |
|---|---|---|---|---|---|
| <=2% | 35 | 71.150 | 8.506 | 9.699 | 1.193 |
| (2,5]% | 30 | 76.129 | 17.613 | 26.779 | 9.166 |
| (5,10]% | 17 | 74.750 | 22.259 | 35.341 | 13.082 |
| >10% | 58 | 75.944 | 31.165 | 53.379 | 21.411 |