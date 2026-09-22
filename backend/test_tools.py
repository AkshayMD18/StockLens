import unittest

from app.strategy.tools import crosses_above, crosses_below, ema, rsi, run_tool


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

    def test_rsi_uses_wilder_smoothing_and_exposes_previous_value(self):
        result = rsi({"values": [1, 2, 3, 2, 2, 3], "period": 3})
        self.assertEqual(result["values"][:3], [None, None, None])
        self.assertAlmostEqual(result["previous_value"], 66.66666666666666)
        self.assertAlmostEqual(result["value"], 80.95238095238095)

    def test_rsi_rejects_insufficient_or_invalid_input(self):
        with self.assertRaises(ValueError):
            rsi({"values": [1, 2, 3, 4], "period": 3})
        with self.assertRaises(ValueError):
            rsi({"values": [1, 2, 3, 4, 5], "period": 0})

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

    def test_history_accepts_today_date_token(self):
        import asyncio
        from datetime import date
        from unittest.mock import AsyncMock, patch

        with (
            patch("app.strategy.tools.date") as mock_date,
            patch(
                "app.strategy.tools.call_kite_tool",
                new=AsyncMock(
                    side_effect=[
                        [{"tradingsymbol": "RELIANCE", "instrument_token": 738561}],
                        [{"close": 1}],
                    ]
                ),
            ) as call,
        ):
            mock_date.today.return_value = date(2026, 9, 21)
            asyncio.run(
                run_tool(
                    "zerodha",
                    "market.history",
                    {
                        "symbol": "RELIANCE",
                        "interval": "5minute",
                        "from_date": "today",
                        "to_date": "today",
                    },
                    ["loaded"],
                )
            )

        self.assertEqual(
            call.await_args_list[1].args[2],
            {
                "instrument_token": 738561,
                "from_date": "2026-09-21 00:00:00",
                "to_date": "2026-09-21 23:59:59",
                "interval": "5minute",
            },
        )

    def test_history_uses_lookback_days(self):
        import asyncio
        from datetime import date
        from unittest.mock import AsyncMock, patch

        with (
            patch("app.strategy.tools.date") as mock_date,
            patch(
                "app.strategy.tools.call_kite_tool",
                new=AsyncMock(
                    side_effect=[
                        [{"tradingsymbol": "RELIANCE", "instrument_token": 738561}],
                        [{"close": 1}],
                    ]
                ),
            ) as call,
        ):
            mock_date.today.return_value = date(2026, 9, 21)
            asyncio.run(
                run_tool(
                    "zerodha",
                    "market.history",
                    {"symbol": "RELIANCE", "lookback_days": 400},
                    ["loaded"],
                )
            )

        self.assertEqual(call.await_args_list[1].args[2]["from_date"], "2025-08-17 00:00:00")

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
