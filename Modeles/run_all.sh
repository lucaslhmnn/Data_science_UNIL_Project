#!/usr/bin/env bash
# Exécution complète du premier jet des modèles de fréquence (voir Modeles/README.md).
# Usage, depuis la racine du dépôt :  bash Modeles/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."                      # racine du dépôt, quel que soit le dossier courant

VENV=Modeles/.venv
if [ ! -x "$VENV/bin/python" ]; then
  echo "Création de l'environnement $VENV (versions de Modeles/environnement.txt)"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r Modeles/environnement.txt
fi

# LightGBM a besoin de libomp. Sans Homebrew, on désigne la copie fournie par scikit-learn dans le venv
# (voir VERIFICATIONS.md, V5). Sans effet si le dossier n'existe pas (par exemple sous Linux).
OMP_DIR=$(ls -d "$VENV"/lib/python3*/site-packages/sklearn/.dylibs 2>/dev/null | head -1 || true)
if [ -n "$OMP_DIR" ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="$PWD/$OMP_DIR${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
fi
export PYTHONHASHSEED=42

mkdir -p Modeles/resultats Modeles/figures Modeles/logs
rm -f Modeles/BLOCAGE.md
{
  echo "# SHA-256 des fichiers d'entrée lus par Modeles/ ($(date '+%Y-%m-%d %H:%M:%S %Z'), commit $(git rev-parse --short HEAD))"
  shasum -a 256 EDA/ds_clean.csv EDA/ds_clean_roles.json EDA/build_ds_clean.py \
    EDA/figures/eda_key_numbers.json Data_cleaning/clean/claims_clean.parquet
} > Modeles/ENTREES.txt

{
  echo "Exécution du $(date '+%Y-%m-%d %H:%M:%S %Z')"
  "$VENV/bin/python" --version
  "$VENV/bin/pip" freeze | grep -iE "^(pandas|numpy|scipy|statsmodels|lightgbm|matplotlib|pyarrow|scikit-learn)=="
  echo "SEED = 42 ; PYTHONHASHSEED = $PYTHONHASHSEED ; DYLD_FALLBACK_LIBRARY_PATH = ${DYLD_FALLBACK_LIBRARY_PATH:-}" | sed "s|$PWD/||g"
} > Modeles/logs/00_environnement.log

: > Modeles/logs/durees.log
run() {
  local name=$1; shift
  local t0; t0=$(date +%s)
  set +e
  "$VENV/bin/python" "$@" > "Modeles/logs/$name.log" 2>&1
  local status=$?
  set -e
  echo "$name : $(( $(date +%s) - t0 )) s (code de sortie $status)" | tee -a Modeles/logs/durees.log
  return $status
}

if ! run 01_verifications Modeles/scripts/01_verifications.py; then
  echo "BLOCAGE : un contrôle bloquant a échoué, aucun modèle n'est ajusté. Voir Modeles/BLOCAGE.md."
  exit 2
fi
run 02_modeles Modeles/scripts/02_modeles.py
run 03_evaluation Modeles/scripts/03_evaluation.py
echo "Terminé. Résultats : Modeles/resultats/ ; figures : Modeles/figures/ ; journaux : Modeles/logs/"
