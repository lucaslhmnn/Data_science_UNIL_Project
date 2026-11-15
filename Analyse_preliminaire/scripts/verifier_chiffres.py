"""Contrôle qualité de section_modelisation.qmd. Écrit logs/verification_chiffres.log ; code de sortie 1 en
cas d'erreur (la livraison est alors bloquée : corriger le texte, jamais les CSV).

Contrôles :
 1. chaque chiffre de tableaux/chiffres_cles.json est relu dans sa source (tolérance relative 1e-9) et son
    affichage arrondi est recalculé (égalité exacte) ;
 2. chaque ck("clé") de la section existe dans le registre ;
 3. aucun chiffre écrit à la main dans la prose (hors années, dates, versions et constantes listées) ;
 4. (si Quarto est disponible) rendu de la section : chaque valeur citée apparaît dans la sortie, sans erreur ;
 5. registre <-> texte : chaque Rk de STATUT_RESULTATS.md est marqué dans la section, et inversement ;
 6. chemins des figures et tableaux de la section ;
 7. mots interdits (prouve, démontre, best model…) et tirets cadratins ;
 8. avertissements (non bloquants) : phrases causales sans étiquette [Not demonstrated] à relire.
Usage (racine du dépôt) : Modeles/.venv/bin/python Analyse_preliminaire/scripts/verifier_chiffres.py"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registre as R  # noqa: E402

AP, ROOT = R.AP, R.ROOT
QMD = AP / "section_modelisation.qmd"
LOG = AP / "logs" / "verification_chiffres.log"
QUARTO = Path.home() / "opt" / "quarto-1.11.9" / "bin" / "quarto"
RENDER_PY = ROOT / ".venv" / "bin" / "python"           # environnement avec Jupyter (le venv de Modeles n'en a pas)
ALLOWED = [r"Region 4", r"Rating 2\.0", r"SHA-256", r"seed 42", r"Python 3\.13\.0", r"statsmodels 0\.15\.0",
           r"LightGBM 4\.7\.0", r"per 1,000", r"1,000 average", r"\b\d{2}/\d{2}/\d{4}\b", r"\b\d{2}:\d{2}\b",
           r"\b(19|20)\d{2}\b", r"^\s*\d+\.\s"]


def main():
    log, errors, warns = [], [], []
    ck = json.loads((AP / "tableaux" / "chiffres_cles.json").read_text())
    qmd = QMD.read_text()

    # 1. Sources
    log.append("== 1. Chiffres relus dans leur source")
    for k, (src, kind) in R.CHIFFRES.items():
        v = R.value(k)
        if k not in ck:
            errors.append(f"clé {k} absente de chiffres_cles.json")
            continue
        rel = abs(v - ck[k]["valeur"]) / max(abs(v), 1e-12)
        disp = R.fmt(v, kind)
        ok = rel <= 1e-9 and disp == ck[k]["affichage"]
        log.append(f"  {'OK ' if ok else 'ÉCART'} {k:28s} source={v:.10g} json={ck[k]['valeur']:.10g} affichage={disp}")
        if not ok:
            errors.append(f"{k} : source {v} / json {ck[k]['valeur']} / affichage {disp} vs {ck[k]['affichage']}")
    extra = set(ck) - set(R.CHIFFRES)
    if extra:
        errors.append(f"clés du JSON absentes du registre : {sorted(extra)}")

    # 2. Clés citées
    used = re.findall(r'ck\("([A-Za-z0-9_]+)"\)', qmd)
    unknown = sorted(set(used) - set(ck))
    log.append(f"== 2. Clés citées dans la section : {len(set(used))} distinctes ; inconnues : {unknown or 'aucune'}")
    if unknown:
        errors.append(f"clés inconnues dans la section : {unknown}")

    # 3. Chiffres écrits à la main dans la prose
    prose = re.sub(r"```.*?```", " ", qmd, flags=re.S)
    prose = re.sub(r"<!--.*?-->", " ", prose, flags=re.S)
    prose = re.sub(r"`[^`]*`", " ", prose)
    prose = re.sub(r"\{#[^}]*\}|\]\([^)]*\)|@\S+", " ", prose)
    hand = []
    for ln in prose.splitlines():
        s = ln
        for pat in ALLOWED:
            s = re.sub(pat, " ", s)
        for m in re.finditer(r"(?<![A-Za-z_])\d[\d,.]*%?", s):
            hand.append((m.group(0), ln.strip()[:110]))
    log.append(f"== 3. Chiffres écrits à la main dans la prose : {len(hand)}")
    for tok, ctx in hand:
        log.append(f"  « {tok} » dans : {ctx}")
        errors.append(f"chiffre écrit à la main : {tok} ({ctx[:60]})")

    # 5. Registre <-> texte
    marks = set(re.findall(r"<!-- (R\d+) -->", qmd))
    reg = {r[0] for r in R.RESULTATS}
    log.append(f"== 5. Registre : {len(reg)} résultats ; marqués dans la section : {len(marks)}")
    if reg - marks:
        errors.append(f"résultats du registre absents de la section : {sorted(reg - marks, key=lambda x: int(x[1:]))}")
    if marks - reg:
        errors.append(f"marqueurs de la section absents du registre : {sorted(marks - reg)}")
    cited_keys = set(used)
    for rid, _, keys, st, _ in R.RESULTATS:
        if keys and not (set(keys) & cited_keys):
            warns.append(f"{rid} : aucune de ses valeurs n'est citée dans le texte (seulement en tableau ou registre)")

    # 6. Figures et tableaux
    figs = re.findall(r"\]\((\.\./Analyse_preliminaire/figures/[^)]+)\)", qmd)
    for f in figs:
        p = (AP / f.replace("../Analyse_preliminaire/", "")).resolve()
        log.append(f"  figure {f} : {'existe' if p.exists() else 'ABSENTE'}")
        if not p.exists():
            errors.append(f"figure absente : {f}")
    for t in re.findall(r'ap_table\("([^"]+)"\)', qmd):
        if not (AP / "tableaux" / f"{t}.csv").exists():
            errors.append(f"tableau absent : {t}")
    log.append(f"== 6. Figures : {len(figs)} ; tableaux : {len(re.findall(r'ap_table', qmd)) - 1}")

    # 7. Mots interdits et tirets cadratins
    bad = [w for w in [r"\bprove[sd]?\b", r"\bdemonstrates?\b", r"\bdemonstrated\b(?<!Not demonstrated)",
                       r"best model", r"\bprouve", r"\bdémontre"] if re.search(w, prose, flags=re.I)]
    demo = [m.start() for m in re.finditer(r"demonstrated", prose, flags=re.I)]
    demo_bad = [i for i in demo if prose[max(0, i - 4):i].lower() != "not "]
    if demo_bad:
        errors.append(f"« demonstrated » hors de l'étiquette [Not demonstrated] : {len(demo_bad)} occurrence(s)")
    bad = [b for b in bad if "demonstrated" not in b]
    if bad:
        errors.append(f"mots interdits : {bad}")
    if "—" in qmd:
        errors.append("tiret cadratin (—) présent dans la section")
    log.append(f"== 7. Mots interdits : {bad or 'aucun'} ; « demonstrated » hors étiquette : {len(demo_bad)} ; "
               f"tiret cadratin : {'oui' if chr(0x2014) in qmd else 'non'}")

    # 8. Phrases causales à relire (avertissement)
    for sent in re.split(r"(?<=[.;])\s+", prose):
        if re.search(r"\b(because|due to|caused|causes|explains|driven by)\b", sent, flags=re.I) and \
                "Not demonstrated" not in sent:
            warns.append(f"phrase causale à relire : {sent.strip()[:140]}")

    # 4. Rendu Quarto
    if QUARTO.exists() and RENDER_PY.exists():
        env = {**os.environ, "QUARTO_PYTHON": str(RENDER_PY)}
        r = subprocess.run([str(QUARTO), "render", "rendu_test.qmd", "--to", "gfm", "--output", "rendu_verification.md"],
                           cwd=AP, env=env, capture_output=True, text=True)
        out = AP / "rendu_verification.md"
        if r.returncode != 0 or not out.exists():
            errors.append(f"rendu Quarto en échec (code {r.returncode}) : {r.stderr[-400:]}")
        else:
            text = out.read_text()
            missing = [k for k in sorted(set(used)) if ck[k]["affichage"] not in text]
            for bad_tok in ["Traceback", "KeyError", "NameError", "nan%", " nan ", "None"]:
                if bad_tok in text:
                    errors.append(f"le rendu contient « {bad_tok} »")
            log.append(f"== 4. Rendu Quarto (gfm) : OK ; valeurs citées absentes du rendu : {missing or 'aucune'}")
            if missing:
                errors.append(f"valeurs absentes du rendu : {missing}")
            out.unlink()
            shutil.rmtree(AP / "rendu_verification_files", ignore_errors=True)
    else:
        log.append("== 4. Rendu Quarto : non testé (Quarto ou environnement Jupyter absent)")

    log.append("")
    log += [f"AVERTISSEMENT : {w}" for w in warns]
    log += [f"ERREUR : {e}" for e in errors]
    log.append(f"RÉSULTAT : {'OK, aucun écart' if not errors else f'{len(errors)} erreur(s), livraison bloquée'} ; "
               f"{len(warns)} avertissement(s)")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log[-(len(errors) + len(warns) + 1):]))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
