# ==============================================================================
# Path: API/BINANCE/public.py
# Role: Клиент для работы с публичным API Binance Futures
# ==============================================================================

# API/BINANCE/public.py

from __future__ import annotations

import aiohttp

from typing import Optional, Dict, List, Any

class BinancePublic:
    BASE_URL = "https://fapi.binance.com"

    # ==================================================
    # INTERNAL GET
    # ==================================================
    @staticmethod
    async def _get(
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Внутренний GET для публичных запросов."""

        url = BinancePublic.BASE_URL + path

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json()

        except Exception:
            return None

    # ==================================================
    # PUBLIC ENDPOINTS
    # ==================================================

    @staticmethod
    async def get_instruments() -> Optional[List[Dict]]:
        """GET /fapi/v1/exchangeInfo"""
        data = await BinancePublic._get("/fapi/v1/exchangeInfo")

        if isinstance(data, dict) and isinstance(data.get("symbols"), list):
            return data["symbols"]

        return None

    @staticmethod
    async def get_mark_price(symbol: str) -> Optional[float]:
        """GET /fapi/v1/premiumIndex"""
        params = {"symbol": symbol.upper()}

        data = await BinancePublic._get(
            "/fapi/v1/premiumIndex",
            params=params,
        )

        if isinstance(data, dict) and "markPrice" in data:
            try:
                return float(data["markPrice"])
            except Exception:
                return None

        return None

    @staticmethod
    async def get_last_price(symbol: str) -> Optional[float]:
        """GET /fapi/v1/ticker/price (symbol)"""
        params = {"symbol": symbol.upper()}

        data = await BinancePublic._get(
            "/fapi/v1/ticker/price",
            params=params,
        )

        if isinstance(data, dict) and "price" in data:
            try:
                return float(data["price"])
            except Exception:
                return None

        return None

    @staticmethod
    async def get_all_prices() -> Optional[List[Dict]]:
        """GET /fapi/v1/ticker/price (без symbol) -> список всех {symbol, price}"""
        data = await BinancePublic._get(
            "/fapi/v1/ticker/price",
            params=None,
        )

        if isinstance(data, list):
            return data

        return None

    @staticmethod
    async def get_prices_bulk(symbols: List[str]) -> Dict[str, float]:
        """Один запрос, возвращает цены только по нужным symbols."""

        out: Dict[str, float] = {}
        if not symbols:
            return out

        data = await BinancePublic.get_all_prices()
        if not data:
            return out

        want = {(s or "").upper() for s in symbols if s}
        for row in data:
            try:
                if not isinstance(row, dict):
                    continue
                sym = (row.get("symbol") or "").upper()
                if sym in want:
                    out[sym] = float(row.get("price"))
            except Exception:
                continue

        return out
