"""Procesamiento de texto en español: normalización, tokenización y raíz ligera.

Todo es determinista y sin dependencias externas.
"""
from __future__ import annotations

import re
import unicodedata

# Palabras vacías: se eliminan porque casi no aportan significado.
# Se conservan a propósito palabras interrogativas informativas
# (cuándo, dónde, cuántos, quién, cómo) porque distinguen preguntas.
STOPWORDS = frozenset(
    """
    a al algo algunas algunos ante antes aqui asi aun aunque cada con contra
    cual cuales cuyo de del desde donde dos e el ella ellas ellos en entre eres
    es esa esas ese eso esos esta estan estar este esto estos fue ha hace hacen
    han hasta hay la las le les lo los me mi mis mucho muy nada ni no nos o os
    otra otras otro otros para pero poco por porque que se ser si sin sobre son
    su sus tambien te tengo ti tiene tienen todo todos tu tus un una uno unos
    va vas voy y ya yo se sera seria puede pueden puedo podria quiero quiere
    dime digame explicame cuentame decir dices oye oyes onda pues bueno entonces porfa favor plis wey guey neta osea hey ey ps ok
    """.split()
)

# Sinónimos / variantes ortográficas -> forma canónica (ya sin acentos).
SYNONYMS = {
    "q": "que",
    "k": "que",
    "ke": "que",
    "pq": "que",
    "xq": "por",
    "x": "por",
    "d": "de",
    "cmo": "como",
    "tmb": "tambien",
    "altar": "ofrenda",
    "altares": "ofrenda",
    "ofrendas": "ofrenda",
    "cempasuchitl": "cempasuchil",
    "zempasuchil": "cempasuchil",
    "cempoalxochitl": "cempasuchil",
    "cempohualxochitl": "cempasuchil",
    "zempoalxochitl": "cempasuchil",
    "cempazuchil": "cempasuchil",
    "cempasuchiles": "cempasuchil",
    "veladora": "vela",
    "veladoras": "vela",
    "cirio": "vela",
    "cirios": "vela",
    "incienso": "copal",
    "sahumerio": "copal",
    "sahumerios": "copal",
    "cementerio": "panteon",
    "cementerios": "panteon",
    "tumbas": "tumba",
    "difuntos": "muertos",
    "difunto": "muerto",
    "fallecidos": "muertos",
    "fallecido": "muerto",
    "fallecidas": "muertos",
    "fallecida": "muerto",
    "jalogüin": "halloween",
    "jalowin": "halloween",
    "hallowen": "halloween",
    "ninos": "nino",
    "ninas": "nino",
    "catrin": "catrina",
    "calaveritas": "calavera",
    "calaveras": "calavera",
    "calaca": "calavera",
    "calacas": "calavera",
    "esqueleto": "calavera",
    "esqueletos": "calavera",
    "azteca": "mexica",
    "aztecas": "mexica",
    "mexicas": "mexica",
    "prehispanica": "prehispanico",
    "prehispanicos": "prehispanico",
    "prehispanicas": "prehispanico",
    "mayas": "maya",
    "purepechas": "purepecha",
    "perrito": "perro",
    "perritos": "perro",
    "perros": "perro",
    "gatos": "gato",
    "mascotas": "mascota",
    "fotos": "foto",
    "fotografia": "foto",
    "fotografias": "foto",
    "retrato": "foto",
    "retratos": "foto",
    "animas": "anima",
    "almas": "alma",
    "cdmx": "mexico",
}


# Lematización de dominio: verbos y términos equivalentes -> una sola forma.
_GROUPS = {
    "celebra": "festejan festeja festejar festejo festejos festejamos celebran celebra celebrar celebramos celebro",
    "fiesta": "celebracion celebraciones festividad festividades fiesta fiestas tradicion tradiciones costumbre costumbres",
    "origen": "salio surgio nacio empezo comenzo inicio viene vienen proviene procede comienzo empieza empezar surge nace origino originaron historia",
    "crear": "invento inventaron inventor creo creador creada creado crearon",
    "nino": "chiquitos chiquito pequenos pequeno infantil infantiles infancia",
    "cuanto": "cuantos cuantas cuanta",
    "nivel": "niveles escalon escalones piso pisos",
    "gato": "gatito gatitos gatos",
    "experto": "historiadores historiador especialistas especialista academicos expertos investigadores",
    "alma": "almas anima animas espiritu espiritus",
    "mexico": "mexicano mexicanos mexicana mexicanas",
    "significa": "significan significado significados simboliza simbolizan representa representan simbolo simbolos representacion",
    "sirve": "sirven utilidad funcion usa usan utiliza utilizan uso",
    "poner": "ponen pone colocan coloca colocar poniendo pongo ponemos ponerle",
    "hacer": "hago hacemos armar armo preparar preparan construir montar",
    "morir": "murio muere murieron fallecio fallecieron",
    "encender": "enciende encienden encender prende prenden prender prendido encendidas encendidos",
    "elemento": "elementos partes parte componentes componente piezas cosas objetos materiales",
    "diferencia": "diferente diferentes diferencian distinto distintos distinta igual iguales parecen parecido",
}
for _canon, _words in _GROUPS.items():
    for _w in _words.split():
        SYNONYMS.setdefault(_w, _canon)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def strip_accents(text: str) -> str:
    """Quita acentos y diéresis, y convierte ñ en n."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    """minúsculas, sin acentos, solo letras/dígitos separados por un espacio."""
    text = strip_accents(text.lower())
    return _NON_ALNUM.sub(" ", text).strip()


def stem(token: str) -> str:
    """Raíz ligera: quita plural y vocal final. Suficiente para este dominio."""
    if len(token) <= 3 or token.isdigit():
        return token
    if token.endswith("es") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]
    if len(token) > 4 and token[-1] in "aeo":
        token = token[:-1]
    return token


def raw_tokens(text: str) -> list[str]:
    """Tokens normalizados (sin quitar stopwords ni aplicar raíz)."""
    return normalize(text).split()


def content_tokens(text: str, vocabulary: set[str] | None = None) -> list[str]:
    """Tokens de contenido listos para indexar o consultar.

    Pasos: normalizar -> (corregir ortografía contra `vocabulary`) -> sinónimos
    -> quitar stopwords -> raíz.
    """
    out: list[str] = []
    for tok in raw_tokens(text):
        if vocabulary is not None and tok not in vocabulary and tok not in STOPWORDS:
            tok = correct_spelling(tok, vocabulary)
        tok = SYNONYMS.get(tok, tok)
        if tok in STOPWORDS:
            continue
        out.append(stem(tok))
    return out


def with_bigrams(tokens: list[str]) -> list[str]:
    """Agrega bigramas (p. ej. 'papel_picado') para capturar términos compuestos."""
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]


def correct_spelling(token: str, vocabulary: set[str]) -> str:
    """Corrige errores de dedo comparando con el vocabulario conocido.

    Solo actúa en palabras de 5+ letras y con similitud >= 0.82, para no
    "inventar" coincidencias. Es determinista (desempate alfabético).
    """
    if len(token) < 5 or token in vocabulary:
        return token
    import difflib

    matches = difflib.get_close_matches(token, sorted(vocabulary), n=1, cutoff=0.82)
    return matches[0] if matches else token
