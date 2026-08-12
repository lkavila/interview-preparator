"""Static (server-side) validation for exercise answers.

LLM-validated types (code, open_text) are handled by ollama_service.
"""

from typing import Any


def _norm(value: Any) -> str:
    s = str(value).strip().lower()
    # normalize numeric strings: "5.0" == "5"
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
        return str(f)
    except ValueError:
        return s


def validate_multiple_choice(answer: dict, solution: dict) -> bool:
    selected = answer.get("selected", [])
    if isinstance(selected, int):
        selected = [selected]
    return sorted(int(i) for i in selected) == sorted(int(i) for i in solution["correct"])


def validate_matching(answer: dict, solution: dict) -> bool:
    pairs = answer.get("pairs", {})
    expected = solution["pairs"]
    if len(pairs) != len(expected):
        return False
    return all(str(pairs.get(k)) == str(v) for k, v in expected.items())


def validate_ordering(answer: dict, solution: dict) -> bool:
    order = [str(x) for x in answer.get("order", [])]
    return order == [str(x) for x in solution["order"]]


def validate_table_builder(answer: dict, solution: dict) -> bool:
    columns = answer.get("columns", [])
    expected = solution["columns"]
    allow_extra = solution.get("allow_extra", False)
    if not allow_extra and len(columns) != len(expected):
        return False

    given = {_norm(c.get("name", "")): _norm(c.get("type", "")) for c in columns}
    for exp in expected:
        name = _norm(exp["name"])
        types = exp["type"] if isinstance(exp["type"], list) else [exp["type"]]
        accepted = {_norm(t) for t in types}
        if name not in given or given[name] not in accepted:
            return False
    return True


def validate_sql(answer: dict, solution: dict) -> bool:
    """The client runs the user's SQL in PGlite and sends back the rows produced
    by the verification query. We compare against the expected rows."""
    rows = answer.get("rows")
    if rows is None:
        return False
    expected = solution["expected_rows"]
    if len(rows) != len(expected):
        return False
    ordered = solution.get("ordered", False)

    norm_rows = [tuple(_norm(v) for v in row) for row in rows]
    norm_expected = [tuple(_norm(v) for v in row) for row in expected]
    if ordered:
        return norm_rows == norm_expected
    return sorted(norm_rows) == sorted(norm_expected)


STATIC_VALIDATORS = {
    "multiple_choice": validate_multiple_choice,
    "matching": validate_matching,
    "ordering": validate_ordering,
    "table_builder": validate_table_builder,
    "sql": validate_sql,
}


def validate_static(exercise_type: str, answer: dict, solution: dict) -> bool:
    validator = STATIC_VALIDATORS.get(exercise_type)
    if validator is None:
        raise ValueError(f"no static validator for exercise type '{exercise_type}'")
    try:
        return validator(answer, solution)
    except (KeyError, TypeError, ValueError):
        return False
