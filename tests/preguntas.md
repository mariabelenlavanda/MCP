# Preguntas para evaluar el MCP

## Preguntas

- **¿Qué información hay?**
  - Tool: list_available_tables

- **¿Qué valores tiene [columna]?**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard

- **¿Cuántos registros tiene [tabla]?**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard
  - Hay que vigilar que solo traiga un número y no de el número y los datos

- **¿Cuánto vale [indicador]?**
  - Tool: list_available_tables -> describe_pbi_dashboard -> query_pbi_dashboard
    Hay que ver que use el indicador del modelo y no lo recalcule

- **¿[Indicador] para [categoría]?**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard
  
- **Compara [A] y [B] (consultas)**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard
  - Tener en cuenta que pueden tener fechas distintas y por tanto periodos distintos y que no haga las comparaciones mal

- **Top 10 por [indicador]**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard

- **¿Cómo evolucionó [indicador]?**
  - Tool: describe_pbi_dashboard -> query_pbi_dashboard

- **¿Por qué cambió [indicador]?**
  - Tool: describe_pbi_dashboard de varias tablas-> query_pbi_dashboard
 Hay que ver si se hace unas TOOL para ver las relaciones entre las tablas

- **¿Cómo se calcula [medida]?**
  - Tool: describe_pbi_dashboard

- **¿Cómo vamos?**
  - Esto es como pedir un resumen por lo que se haria con un TOOL de resumen????


