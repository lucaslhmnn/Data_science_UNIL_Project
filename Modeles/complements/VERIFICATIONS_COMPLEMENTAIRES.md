# Vérifications complémentaires VC1 à VC4

> Générées par `Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)` le 15/11/2026 à 18:58:02 CET. Graine : 42. Chaque section : commande, sortie brute, statut (CONFORME / ÉCART / DÉFAUT) et conclusion calculée selon les règles du script.

## Synthèse

| vérification | intitulé | statut |
|---|---|---|
| VC1 | Offset dans la validation de LightGBM | CONFORME |
| VC2 | Contrôle croisé de M3 (binomial négatif) | CONFORME |
| VC3 | Zone × temps et système de tarification | ÉCART |
| VC4 | Les 13 lignes exclues | CONFORME |

## VC1 Offset dans la validation de LightGBM : **CONFORME**

Commande : `Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)`, fonction `vc1_offset_validation`.

```text
Lecture de Modeles/scripts/02_modeles.py :
   r_fit = fit_part[col].sum() / fit_part["exposure_years"].sum()
   dva = lgb.Dataset(Xv, yv, init_score=initv, categorical_feature=["zone"], reference=dtr)
   b = fit_lgb(lgb_matrix(fit_part), fit_part[col].to_numpy(float), fit_part["log_e"] + np.log(r_fit),
   lgb_matrix(val_part), val_part[col].to_numpy(float), val_part["log_e"] + np.log(r_fit), params)
   callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])
   "metric": "poisson"
-> Le Dataset de validation reçoit init_score = log(e) + log(r_fit), r_fit calculé sur les lignes d'ajustement (2010, 2017) : True

Cible payes : hyperparamètres {learning_rate=0.02, num_leaves=7, min_data_in_leaf=100, lambda_l2=1.0}, itération retenue au premier jet = 122
  r_fit = 0.00532766 (taux des lignes 2010-2017) ; log(r_fit) = -5.234843
  métrique LightGBM « poisson » (validation) = moyenne de (mu - y log mu) calculée à la main : écart absolu max sur 400 itérations = 5.862e-14
  déviance calculée à la main : minimum sur les 222 itérations entraînées au premier jet à l'itération 122 (déviance 100 796.4) ; minimum sur 400 itérations : 122 (déviance 100 796.4)
  déviance à l'itération retenue 122 : 100 796.4 ; sans offset en validation (illustration) : 163 013.5

Cible tous : hyperparamètres {learning_rate=0.02, num_leaves=7, min_data_in_leaf=100, lambda_l2=10.0}, itération retenue au premier jet = 113
  r_fit = 0.00757382 (taux des lignes 2010-2017) ; log(r_fit) = -4.883057
  métrique LightGBM « poisson » (validation) = moyenne de (mu - y log mu) calculée à la main : écart absolu max sur 400 itérations = 7.461e-14
  déviance calculée à la main : minimum sur les 213 itérations entraînées au premier jet à l'itération 113 (déviance 116 946.9) ; minimum sur 400 itérations : 113 (déviance 116 946.9)
  déviance à l'itération retenue 113 : 116 946.9 ; sans offset en validation (illustration) : 207 750.2
```

**Conclusion** : La validation reçoit son propre init_score = log(e) + log(r_fit), r_fit étant le taux des lignes d'ajustement 2010-2017 ; la métrique d'arrêt précoce de LightGBM coïncide avec la log-vraisemblance négative recalculée à la main avec cet offset, et l'itération qui minimise la déviance calculée à la main (dans la fenêtre réellement entraînée) est celle retenue. Aucun nouveau réglage n'est nécessaire : les ablations réutilisent les hyperparamètres du premier jet.

## VC2 Contrôle croisé de M3 (binomial négatif) : **CONFORME**

Commande : `Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)`, fonction `vc2_binomial_negatif`.

```text

Cible payes : alpha (M3, exact) = 6.126863
  coefficients GLM NegativeBinomial(alpha fixé) vs M3 :
                            GLM_NB_alpha_fixe  M3_NegativeBinomial  ecart_absolu
const                               -4.732274            -4.732276  1.450000e-06
zone_V*                              0.470674             0.470674  2.600000e-07
zone_A*                              0.218698             0.218698  3.300000e-07
couverture_k$                       -0.004331            -0.004331  0.000000e+00
log1p_hist_per_1000                  0.062615             0.062615  6.000000e-08
log1p_county_hist_per_1000           0.156689             0.156689  9.000000e-08
  log-vraisemblance : GLM -18337.9234 ; M3 -18337.9234 ; écart 1.310e-10
  M3 sur l'entraînement : Σ(y-μ) = -83 884.49 ; Σ(y-μ)/(1+αμ) = 0.000000 ; Σμ/Σy = 1.9436
  NB constante + offset seuls : converge = True, alpha = 6.5471, Σμ/Σy = 2.6366

Cible tous : alpha (M3, exact) = 4.239792
  coefficients GLM NegativeBinomial(alpha fixé) vs M3 :
                            GLM_NB_alpha_fixe  M3_NegativeBinomial  ecart_absolu
const                               -4.363723            -4.363724  1.010000e-06
zone_V*                              0.552272             0.552272  2.100000e-07
zone_A*                              0.191602             0.191603  2.100000e-07
couverture_k$                       -0.003823            -0.003823  0.000000e+00
log1p_hist_per_1000                  0.063169             0.063169  4.000000e-08
log1p_county_hist_per_1000           0.116535             0.116535  7.000000e-08
  log-vraisemblance : GLM -22074.7388 ; M3 -22074.7388 ; écart 6.185e-11
  M3 sur l'entraînement : Σ(y-μ) = -104 822.12 ; Σ(y-μ)/(1+αμ) = -0.000000 ; Σμ/Σy = 1.8516
  NB constante + offset seuls : converge = True, alpha = 4.4931, Σμ/Σy = 2.4107
```

**Conclusion** : Le GLM NegativeBinomial à α fixé reproduit M3 (écart maximal sur les coefficients 1.4e-06). Sur l'entraînement, Σ(y-μ)/(1+αμ) est nul (équation du score de la constante en NB2, lien log) tandis que Σ(y-μ) ne l'est pas : Σμ/Σy = 1.944 (payés), 1.852 (tous). Cela étaye la première partie du § 7.2 (l'estimateur NB2 n'impose pas l'égalité des totaux). Avec la constante et l'offset seuls, Σμ/Σy vaut déjà 2.637 (payés) : l'écart de niveau existe sans aucune variable. Le rôle précis de la valeur de α n'est pas isolé par ce calcul (non démontré).

## VC3 Zone × temps et système de tarification : **ÉCART**

Commande : `Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)`, fonction `vc3_zone_temps`.

```text
Par année et par zone (ds_clean, 22 485 lignes) :
 year zone   exposition  payes  tous  taux_payes_1000  taux_tous_1000  part_exposition  part_payes  part_tous
 2010   A* 1063892.9695   3813  4895           3.5840          4.6010           0.6307      0.6585     0.6556
 2010   V*   21936.8715     18    32           0.8205          1.4587           0.0130      0.0031     0.0043
 2010    X  601044.9333   1959  2539           3.2593          4.2243           0.3563      0.3383     0.3401
 2011   A* 1040459.6665   8191 10783           7.8725         10.3637           0.6260      0.8739     0.8495
 2011   V*   22285.4298     61   113           2.7372          5.0706           0.0134      0.0065     0.0089
 2011    X  599265.1521   1121  1797           1.8706          2.9987           0.3606      0.1196     0.1416
 2012   A* 1034341.4381   3010  4807           2.9101          4.6474           0.6237      0.5839     0.6044
 2012   V*   22428.2323    239   326          10.6562         14.5353           0.0135      0.0464     0.0410
 2012    X  601605.9761   1906  2821           3.1682          4.6891           0.3628      0.3697     0.3547
 2013   A* 1030454.2846   1235  1980           1.1985          1.9215           0.6163      0.4879     0.5059
 2013   V*   22395.3786     10    28           0.4465          1.2503           0.0134      0.0040     0.0072
 2013    X  619134.9209   1286  1906           2.0771          3.0785           0.3703      0.5081     0.4870
 2014   A* 1015346.5958   1619  2478           1.5945          2.4405           0.5954      0.4147     0.4497
 2014   V*   22009.4362     42    78           1.9083          3.5439           0.0129      0.0108     0.0142
 2014    X  667985.5580   2243  2954           3.3579          4.4223           0.3917      0.5745     0.5361
 2015   A*  907241.2503   4416  6116           4.8675          6.7413           0.5777      0.6640     0.6547
 2015   V*   21690.7071     92   183           4.2414          8.4368           0.0138      0.0138     0.0196
 2015    X  641382.1320   2143  3043           3.3412          4.7444           0.4084      0.3222     0.3257
 2016   A*  845794.4003  11583 15372          13.6948         18.1746           0.5688      0.7595     0.7368
 2016   V*   21466.2617    751  1133          34.9851         52.7805           0.0144      0.0492     0.0543
 2016    X  619704.5549   2917  4357           4.7071          7.0308           0.4168      0.1913     0.2088
 2017   A*  817809.4928  15913 23205          19.4581         28.3746           0.5567      0.7905     0.7724
 2017   V*   20698.0612    730  1034          35.2690         49.9564           0.0141      0.0363     0.0344
 2017    X  630545.0792   3487  5805           5.5301          9.2063           0.4292      0.1732     0.1932
 2018   A*  791830.6583  11736 13983          14.8214         17.6591           0.5297      0.6884     0.6605
 2018   V*   19825.9784   1019  1454          51.3972         73.3381           0.0133      0.0598     0.0687
 2018    X  683121.7540   4292  5732           6.2829          8.3909           0.4570      0.2518     0.2708
 2019   A*  772436.8857   2301  2985           2.9789          3.8644           0.5226      0.7505     0.7231
 2019   V*   19047.3615     54    71           2.8350          3.7276           0.0129      0.0176     0.0172
 2019    X  686451.5169    711  1072           1.0358          1.5617           0.4645      0.2319     0.2597
 2020   A*  768363.7942   8812 11189          11.4685         14.5621           0.5260      0.7371     0.7155
 2020   V*   18421.2428    855  1155          46.4138         62.6994           0.0126      0.0715     0.0739
 2020    X  673944.9363   2288  3295           3.3949          4.8891           0.4614      0.1914     0.2107
 2021   A*  765188.9721   2128  2720           2.7810          3.5547           0.5332      0.6406     0.6263
 2021   V*   18037.0334     35    43           1.9405          2.3840           0.0126      0.0105     0.0099
 2021    X  651907.4348   1159  1580           1.7779          2.4237           0.4542      0.3489     0.3638
 2022   A*  745555.0733  27527 33260          36.9215         44.6111           0.5496      0.9023     0.8782
 2022   V*   18789.4768    889  1091          47.3137         58.0644           0.0139      0.0291     0.0288
 2022    X  592127.4213   2091  3521           3.5313          5.9464           0.4365      0.0685     0.0930
 2023   A*  727451.1659   7011  8286           9.6378         11.3905           0.5680      0.9148     0.8938
 2023   V*   19118.4413    232   285          12.1349         14.9071           0.0149      0.0303     0.0307
 2023    X  534175.9002    421   700           0.7881          1.3104           0.4171      0.0549     0.0755
 2024   A*  749062.2720  50277 56942          67.1199         76.0177           0.5832      0.9119     0.9011
 2024   V*   19577.7263   1861  2173          95.0570        110.9935           0.0152      0.0338     0.0344
 2024    X  515768.5392   2998  4076           5.8127          7.9028           0.4016      0.0544     0.0645

Taux pour 1 000 polices-années, entraînement vs test :
      taux_payes_train  taux_payes_test  multiplicateur_payes  taux_tous_train  taux_tous_test  multiplicateur_tous
zone                                                                                                               
A*               6.848           25.496                 3.723            9.293          29.928                3.221
V*              14.108           41.216                 2.922           20.825          50.530                2.426
X                3.475            3.018                 0.869            5.043           4.438                0.880

Regroupement défini dans Data_cleaning/clean/clean_data.py (CONFIG) :
"flood_zone_groups": {
        "A*": ["A", "AE", "A99", "AH", "AHB", "AO", "AOB", "AR", "ARE", "ARH", "ARO", "ARA"]
              + [f"A{i}" for i in range(1, 31)] + [f"A{i:02d}" for i in range(1, 10)],
        "V*": ["V", "VE"] + [f"V{i}" for i in range(1, 31)] + [f"V{i:02d}" for i in range(1, 10)],
        "X": ["X", "B", "C"],   # B et C : anciennes appellations des zones X (dictionnaire v3)
        "D": ["D"],
    },
   "flood_zone_other": "autre",
   ZONES = ["V*", "A*", "X"]
   no_zone = (~c["zone"].isin(ZONES)).mean()
   c = c[c["zone"].isin(ZONES)]
   e = e[e["zone"].isin(ZONES)]

Colonnes de zone dans claims_clean.parquet : flood_zone_group uniquement (pas de ratedFloodZone brut).
Fichier brut lu (agrégation seulement) : NfipClaimsV3_SE.parquet, restreint aux id de claims_clean, années 2010-2024 (254550 sinistres).
Part des principaux codes bruts par année :
code      AE       X      AH     AHB       A      VE       C     A05     A06       B     A07     A08
year                                                                                                
2010  0.4454  0.2712  0.0036  0.0243  0.0779  0.0039  0.0444  0.0071  0.0210  0.0239  0.0033  0.0047
2011  0.6199  0.1195  0.0069  0.0189  0.0400  0.0076  0.0143  0.0495  0.0370  0.0071  0.0115  0.0082
2012  0.3197  0.2678  0.0226  0.0866  0.0472  0.0369  0.0554  0.0050  0.0036  0.0313  0.0030  0.0261
2013  0.3512  0.4358  0.0089  0.0384  0.0699  0.0066  0.0358  0.0023  0.0020  0.0132  0.0028  0.0036
2014  0.3277  0.5016  0.0047  0.0223  0.0364  0.0121  0.0183  0.0060  0.0089  0.0161  0.0132  0.0049
2015  0.5317  0.2978  0.0049  0.0075  0.0539  0.0108  0.0169  0.0083  0.0033  0.0104  0.0060  0.0031
2016  0.6149  0.1754  0.0019  0.0020  0.0210  0.0499  0.0241  0.0065  0.0035  0.0083  0.0281  0.0069
2017  0.6697  0.1835  0.0357  0.0229  0.0196  0.0334  0.0048  0.0024  0.0008  0.0041  0.0028  0.0024
2018  0.5910  0.2529  0.0018  0.0016  0.0248  0.0648  0.0075  0.0038  0.0058  0.0033  0.0011  0.0033
2019  0.6303  0.2462  0.0136  0.0041  0.0519  0.0168  0.0081  0.0065  0.0010  0.0036  0.0012  0.0007
2020  0.6096  0.2060  0.0496  0.0115  0.0243  0.0723  0.0030  0.0007  0.0019  0.0021  0.0019  0.0033
2021  0.5399  0.3519  0.0062  0.0007  0.0696  0.0099  0.0085  0.0000  0.0011  0.0034  0.0002  0.0021
2022  0.8435  0.0922  0.0054  0.0006  0.0222  0.0288  0.0003  0.0002  0.0000  0.0005  0.0001  0.0016
2023  0.7506  0.0752  0.1224  0.0061  0.0131  0.0304  0.0003  0.0000  0.0000  0.0000  0.0000  0.0000
2024  0.8794  0.0641  0.0019  0.0001  0.0156  0.0342  0.0003  0.0000  0.0000  0.0001  0.0001  0.0000
Codes présents seulement jusqu'en 2021 : ['A02', 'A18', 'A19', 'A20', 'A21', 'A23', 'A25', 'D', 'NA', 'V', 'V04', 'V05', 'V07', 'V08', 'V10', 'V11', 'V14', 'V19', 'V21'] ; seulement à partir de 2022 : aucun ; parmi eux, part annuelle max ≥ 1 % : ['NA']
Groupes de claims_clean par année (y compris D, autre, NA) :
flood_zone_group     A*  D    V*     X
year                                  
2010               4895  0    32  2540
2011              10813  1   113  1798
2012               4809  0   326  2823
2013               1982  0    28  1908
2014               2479  1    78  2958
2015               6123  0   183  3046
2016              15387  0  1139  4365
2017              23228  3  1036  5813
2018              14003  0  1462  5737
2019               3003  0    71  1078
2020              11202  2  1155  3310
2021               2724  1    43  1583
2022              33261  0  1091  3522
2023               8286  0   285   700
2024              56943  0  2173  4076

Part des sinistres (tous) codés Risk Rating 2.0, par année et par zone :
flood_zone_group     A*     V*      X
year                                 
2010              0.107  0.188  0.061
2011              0.208  0.372   0.21
2012              0.217  0.521  0.118
2013              0.229  0.357  0.109
2014              0.277   0.41  0.177
2015              0.325   0.18  0.227
2016              0.392  0.357  0.276
2017              0.502  0.508  0.309
2018              0.564  0.679  0.409
2019              0.586  0.775  0.392
2020              0.709  0.824  0.504
2021              0.746  0.884  0.581
2022              0.964  0.971  0.931
2023                1.0    1.0  0.997
2024                1.0    1.0    1.0
Exposition par système de tarification : non disponible dans les fichiers propres (zone_year.parquet n'a pas cette ventilation) ; rien n'est reconstruit.
```

**Conclusion** : Taux de sinistres payés, test / entraînement : V* × 2.92, A* × 3.72, X × 0.87. Des codes bruts représentant au moins 1 % d'une année apparaissent ou disparaissent autour de fin 2021 : un changement de codage est une hypothèse à vérifier (voir la sortie). La part Risk Rating 2.0 est tabulée par année et zone ; aucune cause n'est attribuée.

## VC4 Les 13 lignes exclues : **CONFORME**

Commande : `Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)`, fonction `vc4_lignes_exclues`.

```text
county_id zone  year period  exposure_years  n_claims  n_all  hist_per_1000  county_hist_per_1000
    13197   A*  2021   test        0.947296         0      0            NaN                   NaN
    13197   A*  2022   test        0.999316         0      0            NaN                   NaN
    13197   A*  2023   test        0.999316         0      0            NaN                   NaN
    13197   A*  2024   test        1.002050         0      0            NaN                   NaN
    13197    X  2020   test        0.380561         0      0            NaN                   NaN
    13197    X  2021   test        1.618070         0      0            NaN                   NaN
    13239   A*  2022   test        0.435318         0      0            NaN                 0.000
    13239   A*  2023   test        0.999316         0      0            NaN                 0.000
    13239   A*  2024   test        1.002050         0      0            NaN                 0.000
    13307   A*  2023   test        0.544832         0      0            NaN                   NaN
    13307   A*  2024   test        1.002050         0      0            NaN                   NaN
    37081   V*  2021   test        0.596851         0      0            NaN               176.578
    37081   V*  2022   test        0.402464         0      0            NaN               176.578

Toutes en test : True ; aucun sinistre (payés et tous) : True ; part de l'exposition du test : 1.603e-06
cible modele  deviance_test_avec_13  deviance_test_sans_13  ecart_relatif
payes     M0          547574.875186          547574.752845   2.234234e-07
payes     M1          508724.842413          508724.691703   2.962495e-07
 tous     M0          592663.685653          592663.516268   2.858027e-07
 tous     M1          551747.127512          551746.918321   3.791425e-07
```

**Conclusion** : Les 13 lignes sont toutes en test, sans aucun sinistre, et pèsent 1.6e-06 de l'exposition du test. Les inclure change la déviance de test de M0 et M1 d'au plus 3.8e-07 en relatif : exclusion négligeable.

Durée : 4.3 s.
