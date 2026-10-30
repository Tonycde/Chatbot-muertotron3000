# Metodología de pruebas y resultados

## Conjuntos
| Conjunto | Uso | Contenido |
|---|---|---|
| Leave-one-out (KB) | **ajuste** de pesos/umbrales | cada pregunta de la base se consulta con ella excluida |
| `tools/sweep.py` (negativos de desarrollo) | **ajuste** de umbrales | 33 preguntas fuera/cerca de dominio |
| `evaluation/eval_set.json` | **desarrollo** (visto durante el diseño) | 78 paráfrasis, 30 fuera de dominio, 10 cercanas sin respuesta, 42 adversariales |
| `evaluation/holdout_set.json` | **prueba final** | 47 paráfrasis, 15 fuera de dominio, 8 cercanas, 15 adversariales |

### Transparencia metodológica
* Durante el desarrollo se detectó que algunas paráfrasis añadidas a la base duplicaban preguntas de `eval_set.json`
  (fuga de datos); se **eliminaron 54 duplicados exactos**. Aun así, `eval_set.json` queda como conjunto de *desarrollo*:
  sus cifras son optimistas.
* El holdout se escribió con el sistema congelado y se ejecutó una vez. Después se corrigió **un bug** (el patrón de
  «fuentes» capturaba «de dónde viene») y se ajustó **una** expectativa trivial (`1 2 3 4 5` → `no_letters`). Las cifras abajo son
  las posteriores a ese bug; la primera corrida dio 63.8 % de exactitud en paráfrasis.

## Resultados (`python evaluation/run_eval.py [--file holdout_set.json]`)
| Métrica | Desarrollo | Holdout |
|---|---|---|
| Paráfrasis → entrada correcta | 92.3 % (82.1 % directa) | **66.0 %** (53.2 % directa) |
| Fuera de dominio sin inventar | 100 % (30) | 100 % (15) |
| Cercanas al dominio sin dato → no responde | 100 % (10) | 87.5 % (8) — 1 fuga: «a qué hora empieza la alumbrada de Mixquic» devuelve la entrada Mixquic |
| Adversariales / seguridad | 100 % (42) | 100 % (15) |
| Determinismo / independencia del historial | sí | sí |
| Leave-one-out (325 preguntas) | top-1 80.6 % · aceptada 64.3 % | — |

## Interpretación
* **Fortaleza**: seguridad y no-alucinación. Ninguna pregunta fuera de dominio produjo respuesta; ningún intento de inyección
  cambió el comportamiento ni el contenido; las crisis y el duelo reciben respuesta de apoyo.
* **Debilidad**: *recall* en paráfrasis lejanas. Es una limitación inherente a la recuperación léxica con ~7 formulaciones por tema.
  El sistema falla de forma segura: en la mayoría de los fallos pide aclaración o dice que no sabe en lugar de contestar mal
  (en el holdout, 3 de 47 respondieron con una entrada equivocada: 1 con respuesta directa y 2 con aviso «no estoy seguro»).
* **Compromiso umbral**: bajar umbrales sube el recall pero introduce fugas; se priorizó cero fugas en desarrollo.

## Pruebas automáticas (`python -m pytest`, 62 pruebas)
Integridad de la base y fuentes · respuestas correctas (errores de dedo, mayúsculas, sin acentos, saludo+pregunta) ·
preguntas compuestas · fuera de dominio · prompt injection · persona falsa / premisa falsa · crisis · duelo · entradas
hostiles (XSS, SQL, JNDI, path traversal, caracteres de control, emojis, 600 caracteres) · determinismo · independencia del historial ·
seguimientos · umbrales mínimos de calidad sobre ambos conjuntos.
