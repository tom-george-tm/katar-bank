from __future__ import annotations

def trim_whitespace_in_json_fields(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return {field_name: trim_whitespace_in_json_fields(field_value) for field_name, field_value in value.items()}
    if isinstance(value, list):
        return [trim_whitespace_in_json_fields(item) for item in value]
    return value

def normalize_structured_vision_output(structured_output: dict) -> dict:
    return trim_whitespace_in_json_fields(structured_output)
