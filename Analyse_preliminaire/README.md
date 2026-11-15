# Analyse_preliminaire/ : base permanente de l'analyse préliminaire de fréquence

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir
> `STATUT_RESULTATS.md`** · aucun commit à ce stade.

## Objet

Ce dossier rassemble, sous une forme durable, tout ce qui a été produit sur les modèles de fréquence
(`Modeles/` et `Modeles/complements/`). Il contient une section prête pour le rapport de la mise à jour du
16/11/2026, et un registre qui permettra de confirmer, corriger ou abandonner chaque résultat sans réécrire
la documentation.

- **Aucun modèle n'est ajusté ici.** Tous les chiffres sont lus dans les CSV et JSON existants.
- **Statut** : le dossier est permanent ; ses **résultats** sont provisoires et exploratoires.

## Structure

| Élément | Rôle |
|---|---|
| `section_modelisation.qmd` | Section du rapport, en anglais (`CLAUDE.md` : English only), chiffres insérés par code |
| `STATUT_RESULTATS.md` | Registre des 23 résultats : statut, valeur, source, condition pour changer de statut ; journal des versions |
| `TRACABILITE.md` | Pour chaque chiffre : fichier source, cellule, valeur exacte, affichage |
| `INCOHERENCES_DOCUMENTAIRES.md` | 18 incohérences vérifiées dans les fichiers existants, avec un texte proposé (rien n'est appliqué) |
| `PASSAGES_A_COMPLETER.md` | Les 4 passages `TO FILL BY TEAM` du rapport et ce qui peut, ou non, être proposé |
| `NOTE_ENSEIGNANT.md` | Brouillon de note sur le changement de cap (non envoyé) |
| `PLAN_COMMIT.md` | Plan de commit proposé (non exécuté) |
| `figures/` | 4 figures régénérées depuis les CSV, et `SOURCES.md` |
| `tableaux/` | `chiffres_cles.json` et 14 tableaux (CSV et Markdown, avec source et statut en tête) |
| `scripts/registre.py` | Registre unique : clé → fichier et cellule source ; résultats R1 à R23 |
| `scripts/extraire.py` | Produit `chiffres_cles.json`, les tableaux, les figures, `STATUT_RESULTATS.md` et `TRACABILITE.md` |
| `scripts/verifier_chiffres.py` | Contrôle qualité (voir ci-dessous) ; écrit `logs/verification_chiffres.log` |
| `rendu_test.qmd` | Enveloppe de test du rendu, dans ce dossier uniquement |
| `run_all.sh` | Exécution complète : extraction, puis vérification |

## Reproduire et vérifier

Depuis la racine du dépôt, après `Modeles/run_all.sh` et `Modeles/complements/run_all.sh` :

```bash
bash Analyse_preliminaire/run_all.sh
```

`verifier_chiffres.py` sort en erreur, et bloque donc la livraison, si l'un de ces contrôles échoue :
- un chiffre ne correspond plus à sa source ;
- la section cite une clé inconnue ;
- un chiffre est écrit à la main dans la prose ;
- un résultat du registre n'est pas marqué dans la section, ou l'inverse ;
- une figure ou un tableau manque ;
- un mot interdit ou un tiret cadratin apparaît ;
- une valeur citée manque dans le rendu.

Dernier passage (15/11/2026) : **OK, aucun écart.**

**Tester le rendu HTML** (Quarto 1.11.9, installé dans `~/opt/` ; environnement Jupyter du dépôt) :

```bash
cd Analyse_preliminaire
QUARTO_PYTHON=../.venv/bin/python ~/opt/quarto-1.11.9/bin/quarto render rendu_test.qmd --to html
```

Le rendu du 15/11/2026 réussit, sans avertissement ni renvoi cassé. `rendu_test.html` est un fichier
généré, à ne pas commiter.

## Intégrer la section dans `report.qmd`

`CLAUDE.md` interdit de changer l'ordre des sections du gabarit. Deux options, **à tester et à décider par
l'équipe** (non faites) :

1. **Dans « Findings and Discussion »** (`quarto_report/sections/_analysis.qmd`) :
   - copier `section_modelisation.qmd` dans `quarto_report/sections/_preliminary_analysis.qmd` ;
   - descendre chaque titre d'un niveau (`#` devient `##`, `##` devient `###`) ;
   - ajouter `{{< include sections/_preliminary_analysis.qmd >}}` dans `report.qmd`, juste après la ligne
     `{{< include sections/_analysis.qmd >}}`.
2. **En annexe** : même copie, avec l'include placé sous `# Appendices {.unnumbered}` de `report.qmd`.

Dans les deux cas :
- les chemins `../Analyse_preliminaire/figures/…` sont relatifs à `quarto_report/`, comme ceux de
  `../EDA/figures/…` ;
- le bloc `ap-setup` retrouve `Analyse_preliminaire/` en remontant les dossiers depuis le répertoire de
  rendu ;
- les étiquettes (`sec-ap`, `fig-ap-*`, `tbl-ap-*`) sont préfixées pour éviter les collisions.

## Faire évoluer un résultat

Quand un travail ultérieur confirme, corrige ou abandonne un résultat Rk :
1. modifier sa ligne dans `RESULTATS` (`scripts/registre.py`) : statut, énoncé ou condition ;
2. si une valeur change, pointer la clé vers le nouveau fichier source dans `CHIFFRES` ;
3. ajouter une entrée au journal des versions (constantes `VERSION` et `DATE` de `scripts/extraire.py`, et
   ligne du journal dans `build_statut`) ;
4. relancer `bash Analyse_preliminaire/run_all.sh`.

Les phrases de la section sont formulées de façon conditionnelle (« in this design », « at this stage ») :
elles restent vraies tant que l'étiquette suit le registre.

## Ce qui reste à valider par l'équipe

- L'intégration de la section (option 1 ou 2) et sa longueur.
- Les propositions de `INCOHERENCES_DOCUMENTAIRES.md` qui touchent des fichiers existants (n° 1 à 8 et 16
  à 18, dont 2 de gravité élevée : l'offset de LightGBM dans `_analysis.qmd` et `requirements.txt`).
  Elles ont été appliquées puis annulées à la demande de l'équipe. Les n° 9 à 14 sont corrigés dans
  `Modeles/`.
- Le lien de partage et le script de filtrage des fichiers `*_SE.parquet` (Lucas Lehmann).
- Les passages `TO FILL BY TEAM` (3 attendent une information absente du dépôt).
- L'envoi éventuel de `NOTE_ENSEIGNANT.md`.
- Le plan de commit (`PLAN_COMMIT.md`).
