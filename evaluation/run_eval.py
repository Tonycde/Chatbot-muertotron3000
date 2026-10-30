"""Evalúa el chatbot y reporta métricas.

Uso:  python evaluation/run_eval.py [--verbose] [--json]

Mide:
  1. Validación leave-one-out sobre las preguntas de la base de conocimiento.
  2. Exactitud (top-1) en preguntas parafraseadas e independientes.
  3. Tasa de rechazo en preguntas fuera de dominio y cercanas al dominio.
  4. Cumplimiento de casos adversariales / de seguridad.
  5. Determinismo (misma entrada -> misma salida).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from muertotron import Bot  # noqa: E402
from muertotron import bot as botmod  # noqa: E402

ANSWERING = {"answer", "tentative"}


def leave_one_out(verbose: bool) -> dict:
    base = Bot()
    total = correct = accepted = 0
    errors = []
    for e in base.entries:
        for i, q in enumerate(e["preguntas"]):
            b = Bot(exclude={(e["id"], i)})
            hits = b.retriever.search(q, k=1)
            total += 1
            ok_id = bool(hits) and hits[0].entry_id == e["id"]
            correct += ok_id
            accepted += ok_id and hits[0].score >= botmod.TENTATIVE
            if not ok_id:
                errors.append((q, e["id"], hits[0].entry_id if hits else None))
    return {"total": total, "top1": correct / total, "top1_and_accepted": accepted / total, "errors": errors}


def run(verbose: bool = False, file: str = "eval_set.json") -> dict:
    data = json.loads((ROOT / "evaluation" / file).read_text(encoding="utf-8"))
    res: dict = {}

    res["leave_one_out"] = leave_one_out(verbose)

    # 2) en dominio
    ok = direct = 0
    fails = []
    for item in data["en_dominio"]:
        r = Bot().reply(item["q"])
        good = r.intent in ANSWERING and r.entry_id == item["entrada"]
        direct += good and r.intent == "answer"
        ok += good
        if not good:
            fails.append((item["q"], item["entrada"], r.intent, r.entry_id, r.confidence))
    res["en_dominio"] = {"total": len(data["en_dominio"]), "accuracy": ok / len(data["en_dominio"]),
                         "direct": direct / len(data["en_dominio"]), "fails": fails}

    # 3) fuera de dominio
    rej = 0
    leaks = []
    for q in data["fuera_de_dominio"]:
        r = Bot().reply(q)
        good = r.intent not in ANSWERING
        rej += good
        if not good:
            leaks.append((q, r.entry_id, r.confidence))
    res["fuera_de_dominio"] = {"total": len(data["fuera_de_dominio"]), "rejection": rej / len(data["fuera_de_dominio"]), "leaks": leaks}

    rej = 0
    leaks = []
    for q in data["cerca_del_dominio_sin_respuesta"]:
        r = Bot().reply(q)
        good = r.intent not in ANSWERING
        rej += good
        if not good:
            leaks.append((q, r.entry_id, r.confidence))
    n = len(data["cerca_del_dominio_sin_respuesta"])
    res["cerca_del_dominio"] = {"total": n, "rejection": rej / n, "leaks": leaks}

    # 4) adversarial
    ok = 0
    fails = []
    for item in data["adversarial"]:
        r = Bot().reply(item["q"])
        good = r.intent in item["esperado"]
        if good and "entrada" in item and r.intent in ANSWERING:
            good = r.entry_id == item["entrada"]
        text = r.plain().lower()
        for s in item.get("contiene", []):
            good = good and s.lower() in text
        for s in item.get("no_contiene", []):
            good = good and s.lower() not in text
        if r.intent in ANSWERING:
            for s in item.get("contiene_si_answer", []):
                good = good and s.lower() in text
        ok += good
        if not good:
            fails.append((item["q"], item["esperado"], r.intent, r.entry_id))
    res["adversarial"] = {"total": len(data["adversarial"]), "pass_rate": ok / len(data["adversarial"]), "fails": fails}

    # 5) determinismo
    qs = [i["q"] for i in data["en_dominio"][:20]] + data["fuera_de_dominio"][:10] + [i["q"] for i in data["adversarial"]]
    det = True
    for q in qs:
        outs = {Bot().reply(q).plain() for _ in range(3)}
        det &= len(outs) == 1
    # y estabilidad frente al historial: misma pregunta tras otras conversaciones
    b = Bot()
    for q in data["fuera_de_dominio"][:5] + [i["q"] for i in data["en_dominio"][:5]]:
        b.reply(q)
    hist_ok = all(b.reply(i["q"]).entry_id == Bot().reply(i["q"]).entry_id for i in data["en_dominio"][:15])
    res["determinismo"] = {"misma_entrada_misma_salida": det, "independiente_del_historial": hist_ok}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--file", default="eval_set.json", help="eval_set.json (desarrollo) o holdout_set.json (prueba final)")
    a = ap.parse_args()
    res = run(a.verbose, a.file)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    lo = res["leave_one_out"]
    print("=== Evaluación de Muertotron3000 ===")
    print(f"Umbrales: ACCEPT={botmod.ACCEPT}  TENTATIVE={botmod.TENTATIVE}  CLARIFY={botmod.CLARIFY}")
    print(f"1) Leave-one-out ({lo['total']} preguntas): top-1 = {lo['top1']:.1%}   top-1 y aceptada = {lo['top1_and_accepted']:.1%}")
    print(f"2) Paráfrasis independientes ({res['en_dominio']['total']}): exactitud = {res['en_dominio']['accuracy']:.1%} (respuesta directa: {res['en_dominio']['direct']:.1%}; el resto con aviso «no estoy seguro»)")
    print(f"3) Fuera de dominio ({res['fuera_de_dominio']['total']}): rechazo = {res['fuera_de_dominio']['rejection']:.1%}")
    print(f"   Cerca del dominio sin respuesta ({res['cerca_del_dominio']['total']}): rechazo = {res['cerca_del_dominio']['rejection']:.1%}")
    print(f"4) Adversariales/seguridad ({res['adversarial']['total']}): cumplimiento = {res['adversarial']['pass_rate']:.1%}")
    print(f"5) Determinismo: {res['determinismo']}")
    if a.verbose:
        for key in ("en_dominio", "fuera_de_dominio", "cerca_del_dominio", "adversarial"):
            for f in res[key].get("fails", []) + res[key].get("leaks", []):
                print(f"  [{key}] {f}")
        for f in lo["errors"]:
            print(f"  [leave_one_out] {f}")


if __name__ == "__main__":
    main()
