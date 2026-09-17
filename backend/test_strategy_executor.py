import unittest

from app.strategy.strategy_executor import (
    StrategyError, check_execution_steps, evaluate_condition_node, get_start_node,
    parse_operation_node, parse_result_node, resolve_reference, resolve_value,
    store_output, validate_inputs, validate_reference_syntax, validate_strategy,
)


class StrategyExecutorParsingTests(unittest.TestCase):
    def setUp(self):
        self.state = {"input": {"symbol": "RELIANCE"}, "history": {"close": [100, 101]}, "signal": {"value": True}}
        self.strategy = {"version": 1, "start": "op", "nodes": {
            "op": {"type": "operation", "source": "custom", "operation": "indicator.ema", "inputs": {"values": "$history.close"}, "output": "ema", "next": "condition"},
            "condition": {"type": "condition", "value": "$signal.value", "operator": "equals", "compare_to": True, "on_true": "buy", "on_false": "sell"},
            "buy": {"type": "result", "decision": "BUY"}, "sell": {"type": "result", "decision": "SELL"},
        }}

    def test_references_and_recursive_values(self):
        self.assertEqual(resolve_reference("$input.symbol", self.state), "RELIANCE")
        self.assertEqual(resolve_reference("$history.close", self.state), [100, 101])
        self.assertEqual(resolve_value({"x": "$input.symbol", "nested": ["$history.close"]}, self.state), {"x": "RELIANCE", "nested": [[100, 101]]})
        with self.assertRaisesRegex(StrategyError, r"\$missing.value"):
            resolve_reference("$missing.value", self.state)
        with self.assertRaisesRegex(StrategyError, "non-negative integer"):
            resolve_reference("$history.close.-1", self.state)

    def test_store_output_and_input_protection(self):
        store_output(self.state, "ema", {"value": 100})
        store_output(self.state, "analysis.technical.ema20", 100)
        self.assertEqual(self.state["ema"]["value"], 100)
        self.assertEqual(self.state["analysis"]["technical"]["ema20"], 100)
        with self.assertRaises(StrategyError): store_output(self.state, "input.symbol", "x")

    def test_start_operation_and_conditions(self):
        self.assertEqual(get_start_node(self.strategy)["type"], "operation")
        parsed = parse_operation_node(self.strategy["nodes"]["op"], self.state, strategy=self.strategy, node_id="op")
        self.assertEqual(parsed["inputs"]["values"], [100, 101])
        self.assertEqual(evaluate_condition_node(self.strategy["nodes"]["condition"], self.state, strategy=self.strategy), "buy")
        self.state["signal"]["value"] = False
        self.assertEqual(evaluate_condition_node(self.strategy["nodes"]["condition"], self.state, strategy=self.strategy), "sell")
        self.strategy["nodes"]["condition"]["operator"] = "contains"
        with self.assertRaisesRegex(StrategyError, "Unsupported condition operator"):
            evaluate_condition_node(self.strategy["nodes"]["condition"], self.state)

    def test_result_inputs_structure_and_step_errors(self):
        self.assertEqual(parse_result_node({"type": "result", "decision": "BUY", "score": "$signal.value"}, self.state), {"decision": "BUY", "score": True})
        with self.assertRaises(StrategyError): validate_inputs({"inputs": {"symbol": {"type": "string", "required": True}}}, {})
        with self.assertRaises(StrategyError): validate_inputs({"inputs": {"count": {"type": "integer"}}}, {"count": True})
        with self.assertRaisesRegex(StrategyError, "Undeclared strategy input"):
            validate_inputs({"inputs": {"symbol": {"type": "string"}}}, {"symbol": "X", "random_value": 1})
        self.assertEqual(validate_inputs({"inputs": {"symbol": {"type": "string", "required": True}}}, {"symbol": "RELIANCE"}), {"input": {"symbol": "RELIANCE"}})
        validate_strategy(self.strategy)
        with self.assertRaises(StrategyError): check_execution_steps(1000)

    def test_invalid_structure(self):
        broken = {"version": 1, "start": "op", "nodes": {"op": {"type": "unknown"}}}
        with self.assertRaises(StrategyError): validate_strategy(broken)
        self.strategy["nodes"]["condition"]["on_true"] = "gone"
        with self.assertRaises(StrategyError): validate_strategy(self.strategy)
        self.strategy.pop("start")
        with self.assertRaises(StrategyError): get_start_node(self.strategy)
        with self.assertRaises(StrategyError): parse_operation_node({"type": "operation"}, self.state, node_id="op")
        with self.assertRaisesRegex(StrategyError, "Invalid state reference"):
            validate_reference_syntax({"value": "$$$broken.reference"})
        with self.assertRaisesRegex(StrategyError, "failed condition"):
            evaluate_condition_node({"type": "condition", "value": "ABC", "operator": "greater_than", "compare_to": 20, "on_true": "x", "on_false": "y"}, self.state)
        self.strategy["start"] = "op"
        self.strategy["nodes"]["condition"]["on_true"] = 1
        with self.assertRaisesRegex(StrategyError, "invalid 'on_true'"):
            validate_strategy(self.strategy)

    def test_analysis_validation(self):
        self.strategy["analysis"] = {"symbol": "$input.symbol"}
        validate_strategy(self.strategy)
        self.strategy["analysis"] = []
        with self.assertRaisesRegex(StrategyError, "analysis.*dictionary"):
            validate_strategy(self.strategy)
        self.strategy["analysis"] = {"symbol": "$$bad"}
        with self.assertRaisesRegex(StrategyError, "Invalid state reference"):
            validate_strategy(self.strategy)


if __name__ == "__main__":
    unittest.main()
