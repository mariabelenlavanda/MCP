"""Extrae las fórmulas DAX de las medidas a partir de la definición TMSL de Fabric.

"""

import base64
import json
from typing import Any


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


def measure_expressions(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Name, table, and DAX expression of the visible measures."""
    model = _tmsl_model(_first_tmsl_model(decode_definition_parts(envelope)))
    out = []
    for table in model.get("tables") or []:
        for measure in table.get("measures") or []:
            if measure.get("isHidden"):
                continue
            expression = measure.get("expression")
            if isinstance(expression, list):
                expression = "\n".join(str(line) for line in expression)
            out.append({
                "name": measure.get("name"),
                "table": table.get("name"),
                "expression": expression,
            })
    return out