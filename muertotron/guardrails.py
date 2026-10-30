"""Reglas de seguridad y de conversación (capa previa a la recuperación).

Son reglas explícitas y auditables (expresiones regulares sobre texto
normalizado). Como el sistema NO usa un modelo generativo, estas reglas no
son lo que impide que lo "rompan" con prompt injection; sirven para dar
respuestas claras, consistentes y transparentes ante esos intentos.
"""
from __future__ import annotations

import re

from . import text as T

MAX_CHARS = 500

# Contacto de ayuda en México (verificar vigencia antes de entregar; ver docs).
LINEA_DE_LA_VIDA = "800 911 2000"

# ------------------------------------------------------------------ patrones
_CRISIS = [
    r"\b(quiero|quisiera|pienso|voy a|me gustaria|ganas de)\s+(morir|morirme|matarme|suicidarme|desaparecer)",
    r"\bme (quiero|voy a|pienso|quisiera) (matar|suicidar)",
    r"\bsuicid",
    r"\bno quiero (vivir|seguir viviendo|estar vivo|estar viva|seguir aqui)",
    r"\b(hacerme|hacerle) dano\b",
    r"\bautolesion",
    r"\bcortarme\b",
    r"\bya no quiero estar aqui\b",
    r"\bmejor (estar|estaria) (muerto|muerta)\b",
    r"\bojala (me muriera|estuviera muerto|estuviera muerta|no despertar)",
    r"\bacabar con (todo|mi vida)\b",
    r"\bterminar con (todo|mi vida)\b",
]

_GRIEF = [
    r"\b(se murio|murio|fallecio|se me murio|perdi a|extrano a|extrano mucho a|me hace falta)\s+(mi|mis|a mi|a mis)?\s*"
    r"(abuel|papa|mama|pap|mam|herman|tio|tia|prim|amig|hij|perr|gat|mascota|novi)",
    r"\bestoy triste porque\b.*\b(murio|fallecio|perdi)",
    r"\b(mi|mis)\s+(abuel\w*|papa|mama|herman\w*|tio|tia|amig\w*|perr\w*|gat\w*)\s+(murio|fallecio|se murio|ya no esta)\b",
]

_INJECTION = [
    r"\bignor\w*\s+(todo|todas|todos|tus|las|los|lo|el|la)?\s*(las |los )?(instrucciones|reglas|indicaciones|restricciones|anteriores|previo\w*)",
    r"\b(olvida|olvidate de)\s+(todo|tus|las|lo)",
    r"\b(ignore|disregard|forget)\s+(all|your|previous|the)",
    r"\b(system|developer)\s*prompt\b",
    r"\bprompt (del )?(sistema|inicial|oculto)\b",
    r"\b(tus|sus) instrucciones\b",
    r"\b(muestra|revela|dime|repite|imprime|dame)\s+(tu|tus|el|las)\s+(prompt|instrucciones|configuracion|reglas)",
    r"\b(eres|seras|ahora eres|a partir de ahora (eres|seras))\s+(un|una|el|la)?\s*(\w+\s+){0,2}(sin (filtros|restricciones|reglas)|dan|libre)",
    r"\b(actua|actuas|comportate|finge|simula|haz de cuenta|pretende|imagina que eres)\b.*\b(como|que eres|ser)\b",
    r"\bolvida\b",
    r"\b(ahora|ya) (eres|seras|no eres)\b",
    r"\bdeja de ser\b",
    r"\bnuevas? reglas\b",
    r"\[ ?(system|sistema|admin|developer)\b",
    r"\bmodo (desarrollador|dios|libre|sin restricciones|developer|dan)\b",
    r"\bjailbreak\b",
    r"\bsin (restricciones|filtros|censura|limites)\b",
    r"\b(roleplay|role play|juego de roles)\b",
    r"\bdo anything now\b",
    r"\ba partir de ahora\b",
    r"\bresponde (solo|unicamente) (con|en)\b",
    r"\bcontrasena|password|api key|clave secreta|token secreto\b",
]

_UNSUPPORTED = [
    r"\b(escribe|escribeme|redacta|redactame|genera|generame|crea|creame|hazme|haz|inventa|inventame|dame un)\s+(un|una|mi|el|la|unos|unas)?\s*"
    r"(ensayo|poema|cuento|historia|resumen|tarea|codigo|programa|script|cancion|carta|discurso|calavera|texto|trabajo|redaccion|informe)",
    r"\bhaz(me)? mi tarea\b",
    r"\b(traduce|traduceme|traducir)\b",
    r"\b(resuelve|resuelveme|calcula|calculame)\b",
    r"\b(programa|codigo) en (python|java|c\+\+|javascript|c)\b",
    r"\b(dibuja|dibujame|genera una imagen|crea una imagen)\b",
    r"\b(en ingles|en frances|en aleman|en italiano|en portugues|en chino|en japones)\b",
]

_ABUSE = [
    r"\b(pendej\w*|idiota\w*|estupid\w*|imbecil\w*|tont[oa]s?|mierda|put[oa]s?|chinga\w*|verga|cabron\w*|culer[oa]s?|pinche|maldit[oa]|inutil\w*|bruto|bruta|baboso|babosa)\b",
]

_ENGLISH_WORDS = {
    "the", "what", "is", "are", "how", "who", "why", "when", "where", "of", "in",
    "tell", "me", "about", "you", "can", "do", "does", "day", "dead", "and", "your",
    "hello", "please", "explain", "which", "this", "that", "with", "for", "my",
    "all", "previous", "instructions", "ignore", "say", "write", "give", "show", "system", "prompt",
    "now", "will", "from", "tradition", "mexico", "mexican", "altar", "offering", "skull", "celebrate",
}

_GREETING_TOKENS = {
    "hola", "holi", "holaa", "buenas", "buenos", "dias", "tardes", "noches", "buen", "dia",
    "que", "tal", "hey", "ey", "saludos", "hello", "hi", "como", "estas", "onda", "pasa",
    "quiubo", "quihubo", "qué",
}
_THANKS_TOKENS = {"gracias", "muchas", "mil", "muy", "amable", "ok", "vale", "perfecto", "genial",
                  "excelente", "listo", "entendido", "chido", "super", "bueno", "bien", "thanks", "okey", "okay"}
_BYE_TOKENS = {"adios", "chao", "chau", "bye", "hasta", "luego", "pronto", "nos", "vemos", "despedida", "me", "voy"}

_IDENTITY = [
    r"\bquien eres\b", r"\bcomo te llamas\b", r"\bcual es tu nombre\b", r"\beres (un |una )?(robot|bot|ia|inteligencia artificial|humano|persona|real)\b",
    r"\bque eres\b", r"\beres chat ?gpt\b", r"\beres (claude|gemini|gpt|copilot|alexa|siri)\b",
]
_HOW_IT_WORKS = [
    r"\bde donde (sacas|obtienes) (tu|tus|la|las|esa|esas|esta|estas)\b", r"\bfuentes?\b", r"\bquien (te|lo) (informa|informo|enseno|programo|hizo|creo|alimenta)\b",
    r"\bquien es tu experto\b", r"\b(tu|el|quien es el) experto\b", r"\bcomo funcionas\b", r"\bcomo (estas )?(hecho|programado|construido)\b",
    r"\bque modelo (usas|eres)\b", r"\busas (chat ?gpt|gpt|ia|inteligencia artificial|un llm)\b", r"\bpor que (deberia|debo) (creerte|confiar)\b",
    r"\bque tan confiable\b", r"\btu informacion (es|esta)\b", r"\bbase de conocimiento\b", r"\bllm\b",
    r"\bque sabes\b.*\bdonde\b", r"\bcomo sabes\b",
]
_HELP = [
    r"^(ayuda|help|menu|temas|opciones|instrucciones)$", r"\bque (puedes|sabes) (hacer|responder|contestar)\b", r"\ben que (me )?(puedes )?ayud\w+\b",
    r"\bde que (puedes )?(hablar|hablas)\b", r"\bque temas\b", r"\bque preguntas (puedo|puedes)\b", r"\bpara que sirves\b",
]
_MORE = [
    r"^(y )?(que )?mas( datos| informacion| info)?\??$", r"\b(cuentame|dime|explica|dame|quiero|necesito|amplia|profundiza)\w*( me)? (un poco |algo )?(mas|otro dato|otra cosa|mas detalles|mas informacion)\b",
    r"^(otro|otra)( dato| cosa)?$", r"^(sigue|continua|continua por favor)$", r"^y eso\??$", r"^(y )?por que\??$", r"^profundiza$",
    r"^(dame )?(un )?dato curioso$", r"^(algo )?mas( sobre eso)?$",
]
_REPEAT = [r"\b(repite|repitelo|repetir|otra vez|de nuevo|no entendi)\b"]


def _any(patterns: list[str], s: str) -> bool:
    return any(re.search(p, s) for p in patterns)


def _only_tokens(s: str, allowed: set[str], required: set[str] | None = None) -> bool:
    toks = s.split()
    if not toks or len(toks) > 6:
        return False
    if not all(t in allowed for t in toks):
        return False
    return required is None or any(t in required for t in toks)


# ------------------------------------------------------------------ detectores
def detect(raw: str) -> dict[str, bool | str]:
    """Analiza el mensaje y devuelve banderas. No decide la respuesta final."""
    s = T.normalize(raw)
    toks = s.split()
    letters = sum(ch.isalpha() for ch in raw)
    flags: dict[str, bool | str] = {
        "empty": not raw.strip(),
        "too_long": len(raw) > MAX_CHARS,
        "no_letters": bool(raw.strip()) and letters == 0,
        "crisis": _any(_CRISIS, s),
        "grief": _any(_GRIEF, s),
        "injection": _any(_INJECTION, s),
        "unsupported": _any(_UNSUPPORTED, s),
        "abuse": _any(_ABUSE, s),
        "greeting": _only_tokens(s, _GREETING_TOKENS | {"dia", "dias"}, {"hola", "holi", "holaa", "buenas", "buenos", "buen", "hey", "ey", "saludos", "hello", "hi", "quiubo", "quihubo"}),
        "thanks": _only_tokens(s, _THANKS_TOKENS, {"gracias", "thanks", "ok", "vale", "okey", "okay", "perfecto", "genial", "excelente", "entendido", "listo", "chido", "super"}),
        "bye": _only_tokens(s, _BYE_TOKENS, {"adios", "chao", "chau", "bye", "hasta", "vemos"}),
        "identity": _any(_IDENTITY, s),
        "how_it_works": _any(_HOW_IT_WORKS, s),
        "help": _any(_HELP, s),
        "more": _any(_MORE, s),
        "repeat": _any(_REPEAT, s),
    }
    eng = sum(t in _ENGLISH_WORDS for t in toks)
    flags["english"] = eng >= 2 and eng >= len(toks) * 0.5
    return flags


# ------------------------------------------------------------------ respuestas fijas
MSG_EMPTY = "Escribe tu pregunta sobre el Día de Muertos y con gusto te ayudo."
MSG_TOO_LONG = (
    f"Tu mensaje es muy largo (máximo {MAX_CHARS} caracteres). "
    "¿Puedes hacer una pregunta más corta y concreta sobre el Día de Muertos?"
)
MSG_NO_LETTERS = "No logré entender ese mensaje. Intenta escribir tu pregunta con palabras, por ejemplo: «¿Qué es una ofrenda?»"
MSG_ENGLISH = (
    "Por ahora solo puedo conversar en español. ¿Puedes escribir tu pregunta en español?\n\n"
    "(I can only chat in Spanish for now. Please ask your question about Día de Muertos in Spanish.)"
)
MSG_CRISIS = (
    "Siento mucho que estés pasando por algo tan difícil. Lo que sientes importa y no tienes que enfrentarlo solo o sola. "
    "Por favor, habla ahora con un adulto de confianza (familiar, maestro, orientador) y cuéntale cómo te sientes.\n\n"
    f"En México puedes comunicarte con la Línea de la Vida al {LINEA_DE_LA_VIDA} (gratuita), "
    "y si estás en peligro o necesitas ayuda urgente, llama al 911.\n\n"
    "Soy un programa informativo sobre el Día de Muertos y no puedo ayudarte como lo haría una persona, "
    "pero me importa que recibas apoyo."
)
MSG_GRIEF = (
    "Lamento mucho tu pérdida. Es normal sentir tristeza y extrañar a esa persona. "
    "El Día de Muertos nació justamente para recordar con cariño a quienes ya no están: "
    "puedes armar una pequeña ofrenda con su foto y lo que le gustaba, contar historias suyas con tu familia "
    "o escribirle una carta. Hablar con un adulto de confianza sobre cómo te sientes también puede ayudarte.\n\n"
    "Si quieres, puedo contarte cómo armar una ofrenda."
)
MSG_ABUSE = "Prefiero que conversemos con respeto. Con gusto respondo tus dudas sobre el Día de Muertos en México."
MSG_INJECTION = (
    "No puedo cambiar mis reglas ni revelar o modificar mi configuración: soy un sistema basado en una base de conocimiento "
    "fija sobre el Día de Muertos en México, y solo respondo con esa información. ¿Qué te gustaría saber de la tradición?"
)
MSG_UNSUPPORTED = (
    "No puedo hacer esa tarea (por ejemplo redactar textos, traducir, programar o resolver ejercicios): "
    "solo respondo preguntas sobre el Día de Muertos con la información de mi base de conocimiento."
)
MSG_GREETING = (
    "¡Hola! Soy Muertotron3000. Puedo responder preguntas sobre el Día de Muertos en México: su historia, "
    "la ofrenda y sus símbolos, y cómo se celebra en distintas regiones. ¿Qué te gustaría saber?"
)
MSG_THANKS = "¡Con gusto! Si tienes otra duda sobre el Día de Muertos, aquí estoy."
MSG_BYE = "¡Hasta luego! Que disfrutes mucho esta tradición mexicana."
MSG_OOS = (
    "Eso queda fuera de lo que sé: mi conocimiento se limita al Día de Muertos en México. "
    "Prueba con una pregunta como: «¿Qué es una ofrenda?», «¿Por qué se usa el cempasúchil?» o «¿Cuál es el origen del Día de Muertos?»."
)
MSG_CLARIFY = "No estoy seguro de haber entendido tu pregunta. ¿Quisiste preguntar alguna de estas?"
