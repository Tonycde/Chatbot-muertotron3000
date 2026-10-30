# 💀 Muertotron3000 — Chatbot sobre el Día de Muertos en México

Sistema inteligente **basado en conocimiento** para estudiantes de secundaria.
Proyecto de la optativa *Sistemas Inteligentes* (Matemáticas Aplicadas).

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Tonycde/Chatbot-muertotron3000)

> **Para el profesor — probarlo en 1 minuto:** clic en el botón de Codespaces (arriba) → se instala solo y abre la
> interfaz web. Active **«Modo transparencia»** en la barra lateral para ver la entrada elegida, los puntajes y las reglas.
> En Codespaces se abre un editor (VS Code); en la terminal ejecute `streamlit run app.py` si no arrancó solo y abra el puerto **8501** (pestaña PORTS → globo) para ver el chat.
> Alternativa local: `pip install -r requirements.txt && streamlit run app.py` (o `python cli.py --debug`).

## ¿Por qué no usa un LLM?
Decisión de diseño deliberada: el requisito es **consistencia** y **fuente de datos identificable (el «experto»)**.
Un modelo generativo puede inventar, contradecirse o ser manipulado con *prompt injection*. Este sistema:

* **Solo dice lo que está en una base de conocimiento curada** (`data/knowledge_base.json`, 44 entradas).
* **Cita las fuentes** de cada respuesta (`data/sources.json`, con nivel de fiabilidad y estado de verificación).
* **Es determinista**: misma pregunta → misma respuesta, sin importar el historial (verificado con pruebas).
* **Sabe cuándo no sabe**: umbrales de confianza → respuesta directa / con aviso / aclaración / «fuera de mi conocimiento».
* **No ejecuta instrucciones del usuario**: no hay modelo que obedecer; además reglas explícitas responden de forma clara a intentos de manipulación.

## El «experto» (fuente de datos)
Resumen (detalle en [`docs/FUENTES_Y_EXPERTO.md`](docs/FUENTES_Y_EXPERTO.md)): corpus curado manualmente a partir de
**UNESCO, INAH, SEP (Nueva Escuela Mexicana), INPI/Gobierno de México** y material de divulgación que cita a esas
instituciones. Cada afirmación está ligada a su fuente; las entradas con respaldo débil están marcadas
(`confianza: media`, fuente «POR VALIDAR») y listadas en [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md).

## Arquitectura (resumen)
```
mensaje ─▶ validación ─▶ seguridad (crisis/duelo/abuso) ─▶ idioma ─▶ conversación básica
        ─▶ recuperación TF-IDF + coseno (+ cobertura, palabras clave, penalización por palabras desconocidas)
        ─▶ umbrales ─▶ respuesta directa │ con aviso │ aclaración numerada │ fuera de dominio
```
Detalle matemático en [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

## Estructura
```
app.py                 Interfaz web (Streamlit, tema Día de Muertos)   assets/  Ilustraciones SVG propias        cli.py   Interfaz de terminal
muertotron/             text.py · retriever.py · guardrails.py · bot.py
data/                  knowledge_base.json · sources.json
evaluation/            eval_set.json (desarrollo) · holdout_set.json · run_eval.py
tests/                 62 pruebas (pytest)             tools/   sweep.py (calibración) · trazabilidad.py
docs/                  ARQUITECTURA · FUENTES_Y_EXPERTO · PRUEBAS · TRAZABILIDAD · GUIA_PARA_ROMPERLO
```

## Ejecutar pruebas y evaluación
```bash
pip install -r requirements.txt
python -m pytest -q                 # 62 pruebas
python evaluation/run_eval.py -v    # métricas (dev)  |  --file holdout_set.json (holdout)
```

## Resultados (resumen; detalle y limitaciones en [`docs/PRUEBAS.md`](docs/PRUEBAS.md))
| Conjunto | Métrica | Resultado |
|---|---|---|
| Fuera de dominio (45 preguntas) | no inventa respuesta | 100 % |
| Adversarial / seguridad (57 casos) | comportamiento esperado | 98–100 % |
| Paráfrasis en dominio (desarrollo) | entrada correcta | 92 % (82 % respuesta directa) |
| Paráfrasis en dominio (**holdout**) | entrada correcta | **66 %** (53 % directa) |
| Determinismo | misma salida | 100 % |

El holdout es deliberadamente duro (frases muy alejadas de las de la base). La limitación principal es léxica: ver `docs/PRUEBAS.md`.

## Limitaciones conocidas
Sin comprensión semántica profunda (es recuperación léxica); solo español; ~44 temas; algunas entradas dependen de
fuentes por validar. Ante preguntas casi-en-dominio sin dato exacto (p. ej. horarios) puede responder el tema más cercano.

## Licencia
MIT. Los textos de la base son redacciones propias basadas en las fuentes citadas (no copias).
