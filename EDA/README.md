# EDA : fréquence des sinistres inondation (NFIP, Région IV de FEMA)

Analyse exploratoire au service de la question de recherche du projet : **un modèle LightGBM
(Poisson) prédit-il mieux la fréquence des sinistres qu'un GLM de Poisson ou binomial négatif ?**
La fréquence est le nombre de sinistres payés rapporté au nombre de polices en vigueur
(polices-années). Entraînement 2010-2019, test 2020-2024.

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `ds_clean.csv` | Le dataset d'analyse : une ligne par comté × zone d'inondation × année, 2010-2024 |
| `ds_clean_roles.json` | Rôle et définition de chaque colonne, sinistres écartés, 10 plus gros événements |
| `eda.py` | L'EDA : lit `ds_clean.csv`, écrit les figures et les tableaux dans `EDA/figures/` |
| `build_ds_clean.py` | Construit `ds_clean.csv` à partir des données nettoyées |

## Lancer

```bash
python3 EDA/eda.py              # l'EDA (le CSV est versionné, rien à reconstruire)
python3 EDA/build_ds_clean.py   # seulement si les données nettoyées changent
```

Sorties dans `EDA/figures/` : `eda_1` à `eda_6` (PNG et PDF), `eda_key_numbers.json` (tous les
chiffres cités dans le rapport), `eda_by_year.csv`, `eda_by_state.csv`,
`eda_unit_year_summary.csv`.

## Le dataset `ds_clean`

### Construction

`build_ds_clean.py` part de deux fichiers déjà nettoyés et versionnés (maisons individuelles,
Région IV) :

- `Data_cleaning/clean/claims_clean.parquet` : une ligne par sinistre ;
- `Data_cleaning/clean/zone_year.parquet` : exposition des polices par zone × comté × année.

Sinistres et polices sont anonymisés et n'ont aucun identifiant commun : on ne peut pas relier un
sinistre à sa police. Le script fait donc deux comptages indépendants, ramenés au même niveau
(comté × zone × année), puis les met côte à côte :

1. **Exposition** : somme des polices-années par comté, zone et année, et couverture moyenne.
2. **Sinistres** : nombre de sinistres avec un montant bâtiment payé > 0 (la cible), nombre total
   de sinistres, sinistres des 10 plus gros événements.
3. **Jointure** : une cellule avec des polices mais sans sinistre reçoit 0 (c'est un vrai zéro).
4. **Historique** : sinistres payés 1990-2008, par cellule et par comté, rapportés aux polices
   moyennes de 2010-2019 (aucune information de la période de test).
5. **Contrôles et vérifications** : période, fréquence brute, faible exposition ; ni doublon, ni
   comté hors Région IV.

Aucune valeur n'est imputée ni modifiée : on compte et on additionne. Les totaux sont conservés à
99,5 % pour les sinistres payés et 99,7 % pour l'exposition. L'écart correspond aux sinistres sans
comté (0,08 %) ou en zone D ou sans zone (0,37 %), exclus volontairement.

### Pourquoi comté × zone × année

- Une fréquence demande le numérateur (sinistres, seulement dans `claims_clean`) et le
  dénominateur (polices, seulement dans `zone_year`) sur la même ligne.
- C'est le niveau le plus fin commun aux deux fichiers disponibles.
- Garder la zone comme dimension conserve le facteur de risque le plus net. Moyennée par comté,
  la zone n'est presque plus liée à la fréquence (ρ = 0,07 contre un écart de 1 à 4 entre zones).
- Il n'y a pas d'exposition avant 2009 : pas de fréquence calculable avant.

C'est la version comté × zone de la table par secteur de recensement prévue par le CLAUDE.md
(`tract_year.parquet`), qui demande les fichiers bruts.

### Colonnes

| Rôle | Colonnes |
|---|---|
| Identifiants | `county_id` (FIPS, 5 caractères, à lire comme texte), `zone` (V*, A*, X), `year`, `state` |
| Cible | `n_claims` : sinistres avec montant bâtiment payé > 0 |
| Offset | `exposure_years` : polices-années en vigueur |
| Variables du modèle | `zone`, `coverage_real` (couverture moyenne en USD constants de 2024, à utiliser dans les modèles), `mean_coverage` (USD nominaux, monte avec les prix : sert d'année déguisée, à éviter), `hist_claims_1990_2008`, `hist_per_1000`, `county_hist_per_1000` |
| Contrôles (jamais en entrée du modèle) | `period`, `n_all`, `n_major`, `major_event_share`, `freq_per_1000`, `low_exposure`, `partial_year`, `n_policy_rows` |

Ni l'année ni les primes ne sont des variables du modèle (règles du CLAUDE.md). Lire le CSV en
Python : `pd.read_csv("EDA/ds_clean.csv", dtype={"county_id": str})`.

Effectifs : 22 485 lignes, 734 comtés, 1 533 cellules comté × zone, 197 482 sinistres payés,
22,7 M de polices-années (14 999 lignes en entraînement, 7 486 en test).

## Conclusions de l'EDA

Chiffres issus de `EDA/figures/eda_key_numbers.json`.

**C1. Le risque est piloté par des catastrophes, pas par le portefeuille** (`eda_1`). L'exposition
est stable (de 1,69 M à 1,28 M de polices-années, −24 %), mais la fréquence annuelle varie d'un
facteur 28 : de 1,5 sinistre pour 1 000 polices en 2013 à 42,9 en 2024. Les pics correspondent aux
ouragans (Matthew, Irma, Florence, Ian, Helene).

**C2. Les sinistres sont extrêmement concentrés** (`eda_3`). 1 % des comtés-zones-années
concentrent 78 % des sinistres payés, et les 10 plus gros événements 71 %.

**C3. Les comptes sont fortement surdispersés** (`eda_2`). 73 % des comtés-zones-années n'ont aucun
sinistre, le maximum atteint 17 701. La dispersion vaut 126 à année et zone fixées (1 sous
Poisson), α du binomial négatif ≈ 2,3. Le Poisson simple est inadapté : cela justifie la
comparaison avec le binomial négatif et LightGBM.

**C4. La zone d'inondation est le facteur de risque le plus net** (`eda_4`). Pour 1 000
polices-années en entraînement : V 14,1, A 6,8, X 3,5. Classement V > A > X sur les deux périodes.
La zone V ne représente que 1,4 % des polices.

**C5. L'historique porte du signal, la couverture peu** (`eda_5`, années d'entraînement
uniquement). Sinistres 1990-2008 pour 1 000 polices : ρ = 0,35 dans la même cellule, 0,33 pour le
comté. Couverture moyenne : ρ = −0,18.

**C6. La période de test ne ressemble pas à l'entraînement** (`eda_3`, `eda_6`). Le test concentre
55 % des sinistres pour 30 % de l'exposition, et la fréquence passe de 5,6 à 15,9. Les lieux
touchés changent : la persistance de la fréquence d'une cellule entre périodes n'est que de
ρ = 0,11. La Floride passe de 2,8 à 20,0, la Caroline du Nord de 24,3 à 6,9. Tous les modèles
devraient avoir des scores faibles et sous-estimer le niveau du test : il faut les comparer sur le
classement et la calibration, pas seulement sur une erreur globale.

**C7. Compter des sinistres sans les polices induit en erreur** (justification de la fusion). La
zone V fait 3 % des sinistres mais c'est la plus risquée. La Floride a le plus de sinistres (35 %)
mais la fréquence la plus basse sur 2010-2019 (8e sur 8 États).

## Ce qui va dans le rapport

### À inclure absolument

| Section | Contenu |
|---|---|
| Data | Construction de `ds_clean` (deux comptages agrégés puis joints), unité, période, effectifs, pertes (0,45 % des sinistres), cible et offset |
| Data | L'argument C7 pour justifier la fusion |
| EDA, univarié | `eda_1` (C1), `eda_2` (C3), `eda_3` (C2) |
| EDA, bivarié | `eda_4` (C4) |
| EDA, corrélation | `eda_6` (C6) |
| Key Findings | Conclusions numérotées, chacune avec sa figure et sa conséquence pour le modèle |
| Limites | Niveau comté × zone en attendant les secteurs ; population assurée uniquement ; exposition seulement depuis 2009 |

Chaque figure doit être interprétée (ce qu'on voit, pourquoi c'est important, conséquence pour le
modèle), et les chiffres du texte doivent venir du code (`eda_key_numbers.json`).

### Optionnel

- `eda_5` (variables candidates) : une phrase dans le corps, la figure peut aller en annexe.
- Le panneau (a) de `eda_6` (fréquence par État) : illustre C6, le panneau (b) porte le message.
- Les tableaux `eda_by_year.csv` et `eda_by_state.csv`.
- Un test formel de surdispersion (Cameron-Trivedi) ; la statistique de dispersion de Pearson
  remplit déjà le rôle de test statistique.
- L'ancienne analyse au niveau du sinistre (montants, paiement) : hors question de recherche.

## Limites

- Niveau comté × zone : moins fin que le secteur de recensement prévu, donc moins de zéros et une
  zone moyennée à l'intérieur du comté pour les autres variables.
- Population assurée uniquement (le NFIP n'est obligatoire qu'en zone à risque).
- Exposition disponible seulement depuis 2009.
- `mean_coverage` est en dollars nominaux (+19 % de 2010 à 2024). `coverage_real` la déflate avec
  le CPI de l'année précédente (−16 % sur la même période) : c'est elle qu'il faut donner aux modèles.
- Hors des dix plus grands événements, la fréquence est stable (2,3 pour 1 000 en entraînement,
  2,9 en test) : voir la ligne orange du panneau (c) de la figure 1.
- Avant 2018, la plupart des sinistres « non payés » viennent d'un montant vide recodé en 0 au
  nettoyage ; la cible (montant payé > 0) n'en dépend pas, le compte `n_all` si.
