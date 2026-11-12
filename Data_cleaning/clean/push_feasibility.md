# Peut-on pousser les données nettoyées sur GitHub ?

> Diagnostic en lecture seule du 12/11/2026 : il décrit l'état du dépôt **avant** le partage. La
> recommandation a ensuite été appliquée sur la branche `data-cleaning` : `.gitignore` avec exceptions,
> `requirements.txt`, mention OpenFEMA et README.
> Tailles en Mo binaires (Mio, 1 Mio = 1 048 576 octets), l'unité des limites GitHub.

## Verdict : oui, sous condition

**Les trois fichiers parquet nettoyés pèsent 16,7 Mio au total, et le plus gros 15,6 Mio.** C'est bien en
dessous de l'avertissement de Git (50 Mio) et du blocage de GitHub (100 Mio). Ils peuvent aller dans Git
**sans Git LFS**. Il faut d'abord régler quatre points :

1. **`.gitignore`** : il ignore aujourd'hui `*.parquet` et `Data_cleaning/clean/*.parquet`. Il faut
   autoriser explicitement les trois fichiers nettoyés.
2. **Conditions OpenFEMA** : ajouter la mention d'attribution obligatoire et préciser que les données
   sont modifiées par le groupe (voir § 7).
3. **Reproductibilité** : ajouter un `requirements.txt` et le script qui a produit les fichiers bruts
   `*_SE.parquet`, absent du dépôt.
4. **Fichiers bruts** : ils restent hors de Git. Celui des polices (1 265 Mio) dépasse la limite des
   100 Mio : ils se partagent ailleurs (option d).

## 1. Fichiers de `Data_cleaning/clean/`

| Fichier | Taille | > 50 Mio | > 100 Mio | Verdict |
|---|---:|:-:|:-:|---|
| `claims_clean.parquet` | 15,59 Mio | non | non | poussable tel quel |
| `zone_year.parquet` | 0,85 Mio | non | non | poussable tel quel |
| `claims_anomalies.parquet` | 0,22 Mio | non | non | poussable tel quel |
| `clean_data.py` | 0,09 Mio | non | non | poussable tel quel |
| `audit_report.md` | 0,02 Mio | non | non | poussable tel quel |
| `cleaning_report.md` | 0,01 Mio | non | non | poussable tel quel |
| `sentinel_report.md` | 0,01 Mio | non | non | poussable tel quel |
| `data_dictionary.csv` | < 0,01 Mio | non | non | poussable tel quel |
| `push_feasibility.md` (ce fichier) | < 0,01 Mio | non | non | poussable tel quel |

Pour comparaison, les fichiers d'entrée de `Data_cleaning/` :

| Fichier | Taille | Verdict |
|---|---:|---|
| `NfipPoliciesV3_SE.parquet` (brut, utilisé) | 1 264,84 Mio | **trop gros** (> 100 Mio) |
| `NfipClaimsV3_SE.parquet` (brut, utilisé) | 41,18 Mio | possible, mais inutile et lourd dans l'historique |
| `NfipPoliciesV3_south.parquet` (ancien, non utilisé) | 2 806,34 Mio | **trop gros** |
| `NfipClaimsV3_south.parquet` (ancien, non utilisé) | 118,70 Mio | **trop gros** |
| `CPI_1978_2026.xlsx` (BLS) | 0,02 Mio | poussable tel quel |
| `dictionary/OpenFemaDataSetFields.csv` | 0,49 Mio | poussable tel quel |

## 2. État Git local

- Branche courante : `main`, à jour avec `origin/main` (dernier commit `cffe1da`). Une branche locale
  `test-acces` existe ; sa branche distante a été supprimée (`gone`).
- Remote : `origin` = `https://github.com/lucaslhmnn/Data_science_UNIL_Project.git`. Le dépôt appartient
  au compte `lucaslhmnn`, pas au mien.
- `git status` : `.gitignore` modifié (non commité) et `Data_cleaning/` entièrement non suivi.
- `.gitignore` actuel :

  ```
  *.parquet
  # Données nettoyées (trop lourdes pour GitHub)
  Data_cleaning/clean/*.parquet
  # Environnement virtuel
  .venv/
  # Fichiers générés automatiquement
  __pycache__/
  .DS_Store
  ```

  **Tous les parquet, bruts comme nettoyés, sont ignorés** (vérifié avec `git check-ignore`).
  Le commentaire « trop lourdes pour GitHub » est contredit par le présent diagnostic pour les fichiers
  nettoyés.

## 3. Poids du dépôt et historique

- `git count-objects -vH` : pack de 3,03 Kio, 5 objets libres (20 Kio) ; dossier `.git` : **168 Kio**.
- Les plus gros objets de tout l'historique (`git rev-list --objects --all`) sont `download_nfip.py`,
  deux versions de `README.md` et `.gitignore`, tous sous 0,01 Mio. **Aucun fichier brut ni gros fichier
  n'a jamais été commité** : l'historique est propre.
- Point d'attention : un parquet ne se compresse pas par différence entre versions. Chaque nouveau commit
  de `claims_clean.parquet` ajoute environ 16 Mio à l'historique, pour toujours. Dix régénérations
  commitées feraient environ 160 Mio. C'est acceptable face à la recommandation GitHub (dépôt idéalement
  < 1 Go), à condition de ne commiter que des versions validées.

## 4. Dépôt distant (non vérifiable d'ici)

`gh` (GitHub CLI) n'est pas installé. **Je n'ai donc pas pu vérifier** la visibilité, la taille côté GitHub
ni les droits des collègues. Indices locaux seulement :

- Le `README.md` affirme : « This is a public repo » (déclaratif, non vérifié).
- Le commit `87e3da5` « Test d'accès en écriture » sur `test-acces` suggère qu'un accès en écriture a été
  testé.
- Le dépôt appartient à `lucaslhmnn` : c'est son compte qui supporterait un éventuel quota Git LFS.

Pour vérifier (non exécuté) :

```bash
brew install gh && gh auth login
gh repo view lucaslhmnn/Data_science_UNIL_Project --json visibility,diskUsage,viewerPermission
gh api repos/lucaslhmnn/Data_science_UNIL_Project/collaborators --jq '.[] | {login, role_name}'
```

La dernière commande n'aboutit que si l'on est administrateur du dépôt.

## 5. Git LFS

- **Non installé** sur cette machine (`git: 'lfs' is not a git command`) et **non activé** sur le dépôt
  (pas de `.gitattributes`).
- Documentation GitHub, **vérifiée en ligne le 12/11/2026** :
  - « GitHub blocks files larger than 100 MiB » ; avertissement de Git au-delà de 50 MiB ; ajout par le
    navigateur limité à 25 MiB ; dépôt recommandé « ideally less than 1 GB, and less than 5 GB is
    strongly recommended » ([About large files on GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)).
  - Quota LFS gratuit (GitHub Free et Pro) : **10 GiB de stockage et 10 GiB de bande passante**.
    « Bandwidth and storage usage always count against the repository owner's account. » Les
    téléchargements comptent, dépôt public ou privé. Une fois le quota dépassé sans moyen de paiement,
    le stockage bloque les nouveaux push et la bande passante désactive LFS jusqu'au mois suivant
    ([Git LFS billing](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)).
  - Taille maximale d'un fichier LFS : 2 GB (Free et Pro)
    ([About Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)).
  - Je n'ai pas vérifié l'unité de cette période (mois civil ou cycle de facturation) au-delà de ce que
    disent ces pages.

## 6. Réduction de taille (tests dans `clean/_size_test/`, supprimé ensuite)

`claims_clean.parquet` est aujourd'hui écrit en Snappy (défaut de pandas), en un seul groupe de lignes.

| Variante | Taille | Gain |
|---|---:|---:|
| Snappy (actuel) | 15,59 Mio | – |
| gzip | 12,75 Mio | −18 % |
| zstd niveau 3 | 12,87 Mio | −17 % |
| zstd niveau 9 | 12,35 Mio | −21 % |
| zstd niveau 19 | 12,20 Mio | −22 % |
| Échantillon aléatoire 5 % (31 085 lignes, zstd 9, `random_state=42`) | 0,91 Mio | −94 % |

- Chaque variante relue est identique au fichier d'origine (`DataFrame.equals`).
- Les 7 colonnes catégorielles (`flood_zone_group`, `foundation_type`, `n_floors`, `county_fips`,
  `rating_system`, `floodEvent`, `state`) sont bien stockées en **dictionnaire** (type Arrow
  `dictionary`, encodage `RLE_DICTIONARY`, page de dictionnaire présente).
- Conclusion : compresser n'est **pas nécessaire** pour passer les limites. zstd ferait gagner environ
  3 Mio par version, ce qui compte surtout si on recommite souvent. Il faudrait modifier `clean_data.py`
  (`compression="zstd"`) ; ce n'est pas fait.

## 7. Contenu et conditions d'utilisation

- Source : OpenFEMA, jeux **FIMA NFIP Redacted Claims v3** et **Redacted Policies v3**, publics et déjà
  caviardés par FEMA (adresses absentes, coordonnées arrondies à 0,1°, ville remplacée par une valeur
  fixe).
- **`claims_clean.parquet`** (23 colonnes) : `paid_flag`, `paid_building_real`, `building_coverage`,
  `deductible_amount`, `flood_zone_group`, `foundation_type`, `elevated_building`, `building_age`,
  `n_floors`, `primary_residence`, `county_fips`, `loss_year`, `rating_system`, `water_depth`,
  `flood_duration`, `floodEvent`, `building_coverage_real`, `deductible_amount_real`,
  `buildingPropertyValue`, `state`, `loss_month_period`, `id`, `paid_na_to_zero`.
  **Aucune adresse, aucun code postal, aucune coordonnée.** La géographie la plus fine est le comté.
- **`zone_year.parquet`** (9 colonnes) : agrégats par zone × comté × année. Aucune donnée individuelle.
- **`claims_anomalies.parquet`** contient volontairement **toutes les 84 colonnes brutes**, dont
  `reportedZipCode`, `censusGeoid`, `latitude` et `longitude`. Ce sont les valeurs déjà publiées par FEMA,
  rien n'a été ajouté. Mais c'est le seul fichier avec une géographie fine : on peut l'exclure si l'on
  veut minimiser ce qu'on republie.
- Conditions OpenFEMA (vérifiées en ligne le 12/11/2026,
  [Terms and Conditions](https://www.fema.gov/about/openfema/terms-conditions)). Elles ne parlent pas
  explicitement de republication sur GitHub, mais imposent :
  - la mention « This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not
    endorsed by FEMA », avec la source et la date d'accès ;
  - de ne pas présenter des données modifiées comme provenant de FEMA ; nos fichiers sont modifiés, il
    faut le dire ;
  - de ne publier aucune information pouvant conduire à identifier des personnes ;
  - de ne pas utiliser les logos FEMA/DHS.

## 8. Reproductibilité

- `clean_data.py` régénère **tout** en environ 6 secondes à partir de trois fichiers d'entrée, avec
  `audit`, `sentinels` puis `clean`. Toutes les règles sont dans `CONFIG`, et `data_dictionary.csv` et
  les rapports documentent chaque transformation.
- Fichiers d'entrée nécessaires (≈ 1,27 Gio au total) :
  - `NfipClaimsV3_SE.parquet` (41 Mio) et `NfipPoliciesV3_SE.parquet` (1 265 Mio) : OpenFEMA API v3
    (`NfipClaims`, `NfipPolicies`), filtrés sur AL, FL, GA, KY, MS, NC, SC, TN ;
  - `CPI_1978_2026.xlsx` (0,02 Mio) : BLS, série CUUR0000SA0.
- **Deux manques empêchent aujourd'hui une reproduction complète par un collègue :**
  1. Le script qui a produit les fichiers `*_SE.parquet` n'est pas dans le dépôt. `download_nfip.py`
     ne télécharge que le Delaware, à titre de test.
  2. Il n'y a pas de `requirements.txt`. Les paquets utilisés sont `duckdb`, `pyarrow`, `pandas` et
     `openpyxl` (versions locales : 2.0.0, 26.0.1, 3.1.1, 3.1.5).

## 9. Options

| Option | Avantages | Inconvénients |
|---|---|---|
| **(a) Git LFS** | Fichiers versionnés hors historique Git ; gère des fichiers jusqu'à 2 GB, donc même les bruts | Inutile pour 17 Mio ; chacun doit installer `git-lfs` ; quota du **propriétaire** (`lucaslhmnn`) : le brut des polices (1,24 Gio) ferait environ 8 clones par mois avant blocage de la bande passante |
| **(b) Fichier compressé ou échantillon** | zstd : −21 % ; échantillon 5 % : 0,9 Mio, utile pour démo et tests | Compresser est inutile ici ; un échantillon seul ne suffit pas pour modéliser ; deux versions à maintenir |
| **(c) Dépôt de données séparé** | Isole le code de l'historique des données | Deux dépôts ou un sous-module à gérer : lourd pour 3 étudiants, pour 17 Mio |
| **(d) Partage hors Git** (SWITCHdrive, Google Drive) | Seule option simple pour les **bruts** (1,3 Gio) ; pas de limite de fichier | Pas de versionnement ; lien à maintenir ; risque de versions divergentes sans somme de contrôle |
| **(e) Chacun régénère avec `clean_data.py`** | Garantit que tout le monde a exactement le même résultat ; rien de lourd dans Git | Chacun doit récupérer 1,3 Gio de bruts (donc (d) ou un script de téléchargement) et installer l'environnement |

Commandes (non exécutées) :

**(a) Git LFS**
```bash
brew install git-lfs && git lfs install
git lfs track "Data_cleaning/clean/*.parquet"        # crée .gitattributes
# puis autoriser les fichiers dans .gitignore (voir « Avant de pousser »)
git add .gitattributes Data_cleaning/clean/*.parquet
git commit -m "Données nettoyées via Git LFS" && git push
```

**(b) Échantillon de démonstration**
```bash
.venv/bin/python -c "import pandas as pd; d = pd.read_parquet('Data_cleaning/clean/claims_clean.parquet'); d.sample(frac=0.05, random_state=42).to_parquet('Data_cleaning/clean/claims_sample5.parquet', index=False, compression='zstd', compression_level=9)"
```

**(c) Dépôt de données séparé**
```bash
gh repo create lucaslhmnn/Data_science_UNIL_data --private
git submodule add https://github.com/lucaslhmnn/Data_science_UNIL_data.git data
```

**(d) Partage hors Git**
```bash
shasum -a 256 Data_cleaning/*_SE.parquet Data_cleaning/CPI_1978_2026.xlsx > Data_cleaning/raw_checksums.sha256
# déposer les fichiers sur SWITCHdrive, noter le lien dans le README, commiter le fichier .sha256
# chez les collègues, après téléchargement :
shasum -a 256 -c Data_cleaning/raw_checksums.sha256
```

**(e) Régénération**
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python Data_cleaning/clean/clean_data.py audit
.venv/bin/python Data_cleaning/clean/clean_data.py sentinels
.venv/bin/python Data_cleaning/clean/clean_data.py clean
```

## 10. Recommandation

**Pousser directement dans Git, sans LFS, les trois parquet nettoyés avec le script, les rapports et le
dictionnaire. Partager les fichiers bruts par SWITCHdrive (option d), avec des sommes de contrôle, pour
que chacun puisse aussi régénérer (option e).**

Pourquoi : 16,7 Mio ne justifient ni LFS (installation chez chacun et quota du propriétaire) ni un dépôt
séparé. Vos collègues ont les données en un `git pull`. Les bruts, eux, ne peuvent pas aller sur GitHub
sans LFS (1 265 Mio) et consommeraient vite le quota LFS du propriétaire.

### Avant de pousser

1. **`.gitignore`** : remplacer la ligne `Data_cleaning/clean/*.parquet` par des exceptions au `*.parquet`
   général. Les exceptions doivent venir après `*.parquet` :
   ```
   *.parquet
   !Data_cleaning/clean/claims_clean.parquet
   !Data_cleaning/clean/zone_year.parquet
   !Data_cleaning/clean/claims_anomalies.parquet
   ```
   Vérifier ensuite que les bruts restent ignorés : `git check-ignore -v Data_cleaning/*.parquet`.
2. **Attribution** : ajouter au `README.md`, ou dans un `Data_cleaning/README.md`, la mention OpenFEMA
   obligatoire, la date d'accès, et la phrase « données modifiées par le groupe, non validées par FEMA ».
3. **`requirements.txt`** à la racine, avec les versions ci-dessus. Commiter aussi le script qui a produit
   les fichiers `*_SE.parquet`.
4. **Branche dédiée et revue** :
   ```bash
   git switch -c data-cleaning
   git add .gitignore requirements.txt README.md Data_cleaning/clean Data_cleaning/CPI_1978_2026.xlsx \
           Data_cleaning/dictionary Data_cleaning/variable_families.md Data_cleaning/variable_families.py
   git status        # vérifier qu'aucun brut ni .venv n'apparaît
   git commit -m "Nettoyage des sinistres NFIP Région IV : script, rapports, données nettoyées"
   git push -u origin data-cleaning
   gh pr create --base main      # ou ouvrir la pull request sur github.com
   ```
5. **Discipline d'équipe** : ne recommiter les parquet que pour une version validée (environ 16 Mio de
   plus dans l'historique à chaque fois) ; une seule personne régénère et pousse.
6. **Optionnel** : décider si `claims_anomalies.parquet` est publié (il contient les ZIP et les
   coordonnées arrondies publiés par FEMA). Les adresses e-mail Git des commits sont visibles si le dépôt
   est public ; on peut utiliser l'adresse « noreply » de GitHub (`git config user.email`).
