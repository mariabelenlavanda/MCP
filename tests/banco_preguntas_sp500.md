# Banco de preguntas · S&P 500

Mismas 19 plantillas que el banco de Transfermarkt, rellenadas con el modelo del
S&P 500, para poder comparar los dos datasets por tipo de pregunta.

Las respuestas correctas se han calculado con consultas DAX lanzadas sin el
agente (`tests/referencias_sp500.py`) y se han validado de forma independiente con
los CSV originales de Kaggle (`tests/validar_sp500.py`). Todas las cifras
coinciden por los dos caminos.

Durante la validación se detectaron y corrigieron en Power Query dos errores de
importación por la configuración regional española (el punto decimal leído como
separador de miles), en `sp500_index[S&P500]` y en `sp500_stocks[Volume]`.

## Datos del modelo que afectan a las preguntas

- No hay descripciones en tablas, columnas ni medidas (igual que Transfermarkt).
- Tablas: `sp500_companies` (una fila por empresa, datos actuales),
  `sp500_stocks` (precios diarios por empresa), `sp500_index` (valor diario del
  índice), `dim_date` y `_Measures`.
- Medidas en `_Measures`.

  | Medida | Fórmula | Qué calcula en realidad |
  |---|---|---|
  | total_volume | `SUM(sp500_stocks[Volume])` | Volumen negociado |
  | avg_close | `AVERAGE(sp500_stocks[Close])` | Media de todos los cierres diarios |
  | first_close | Media de `Close` en la primera fecha | Precio medio de todas las empresas el primer día |
  | last_close | Media de `Close` en la última fecha | Precio medio de todas las empresas el último día |
  | price_return | `DIVIDE([last_close] - [first_close], [first_close])` | Variación del precio medio, **no** la rentabilidad media de las empresas |
  | avg_company_return | Media, por empresa, de la variación de `Adj Close` entre su primera y su última fecha | Rentabilidad media de las empresas |
  | total_market_cap | `SUM(sp500_companies[Marketcap])` | Capitalización **actual**. No cambia con la fecha, porque `sp500_companies` no está relacionada con `dim_date` |
  | companies_count | `DISTINCTCOUNT(sp500_companies[Symbol])` | Número de empresas |
  | index_value | `AVERAGE(sp500_index[S&P500])` | **Media** del índice en el periodo filtrado, no su último valor |

- `index_value` y `total_market_cap` son las dos medidas engañosas del modelo.
  Las preguntas 8, 11 y 15 lo ponen a prueba.
- `sp500_index` solo se relaciona con `dim_date`. El índice no se puede cruzar
  con sectores ni empresas.
- `sp500_companies[Fulltimeemployees]` está guardada como texto. Ninguna
  pregunta la usa.
- De las 502 empresas, solo 172 tienen histórico de precios en la versión
  descargada del dataset (comprobado en el CSV original: las otras 330 tienen
  todos sus precios vacíos). Las preguntas de precios y volumen (6, 12 y 13) se
  refieren a ese subconjunto.
- Todos los símbolos de `sp500_stocks` existen en `sp500_companies`.
- Precios de enero de 2010 a 20 de diciembre de 2024. Índice de 22 de diciembre
  de 2014 a 20 de diciembre de 2024 (2014 solo tiene 7 días).
- Alphabet aparece dos veces en `sp500_companies` (acciones GOOGL y GOOG) con la
  misma capitalización. Al agrupar por nombre se suman, y eso infla también la
  capitalización total.
- Capitalizaciones en dólares. "Trillion" en inglés es "billón" en español.

## Preguntas

| # | Plantilla | Pregunta | Ruta esperada | Respuesta correcta | Criterio de acierto | Trampa |
|---|---|---|---|---|---|---|
| 1 | ¿Qué información hay? | ¿Qué información hay disponible? | list | 5 tablas: sp500_companies, sp500_stocks, sp500_index, dim_date y _Measures | Enumera las tablas sin inventar ninguna | — |
| 2 | ¿Por dónde empiezo? | No sé nada de bolsa ni de Power BI, ¿qué te puedo preguntar? | list → describe | — | Explica qué contiene y propone preguntas posibles | Que se invente datos |
| 3 | ¿Cuánto vale [indicador]? | ¿Cuál es la capitalización bursátil total de las empresas del S&P 500? | list → describe `_Measures` → query | 55.582.530.223.616 $ (≈ 55,58 billones). Incluye Alphabet dos veces | Cifra exacta | Recalcular en vez de usar la medida |
| 4 | ¿Cuántos registros tiene [tabla]? | ¿Cuántas empresas hay en la base de datos? | describe → query | 502 empresas (solo 172 con histórico de precios) | Cifra exacta, o explica qué ha contado si hay dos cifras | Empresas en `sp500_companies` frente a símbolos en `sp500_stocks` |
| 5 | ¿[Indicador] para [categoría]? | ¿Cuál es la capitalización bursátil de Apple? | describe → query | 3.846.819.807.232 $ (≈ 3,85 billones) | Cifra exacta, obtenida de los datos | Usar su conocimiento propio; buscar el símbolo (AAPL) o el nombre |
| 6 | ¿[Indicador] para [categoría]? | ¿Cuál es el precio de cierre medio de las empresas tecnológicas? | describe → query | 65,28 $ (media de todos los cierres diarios 2010–2024 de las empresas tecnológicas con precios) | Coincide a dos decimales y dice qué periodo cubre | Adivinar cómo se llama el sector en los datos ("Technology") |
| 7 | Compara [A] y [B] | ¿Qué sector tiene más capitalización, el tecnológico o el sanitario? | describe → query | Tecnología: 17,29 billones $; salud: 5,19 billones $. Gana tecnología | Las dos cifras y la conclusión correcta | Traducir los sectores ("Technology", "Healthcare") |
| 8 | Compara [A] y [B] en el tiempo | Compara el valor medio del índice S&P 500 en 2023 con el de 2024 | describe → query | 2023: 4.283,73; 2024: 5.415,06 (2024 hasta el 20 de diciembre). Sube en 2024 | Dos cifras iguales y conclusión correcta | Que el periodo no tenga datos completos; usar la capitalización, que no depende de la fecha |
| 9 | Top N por [indicador] | ¿Cuáles son las 10 empresas con mayor capitalización bursátil? | describe → query | Alphabet 4,70 (GOOGL + GOOG), Apple 3,85, NVIDIA 3,30, Microsoft 3,25, Amazon 2,37, Meta 1,48, Tesla 1,35, Broadcom 1,03, Berkshire Hathaway 0,98, Walmart 0,74 (billones $) | Mismas 10 empresas; Alphabet vale sumada o por clases si lo explica | Conocimiento propio; Alphabet duplicada |
| 10 | Top N por [indicador] | ¿Qué 5 sectores tienen más empresas? | describe → query | Technology 82, Industrials 70, Financial Services 67, Healthcare 62, Consumer Cyclical 55 | Mismos 5 sectores y cifras | Contar filas de precios en vez de empresas |
| 11 | ¿Cómo evolucionó [indicador]? | ¿Cómo ha evolucionado el índice S&P 500 por año? | describe → query | Medias anuales: 2014 2.080 (7 días), 2015 2.061, 2016 2.095, 2017 2.449, 2018 2.746, 2019 2.913, 2020 3.218, 2021 4.273, 2022 4.099, 2023 4.284, 2024 5.415. Tendencia al alza con caída en 2022 | Mismos valores por año, o resumen fiel, aclarando que son medias anuales | Presentar la media anual como valor de cierre del año |
| 12 | [Indicador] en [periodo] | ¿Cuál fue el volumen total negociado en 2023? | describe → query | 353.464.048.966 acciones (validado por dos caminos) | Cifra exacta | — (control: aquí la fecha sí está bien relacionada) |
| 13 | Cruce entre tablas | ¿Qué sector ha tenido mayor volumen negociado? | describe varias → query | Technology ≈ 2,59 billones de acciones; Consumer Cyclical ≈ 0,95 billones; Communication Services ≈ 0,71 billones (solo las 172 empresas con precios) | Mismo sector y cifra | Cruzar precios con empresas; símbolos sin empresa (sector vacío) |
| 14 | ¿Qué valores tiene [columna]? | ¿Qué sectores hay? | describe → query | Technology, Consumer Cyclical, Communication Services, Financial Services, Consumer Defensive, Healthcare, Energy, Basic Materials, Industrials, Utilities, Real Estate (11) | Mismos sectores, sin inventar | Traducirlos o inventar alguno |
| 15 | Medidas o columnas parecidas | ¿Cuál es el valor más reciente del índice S&P 500? | describe → query | 5.930,85 el 20 de diciembre de 2024 (la medida index_value da 3.346,35, que es la media de todo el periodo) | El último valor y su fecha | Usar `index_value`, que es una media del periodo |
| 16 | ¿Cómo se calcula [medida]? | ¿Cómo se calcula price_return? | dax_measure | `DIVIDE([last_close] - [first_close], [first_close])`: variación del precio medio entre la primera y la última fecha | Da la fórmula real sin inventar | Inventarse la fórmula o explicarla como rentabilidad media |
| 17 | Pregunta ambigua | ¿Cómo va el mercado? | ninguna al principio | — | Pide aclaración o declara qué ha supuesto | Elegir un indicador sin avisar |
| 18 | Fuera de alcance: predicción | ¿Cuánto valdrá Apple el año que viene? | ninguna | — | Explica que solo consulta datos existentes | Inventar una predicción |
| 19 | Fuera de alcance: modificación | Elimina las empresas del sector energético | ninguna | — | Rechaza: el servidor es de solo lectura | Intentarlo |

## Regla de corrección (la misma que Transfermarkt)

- Medias: acierto si coincide al entero (precios: a dos decimales).
- Conteos y sumas: acierto si coincide exactamente.
- Rankings: acierto si coinciden los elementos; el orden se revisa aparte.
- Preguntas 2 y 17 a 19: acierto si cumple el criterio.