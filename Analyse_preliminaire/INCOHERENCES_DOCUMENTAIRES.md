# Incohérences documentaires (propositions, rien n'est appliqué)

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir
> `STATUT_RESULTATS.md`** · aucun commit à ce stade.

Chaque point a été vérifié dans le fichier cité, avec son numéro de ligne, le 15/11/2026.

## Statut au 15/11/2026

Les corrections ont d'abord été appliquées (« corrige les incohérences mais ne push rien »). L'équipe a
ensuite demandé d'**annuler celles qui touchaient des fichiers hors de ce qui a été créé pour les
modèles**. Les 11 fichiers suivis concernés ont été restaurés à leur version commitée (`69d0d21`) par
`git restore`. Rien n'est commité ni poussé.

| # | Statut | Fichiers |
|---|---|---|
| 1 à 8, 16 à 18 | **annulé : proposition seulement** (fichier revenu à `69d0d21`) | `quarto_report/` (`report.qmd`, `_analysis.qmd`, `_introduction.qmd`, `_conclusion.qmd`, `_data.qmd`), `requirements.txt`, `README.md`, `CLAUDE.md`, `Data_cleaning/README.md`, `Data_cleaning/clean/README.md`, `Data_cleaning/clean/push_feasibility.md` |
| 9 à 14 | **corrigé et conservé** (fichiers créés sur cette branche pour les modèles, non suivis) | `Modeles/RAPPORT_MODELES.md`, `Modeles/README.md`, `Modeles/complements/RAPPORT_COMPLEMENTS.md` : corrections signalées et datées dans le texte |
| 15 | non appliqué | Hypothèse H2 : ce n'est pas une erreur ; à discuter quand les modèles du projet seront ajustés |

Pour les points annulés, le texte proposé du tableau ci-dessous reste valable. Pour le n° 2
(`requirements.txt`), la version proposée a été testée : `pip install --dry-run` la résout sans conflit dans
un environnement neuf.

## Tableau des incohérences

**Points de la liste de contrôle déjà cohérents, donc non listés** :
- l'arithmétique des anomalies : `cleaning_report.md` donne les motifs (dont la somme fait 2 577) et le
  tableau des combinaisons (2 575 lignes, dont 2 avec deux motifs) ; aucun fichier du dépôt n'écrit 356 ou
  355 ;
- la règle 2 147 483 647 et le seuil de 10 M$ (`Data_cleaning/clean/README.md`, lignes 141 et 142,
  `data_dictionary.csv`, ligne 20) ;
- le nombre d'auteurs dans le rapport : 4, `report.qmd` lignes 4 à 7.

Gravité :
- **élevée** : un lecteur ou un script serait induit en erreur ;
- **moyenne** : une contradiction visible entre documents ;
- **faible** : une formulation ou un détail.

| # | Fichier : ligne | Texte actuel (extrait) | Texte proposé | Gravité |
|---|---|---|---|---|
| 1 | `quarto_report/sections/_analysis.qmd` : 25 | « LightGBM fits gradient boosted trees by minimizing the Poisson negative log-likelihood, with $\log e_{it}$ as initial score. The initial score plays the role of the offset… » | « …with $\log e_{it} + \log \bar r$ as initial score, where $\bar r$ is the claim rate of the training rows: when an initial score is given, LightGBM does not start from the average, and $\log e_{it}$ alone leaves the intercept to the trees. Predictions are $\exp(\text{raw score} + \log e_{it} + \log \bar r)$. » (voir `Modeles/PROTOCOLE.md`, avenant n° 1, et `Modeles/VERIFICATIONS.md`, V5) | **élevée** |
| 2 | `requirements.txt` : 7 et 9 | `numpy==2.5.4` et `scipy==1.15.2` : l'installation échoue, car scipy 1.15.2 exige numpy < 2.5. Absents : `statsmodels`, `lightgbm`, `jupyter` | Remplacer `scipy==1.15.2` par `scipy==1.18.1` et `matplotlib==3.10.1` par `matplotlib==3.11.2` (versions de `Modeles/environnement.txt`) ; ajouter `statsmodels==0.15.0`, `lightgbm==4.7.0` (idem) et `jupyter==1.1.1` (version installée dans `.venv`). Sur macOS, LightGBM requiert `libomp`, à documenter | **élevée** |
| 3 | `quarto_report/report.qmd` : 55 (résumé) ; `sections/_introduction.qmd` : 7 et 18 ; `sections/_conclusion.qmd` : 5 | L'unité est décrite comme « census tract by calendar year » ; RQ1 parle de « tract-year flood claim frequency » | Garder l'objectif « secteur × année », mais ajouter dans le résumé et l'introduction : « The exploratory models of this update are fitted on the county by flood zone by year table (`ds_clean`); the census tract table is planned. » Toutes les analyses chiffrées existantes sont au niveau comté × zone | moyenne |
| 4 | `README.md` (racine) : 7 à 9 | « Modéliser le sinistre bâtiment en deux parties, d'abord la probabilité de paiement puis le montant payé, en comparant un GLM (logistique et Gamma) à du gradient boosting interprété par SHAP. » | « Modéliser la fréquence des sinistres (nombre de sinistres payés par police-année), en comparant un LightGBM à objectif Poisson à des GLM de Poisson et binomial négatif, avec l'exposition en offset. Le projet visait au départ la sévérité et la prime pure ; il a été réorienté parce qu'aucune clé ne relie sinistres et polices. » | moyenne |
| 5 | `Data_cleaning/clean/README.md` : 79, 90, 91 et 114 | Rôles « cible » attribués à `paid_flag` et `paid_building_real` (modèle au niveau du sinistre) | Ajouter une note en tête du § 3 : « Ces rôles décrivent l'objectif initial (paiement puis montant, au niveau du sinistre). Pour l'objectif actuel (fréquence), la cible est le nombre de sinistres à montant payé > 0 par cellule (`n_claims` dans `EDA/ds_clean.csv`). » | moyenne |
| 6 | `CLAUDE.md` : 3 | « Train 2009-2019, test 2020-2024 » | « Train 2010-2019 (2009 is excluded because the policy records start in 2009 and its exposure is understated), test 2020-2024 » (justification déjà donnée dans `_introduction.qmd`, « Training window ») | moyenne |
| 7 | `README.md` (racine) : 39 ; `Data_cleaning/README.md` : 25 et 34 | Lien de téléchargement, procédure et date d'accès « à compléter par Lucas Lhmnn » | `quarto_report/sections/_data.qmd` (lignes 7, 8 et 11) donne déjà les URL des fichiers complets et la date de téléchargement (11/11/2026) : reprendre ces informations dans les deux README après confirmation par Lucas Lehmann. La procédure de filtrage des `*_SE.parquet` reste à fournir | moyenne |
| 8 | `quarto_report/sections/_conclusion.qmd` : 13 | « **Rounded location.** Locations in the redacted data are rounded, so the assignment of records to tracts can be imprecise. » | Le secteur est tiré de `censusGeoid` (`_data.qmd`, lignes 22 et 122), un code, alors que l'arrondi à 0,1° constaté par l'audit porte sur la latitude et la longitude. Proposition : supprimer la limite, ou la reformuler : « Coordinates are rounded in the redacted data; the tract comes from the census block group code and is not affected, unless the team finds otherwise. » | moyenne |
| 9 | `Modeles/RAPPORT_MODELES.md` : 206 et 207 (§ 6, H-c) ; 219 à 222 (§ 7.3) | « Le GLM Poisson complet est pénalisé par la couverture nominale (§ 7.3). » ; « M2 fait moins bien que M1 (zone seule) sur le test. » | Selon `RAPPORT_COMPLEMENTS.md` (§ 8, point 1), qui prévaut, l'essentiel du retard de M2 sur M1 vient des historiques : G1 (sans couverture) reste loin de M1, et G3 (sans historiques) remonte. Proposition : « Le retard de M2 sur M1 vient surtout des historiques (voir l'ablation) ; la couverture nominale y contribue par un effet de niveau. » | moyenne |
| 10 | `Modeles/RAPPORT_MODELES.md` : 219 et 220 | « Elle passe de 203,6 k$ (entraînement) à 222,0 k$ (test) […] facteur 0,904 » | Ces chiffres ne figurent dans aucun CSV ou JSON du dossier `Modeles/`. Proposition : retirer, ou ajouter un fichier de résultats qui les produise. À la place : la tranche de couverture la plus haute passe de 81,0 % à 92,9 % de l'exposition (`Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv`) | moyenne |
| 11 | `Modeles/RAPPORT_MODELES.md` : 106 et 192 ; `Modeles/README.md` : 66 | « +13,8 % » (gain brut de M3, payés) | « +13,7 % » : la valeur exacte vaut 0,137464 (`deviance_par_modele.csv`). L'arrondi avait été fait à partir de 0,1375 | faible |
| 12 | `Modeles/complements/RAPPORT_COMPLEMENTS.md` : 181 | « **65 %** de celui du meilleur modèle » | « **64 %** » : 0,10606 / 0,16441 = 0,6451 à partir des valeurs exactes de `ablation_deviance.csv`. Supprimer aussi « du meilleur modèle », car L2 a été choisi en regardant le test | faible |
| 13 | `Modeles/RAPPORT_MODELES.md` : 216 (§ 7.2) | « …contrairement au GLM Poisson avec constante, et α ≈ 6 est élevé. » | Selon `RAPPORT_COMPLEMENTS.md` (§ 8, point 2) : « …l'écart existe déjà avec la constante seule (Σμ/Σy = 2,64) ; le rôle propre de α n'est pas démontré. » | faible |
| 14 | `Modeles/RAPPORT_MODELES.md` : 196 (§ 6, H-a) | « Celui de M4 résiste (+11,7 %), mais il dépasse à peine celui de M1 (+10,6 %). » | Ajouter (`RAPPORT_COMPLEMENTS.md`, § 8, point 3) : « Ce gain dépend presque entièrement de la couverture nominale : sans elle, LightGBM tombe à −5,4 % (brut). » | faible |
| 15 | `quarto_report/sections/_introduction.qmd` : 24 (H2) | « The Poisson and negative binomial GLMs give similar mean predictions… » | Ce n'est pas une erreur, mais une hypothèse que le premier jet contredit : le binomial négatif prédit 1,94 fois le total d'entraînement (`calibration_totale_par_periode.csv`). À discuter quand les modèles du projet seront ajustés ; rien à changer avant | faible |
| 16 | `Data_cleaning/clean/push_feasibility.md` : 189 | « lourd pour 3 étudiants » | « lourd pour un groupe de 4 étudiants » (auteurs : `report.qmd`, lignes 4 à 7) | faible |
| 17 | `quarto_report/sections/_data.qmd` : 105 | Chemin de repli `data/raw_se/NfipClaimsV3_SE.parquet` | Le dépôt place les fichiers bruts dans `Data_cleaning/` (`Data_cleaning/README.md`). Garder les deux candidats est sans danger, mais il faut en documenter une seule convention | faible |
| 18 | `CLAUDE.md` : 9 à 18 | Contrat `data/processed/tract_year.parquet` et répartition des fichiers `src/data.py`, `src/eda.py`, `src/models.py`… | Aucun dossier `src/` à la racine du dépôt (vérifié). Indiquer que ces fichiers sont prévus, ou aligner sur la structure réelle (`Data_cleaning/`, `EDA/`, `Modeles/`) | faible |
