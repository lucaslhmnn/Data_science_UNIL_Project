#!/usr/bin/env bash
# Analyse_preliminaire/ : régénère chiffres, tableaux, figures et registres à partir des fichiers EXISTANTS
# (aucun modèle n'est ajusté), puis vérifie la section. Usage, depuis la racine du dépôt :
#   bash Analyse_preliminaire/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=Modeles/.venv/bin/python
if [ ! -x "$PY" ]; then echo "ARRÊT : Modeles/.venv absent (créé par Modeles/run_all.sh)."; exit 1; fi
mkdir -p Analyse_preliminaire/logs
"$PY" Analyse_preliminaire/scripts/extraire.py | tee Analyse_preliminaire/logs/extraire.log
# Vérification : relit les sources, contrôle la section et teste le rendu Quarto (gfm) s'il est disponible
"$PY" Analyse_preliminaire/scripts/verifier_chiffres.py
