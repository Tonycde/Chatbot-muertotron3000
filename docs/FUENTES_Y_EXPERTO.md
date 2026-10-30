# La fuente de datos: ¿quién es el «experto»?

## Definición
El experto del sistema **no es un modelo**: es un **corpus curado de fuentes institucionales** más un **proceso de
curaduría y validación humana**.

| Rol | Quién / qué |
|---|---|
| Fuentes primarias (nivel 1) | UNESCO (Lista Representativa del Patrimonio Inmaterial); INAH (fichas y revista *Hereditas*); INPI (Gobierno de México) |
| Fuentes educativas oficiales (nivel 2) | SEP – Nueva Escuela Mexicana; material didáctico UNAM (basado en INPI/INAFED) |
| Divulgación (nivel 3) | Prensa que cita a INPI/UNAM (UnoTV, VIVE USA) — solo para corroborar fechas y símbolos |
| Secundarias (nivel 4) | Wikipedia (únicamente para señalar el debate académico y datos de cultura popular) y conocimiento general **por validar** |
| Curador | El/la autor/a del proyecto: redacta cada respuesta con palabras propias, apropiada para 12–15 años |
| Validador humano | _(completar: nombre y cargo del docente de Historia/Formación Cívica o promotor cultural que revise)_ |

Registro completo con URL, nivel y estado de verificación: `data/sources.json`. Mapa entrada→fuente: `docs/TRAZABILIDAD.md`.

## Proceso de construcción
1. Búsqueda de fuentes institucionales (consulta realizada el 30/10/2026; se leyeron fragmentos accesibles vía buscador).
2. Redacción de cada entrada: respuesta corta (15–160 palabras), 5–11 formas de preguntarla, palabras clave y fuentes.
3. Etiquetado de **confianza**: *alta* = respaldada por fuente nivel ≤ 2; *media* = respaldo parcial, tradición regional o
   dato por contrastar.
4. Pruebas automáticas de integridad (`tests/test_knowledge_base.py`): toda entrada cita fuentes existentes y las de confianza alta
   exigen fuente institucional.

## Honestidad sobre el estado actual (leer antes de la entrega)
* **18 de 44 entradas** dependen de una fuente marcada *POR VALIDAR* (principalmente regiones, Catrina/Posada, Mictlán, mascotas).
  Su contenido es conocimiento general ampliamente difundido, pero **no se contrastó con una fuente institucional concreta**.
* La página del INPI y la de la Secretaría de Cultura CDMX se citan pero solo se vieron referencias/títulos, no el texto completo.
* Hay diversidad real de prácticas entre regiones y familias; el sistema lo declara en las respuestas pertinentes.
* El debate académico sobre cuánto del Día de Muertos es prehispánico vs. colonial/moderno está representado en la entrada
  `debate_origen`, sin tomar partido.

## Cómo cerrar los pendientes (checklist del autor)
- [ ] Abrir cada URL de `sources.json` y confirmar que el contenido respalda lo escrito.
- [ ] Sustituir `conocimiento_general` por referencias concretas (libro, museo, INAH) y cambiar `estado`.
- [ ] Que un docente/experto revise las 44 respuestas y se anote en la tabla de arriba.
- [ ] Re-ejecutar `python tools/trazabilidad.py > docs/TRAZABILIDAD.md` y `python -m pytest`.
