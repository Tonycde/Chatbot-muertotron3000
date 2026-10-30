"""Calibración de pesos y umbrales (NO usa evaluation/eval_set.json ni el holdout).

Procedimiento:
  * Positivos: cada pregunta de la KB, consultada con esa pregunta excluida
    (leave-one-out) -> la entrada correcta es la de su propia entrada.
  * Negativos de desarrollo: consultas fuera de dominio / sin respuesta escritas
    aquí mismo (distintas de las de evaluation/).
Se exploran combinaciones de pesos y se reporta, para el mejor umbral de
aceptación, exactitud top-1 en LOO, precisión y recall.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from muertobot import retriever as R  # noqa: E402
from muertobot.bot import Bot  # noqa: E402

DEV_NEG = [
    "¿cuál es la capital de España?", "¿cuántos planetas hay?", "dame una receta de tacos", "¿quién descubrió América?",
    "¿qué es un agujero negro?", "cómo se juega futbol", "qué hora es en Tokio", "¿cuál es el río más largo del mundo?",
    "¿cómo se escribe un currículum?", "¿qué es la inflación?", "recomiéndame un videojuego", "¿cómo curar el dolor de cabeza?",
    "cuéntame de la Navidad", "¿qué se celebra el 16 de septiembre?", "¿cómo se celebra el Año Nuevo?", "¿qué es el Día de la Madre?",
    "¿cuál es el mejor equipo de futbol?", "dime un secreto", "¿qué es la democracia?", "¿cómo se hace una página web?",
    "¿quién pintó la Mona Lisa?", "qué es el ADN", "explícame las fracciones", "¿cuánto es la raíz de 144?",
    "¿cuál es el precio del boleto para ir a Mixquic?", "¿qué clima hace en Oaxaca en noviembre?", "¿cuántos panteones hay en México?",
    "¿cuál es la mejor panadería de pan de muerto?", "¿qué cantante se presenta en el desfile?", "¿qué significa soñar con una calavera?",
    "¿cuál es el número de teléfono del INAH?", "¿cuánto mide la Catrina de Posada?", "¿en qué año se hizo la primera ofrenda?",
]


def collect():
    base = Bot()
    pos, neg = [], []
    for e in base.entries:
        for i, q in enumerate(e["preguntas"]):
            b = Bot(exclude={(e["id"], i)})
            pos.append((e["id"], b.retriever.components(q)))
    nb = Bot()
    for q in DEV_NEG:
        neg.append(nb.retriever.components(q))
    return pos, neg


def score(c, w):
    wq, we, wc, wk, oov = w
    q, e, cov, key = c
    es = min(1.0, R.E_GAIN * e)
    gate = max(0.0, min(1.0, (max(q, es) - R.GATE_LO) / R.GATE_W))
    return wq * q + we * es + (wc * cov + wk * key) * gate


def evaluate(pos, neg, w):
    # top-1 LOO
    ok = 0
    pos_scores = []
    for gold, comps in pos:
        ranked = sorted(comps.items(), key=lambda kv: (-score(kv[1], w), kv[0]))
        top_id, top_c = ranked[0]
        if top_id == gold:
            ok += 1
            pos_scores.append(score(top_c, w))
    neg_scores = [max(score(c, w) for c in comps.values()) for comps in neg]
    best = (0, 0, 0, 0)
    for th in [x / 100 for x in range(25, 80)]:
        tp = sum(s >= th for s in pos_scores)
        fp = sum(s >= th for s in neg_scores)
        rec = tp / len(pos)
        prec = tp / (tp + fp) if tp + fp else 0
        # Se exige cero falsos positivos en desarrollo (preferimos "no sé" a inventar).
        if fp == 0 and rec > best[0]:
            best = (rec, prec, th, fp)
    return ok / len(pos), best


if __name__ == "__main__":
    pos, neg = collect()
    grid_q = [0.35, 0.45, 0.55]
    grid_e = [0.10, 0.20]
    grid_c = [0.10, 0.20, 0.30]
    grid_k = [0.10, 0.20]
    rows = []
    for wq, we, wc, wk in itertools.product(grid_q, grid_e, grid_c, grid_k):
        tot = wq + we + wc + wk
        w = (wq / tot, we / tot, wc / tot, wk / tot, 1.0)
        top1, (rec, prec, th, fp) = evaluate(pos, neg, w)
        rows.append((rec, top1, th, w))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    print("recall@FP=0 | top1_LOO | umbral | pesos (q, e, c, k)")
    for rec, top1, th, w in rows[:8]:
        print(f"{rec:11.3f} | {top1:9.3f} | {th:6.2f} | {tuple(round(x, 3) for x in w[:4])}")
