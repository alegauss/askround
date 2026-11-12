"""A JSON Schema checker for the subset askround's published schemas use.

The schemas in `schema/` are standard JSON Schema (draft 2020-12), so any validator
reads them; this one keeps the test suite free of a dependency. It knows: type (one or
a list), const, enum, properties, required, items, minItems, maxItems, pattern, anyOf,
and $ref to a local $defs entry. Anything else in a schema is ignored, never guessed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMAS = Path(__file__).parent.parent / "schema"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is(value, kind: str) -> bool:
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    return isinstance(value, _TYPES[kind])


def errors(value, schema: dict, root: dict | None = None, where: str = "$") -> list[str]:
    root = root or schema
    if "$ref" in schema:
        name = schema["$ref"].removeprefix("#/$defs/")
        return errors(value, root["$defs"][name], root, where)
    found: list[str] = []
    if "anyOf" in schema and not any(not errors(value, s, root, where) for s in schema["anyOf"]):
        found.append(f"{where}: matches none of anyOf")
    kinds = schema.get("type")
    if kinds is not None:
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if not any(_is(value, k) for k in kinds):
            return [f"{where}: {type(value).__name__} is not {kinds}"]
    if "const" in schema and value != schema["const"]:
        found.append(f"{where}: {value!r} != {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{where}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        found.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        found += [f"{where}: missing {k!r}" for k in schema.get("required", []) if k not in value]
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                found += errors(value[key], sub, root, f"{where}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            found.append(f"{where}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            found.append(f"{where}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                found += errors(item, schema["items"], root, f"{where}[{i}]")
    return found


def load(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def check(data: dict) -> list[str]:
    """Validate an output against the schema its own `schema` field names."""
    kind = data["schema"].removeprefix("askround/").split("@")[0]
    if kind in ("round", "brief"):
        return errors(data, load(kind))
    outputs = load("outputs")
    return errors(data, outputs["$defs"][kind], outputs)
