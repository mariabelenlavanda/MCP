"""Convierte la definición TMSL de Fabric en un esquema compacto del modelo.

Adaptado de infrastructure/powerbi_definition.py (repo powerbi-mcp). Solo se queda
la parte del modelo semántico en formato TMSL: tablas, columnas, medidas y
relaciones. Los IDs, las expresiones de las medidas y las particiones quedan fuera.
"""

import base64
import json
from typing import Any

_AUTO_DATE_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")


def parse_semantic_model_definition(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return tables, columns, measures and relationships from a Fabric envelope."""
    parts = decode_definition_parts(envelope)
    tmsl = _first_tmsl_model(parts)
    if tmsl is not None:
        return compact_from_tmsl(tmsl)
    raise ValueError("Fabric returned a semantic model definition without TMSL parts.")


def decode_definition_parts(envelope: dict[str, Any]) -> dict[str, str]:
    """Decode InlineBase64 definition parts to UTF-8 text, keyed by path."""
    definition = envelope.get("definition") if isinstance(envelope, dict) else None
    raw_parts = definition.get("parts") if isinstance(definition, dict) else None
    if not isinstance(raw_parts, list):
        raise ValueError("Fabric definition payload is missing definition.parts.")

    decoded: dict[str, str] = {}
    for part in raw_parts:
        if not isinstance(part, dict):
            continue
        path = str(part.get("path") or "").strip().replace("\\", "/")
        payload = part.get("payload")
        if not path or not isinstance(payload, str) or not payload:
            continue
        try:
            text = base64.b64decode(payload).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        decoded[path] = text
    return decoded


def compact_from_tmsl(document: dict[str, Any]) -> dict[str, Any]:
    model = _tmsl_model(document)
    if model is None:
        raise ValueError("TMSL definition does not contain a model.")
    return _compact_model(
        tables=model.get("tables") or [],
        relationships=model.get("relationships") or [],
        model_description=_optional_text(model.get("description")),
    )


def _tmsl_model(document: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    model = document.get("model")
    if isinstance(model, dict):
        return model
    for wrapper in ("create", "createOrReplace"):
        nested = document.get(wrapper)
        if not isinstance(nested, dict):
            continue
        database = nested.get("database")
        if isinstance(database, dict) and isinstance(database.get("model"), dict):
            return database["model"]
    return None


def _first_tmsl_model(parts: dict[str, str]) -> dict[str, Any] | None:
    for path, text in parts.items():
        lower = path.lower()
        if not (lower.endswith(".bim") or lower.endswith(".json") or lower.endswith(".tmsl")):
            continue
        stripped = text.lstrip()
        if not stripped.startswith("{"):
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            continue
        if _tmsl_model(document) is not None:
            return document
    return None


def _compact_model(
    *,
    tables: list[dict[str, Any]],
    relationships: list[Any],
    model_description: str | None,
) -> dict[str, Any]:
    tables_out: list[dict[str, Any]] = []
    measures_out: list[dict[str, Any]] = []

    for table in tables:
        if not isinstance(table, dict):
            continue
        name = str(table.get("name") or "").strip()
        if not name or table.get("isHidden") or _is_auto_date_table(name):
            continue

        columns_out: list[dict[str, Any]] = []
        for column in table.get("columns") or []:
            if not isinstance(column, dict):
                continue
            column_name = str(column.get("name") or "").strip()
            if (
                not column_name
                or column.get("isHidden")
                or str(column.get("type") or "").lower() == "rownumber"
            ):
                continue
            entry: dict[str, Any] = {
                "name": column_name,
                "data_type": str(
                    column.get("dataType") or column.get("data_type") or "unknown"
                ),
            }
            description = _optional_text(column.get("description"))
            if description:
                entry["description"] = description
            columns_out.append(entry)

        table_entry: dict[str, Any] = {"name": name, "columns": columns_out}
        table_description = _optional_text(table.get("description"))
        if table_description:
            table_entry["description"] = table_description
        tables_out.append(table_entry)

        for measure in table.get("measures") or []:
            if not isinstance(measure, dict):
                continue
            measure_name = str(measure.get("name") or "").strip()
            if not measure_name or measure.get("isHidden"):
                continue
            measure_entry: dict[str, Any] = {"name": measure_name, "table": name}
            description = _optional_text(measure.get("description"))
            if description:
                measure_entry["description"] = description
            folder = _optional_text(measure.get("displayFolder") or measure.get("display_folder"))
            if folder:
                measure_entry["display_folder"] = folder
            data_type = _optional_text(measure.get("dataType") or measure.get("data_type"))
            if data_type:
                measure_entry["data_type"] = data_type
            measures_out.append(measure_entry)

    relationships_out: list[dict[str, str]] = []
    for relationship in relationships:
        parsed = _relationship_entry(relationship)
        if parsed:
            relationships_out.append(parsed)

    payload: dict[str, Any] = {
        "tables": tables_out,
        "measures": measures_out,
        "relationships": relationships_out,
    }
    if model_description:
        payload["description"] = model_description
    return payload


def _relationship_entry(relationship: Any) -> dict[str, str] | None:
    if isinstance(relationship, str):
        return None
    if not isinstance(relationship, dict):
        return None
    if relationship.get("isActive") is False or relationship.get("is_active") is False:
        return None
    from_table = str(relationship.get("fromTable") or relationship.get("from_table") or "").strip()
    from_column = str(
        relationship.get("fromColumn") or relationship.get("from_column") or ""
    ).strip()
    to_table = str(relationship.get("toTable") or relationship.get("to_table") or "").strip()
    to_column = str(relationship.get("toColumn") or relationship.get("to_column") or "").strip()
    if from_table and "." in from_table and not from_column:
        from_table, from_column = from_table.split(".", 1)
    if to_table and "." in to_table and not to_column:
        to_table, to_column = to_table.split(".", 1)
    if not (from_table and from_column and to_table and to_column):
        return None
    return {
        "from": f"{from_table}[{from_column}]",
        "to": f"{to_table}[{to_column}]",
    }


def _is_auto_date_table(name: str) -> bool:
    return name.startswith(_AUTO_DATE_PREFIXES)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None