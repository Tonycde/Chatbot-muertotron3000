"""Recuperación de información: TF-IDF + coseno implementados desde cero.

La puntuación combina tres señales (todas en [0, 1]):

  q  : mayor similitud coseno entre la consulta y alguna de las preguntas de
       ejemplo de la entrada (captura paráfrasis cercanas).
  e  : similitud coseno entre la consulta y el "documento" completo de la
       entrada (tema + palabras clave + preguntas + respuesta).
  c  : cobertura ponderada por IDF de los términos de la consulta que existen
       en el vocabulario de la entrada (penaliza palabras desconocidas).

e' = min(1, E_GAIN * e)
gate = clamp((max(q, e') - GATE_LO) / GATE_W, 0, 1)
score = (W_Q * q + W_E * e' + (W_C * c + W_K * k) * gate) * (1 - OOV_PENALTY * f_oov)

  f_oov: fracción (ponderada) de términos de la consulta totalmente desconocidos.

  k  : cobertura (ponderada por IDF) de los términos de la consulta que están en
       las palabras clave y el tema curados a mano para la entrada.

La compuerta (gate) evita que una coincidencia léxica aislada (por ejemplo, una
sola palabra que casualmente aparece en una respuesta) alcance puntaje alto sin
evidencia de similitud real con la pregunta o con el tema de la entrada.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from . import text as T

W_Q, W_E, W_C, W_K = 0.40, 0.15, 0.25, 0.20
E_GAIN = 2.5
OOV_PENALTY = 0.9  # fracción del puntaje que se pierde si TODA la consulta es desconocida
OOV_WEIGHT = 0.6  # peso (relativo al idf máximo) de una palabra totalmente desconocida
GATE_LO, GATE_W = 0.10, 0.30

SparseVec = dict[str, float]


def _tf_idf(tokens: list[str], idf: dict[str, float], default_idf: float) -> SparseVec:
    counts = Counter(tokens)
    vec = {t: (1.0 + math.log(c)) * idf.get(t, default_idf) for t, c in counts.items()}
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {t: v / norm for t, v in vec.items()} if norm else {}


def cosine(a: SparseVec, b: SparseVec) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def _fit_idf(docs: list[list[str]]) -> tuple[dict[str, float], float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
    return idf, math.log(n + 1) + 1.0  # idf de un término nunca visto


@dataclass
class Hit:
    entry_id: str
    score: float
    q: float
    e: float
    c: float
    k: float = 0.0
    matched_question: str = ""


@dataclass
class Retriever:
    entries: list[dict]
    exclude: set[tuple[str, int]] = field(default_factory=set)  # (id, idx) para validación leave-one-out

    def __post_init__(self) -> None:
        # Vocabulario crudo (para corrección ortográfica).
        vocab: set[str] = set()
        for e in self.entries:
            blob = " ".join([e["tema"], *e["preguntas"], *e["palabras_clave"], e["respuesta"]])
            vocab.update(t for t in T.raw_tokens(blob) if t not in T.STOPWORDS)
        # Incluir las formas canónicas de sinónimos para que la corrección las encuentre.
        vocab.update(T.SYNONYMS.keys())
        self.vocab = vocab

        # Índice A: preguntas de ejemplo.
        self._questions: list[tuple[str, str, list[str]]] = []  # (entry_id, texto, tokens)
        for e in self.entries:
            for i, q in enumerate(e["preguntas"]):
                if (e["id"], i) in self.exclude:
                    continue
                self._questions.append((e["id"], q, T.with_bigrams(T.content_tokens(q))))
        self._idf_q, self._def_q = _fit_idf([t for _, _, t in self._questions])
        self._q_vecs = [_tf_idf(t, self._idf_q, self._def_q) for _, _, t in self._questions]

        # Índice B: documento completo por entrada.
        self._entry_tokens: dict[str, list[str]] = {}
        for e in self.entries:
            qs = [q for i, q in enumerate(e["preguntas"]) if (e["id"], i) not in self.exclude]
            blob = " ".join([e["tema"]] * 2 + e["palabras_clave"] * 2 + qs + [e["respuesta"]])
            self._entry_tokens[e["id"]] = T.with_bigrams(T.content_tokens(blob))
        ids = [e["id"] for e in self.entries]
        self._idf_e, self._def_e = _fit_idf([self._entry_tokens[i] for i in ids])
        self._e_vecs = {i: _tf_idf(self._entry_tokens[i], self._idf_e, self._def_e) for i in ids}
        self._e_vocab = {i: set(self._entry_tokens[i]) for i in ids}
        # Términos curados (tema + palabras clave) por entrada.
        self._e_keys = {
            e["id"]: set(T.content_tokens(" ".join([e["tema"], *e["palabras_clave"]]))) for e in self.entries
        }

    # ------------------------------------------------------------------ consulta
    def query_tokens(self, text: str) -> list[str]:
        return T.content_tokens(text, self.vocab)

    def search(self, text: str, k: int = 3) -> list[Hit]:
        toks = self.query_tokens(text)
        if not toks:
            return []
        q_vec_q = _tf_idf(T.with_bigrams(toks), self._idf_q, self._def_q)
        q_vec_e = _tf_idf(T.with_bigrams(toks), self._idf_e, self._def_e)

        best_q: dict[str, tuple[float, str]] = {}
        for (eid, qtext, _), vec in zip(self._questions, self._q_vecs):
            s = cosine(q_vec_q, vec)
            if s > best_q.get(eid, (0.0, ""))[0]:
                best_q[eid] = (s, qtext)

        uniq = [t for t in dict.fromkeys(toks) if not (t.isdigit() and t not in self._idf_e)]
        weights = {t: self._idf_e.get(t, OOV_WEIGHT * self._def_e) for t in uniq}
        total_w = sum(weights.values()) or 1.0
        oov_frac = sum(w for t, w in weights.items() if t not in self._idf_e) / total_w
        keep = 1.0 - OOV_PENALTY * oov_frac

        hits: list[Hit] = []
        for e in self.entries:
            eid = e["id"]
            q, qtext = best_q.get(eid, (0.0, ""))
            ev = cosine(q_vec_e, self._e_vecs[eid])
            cov = sum(w for t, w in weights.items() if t in self._e_vocab[eid]) / total_w
            e_scaled = min(1.0, E_GAIN * ev)
            gate = max(0.0, min(1.0, (max(q, e_scaled) - GATE_LO) / GATE_W))
            key = sum(w for t, w in weights.items() if t in self._e_keys[eid]) / total_w
            score = (W_Q * q + W_E * e_scaled + (W_C * cov + W_K * key) * gate) * keep
            hits.append(Hit(eid, round(score, 6), round(q, 6), round(ev, 6), round(cov, 6), round(key, 6), qtext))
        # Orden estable: puntuación desc., luego id (determinismo en empates).
        hits.sort(key=lambda h: (-h.score, h.entry_id))
        return hits[:k]

    def components(self, text: str) -> dict[str, tuple[float, float, float, float]]:
        """(q, e, cov, key) de todas las entradas; útil para calibrar pesos (tools/sweep.py)."""
        toks = self.query_tokens(text)
        if not toks:
            return {e["id"]: (0.0, 0.0, 0.0, 0.0) for e in self.entries}
        hits = self.search(text, k=len(self.entries))
        return {h.entry_id: (h.q, h.e, h.c, h.k) for h in hits}

    def specific_tokens(self, text: str, max_df: int = 6) -> dict[str, set[str]]:
        """Para cada término *específico* de la consulta (aparece en <= max_df
        entradas), devuelve el conjunto de entradas cuyo vocabulario lo contiene."""
        out: dict[str, set[str]] = {}
        for t in dict.fromkeys(self.query_tokens(text)):
            owners = {i for i, voc in self._e_vocab.items() if t in voc}
            if 0 < len(owners) <= max_df:
                out[t] = owners
        return out

    def related(self, entry_id: str, k: int = 3) -> list[str]:
        """Entradas más cercanas a `entry_id` (coseno entre vectores de entrada)."""
        base = self._e_vecs[entry_id]
        sims = [(cosine(base, v), i) for i, v in self._e_vecs.items() if i != entry_id]
        sims.sort(key=lambda p: (-p[0], p[1]))
        return [i for _, i in sims[:k]]
