"""Integridad de la base de conocimiento y trazabilidad de fuentes."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
KB = json.loads((DATA / "knowledge_base.json").read_text(encoding="utf-8"))["entradas"]
SRC = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["fuentes"]
REQUIRED = {"id", "tema", "tipo", "preguntas", "palabras_clave", "respuesta", "fuentes", "confianza"}


def test_ids_unicos():
    ids = [e["id"] for e in KB]
    assert len(ids) == len(set(ids))


def test_campos_obligatorios_y_fuentes_existentes():
    for e in KB:
        assert REQUIRED <= set(e), e["id"]
        assert e["preguntas"] and e["palabras_clave"], e["id"]
        assert e["fuentes"], f"{e['id']} sin fuentes"
        for s in e["fuentes"]:
            assert s in SRC, f"{e['id']} cita fuente inexistente {s}"
        assert e["confianza"] in {"alta", "media"}


def test_respuestas_aptas_para_secundaria():
    for e in KB:
        n = len(e["respuesta"].split())
        assert 15 <= n <= 160, f"{e['id']} longitud {n}"


def test_entradas_de_confianza_alta_tienen_fuente_institucional():
    for e in KB:
        if e["confianza"] == "alta":
            assert any(SRC[s]["nivel"] <= 2 for s in e["fuentes"]), e["id"]


def test_fuentes_tienen_metadatos():
    for sid, s in SRC.items():
        assert {"nombre", "tipo", "nivel", "estado"} <= set(s), sid
        if sid != "conocimiento_general":
            assert s["url"].startswith("https://"), sid
