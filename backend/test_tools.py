import unittest

from app.strategy.tools import crosses_above, crosses_below, ema, run_tool


class ToolsTest(unittest.TestCase):
    def test_ema(self):
        self.assertEqual(
            ema({"values": [1, 2, 3], "period": 2}),
            {"values": [None, 1.5, 2.5], "value": 2.5},
        )

    def test_ema_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            ema({"values": [], "period": 2})
        with self.assertRaises(ValueError):
            ema({"values": [1], "period": 0})

    def test_crossings(self):
        data = {"series_a": [1, 3], "series_b": [2, 2]}
        self.assertEqual(crosses_above(data), {"value": True})
        self.assertEqual(crosses_below(data), {"value": False})
        self.assertEqual(
            crosses_above({"series_a": [2, 2], "series_b": [2, 2]}),
            {"value": False},
        )
        self.assertEqual(
            crosses_above({"series_a": [None, 3], "series_b": [2, 2]}),
            {"value": False},
        )

    def test_crossings_validate_series(self):
        with self.assertRaises(ValueError):
            crosses_above({"series_a": [1], "series_b": [2]})
        with self.assertRaises(ValueError):
            crosses_below({"series_a": [1, 2], "series_b": [2]})

    def test_registry_dispatches_tools(self):
        import asyncio

        result = asyncio.run(
            run_tool("custom", "indicator.ema", {"values": [1, 2], "period": 2})
        )
        self.assertEqual(result, {"values": [None, 1.5], "value": 1.5})

    def test_zerodha_source_alias_uses_mcp_dispatcher(self):
        from unittest.mock import AsyncMock, patch

        with patch("app.strategy.tools.session") as session:
            session.return_value.__aenter__ = AsyncMock(return_value=[])
            session.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "app.strategy.tools.call_kite_tool",
                new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], [{"close": 1}]]),
            ) as call:
                import asyncio

                self.assertEqual(
                    asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"})),
                    {"close": [1], "latest": {"close": 1}},
                )
        self.assertEqual(call.await_args_list[1].args[1], "get_historical_data")

    def test_zerodha_dispatcher_reuses_loaded_tools(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.strategy.tools.call_kite_tool",
            new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], [{"close": 1}]]),
        ) as call:
            self.assertEqual(
                asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"}, ["loaded"])),
                {"close": [1], "latest": {"close": 1}},
            )
        self.assertEqual(call.await_args_list[1].args[1], "get_historical_data")
        self.assertEqual(call.await_args_list[1].args[2]["instrument_token"], 738561)

    def test_history_result_is_columnar_for_strategy_references(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        candles = [{"close": 100, "open": 99}, {"close": 101, "open": 100}]
        with patch(
            "app.strategy.tools.call_kite_tool", new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], candles])
        ):
            result = asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"}, ["loaded"]))
        self.assertEqual(
            result,
            {"open": [99, 100], "close": [100, 101], "latest": {"close": 101, "open": 100}},
        )

    def test_wrapped_history_result_is_columnar(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.strategy.tools.call_kite_tool",
            new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], {"data": {"candles": [{"close": 100}]}}]),
        ):
            self.assertEqual(
                asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"}, ["loaded"])),
                {"close": [100], "latest": {"close": 100}},
            )

    def test_text_history_result_is_columnar(self):
        from unittest.mock import AsyncMock, patch

        import asyncio

        response = [{"type": "text", "text": '{"candles": [{"close": 100}]}' }]
        with patch("app.strategy.tools.call_kite_tool", new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], response])):
            self.assertEqual(
                asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"}, ["loaded"])),
                {"close": [100], "latest": {"close": 100}},
            )


if __name__ == "__main__":
    unittest.main()
