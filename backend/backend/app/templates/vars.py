from __future__ import annotations
import re
from typing import Any, Dict, Iterable, Set, Tuple

VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _iter_strings(obj: Any) -> Iterable[Tuple[list, str]]:
    """Yield (path, string) for all string values within nested dict/list structure.

    Path is a list of keys/indices to reach the string value.
    """
    if isinstance(obj, str):
        yield ([], obj)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            for sub_path, s in _iter_strings(v):
                yield ([k, *sub_path], s)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for sub_path, s in _iter_strings(v):
                yield ([i, *sub_path], s)


def parse_vars(plan: Dict[str, Any]) -> Set[str]:
    """Traverse plan (header and scenes) and collect all {{var}} tokens.

    Returns a set of variable names without braces.
    """
    vars_found: Set[str] = set()
    plan = plan or {}
    for _path, text in _iter_strings(plan):
        for m in VAR_PATTERN.finditer(text):
            vars_found.add(m.group(1))
    return vars_found


def apply_vars(plan: Dict[str, Any], inputs: Dict[str, Any] | None) -> Tuple[Dict[str, Any], list[str]]:
    """Replace {{var}} tokens in all strings using provided inputs.

    - Non-string inputs are stringified.
    - Missing variables are left as-is; a warning is returned.
    Returns: (resolved_plan, warnings)
    """
    inputs = inputs or {}
    warnings: list[str] = []
    missing: Set[str] = set()

    def replace_text(s: str) -> str:
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key in inputs and inputs[key] is not None:
                val = inputs[key]
                return str(val)
            missing.add(key)
            return m.group(0)

        return VAR_PATTERN.sub(repl, s)

    def walk(obj: Any) -> Any:
        if isinstance(obj, str):
            return replace_text(obj)
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        return obj

    resolved = walk(plan or {})
    if missing:
        warnings.append("Missing inputs for: " + ", ".join(sorted(missing)))
    return resolved, warnings
