"""Genera la tabla de trazabilidad: qué entrada se apoya en qué fuente y qué falta validar.

Uso: python tools/trazabilidad.py > docs/TRAZABILIDAD.md
"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data"
kb = json.loads((D / "knowledge_base.json").read_text(encoding="utf-8"))["entradas"]
src = json.loads((D / "sources.json").read_text(encoding="utf-8"))["fuentes"]

print("# Trazabilidad entrada → fuentes\n")
print("| Entrada | Confianza | Fuentes (nivel) | Pendiente de validar |")
print("|---|---|---|---|")
pend = 0
for e in kb:
    fs = ", ".join(f"{s} ({src[s]['nivel']})" for s in e["fuentes"])
    por_validar = [s for s in e["fuentes"] if "POR VALIDAR" in src[s]["estado"]]
    pend += bool(por_validar)
    print(f"| `{e['id']}` | {e['confianza']} | {fs} | {'⚠ ' + ', '.join(por_validar) if por_validar else '—'} |")
print(f"\n**{len(kb)} entradas; {pend} dependen de al menos una fuente marcada POR VALIDAR.**")
