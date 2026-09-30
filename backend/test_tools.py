import unittest

from app.tools import CUSTOM_TOOLS, crosses_above, crosses_below, ema, portfolio_exposure, quality_growth_value, rsi, run_tool, screener_fundamentals


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

    def test_screener_fundamentals_returns_stable_json(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        html = """
        <li>Current Price ₹ 149</li><li>Stock P/E 231</li>
        <table><tr><th></th><th>Mar 2024</th><th>Mar 2025</th></tr><tr><td>Sales +</td><td>224</td><td>249</td></tr><tr><td>Operating Profit</td><td>82</td><td>92</td></tr><tr><td>Interest</td><td>4</td><td>3</td></tr><tr><td>Net Profit +</td><td>53</td><td>56</td></tr><tr><td>EPS in Rs</td><td>2.00</td><td>2.13</td></tr></table>
        <table><tr><th></th><th>Mar 2024</th></tr><tr><td>Borrowings +</td><td>18</td></tr><tr><td>Equity Capital</td><td>49</td></tr><tr><td>Reserves</td><td>115</td></tr></table>
        <table><tr><th></th><th>Mar 2024</th></tr><tr><td>Cash from Operating Activity +</td><td>65</td></tr><tr><td>Free Cash Flow</td><td>35</td></tr></table>
        <table><tr><th></th><th>Mar 2024</th></tr><tr><td>ROCE %</td><td>47%</td></tr></table>
        <table><tr><th></th><th>Mar 2024</th></tr><tr><td>Promoters +</td><td>40.06%</td></tr></table>
        <table><tr><th>Return on Equity</th></tr><tr><td>5 Years:</td><td>21%</td></tr><tr><td>3 Years:</td><td>20%</td></tr><tr><td>Last Year:</td><td>5%</td></tr></table>
        """
        response = type("Response", (), {"text": html, "raise_for_status": lambda self: None})()
        with patch("app.tools.screener_fundamentals.httpx.AsyncClient") as client:
            client.return_value.__aenter__ = AsyncMock(return_value=client.return_value)
            client.return_value.__aexit__ = AsyncMock(return_value=None)
            client.return_value.get = AsyncMock(return_value=response)
            result = asyncio.run(screener_fundamentals({"symbol": "avantel"}))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["price"], 149.0)
        self.assertEqual(result["data"]["pe"], 231.0)
        self.assertEqual(result["data"]["roe"], {"latest": 5.0, "3y": 20.0, "5y": 21.0})
        self.assertEqual(result["data"]["revenue"], [{"period": "Mar 2024", "value": 224.0}, {"period": "Mar 2025", "value": 249.0}])
        self.assertEqual(result["data"]["roce"], [{"period": "Mar 2024", "value": 47.0}])
        self.assertIsNone(result["data"]["promoter_pledge"])

    def test_screener_fundamentals_rejects_invalid_symbol(self):
        import asyncio

        result = asyncio.run(screener_fundamentals({"symbol": "bad symbol"}))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error"]["code"], "invalid_symbol")

    def test_registry_awaits_async_custom_tools(self):
        import asyncio

        async def async_tool(data):
            return {"symbol": data["symbol"]}

        previous = CUSTOM_TOOLS["fundamentals.screener"]
        CUSTOM_TOOLS["fundamentals.screener"] = async_tool
        try:
            self.assertEqual(
                asyncio.run(run_tool("custom", "fundamentals.screener", {"symbol": "AVANTEL"})),
                {"symbol": "AVANTEL"},
            )
        finally:
            CUSTOM_TOOLS["fundamentals.screener"] = previous

    def test_quality_growth_value_calculates_buy_signal(self):
        fundamentals = {
            "roe": {"3y": 18, "5y": 17},
            "roce": [{"period": f"Mar {year}", "value": 16} for year in range(2023, 2027)],
            "revenue": [{"period": f"Mar {year}", "value": 100 * 1.2 ** (year - 2023)} for year in range(2023, 2027)],
            "net_profit": [{"period": f"Mar {year}", "value": 10 * 1.2 ** (year - 2023)} for year in range(2023, 2027)],
            "eps": [{"period": f"Mar {year}", "value": 1 * 1.2 ** (year - 2023)} for year in range(2023, 2027)],
            "borrowings": [{"period": "Mar 2026", "value": 20}],
            "equity_capital": [{"period": "Mar 2026", "value": 20}],
            "reserves": [{"period": "Mar 2026", "value": 100}],
            "operating_profit": [{"period": "Mar 2026", "value": 40}],
            "interest": [{"period": "Mar 2026", "value": 4}],
            "operating_cash_flow": [{"period": "Mar 2026", "value": 30}],
            "free_cash_flow": [{"period": f"Mar {year}", "value": 10} for year in range(2024, 2027)],
            "promoter_holding": [{"period": "Mar 2026", "value": 50}],
            "promoter_pledge": 0,
            "pe": 20,
            "historical_pe": None,
            "industry_pe": None,
        }
        closes = list(range(100, 320))
        closes[-1] = 300
        result = quality_growth_value({"fundamentals": fundamentals, "closes": closes})
        self.assertEqual(result["fundamental_status"], "PASS")
        self.assertEqual(result["decision"], "BUY_CANDIDATE")
        self.assertTrue(result["trend"]["long_term_uptrend"])

    def test_quality_growth_value_rejects_or_reviews_exit_from_position_state(self):
        base = {"fundamentals": {"roe": {}, "roce": []}, "closes": []}
        self.assertEqual(quality_growth_value(base)["decision"], "REJECT")
        self.assertEqual(quality_growth_value({**base, "has_position": True})["decision"], "REVIEW_EXIT")

    def test_portfolio_exposure_detects_matching_position(self):
        import asyncio
        from unittest.mock import AsyncMock, patch

        with patch("app.tools.kite.call_kite_tool", new=AsyncMock(side_effect=[[], {"net": [{"tradingsymbol": "AVANTEL", "quantity": 2}]}])):
            result = asyncio.run(portfolio_exposure({"symbol": "AVANTEL"}, ["loaded"]))
        self.assertEqual(result, {"has_position": True, "status": "available", "error": None})

    def test_zerodha_source_alias_uses_mcp_dispatcher(self):
        from unittest.mock import AsyncMock, patch

        with patch("app.tools.kite.kite_session") as session:
            session.return_value.__aenter__ = AsyncMock(return_value=[])
            session.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "app.tools.kite.call_kite_tool",
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
            "app.tools.kite.call_kite_tool",
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
            patch("app.tools.market_history.date") as mock_date,
            patch(
                "app.tools.kite.call_kite_tool",
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
            patch("app.tools.market_history.date") as mock_date,
            patch(
                "app.tools.kite.call_kite_tool",
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
            "app.tools.kite.call_kite_tool", new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], candles])
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
            "app.tools.kite.call_kite_tool",
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
        with patch("app.tools.kite.call_kite_tool", new=AsyncMock(side_effect=[[{"tradingsymbol": "RELIANCE", "instrument_token": 738561}], response])):
            self.assertEqual(
                asyncio.run(run_tool("zerodha", "market.history", {"symbol": "RELIANCE"}, ["loaded"])),
                {"close": [100], "latest": {"close": 100}},
            )


if __name__ == "__main__":
    unittest.main()
