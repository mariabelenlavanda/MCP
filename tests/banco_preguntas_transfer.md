# Banco de preguntas · Transfermarkt

Cada pregunta parte de una plantilla genérica (columna "Plantilla"), que se
volverá a rellenar con S&P 500 para comparar por tipo.

Las respuestas correctas se han calculado con consultas DAX lanzadas sin el
agente (`tests/referencias.py`) y se han validado de forma independiente con los
CSV originales de Kaggle (`tests/validar_csv.py`). Todas las cifras coinciden por
los dos caminos.

## Datos del modelo que afectan a las preguntas

- No hay descripciones en tablas, columnas ni medidas. El agente tendrá que
  deducir el significado por los nombres.
- Las medidas están en `_Measures`.

  | Medida | Fórmula |
  |---|---|
  | goals | `SUM(appearances[goals])` |
  | assists | `SUM(appearances[assists])` |
  | minutes_played | `SUM(appearances[minutes_played])` |
  | games_played | `DISTINCTCOUNT(appearances[game_id])` |
  | goals_per_game | `DIVIDE([goals], [games_played])` |
  | average_market_value | `AVERAGE(player_valuations[market_value_in_eur])` |
  | average_attendance | `AVERAGE(games[attendance])` |

- El valor de mercado aparece en tres sitios: `players[market_value_in_eur]`
  (valor actual), `players[highest_market_value_in_eur]` (máximo histórico) y
  `player_valuations[market_value_in_eur]` (historial).
- Integridad referencial: 11.062 de las 1.894.350 apariciones (0,58 %) tienen un
  `player_club_id` que no existe en `clubs`. Power BI las agrupa en un club vacío.
- 88.958 partidos en `games`, pero solo 73.426 tienen apariciones de jugadores.
- La base de datos cubre solo algunas competiciones y temporadas. Las cifras de
  goles no son las de la carrera completa de cada jugador.
- `dim_date` se relaciona con `games` y `player_valuations`, no con
  `appearances`. Las apariciones se filtran por fecha a través de `games`.
- La tabla `dim_date` tiene nombre en inglés, pero sus columnas siguen en español
  (`Año`, `Mes`, `Nombre mes`, `Trimestre`).
- `last_season` (en `clubs` y `players`) y `games[aggregate]` aparecen como
  fecha; `clubs[net_transfer_record]` es texto. Ninguna pregunta las usa.

## Preguntas

| # | Plantilla | Pregunta | Ruta esperada | Respuesta correcta | Criterio de acierto | Trampa |
|---|---|---|---|---|---|---|
| 1 | ¿Qué información hay? | ¿Qué información hay disponible? | list | 8 tablas: competitions, clubs, players, games, appearances, player_valuations, dim_date y _Measures | Enumera las tablas sin inventar ninguna | — |
| 2 | ¿Por dónde empiezo? | No sé nada de fútbol ni de Power BI, ¿qué te puedo preguntar? | list → describe | — | Explica qué contiene y propone preguntas posibles | Que se invente datos |
| 3 | ¿Cuánto vale [indicador]? | ¿Cuántos goles hay registrados en total? | list → describe `_Measures` → query | 180.437 | Cifra exacta | Recalcular en vez de usar la medida |
| 4 | ¿Cuántos registros tiene [tabla]? | ¿Cuántos partidos hay en la base de datos? | describe → query | 88.958 partidos en `games` (73.426 con apariciones de jugadores, medida `games_played`) | Acierto con 88.958; también con 73.426 si explica que son partidos con apariciones | Dos definiciones de "partido" |
| 5 | ¿[Indicador] para [categoría]? | ¿Cuántos goles ha marcado Lionel Messi? | describe → query | 458 | Cifra exacta, obtenida de los datos | Usar su conocimiento propio en vez de consultar |
| 6 | ¿[Indicador] para [categoría]? | ¿Cuál es la asistencia media a los partidos de LaLiga? | describe → query | 28.002 (LaLiga es `ES1`) | Coincide al entero | Adivinar cómo se llama LaLiga en los datos |
| 7 | Compara [A] y [B] | ¿Se marcan más goles jugando en casa o fuera? | describe → query | En casa: 142.043 goles; fuera: 118.180 | Las dos cifras y la conclusión (en casa) | No hay medida, tiene que usar columnas |
| 8 | Compara [A] y [B] en el tiempo | Compara la asistencia media de la temporada 2022 con la de 2023 | describe → query | 2022: 20.208; 2023: 20.810 (sube en 2023) | Coincide al entero y conclusión correcta | Confundir temporada con año natural |
| 9 | Top N por [indicador] | ¿Cuáles son los 10 jugadores con más goles? | describe → query | Lewandowski 528, Messi 458, Cristiano Ronaldo 434, Kane 414, Suárez 350, Mbappé 330, Salah 309, Aubameyang 308, Immobile 273, Lukaku 272 | Mismos 10 jugadores; el orden se revisa aparte | Conocimiento propio; empates |
| 10 | Top N por [indicador] | ¿Qué 5 estadios tienen más asistencia media? | describe → query | Lusail Stadium 87.027 (12 partidos), Mâs Monumental 85.018 (14, solo 7 con asistencia registrada), FNB-Stadium 83.855 (8), Empower Field at Mile High 75.824 (1), Los Angeles Memorial Coliseum 75.637 (1) | Mismos 5 estadios | Medias con muy pocos partidos; nombre con un fallo de codificación |
| 11 | ¿Cómo evolucionó [indicador]? | ¿Cómo ha evolucionado el valor de mercado medio por año? | describe → query | Serie de 2000 a 2026 (falta 2002). Mínimo reciente 1,70 M€ en 2015 y máximo 3,64 M€ en 2026; sube desde 2022 | Mismos valores por año, o resumen fiel de la tendencia | Usar el valor actual de `players` en vez del historial |
| 12 | [Indicador] en [periodo] | ¿Cuántos goles se marcaron en 2023? | describe → query | 13.726 (validado por dos caminos) | Cifra exacta | La fecha de `appearances` no está unida a `dim_date` |
| 13 | Cruce entre tablas | ¿Qué club ha utilizado más jugadores distintos? | describe varias → query | Genoa CFC, 267 jugadores. Hay además un grupo de 3.893 jugadores sin club identificado | Genoa CFC con 267; acierto también si menciona el grupo sin club | Devolver el club vacío como respuesta |
| 14 | ¿Qué valores tiene [columna]? | ¿Qué posiciones puede tener un jugador? | describe → query | Attack, Defender, Midfield, Goalkeeper (y "Missing", que indica dato ausente) | Las cuatro posiciones, sin inventar | Tratar "Missing" como una posición |
| 15 | Columnas parecidas | ¿Qué jugador tiene ahora mismo el valor de mercado más alto? | describe → query | Empate: Lamine Yamal y Erling Haaland, 200 M€ | Los dos jugadores | Usar el máximo histórico o el historial |
| 16 | ¿Cómo se calcula [medida]? | ¿Cómo se calcula goals_per_game? | dax_measure | `DIVIDE([goals], [games_played])`: goles entre partidos con apariciones | Da la fórmula real sin inventar | Inventarse la fórmula |
| 17 | Pregunta ambigua | ¿Cómo van los equipos? | ninguna al principio | — | Pide aclaración o declara qué ha supuesto | Elegir un indicador sin avisar |
| 18 | Fuera de alcance: predicción | ¿Quién ganará la próxima Champions? | ninguna | — | Explica que solo consulta datos existentes | Inventar una predicción |
| 19 | Fuera de alcance: modificación | Borra los partidos de 2013 | ninguna | — | Rechaza: el servidor es de solo lectura | Intentarlo |

## Regla de corrección (proponer a la tutora)

- Medias: acierto si coincide al entero.
- Conteos y sumas: acierto si coincide exactamente.
- Rankings: acierto si coinciden los elementos; el orden se revisa aparte.
- Preguntas 2 y 17 a 19: acierto si cumple el criterio.