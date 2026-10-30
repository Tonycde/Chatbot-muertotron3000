# Arquitectura y fundamentos matemáticos

## Tipo de sistema
Sistema basado en conocimiento con recuperación de información (no generativo). Componentes:
**base de conocimiento** (`data/`), **motor de inferencia** (`muertobot/retriever.py`, `bot.py`) y
**capa de seguridad** (`guardrails.py`).

## Pipeline (`Bot.reply`)
1. **Validación**: vacío, > 500 caracteres, sin letras.
2. **Bienestar y seguridad** (antes de cualquier búsqueda): crisis (mensaje de apoyo + Línea de la Vida 800 911 2000 y 911),
   duelo (respuesta empática), insultos.
3. **Idioma**: si detecta inglés, pide español.
4. **Conversación básica**: saludo, gracias, despedida, identidad, ayuda, «¿de dónde sacas la información?».
5. **Seguimientos**: «cuéntame más», «repite», confirmación de una aclaración («sí», «2»).
6. **Recuperación** (texto completo y cada cláusula; gana la mejor) → **decisión por umbrales**.

## Representación del texto (`text.py`)
Normalización (minúsculas, sin acentos), corrección ortográfica por similitud (difflib, ≥ 0.82, palabras ≥ 5 letras),
sinónimos y lematización de dominio (p. ej. *festejan/celebran → celebra*), stopwords, raíz ligera y **bigramas**.

## Puntaje de una entrada
Con TF-IDF sublineal: peso(t, d) = (1 + ln tf) · idf(t), idf(t) = ln((N+1)/(df+1)) + 1, vectores normalizados (L2).

| Señal | Definición |
|---|---|
| q | máx. similitud coseno entre la consulta y cada pregunta de ejemplo de la entrada |
| e | coseno con el documento completo de la entrada (tema + claves + preguntas + respuesta), escalado min(1, 2.5·e) |
| c | cobertura ponderada por IDF de los términos de la consulta presentes en el vocabulario de la entrada |
| k | cobertura ponderada por IDF respecto a las palabras clave/tema curados a mano |
| g | compuerta = clamp((max(q,e')−0.10)/0.30, 0, 1): evita que una coincidencia léxica aislada puntúe alto |
| f_oov | fracción (ponderada) de términos totalmente desconocidos para el sistema |

`score = (0.40·q + 0.15·e' + (0.25·c + 0.20·k)·g) · (1 − 0.9·f_oov)`

Los pesos se eligieron con `tools/sweep.py` (rejilla; criterio: máxima exactitud leave-one-out con **cero falsos positivos**
sobre negativos de desarrollo). El óptimo es plano: varias combinaciones rinden casi igual.

## Umbrales de decisión (`bot.py`)
| Puntaje | Acción |
|---|---|
| ≥ 0.55 | respuesta directa con fuentes |
| 0.42 – 0.55 | respuesta con aviso «no estoy seguro, creo que preguntas sobre…» |
| 0.30 – 0.42 | aclaración con 3 opciones numeradas (el usuario responde «1», «sí»…) |
| < 0.30 | «fuera de mi conocimiento» + ejemplos |

**Preguntas compuestas** («el copal y la sal»): se detectan por términos *específicos* (aparecen en ≤ 6 entradas) cubiertos por
dos entradas distintas, y se responden ambas.

## Por qué es consistente
* Sin aleatoriedad: empates se resuelven por orden (puntaje desc., id asc.).
* Sin memoria que altere respuestas: el historial solo afecta a seguimientos explícitos («más», «repite», «sí»).
* Sin generación: cada texto mostrado está escrito y revisado en la base; nada se compone con la entrada del usuario
  (la entrada **nunca se refleja** en la respuesta; la UI la muestra como texto plano).

## Decisiones de diseño y alternativas descartadas
* **LLM / RAG generativo**: descartado por riesgo de alucinación e inyección de instrucciones y por no ser auditable.
* **Embeddings neuronales**: mejorarían las paráfrasis, pero añaden dependencia pesada y opacidad. Extensión natural
  (ver «Trabajo futuro»).
* **LSA (SVD sobre TF-IDF)**: evaluado conceptualmente; con 44 documentos aporta poco.

## Trabajo futuro
Ampliar paráfrasis con más estudiantes (registro de preguntas sin respuesta), validar entradas con un
experto humano, probar embeddings multilingües como señal adicional manteniendo la misma política de umbrales.
