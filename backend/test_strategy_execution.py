import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.strategy.strategy_executor import StrategyError, StrategyExecutor


def strategy(nodes, start="first"):
    return {
        "version": 1,
        "inputs": {"symbol": {"type": "string", "required": True}},
        "start": start,
        "nodes": nodes,
    }


class StrategyExecutionTests(unittest.TestCase):
    def execute(self, definition, *, include_state=False, executor=None):
        return asyncio.run((executor or StrategyExecutor()).execute(
            definition, {"symbol": "RELIANCE"}, include_state
        ))

    def test_operation_result_and_state(self):
        definition = strategy({
            "first": {"type": "operation", "source": "custom", "operation": "one", "inputs": {"symbol": "$input.symbol"}, "output": "value", "next": "done"},
            "done": {"type": "result", "decision": "$value.decision"},
        })
        with patch("app.strategy.strategy_executor.run_tool", new=AsyncMock(return_value={"decision": "BUY"})) as tool:
            result = self.execute(definition, include_state=True)
        self.assertEqual(result, {"status": "completed", "result": {"decision": "BUY"}, "steps": 2, "state": {"input": {"symbol": "RELIANCE"}, "value": {"decision": "BUY"}}})
        tool.assert_awaited_once_with("custom", "one", {"symbol": "RELIANCE"})

    def test_sequential_operations_consume_prior_output_in_order(self):
        definition = strategy({
            "first": {"type": "operation", "source": "custom", "operation": "first", "inputs": {}, "output": "first_value", "next": "second"},
            "second": {"type": "operation", "source": "custom", "operation": "second", "inputs": {"value": "$first_value.value"}, "output": "second_value", "next": "done"},
            "done": {"type": "result", "decision": "$second_value.decision"},
        })
        tool = AsyncMock(side_effect=[{"value": 7}, {"decision": "HOLD"}])
        with patch("app.strategy.strategy_executor.run_tool", new=tool):
            result = self.execute(definition)
        self.assertEqual(result, {"status": "completed", "result": {"decision": "HOLD"}, "steps": 3})
        self.assertEqual(tool.await_args_list[1].args, ("custom", "second", {"value": 7}))

    def test_conditions_select_true_and_false_results(self):
        definition = strategy({
            "first": {"type": "operation", "source": "custom", "operation": "signal", "inputs": {}, "output": "signal", "next": "branch"},
            "branch": {"type": "condition", "value": "$signal.value", "operator": "equals", "compare_to": True, "on_true": "buy", "on_false": "sell"},
            "buy": {"type": "result", "decision": "BUY"},
            "sell": {"type": "result", "decision": "SELL"},
        })
        for signal, decision in ((True, "BUY"), (False, "SELL")):
            with patch("app.strategy.strategy_executor.run_tool", new=AsyncMock(return_value={"value": signal})):
                self.assertEqual(self.execute(definition)["result"]["decision"], decision)

    def test_errors_happen_before_or_during_execution_with_context(self):
        invalid = strategy({"first": {"type": "unknown"}})
        with patch("app.strategy.strategy_executor.run_tool", new=AsyncMock()) as tool:
            with self.assertRaises(StrategyError): self.execute(invalid)
        tool.assert_not_awaited()
        valid = strategy({"first": {"type": "operation", "source": "custom", "operation": "broken", "inputs": {}, "output": "x", "next": "done"}, "done": {"type": "result", "decision": "BUY"}})
        with patch("app.strategy.strategy_executor.run_tool", new=AsyncMock(side_effect=ValueError("bad input"))):
            with self.assertRaisesRegex(StrategyError, "Node: first\\nOperation: broken\\nCause: bad input"):
                self.execute(valid)

    def test_missing_input_and_step_limit(self):
        definition = strategy({"first": {"type": "result", "decision": "BUY"}})
        with self.assertRaises(StrategyError):
            asyncio.run(StrategyExecutor().execute(definition, {}))
        loop = strategy({"first": {"type": "operation", "source": "custom", "operation": "loop", "inputs": {}, "output": "x", "next": "first"}})
        with patch("app.strategy.strategy_executor.run_tool", new=AsyncMock(return_value={})):
            with self.assertRaisesRegex(StrategyError, r"Maximum execution step count \(3\) exceeded"):
                self.execute(loop, executor=StrategyExecutor(3))


if __name__ == "__main__":
    unittest.main()
