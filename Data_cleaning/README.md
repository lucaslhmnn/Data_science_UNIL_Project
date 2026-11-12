# Fichiers d'entrée (bruts) du nettoyage

Les fichiers bruts **ne sont pas versionnés**. Celui des polices (1,24 Gio) dépasse la limite de
100 Mio de GitHub, et `.gitignore` ignore tous les `*.parquet` sauf les trois fichiers nettoyés. Pour
régénérer les données, chaque membre doit placer ces fichiers **directement dans `Data_cleaning/`**, sans
sous-dossier et sans les renommer.

> *This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by
> FEMA.*

## Fichiers attendus

| Fichier | Origine | Taille | Lignes | SHA-256 |
|---|---|---:|---:|---|
| `NfipClaimsV3_SE.parquet` | OpenFEMA API v3, jeu **FIMA NFIP Redacted Claims v3** (entité `NfipClaims`) | 43 178 832 octets (41,2 Mio) | 787 274 | `219b72b53b050dd59cb82df91651e3f6463b44714f9393789dd5b74eb20c3f80` |
| `NfipPoliciesV3_SE.parquet` | OpenFEMA API v3, jeu **FIMA NFIP Redacted Policies v3** (entité `NfipPolicies`) | 1 326 275 914 octets (1,24 Gio) | 31 463 858 | `d06011eec27d0e2663301c7a678fe9276e6d376a22afb56ca862d54b0e830374` |
| `CPI_1978_2026.xlsx` | BLS, CPI-U, série `CUUR0000SA0`, mensuel 1978–2026, non désaisonnalisé | 17 141 octets | – | `3898ce146e2a94e33dbb146552d1a7d7567eb35a57c13e3a6ba3fbb94379f2d3` |

Vérification après téléchargement, depuis la racine du dépôt :

```bash
grep -v '^#' Data_cleaning/clean/CHECKSUMS.txt | shasum -a 256 -c -
```

**Lien de téléchargement des fichiers bruts : à compléter.**

## Filtre appliqué

Les deux fichiers `*_SE.parquet` ne contiennent que les États de la **Région IV de FEMA** : AL, FL, GA,
KY, MS, NC, SC, TN. Pour les sinistres, la colonne filtrée est `state` ; pour les polices,
`propertyState`. L'audit (`clean/audit_report.md`, § 2) a confirmé qu'il n'y a exactement que ces 8
États. Date d'extraction OpenFEMA (`asOfDate`) : 08/09/2026.

## Procédure de création des fichiers `*_SE.parquet` : à compléter

**Le script qui a produit ces deux fichiers n'est pas dans le dépôt.** `download_nfip.py`, à la racine,
ne télécharge que le Delaware, à titre de test. Il faut ajouter ici, ou dans le dépôt :

- le script ou la procédure exacte de téléchargement (endpoint, paramètres `$filter`, `$select`) ;
- la date d'accès à l'API, exigée par les conditions d'OpenFEMA pour la citation ;
- les éventuels traitements entre le téléchargement et l'écriture du parquet.

## Fichier CPI

`CPI_1978_2026.xlsx` est un export du BLS (série `CUUR0000SA0`, « All items in U.S. city average, all
urban consumers, not seasonally adjusted », base 1982-84 = 100). Il est public et léger (17 Kio) : il
**peut être versionné**, mais il ne l'est pas encore. On peut aussi l'exporter à nouveau depuis le site du
BLS (data.bls.gov) pour la série CUUR0000SA0, sur 1978–2026, au format Excel mensuel. La cellule
d'octobre 2025 est vide dans cet export.

## Autres fichiers présents localement (non versionnés, non utilisés par le script)

- `NfipClaimsV3_south.parquet` et `NfipPoliciesV3_south.parquet` : anciennes extractions sur un autre
  ensemble d'États (avec LA, TX, AR, sans KY). Elles sont remplacées par les fichiers `*_SE`.
- `dictionary/OpenFemaDataSetFields.csv` : dictionnaire des champs OpenFEMA (voir `clean/README.md`,
  § 6).
- `variable_families.md` / `variable_families.py` : premier classement exploratoire des variables.
