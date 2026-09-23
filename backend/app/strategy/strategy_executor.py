from __future__ import annotations

import operator
from typing import Any

from app.strategy.tools import run_tool

MAX_EXECUTION_STEPS = 1000
NODE_TYPES = {"operation", "condition", "result"}
CONDITION_OPERATORS = {
    "equals": operator.eq,
    "not_equals": operator.ne,
    "greater_than": operator.gt,
    "greater_than_equal": operator.ge,
    "less_than": operator.lt,
    "less_than_equal": operator.le,
}


class StrategyError(ValueError):
    """A malformed strategy or invalid strategy runtime value."""


class ReferenceResolutionError(StrategyError):
    """A state reference could not be resolved."""


def _node_label(node_id: str | None) -> str:
    return f"Node '{node_id}'" if node_id else "Node"


def _required(node: dict[str, Any], field: str, node_id: str | None = None) -> Any:
    if field not in node:
        raise StrategyError(
            f"{_node_label(node_id)} is missing required field '{field}'"
        )
    return node[field]


def resolve_reference(value: Any, state: dict[str, Any]) -> Any:
    """Resolve a ``$foo.bar`` state reference, leaving ordinary values alone."""
    if not isinstance(value, str) or not value.startswith("$"):
        return value

    reference = value
    validate_reference_syntax(reference)
    parts = value[1:].split(".")

    current: Any = state
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                raise ReferenceResolutionError(
                    f"Unable to resolve state reference '{reference}': '{part}' does not exist"
                )
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit():
                raise ReferenceResolutionError(
                    f"Unable to resolve state reference '{reference}': list index '{part}' must be a non-negative integer"
                )
            if int(part) >= len(current):
                raise ReferenceResolutionError(
                    f"Unable to resolve state reference '{reference}': list index '{part}' does not exist"
                )
            current = current[int(part)]
        else:
            raise ReferenceResolutionError(
                f"Unable to resolve state reference '{reference}': '{part}' does not exist"
            )
    return current


def validate_reference_syntax(value: Any) -> None:
    """Reject malformed references without requiring their state to exist yet."""
    if isinstance(value, str) and value.startswith("$"):
        parts = value[1:].split(".")
        valid = (
            bool(parts)
            and parts[0].isidentifier()
            and all(
                part.isidentifier() or part.lstrip("-").isdigit() for part in parts[1:]
            )
        )
        if not valid:
            raise StrategyError(f"Invalid state reference: {value}")
    elif isinstance(value, dict):
        for item in value.values():
            validate_reference_syntax(item)
    elif isinstance(value, list):
        for item in value:
            validate_reference_syntax(item)


def resolve_value(value: Any, state: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return resolve_reference(value, state)
    if isinstance(value, dict):
        return {key: resolve_value(item, state) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(item, state) for item in value]
    return value


def resolve_inputs(inputs: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise StrategyError("Operation inputs must be a dictionary")
    return resolve_value(inputs, state)


def store_output(state: dict[str, Any], output_path: str, result: Any) -> None:
    if (
        not isinstance(output_path, str)
        or not output_path
        or any(not p for p in output_path.split("."))
    ):
        raise StrategyError("Output path must be a non-empty dot-separated string")
    parts = output_path.split(".")
    if parts[0] == "input":
        raise StrategyError("Output path cannot overwrite 'input'")
    target = state
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        if not isinstance(target[part], dict):
            raise StrategyError(
                f"Cannot store output at '{output_path}': '{part}' is not a dictionary"
            )
        target = target[part]
    target[parts[-1]] = result


def get_node(strategy: dict[str, Any], node_id: str) -> dict[str, Any]:
    if not isinstance(strategy, dict):
        raise StrategyError("Strategy must be a dictionary")
    nodes = strategy.get("nodes")
    if not isinstance(nodes, dict):
        raise StrategyError("Strategy is missing a valid 'nodes' dictionary")
    if node_id not in nodes:
        raise StrategyError(f"Unknown strategy node: {node_id}")
    node = nodes[node_id]
    if not isinstance(node, dict):
        raise StrategyError(f"Node '{node_id}' must be a dictionary")
    if "type" not in node:
        raise StrategyError(f"Node '{node_id}' is missing required field 'type'")
    return node


def get_start_node(strategy: dict[str, Any]) -> dict[str, Any]:
    start = strategy.get("start") if isinstance(strategy, dict) else None
    if not isinstance(start, str) or not start:
        raise StrategyError("Strategy is missing required field 'start'")
    return get_node(strategy, start)


def get_next_node_id(strategy: dict[str, Any], node_id: str) -> str:
    node = get_node(strategy, node_id)
    if node["type"] != "operation":
        raise StrategyError(f"Node '{node_id}' is not an operation node")
    next_node = _required(node, "next", node_id)
    if not isinstance(next_node, str) or not next_node:
        raise StrategyError(f"Node '{node_id}' has invalid 'next'")
    get_node(strategy, next_node)
    return next_node


def parse_operation_node(
    node: dict[str, Any],
    state: dict[str, Any],
    *,
    strategy: dict[str, Any] | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(node, dict) or node.get("type") != "operation":
        raise StrategyError(f"{_node_label(node_id)} must be an operation node")
    source = _required(node, "source", node_id)
    operation = _required(node, "operation", node_id)
    inputs = _required(node, "inputs", node_id)
    output = _required(node, "output", node_id)
    next_node = _required(node, "next", node_id)
    if not all(
        isinstance(value, str) and value
        for value in (source, operation, output, next_node)
    ):
        raise StrategyError(f"{_node_label(node_id)} has an invalid operation field")
    if strategy is not None:
        get_node(strategy, next_node)
    validate_reference_syntax(inputs)
    return {
        "source": source,
        "operation": operation,
        "inputs": resolve_inputs(inputs, state),
        "output": output,
        "next": next_node,
    }


def evaluate_condition_node(
    node: dict[str, Any],
    state: dict[str, Any],
    *,
    strategy: dict[str, Any] | None = None,
    node_id: str | None = None,
) -> str:
    if not isinstance(node, dict) or node.get("type") != "condition":
        raise StrategyError(f"{_node_label(node_id)} must be a condition node")
    condition_operator = _required(node, "operator", node_id)
    comparison = CONDITION_OPERATORS.get(condition_operator)
    if comparison is None:
        raise StrategyError(f"Unsupported condition operator: {condition_operator}")
    value = resolve_value(_required(node, "value", node_id), state)
    compare_to = resolve_value(_required(node, "compare_to", node_id), state)
    try:
        result = comparison(value, compare_to)
    except (TypeError, ValueError) as error:
        raise StrategyError(
            f"{_node_label(node_id)} failed condition '{condition_operator}': {error}"
        ) from error
    destination = _required(node, "on_true" if result else "on_false", node_id)
    if not isinstance(destination, str) or not destination:
        raise StrategyError(f"{_node_label(node_id)} has an invalid branch destination")
    if strategy is not None:
        get_node(strategy, destination)
    return destination


def parse_result_node(
    node: dict[str, Any], state: dict[str, Any], *, node_id: str | None = None
) -> dict[str, Any]:
    if not isinstance(node, dict) or node.get("type") != "result":
        raise StrategyError(f"{_node_label(node_id)} must be a result node")
    _required(node, "decision", node_id)
    result = {key: value for key, value in node.items() if key != "type"}
    validate_reference_syntax(result)
    return resolve_value(result, state)


def validate_inputs(
    strategy: dict[str, Any], runtime_inputs: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    definitions = strategy.get("inputs", {})
    if not isinstance(definitions, dict) or not isinstance(runtime_inputs, dict):
        raise StrategyError("Strategy inputs and runtime inputs must be dictionaries")
    unexpected = set(runtime_inputs) - set(definitions)
    if unexpected:
        raise StrategyError(f"Undeclared strategy input: {sorted(unexpected)[0]}")
    checks = {
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: (
            isinstance(value, (int, float)) and not isinstance(value, bool)
        ),
        "boolean": lambda value: isinstance(value, bool),
    }
    normalized: dict[str, Any] = {}
    for name, definition in definitions.items():
        if not isinstance(definition, dict):
            raise StrategyError(f"Input '{name}' definition must be a dictionary")
        declared_type = _required(definition, "type")
        if declared_type not in checks:
            raise StrategyError(f"Unsupported declared input type: {declared_type}")
        if name not in runtime_inputs:
            if definition.get("required", False):
                raise StrategyError(f"Missing required strategy input: {name}")
            continue
        if not checks[declared_type](runtime_inputs[name]):
            raise StrategyError(
                f"Strategy input '{name}' must be of type {declared_type}"
            )
        normalized[name] = runtime_inputs[name]
    return {"input": normalized}


def validate_strategy(strategy: dict[str, Any]) -> None:
    if not isinstance(strategy, dict):
        raise StrategyError("Strategy must be a dictionary")
    _required(strategy, "version")
    get_start_node(strategy)
    if "analysis" in strategy:
        if not isinstance(strategy["analysis"], dict):
            raise StrategyError("Strategy 'analysis' must be a dictionary")
        validate_reference_syntax(strategy["analysis"])
    for node_id in strategy["nodes"]:
        node = get_node(strategy, node_id)
        node_type = node["type"]
        if node_type not in NODE_TYPES:
            raise StrategyError(f"Node '{node_id}' has unsupported type: {node_type}")
        if node_type == "operation":
            _validate_operation(node, strategy, node_id)
        elif node_type == "condition":
            _validate_condition(node, strategy, node_id)
        else:
            _required(node, "decision", node_id)
            validate_reference_syntax(
                {key: value for key, value in node.items() if key != "type"}
            )


def _validate_operation(
    node: dict[str, Any], strategy: dict[str, Any], node_id: str
) -> None:
    for field in ("source", "operation", "inputs", "output", "next"):
        _required(node, field, node_id)
    if not isinstance(node["inputs"], dict):
        raise StrategyError(f"Node '{node_id}' has invalid 'inputs'")
    validate_reference_syntax(node["inputs"])
    if not all(
        isinstance(node[field], str) and node[field]
        for field in ("source", "operation", "output", "next")
    ):
        raise StrategyError(f"Node '{node_id}' has an invalid operation field")
    get_node(strategy, node["next"])


def _validate_condition(
    node: dict[str, Any], strategy: dict[str, Any], node_id: str
) -> None:
    for field in ("value", "operator", "compare_to", "on_true", "on_false"):
        _required(node, field, node_id)
    if node["operator"] not in CONDITION_OPERATORS:
        raise StrategyError(f"Unsupported condition operator: {node['operator']}")
    validate_reference_syntax(node["value"])
    validate_reference_syntax(node["compare_to"])
    for field in ("on_true", "on_false"):
        destination = node[field]
        if not isinstance(destination, str) or not destination:
            raise StrategyError(f"Node '{node_id}' has invalid '{field}'")
        get_node(strategy, destination)


def check_execution_steps(
    step_count: int, max_steps: int = MAX_EXECUTION_STEPS
) -> None:
    if step_count >= max_steps:
        raise StrategyError(f"Maximum execution step count ({max_steps}) exceeded")


class StrategyExecutor:
    def __init__(
        self, max_execution_steps: int = MAX_EXECUTION_STEPS, tool_runner: Any = None
    ) -> None:
        self.max_execution_steps = max_execution_steps
        self.tool_runner = tool_runner or run_tool

    async def execute(
        self,
        strategy: dict,
        runtime_inputs: dict,
        include_state: bool = False,
        initial_state: dict | None = None,
    ) -> dict:
        state = validate_inputs(strategy, runtime_inputs)
        state.update(initial_state or {})
        validate_strategy(strategy)
        current_node_id = strategy["start"]
        step_count = 0

        while True:
            check_execution_steps(step_count, self.max_execution_steps)
            node = get_node(strategy, current_node_id)
            step_count += 1

            if node["type"] == "operation":
                parsed = parse_operation_node(
                    node, state, strategy=strategy, node_id=current_node_id
                )
                try:
                    tool_result = await self.tool_runner(
                        parsed["source"], parsed["operation"], parsed["inputs"]
                    )
                except Exception as error:
                    raise StrategyError(
                        f"Node: {current_node_id}\n"
                        f"Operation: {parsed['operation']}\n"
                        f"Cause: {error}"
                    ) from error
                store_output(state, parsed["output"], tool_result)
                current_node_id = parsed["next"]
            elif node["type"] == "condition":
                current_node_id = evaluate_condition_node(
                    node, state, strategy=strategy, node_id=current_node_id
                )
            else:
                result = {
                    "status": "completed",
                    "result": parse_result_node(node, state, node_id=current_node_id),
                    "steps": step_count,
                }
                if "analysis" in strategy:
                    result["analysis"] = resolve_value(strategy["analysis"], state)
                if include_state:
                    result["state"] = state
                return result
