#!/usr/bin/env bash
# Compléments au premier jet : vérifications VC1-VC4 et table d'ablation (voir Modeles/complements/README.md).
# Usage, depuis la racine du dépôt :  bash Modeles/complements/run_all.sh
# Réutilise Modeles/.venv (créé par Modeles/run_all.sh) ; n'écrit que dans Modeles/complements/.
set -euo pipefail
cd "$(dirname "$0")/../.."                   # racine du dépôt

VENV=Modeles/.venv
if [ ! -x "$VENV/bin/python" ]; then
  echo "ARRÊT : Modeles/.venv absent. Lancer d'abord Modeles/run_all.sh (qui le crée)."
  exit 1
fi
OMP_DIR=$(ls -d "$VENV"/lib/python3*/site-packages/sklearn/.dylibs 2>/dev/null | head -1 || true)
if [ -n "$OMP_DIR" ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="$PWD/$OMP_DIR${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
fi
export PYTHONHASHSEED=42
C=Modeles/complements
mkdir -p $C/resultats $C/figures $C/logs

{
  echo "# SHA-256 des fichiers d'entrée lus par Modeles/complements/ ($(date '+%Y-%m-%d %H:%M:%S %Z'), commit $(git rev-parse --short HEAD))"
  shasum -a 256 EDA/ds_clean.csv EDA/build_ds_clean.py Data_cleaning/clean/claims_clean.parquet \
    Data_cleaning/clean/clean_data.py Modeles/scripts/commun.py Modeles/scripts/02_modeles.py \
    Modeles/resultats/ajustement_payes.json Modeles/resultats/ajustement_tous.json \
    Modeles/resultats/coefficients_payes.csv Modeles/resultats/coefficients_tous.csv \
    Modeles/resultats/predictions_payes.csv Modeles/resultats/predictions_tous.csv
  if [ -f Data_cleaning/NfipClaimsV3_SE.parquet ]; then
    echo "# Fichier brut lu pour VC3 (agrégats seulement, aucune donnée brute copiée) :"
    shasum -a 256 Data_cleaning/NfipClaimsV3_SE.parquet
  fi
} > $C/ENTREES.txt

{
  echo "Exécution du $(date '+%Y-%m-%d %H:%M:%S %Z')"
  "$VENV/bin/python" --version
  "$VENV/bin/pip" freeze | grep -iE "^(pandas|numpy|scipy|statsmodels|lightgbm|matplotlib|pyarrow|scikit-learn)=="
  echo "SEED = 42 ; PYTHONHASHSEED = $PYTHONHASHSEED ; DYLD_FALLBACK_LIBRARY_PATH = ${DYLD_FALLBACK_LIBRARY_PATH:-}" | sed "s|$PWD/||g"
} > $C/logs/00_environnement.log

: > $C/logs/durees.log
run() {
  local name=$1; shift
  local t0; t0=$(date +%s)
  set +e
  "$VENV/bin/python" "$@" > "$C/logs/$name.log" 2>&1
  local status=$?
  set -e
  echo "$name : $(( $(date +%s) - t0 )) s (code de sortie $status)" | tee -a $C/logs/durees.log
  return $status
}

if ! run c1_verifications $C/scripts/c1_verifications.py; then
  echo "ARRÊT : VC1 en défaut (nouveau réglage requis) ou erreur ; voir $C/logs/c1_verifications.log"
  exit 3
fi
run c2_ablation_modeles $C/scripts/c2_ablation_modeles.py
run c3_ablation_evaluation $C/scripts/c3_ablation_evaluation.py
run c4_descriptif_couverture_hp $C/scripts/c4_descriptif_couverture_hp.py   # hors protocole, descriptif
echo "Terminé. Résultats : $C/resultats/ ; figures : $C/figures/ ; journaux : $C/logs/"
