# Vérifications (phase 1)

> Générées par `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)` le 15/11/2026 à 18:57:53 CET. Chaque section donne la fonction exécutée (dans le script), sa sortie brute et le statut. Graine : 42.

## Synthèse

| contrôle | intitulé | type | statut | remarques |
|---|---|---|---|---|
| V1 | Intégrité de la table | BLOQUANT | RÉUSSI | 2 |
| V2 | Exposition | BLOQUANT | RÉUSSI | 1 |
| V3 | Fuite temporelle des historiques | BLOQUANT | RÉUSSI | 3 |
| V4 | Cible | BLOQUANT | RÉUSSI | 1 |
| V5 | Dépendances | BLOQUANT | RÉUSSI | 2 |
| V6 | Variables | NON BLOQUANT | RÉUSSI | 2 |
| V7 | Dérive entre entraînement et test | NON BLOQUANT | RÉUSSI | 0 |
| V8 | Cohérence avec le rapport | NON BLOQUANT | RÉUSSI | 0 |

## V1 [BLOQUANT] Intégrité de la table : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v1_integrite`.

```text
Fichier : ds_clean.csv ; lignes = 22485 ; colonnes = 18
Types : {'county_id': 'str', 'zone': 'str', 'year': 'int64', 'state': 'str', 'n_claims': 'int64', 'exposure_years': 'float64', 'mean_coverage': 'float64', 'hist_claims_1990_2008': 'int64', 'hist_per_1000': 'float64', 'county_hist_per_1000': 'float64', 'period': 'str', 'n_all': 'int64', 'n_major': 'int64', 'major_event_share': 'float64', 'freq_per_1000': 'float64', 'low_exposure': 'bool', 'partial_year': 'bool', 'n_policy_rows': 'int64'}
Valeurs manquantes par colonne (non nulles) : {'hist_per_1000': 13, 'county_hist_per_1000': 8}
Doublons de la clé (county_id, zone, year) : 0
Années : [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
Années train 2010–2019 ; test 2020–2024 ; chevauchement : aucun
`period` cohérent avec TRAIN=(2010, 2019) / TEST=(2020, 2024) : True
Effectifs : train 14999, test 7486
  rôle de zone dans ds_clean_roles.json : features
  rôle de mean_coverage dans ds_clean_roles.json : features
  rôle de hist_per_1000 dans ds_clean_roles.json : features
  rôle de county_hist_per_1000 dans ds_clean_roles.json : features
  rôle de n_claims : target ; exposure_years : offset ; n_all : controls
```

Remarques :

- n_all a le rôle « controls » dans ds_clean_roles.json (compte de sensibilité), pas « target » : son usage comme seconde cible suit la consigne (V4), écart signalé.
- zone figure à la fois dans « id » et « features » de ds_clean_roles.json (rôle double, cohérent).

## V2 [BLOQUANT] Exposition : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v2_exposition`.

```text
Exposition finie partout : True ; négative : 0 ; nulle : 0
Distribution (min, P1, P5, P50, P95, P99, max) : [0.0027, 0.8757, 2.0041, 43.0609, 3579.3, 19106.936, 231235.0]
Lignes < 0,5 police-année : 108 (0.48% des lignes), exposition 29.57 (0.00013%), sinistres payés 1, tous 1
Exclusion pour le log (exposition ≤ 0) : 0 lignes (0.00%), exposition 0.00%
Seuil d'exclusion des expositions très faibles : aucun (décision pré-enregistrée, PROTOCOLE § 3).
```

Remarques :

- 108 lignes ont moins de 0,5 police-année ; elles sont gardées (aucun seuil), avec 1 sinistres payés.

## V3 [BLOQUANT] Fuite temporelle des historiques : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v3_fuite_historiques`.

```text
build_ds_clean.py : HIST = (1990, 2008)
  ligne : h = claims[claims["year"].between(*HIST) & claims["paid"] & claims["county"].notna()]
  ligne : avg_cz = d[train].groupby(["county", "zone"])["exposure_years"].mean()
  ligne : avg_c = d[train].groupby(["county", "year"])["exposure_years"].sum().groupby("county").mean()
  ligne : d["hist_per_1000"] = 1000 * d["hist_claims_1990_2008"] / avg_cz.reindex(cz).to_numpy()
  ligne : d["county_hist_per_1000"] = 1000 * d["county"].map(hist_c).fillna(0) / d["county"].map(avg_c)
  ligne : claims["year"] = num(claims["loss_year"]).astype(int)
  ligne : claims["paid"] = num(claims["paid_building_real"]) > 0
Colonnes de claims_clean utilisées : loss_year (année de survenue), paid_building_real, county_fips, flood_zone_group
Dénominateur : moyenne de exposure_years (polices-années) des lignes d'entraînement 2010–2019 présentes pour la cellule ; cellules avec moins de 10 années présentes : 80 sur 1528
Recalcul avec les sinistres 1990–2008 (définition du script) :
  hist_claims_1990_2008 : lignes différentes (écart relatif > 1e-5 ou NA différent) = 0 ; écart absolu max = 0
  hist_per_1000 : lignes différentes (écart relatif > 1e-5 ou NA différent) = 0 ; écart absolu max = 0.00532141
  county_hist_per_1000 : lignes différentes (écart relatif > 1e-5 ou NA différent) = 0 ; écart absolu max = 0.00501689
Recalcul avec tous les sinistres de survenue < 2010 (1978–2009), comme demandé :
  hist_per_1000 (<2010) : lignes différentes (écart relatif > 1e-5 ou NA différent) = 11788 ; écart absolu max = 6198.76
  county_hist_per_1000 (<2010) : lignes différentes (écart relatif > 1e-5 ou NA différent) = 16956 ; écart absolu max = 3536.25
  (les écarts de ce second recalcul viennent de la fenêtre 1990–2008 du script, plus étroite que « < 2010 », pas d'une fuite)
```

Remarques :

- Les sinistres qui alimentent les historiques sont ceux de 1990–2008 (aucune année ≥ 2010) : pas de fuite par le numérateur.
- Le dénominateur est l'exposition moyenne 2010–2019 de la cellule (ou du comté). Pour une ligne d'entraînement, il utilise donc l'exposition d'années postérieures à la ligne, et pour la validation interne de LightGBM (2018–2019) l'exposition des années de validation. Ce n'est pas une information de sinistres, mais c'est une légère information future : signalé, non bloquant selon la règle V3 (qui porte sur les années de sinistres).
- La moyenne porte sur les années présentes de la cellule, pas sur 10 ans fixes.

## V4 [BLOQUANT] Cible : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v4_cible`.

```text
Colonnes de comptage : ['n_claims', 'n_all', 'n_major'] (n_policy_rows exclue : nombre de lignes de police)
  n_claims : claims with a positive building paid amount (real USD > 0)
  n_all : all claims, paid or not (sensitivity count)
  n_major : paid claims from the 10 largest named events of 2010-2024
Colonne « tous les sinistres » présente : True -> pas de reconstruction (Modeles/scripts/construire_cible_tous.py non nécessaire)
      n_claims  n_all  tous_>=_payes
year                                
2010      5790   7466           True
2011      9373  12693           True
2012      5155   7954           True
2013      2531   3914           True
2014      3904   5510           True
2015      6651   9342           True
2016     15251  20862           True
2017     20130  30044           True
2018     17047  21169           True
2019      3066   4128           True
2020     11955  15639           True
2021      3322   4343           True
2022     30507  37872           True
2023      7664   9271           True
2024     55136  63191           True
n_all >= n_claims sur toutes les lignes : True
```

Remarques :

- Cible « tous » = n_all : tous les sinistres de la cellule, payés ou non, issus de claims_clean (maisons individuelles, hors anomalies du nettoyage, avec comté et zone V*/A*/X). Avant 2018 environ, la plupart des non-payés viennent d'un paiement NA recodé en 0 au nettoyage.

## V5 [BLOQUANT] Dépendances : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v5_dependances`.

```text
Versions : {'pandas': '3.1.1', 'numpy': '2.5.4', 'scipy': '1.18.1', 'statsmodels': '0.15.0', 'lightgbm': '4.7.0', 'matplotlib': '3.11.2', 'pyarrow': '26.0.1', 'sklearn': '1.9.1'}
DYLD_FALLBACK_LIBRARY_PATH = Modeles/.venv/lib/python3.13/site-packages/sklearn/.dylibs (relatif à la racine du dépôt)
GLM Poisson (statsmodels, offset) sur 100 lignes : converge = True, somme prédite 176.000 / observée 176
(a) init_score = log(e) : somme prédite 6852.784 / observée 176 ; variable constante -> 1 arbre(s), score brut [0.]
(b) init_score = log(e) + log(r) : somme prédite 176.897 / observée 176 (ratio 1.0051)
    contrôle variable constante : écart relatif max avec M0 = 7.93e-16
```

Remarques :

- LightGBM 4.7.0 ne se charge pas sans la bibliothèque système libomp (absente : Homebrew n'est pas installé). Contournement local, sans installation globale : la copie de libomp fournie dans le paquet scikit-learn de Modeles/.venv est désignée par DYLD_FALLBACK_LIBRARY_PATH (positionné par run_all.sh). Solution standard : `brew install libomp`.
- (a) montre pourquoi la procédure initiale ne convient pas : avec un init_score, LightGBM désactive boost_from_average, et une variable constante ne produit qu'un arbre trivial sans coupure (score brut 0). Le modèle part de 1 sinistre par police-année et ne rattrape pas l'intercept en 50 itérations (pas plafonné par poisson_max_delta_step). (b) est la procédure de l'avenant n° 1 de PROTOCOLE.md : elle reproduit M0 exactement avec une variable constante, et la somme observée à moins de 1 % près.

## V6 [NON BLOQUANT] Variables : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v6_variables`.

```text
Lignes exclues par la préparation (PROTOCOLE § 3) : {'lignes_total': 22485, 'exposition_nulle_ou_invalide': 0, 'variable_manquante': 13, 'lignes_gardees': 22472, 'sinistres_payes_exclus': 0, 'sinistres_tous_exclus': 0, 'exposition_exclue': 10.92949}
Manquants par variable (table complète) : {'zone': 0, 'mean_coverage': 0, 'hist_per_1000': 13, 'county_hist_per_1000': 8}
Années et période des lignes à variable manquante : {(2021, 'test'): 3, (2022, 'test'): 3, (2023, 'test'): 3, (2024, 'test'): 3, (2020, 'test'): 1}
Distribution (entraînement) :
                        count        mean        std     min         1%       5%         50%         95%        99%        max
mean_coverage         14999.0  148448.399  48512.729  2400.0  35408.106  64698.0  152416.000  220941.100  239534.42  250000.00
hist_per_1000         14999.0     205.967    479.522     0.0      0.000      0.0      71.387     774.158    1722.85    9722.00
county_hist_per_1000  14999.0     195.581    335.926     0.0      0.000      0.0      94.721     662.745    1160.96    4920.01
Corrélation de Pearson (entraînement) :
                      mean_coverage  hist_per_1000  county_hist_per_1000
mean_coverage                 1.000         -0.086                -0.127
hist_per_1000                -0.086          1.000                 0.594
county_hist_per_1000         -0.127          0.594                 1.000
Corrélation de Spearman (entraînement) :
                      mean_coverage  hist_per_1000  county_hist_per_1000
mean_coverage                 1.000         -0.078                -0.128
hist_per_1000                -0.078          1.000                 0.805
county_hist_per_1000         -0.128          0.805                 1.000
Part de hist_per_1000 = 0 (entraînement) : 0.258 ; county_hist_per_1000 = 0 : 0.164
Zones (lignes, exposition) par période :
       lignes       exposition           
period   test train       test      train
zone                                     
A*       3577  7135  3755613.0  9319608.0
V*        320   683    93943.0   213784.0
X        3576  7181  2967922.0  6350242.0
Modalités rares en entraînement (< 2 % de l'exposition) : {'V*': 0.0135}
Modalités du test absentes de l'entraînement : aucune
VIF (matrice GLM, entraînement) : {'zone_V*': np.float64(1.128), 'zone_A*': np.float64(1.241), 'couverture_k$': np.float64(1.227), 'log1p_hist_per_1000': np.float64(3.007), 'log1p_county_hist_per_1000': np.float64(2.917)}
```

Remarques :

- 13 lignes ont une variable explicative manquante et sont exclues de tous les modèles (0 sinistres payés, 0 sinistres au total).
- Zone rare en entraînement : V* (1.3% de l’exposition).

## V7 [NON BLOQUANT] Dérive entre entraînement et test : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v7_derive`.

```text
      payes   tous         expo  taux_payes_1000  taux_tous_1000
year                                                            
2010   5790   7466  1686874.774            3.432           4.426
2011   9373  12693  1662010.248            5.640           7.637
2012   5155   7954  1658375.647            3.108           4.796
2013   2531   3914  1671984.584            1.514           2.341
2014   3904   5510  1705341.590            2.289           3.231
2015   6651   9342  1570314.089            4.235           5.949
2016  15251  20862  1486965.217           10.256          14.030
2017  20130  30044  1469052.633           13.703          20.451
2018  17047  21169  1494778.391           11.404          14.162
2019   3066   4128  1477935.764            2.075           2.793
2020  11955  15639  1460729.593            8.184          10.706
2021   3322   4343  1435130.278            2.315           3.026
2022  30507  37872  1356470.134           22.490          27.920
2023   7664   9271  1280742.964            5.984           7.239
2024  55136  63191  1284405.531           42.927          49.199
Taux train : payés 5.597, tous 7.749 pour 1 000 polices-années
Taux test : payés 15.927, tous 19.115 pour 1 000 polices-années
Part de 2024 dans les sinistres du test : payés 0.508, tous 0.485
Part de l'exposition par zone et par période :
zone        A*      V*       X
period                        
test    0.5509  0.0138  0.4353
train   0.5867  0.0135  0.3998
```

## V8 [NON BLOQUANT] Cohérence avec le rapport : **RÉUSSI**

Commande : `Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)`, fonction `v8_coherence`.

```text
                                                                élément  valeur citée  valeur observée écart
                                                     lignes de ds_clean     22485.000        22485.000   non
                                                           lignes train     14999.000        14999.000   non
                                                            lignes test      7486.000         7486.000   non
                              dispersion_overall (eda_key_numbers.json)       167.390          167.390   non
                          dispersion_within_year (eda_key_numbers.json)       141.240          141.240   non
                     dispersion_within_year_zone (eda_key_numbers.json)       125.880          125.880   non
part de 2024 dans les sinistres payés du test (rapport externe : 0,508)         0.508            0.508   non
                                 fréquence train (eda_key_numbers.json)         5.597            5.597   non
                                  fréquence test (eda_key_numbers.json)        15.927           15.927   non
```

Durée : 1.6 s.
