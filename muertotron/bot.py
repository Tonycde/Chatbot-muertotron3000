"""Orquestador del chatbot: guardrails -> recuperación -> respuesta."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import guardrails as G
from . import text as T
from .retriever import Retriever

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Umbrales de decisión (calibrados con evaluation/run_eval.py; ver docs/ARQUITECTURA.md).
ACCEPT = 0.55      # >= ACCEPT: respuesta directa
TENTATIVE = 0.42   # entre TENTATIVE y ACCEPT: respuesta con aviso de poca seguridad
CLARIFY = 0.30     # entre CLARIFY y TENTATIVE: se pide aclaración con sugerencias numeradas
COMPOUND_MIN = 0.28  # puntaje mínimo de cada entrada en una pregunta compuesta ("el copal y la sal")


@dataclass
class Reply:
    text: str
    intent: str
    entry_id: str | None = None
    confidence: float | None = None
    sources: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    debug: dict = field(default_factory=dict)

    def plain(self) -> str:
        """Versión de texto plano (para terminal y pruebas)."""
        out = self.text
        if self.sources:
            out += "\n\nFuentes: " + "; ".join(s["nombre"] for s in self.sources)
        if self.suggestions:
            out += "\n\nTambién puedes preguntar:\n" + "\n".join(f"  - {s}" for s in self.suggestions)
        return out


class Bot:
    def __init__(self, kb_path: Path | None = None, sources_path: Path | None = None, exclude=None):
        kb = json.loads((kb_path or DATA_DIR / "knowledge_base.json").read_text(encoding="utf-8"))
        src = json.loads((sources_path or DATA_DIR / "sources.json").read_text(encoding="utf-8"))
        self.entries: list[dict] = kb["entradas"]
        self.by_id = {e["id"]: e for e in self.entries}
        self.sources: dict[str, dict] = src["fuentes"]
        self.retriever = Retriever(self.entries, exclude=set(exclude or ()))
        self.last_entry: str | None = None
        self.last_text: str | None = None
        self.pending: list[str] = []  # entradas sugeridas en la última aclaración

    # ---------------------------------------------------------------- utilidades
    def reset(self) -> None:
        self.last_entry = None
        self.last_text = None
        self.pending = []

    def _source_list(self, entry_ids: list[str]) -> list[dict]:
        seen: dict[str, dict] = {}
        for eid in entry_ids:
            for sid in self.by_id[eid]["fuentes"]:
                if sid not in seen:
                    s = self.sources[sid]
                    seen[sid] = {"id": sid, "nombre": s["nombre"], "url": s["url"], "nivel": s["nivel"]}
        return sorted(seen.values(), key=lambda s: (s["nivel"], s["id"]))

    def _suggest_for(self, entry_ids: list[str], n: int = 2) -> list[str]:
        out: list[str] = []
        for eid in entry_ids:
            for rid in self.retriever.related(eid, 3):
                q = self.by_id[rid]["preguntas"][0]
                if rid not in entry_ids and q not in out:
                    out.append(q)
        return out[:n]

    def _examples(self) -> list[str]:
        return [self.by_id[i]["preguntas"][0] for i in ("que_es", "cempasuchil", "origen") if i in self.by_id]

    def _finish(self, reply: Reply, remember: bool = True) -> Reply:
        if remember:
            self.last_text = reply.text
        return reply

    def _resolve_pending(self, text: str, pend: list[str]) -> str | None:
        if not pend:
            return None
        toks = T.raw_tokens(text)
        if not toks or len(toks) > 4:
            return None
        yes = {"si", "sii", "claro", "eso", "esa", "ese", "correcto", "exacto", "aja", "yes", "ok", "vale", "primera", "primero", "1"}
        pos = {"1": 0, "primera": 0, "primero": 0, "2": 1, "segunda": 1, "segundo": 1, "3": 2, "tercera": 2, "tercero": 2}
        for t in toks:
            if t in pos and pos[t] < len(pend):
                return pend[pos[t]]
        if all(t in yes | {"la", "el", "es", "esa", "pregunta", "por", "favor"} for t in toks) and any(t in yes for t in toks):
            return pend[0]
        return None

    def _answer_reply(self, hits, flags, debug, compound=None, tentative=False, force_entry=None) -> Reply:
        if force_entry:
            class _H:  # pseudo-hit para una aclaración confirmada por la persona
                entry_id = force_entry
                score = 1.0
            chosen = [_H()]
        else:
            chosen = compound or [hits[0]]
        ids = [h.entry_id for h in chosen]
        debug["compound"] = bool(compound)
        body = "\n\n".join(self.by_id[i]["respuesta"] for i in ids)
        if tentative:
            body = (f"No estoy del todo seguro, pero creo que preguntas sobre «{self.by_id[ids[0]]['tema']}». "
                    "Esto es lo que sé:\n\n" + body + "\n\nSi no era lo que buscabas, intenta reformular tu pregunta.")
        if flags.get("unsupported"):
            body = G.MSG_UNSUPPORTED + " Lo más cercano que sí puedo ofrecerte es esto:\n\n" + body
        self.last_entry = ids[0]
        return Reply(
            text=body, intent="tentative" if tentative else "answer", entry_id=ids[0], confidence=round(hits[0].score, 3),
            sources=self._source_list(ids), suggestions=self._suggest_for(ids), debug=debug,
        )

    # ---------------------------------------------------------------- API pública
    def reply(self, user_text: str) -> Reply:
        user_text = user_text if isinstance(user_text, str) else str(user_text)
        flags = G.detect(user_text)
        debug: dict = {"flags": sorted(k for k, v in flags.items() if v)}

        # 1) Validación de entrada
        if flags["empty"]:
            return self._finish(Reply(G.MSG_EMPTY, "empty", debug=debug), remember=False)
        if flags["too_long"]:
            return self._finish(Reply(G.MSG_TOO_LONG, "too_long", debug=debug), remember=False)
        if flags["no_letters"]:
            return self._finish(Reply(G.MSG_NO_LETTERS, "no_letters", debug=debug), remember=False)

        # 2) Seguridad y bienestar (prioridad máxima, antes de cualquier búsqueda)
        if flags["crisis"]:
            return self._finish(Reply(G.MSG_CRISIS, "crisis", debug=debug), remember=False)
        if flags["grief"]:
            return self._finish(Reply(G.MSG_GRIEF, "grief", debug=debug), remember=False)
        if flags["abuse"]:
            return self._finish(Reply(G.MSG_ABUSE, "abuse", debug=debug), remember=False)

        # 3) Idioma
        if flags["english"]:
            return self._finish(Reply(G.MSG_ENGLISH, "english", debug=debug), remember=False)

        # 3b) Respuesta a una aclaración previa ("sí", "1", "la segunda")
        pend = self.pending
        self.pending = []
        chosen = self._resolve_pending(user_text, pend)
        if chosen is not None:
            hits = [h for h in self.retriever.search(self.by_id[chosen]["preguntas"][0], k=1)]
            debug["resolved_clarification"] = chosen
            return self._answer_reply(hits, flags, debug, compound=None, force_entry=chosen)

        # 4) Conversación básica
        if flags["greeting"]:
            return self._finish(Reply(G.MSG_GREETING, "greeting", suggestions=self._examples(), debug=debug), remember=False)
        if flags["thanks"]:
            return self._finish(Reply(G.MSG_THANKS, "thanks", debug=debug), remember=False)
        if flags["bye"]:
            return self._finish(Reply(G.MSG_BYE, "bye", debug=debug), remember=False)
        if flags["how_it_works"] and not flags["injection"]:
            return self._finish(self._about_reply(debug), remember=False)
        if flags["identity"] and not flags["injection"]:
            return self._finish(Reply(
                "Soy Muertotron3000, un programa de computadora (no una persona) que responde preguntas sobre el Día de Muertos en México. "
                "No soy un modelo de lenguaje generativo: busco la respuesta más parecida en una base de conocimiento curada y te muestro de qué fuentes viene.",
                "identity", suggestions=self._examples(), debug=debug), remember=False)
        if flags["help"] and not flags["injection"]:
            return self._finish(self._help_reply(debug), remember=False)

        # 5) Seguimientos ("cuéntame más", "repite")
        if flags["repeat"] and self.last_text:
            return Reply(self.last_text, "repeat", entry_id=self.last_entry, debug=debug)
        if flags["more"]:
            return self._more_reply(debug)

        # 6) Recuperación (texto completo y cada oración/cláusula; gana la de mayor puntaje)
        hits = self._best_search(user_text)
        if hits:
            debug["top"] = [
                {"id": h.entry_id, "score": round(h.score, 3), "q": round(h.q, 3), "e": round(h.e, 3), "cov": round(h.c, 3)}
                for h in hits
            ]
        compound = self._compound(user_text, hits)
        if compound:
            return self._answer_reply(hits, flags, debug, compound=compound)
        if hits and hits[0].score >= ACCEPT:
            return self._answer_reply(hits, flags, debug)
        if hits and hits[0].score >= TENTATIVE and not flags["injection"]:
            return self._answer_reply(hits, flags, debug, tentative=True)

        if flags["injection"]:
            return self._finish(Reply(G.MSG_INJECTION, "injection", debug=debug), remember=False)
        if flags["unsupported"]:
            return self._finish(Reply(G.MSG_UNSUPPORTED, "unsupported", suggestions=self._examples(), debug=debug), remember=False)

        if hits and hits[0].score >= CLARIFY:
            ids = list(dict.fromkeys(h.entry_id for h in hits))[:3]
            self.pending = ids
            sugg = [f"{n}) {self.by_id[i]['preguntas'][0]}" for n, i in enumerate(ids, 1)]
            return self._finish(Reply(G.MSG_CLARIFY + " (Responde con el número o con «sí» para la primera.)", "clarify",
                                      confidence=round(hits[0].score, 3), suggestions=sugg, debug=debug), remember=False)

        return self._finish(Reply(G.MSG_OOS, "out_of_scope", confidence=round(hits[0].score, 3) if hits else 0.0,
                                  debug=debug), remember=False)

    def _best_search(self, text: str):
        """Busca con el texto completo y con cada cláusula; conserva el mejor resultado.

        Hace al sistema robusto a saludos o relleno ("Hola, ¿qué es el copal?") sin
        dar ventaja a textos largos: el empate lo gana el texto completo.
        """
        best = self.retriever.search(text, k=3)
        top = best[0].score if best else 0.0
        for seg in re.split(r"[.?!¿¡;,:\n]+", text):
            if len(seg.split()) < 2 or seg.strip() == text.strip():
                continue
            hits = self.retriever.search(seg, k=3)
            if hits and hits[0].score > top + 1e-9:
                best, top = hits, hits[0].score
        return best

    def _compound(self, text: str, hits) -> list | None:
        """Detecta preguntas con dos temas distintos (p. ej. «el copal y la sal»).

        Condición: la consulta tiene >= 2 términos específicos; dos de las tres
        mejores entradas tienen puntaje mínimo; cada una aporta un término que la
        otra no tiene; y entre ambas cubren todos los términos específicos.
        """
        if len(hits) < 2:
            return None
        spec = self.retriever.specific_tokens(text)
        if len(spec) < 2:
            return None
        cands = [h for h in hits[:3] if h.score >= COMPOUND_MIN]
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                a, b = cands[i], cands[j]
                sa = {t for t, own in spec.items() if a.entry_id in own}
                sb = {t for t, own in spec.items() if b.entry_id in own}
                if sa - sb and sb - sa and (sa | sb) == set(spec):
                    return [a, b]
        return None

    # ---------------------------------------------------------------- respuestas especiales
    def _more_reply(self, debug: dict) -> Reply:
        if self.last_entry is None:
            return Reply("¿Más sobre qué? Primero hazme una pregunta sobre el Día de Muertos, por ejemplo: «¿Qué es una ofrenda?».",
                         "more_no_context", suggestions=self._examples(), debug=debug)
        e = self.by_id[self.last_entry]
        if e.get("mas"):
            return Reply(e["mas"], "more", entry_id=e["id"], sources=self._source_list([e["id"]]),
                         suggestions=self._suggest_for([e["id"]]), debug=debug)
        return Reply("Ya te compartí lo principal de ese tema. Quizá te interese alguno de estos temas relacionados:",
                     "more", entry_id=e["id"], suggestions=self._suggest_for([e["id"]], 3), debug=debug)

    def _help_reply(self, debug: dict) -> Reply:
        temas = ", ".join(sorted({e["tema"].split(" (")[0] for e in self.entries[:12]}))
        return Reply(
            "Puedo responder preguntas sobre el Día de Muertos en México: qué es, cuándo se celebra, su origen, "
            "la ofrenda y el significado de sus elementos (cempasúchil, copal, sal, pan de muerto…), la Catrina, "
            "y cómo se vive en regiones como Michoacán, Oaxaca, Yucatán o la Huasteca. "
            "No puedo hablar de otros temas ni hacer tareas por ti.",
            "help", suggestions=self._examples(), debug=debug)

    def _about_reply(self, debug: dict) -> Reply:
        cats = {}
        for s in self.sources.values():
            cats.setdefault(s["nivel"], []).append(s["nombre"])
        return Reply(
            "Mi «experto» es una base de conocimiento curada por escrito: cada respuesta fue redactada a partir de fuentes "
            "identificadas (UNESCO, INAH, SEP, INPI y material de divulgación que cita a instituciones) y cada una está "
            "ligada a sus fuentes en el repositorio. No invento información ni uso un modelo generativo: elijo la entrada "
            "más parecida a tu pregunta (TF-IDF y similitud coseno) y, si no estoy seguro, te lo digo. "
            "Después de cada respuesta te muestro las fuentes usadas, y si la información es de confianza media, "
            "conviene contrastarla con tu maestro o maestra.",
            "about",
            sources=[{"id": sid, "nombre": s["nombre"], "url": s["url"], "nivel": s["nivel"]}
                     for sid, s in sorted(self.sources.items(), key=lambda kv: (kv[1]["nivel"], kv[0]))
                     if sid != "conocimiento_general"],
            debug=debug)
