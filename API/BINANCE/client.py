# ==============================================================================
# Path: API/BINANCE/client.py
# Role: Клиент для работы с приватным API Binance Futures
# ==============================================================================

# API/BINANCE/client.py

from __future__ import annotations

import asyncio
import aiohttp
import time
import hmac
import hashlib
from typing import Any, Dict, List, Optional
from consts import REQ_TIMEOUT_SEC, TIME_SLACK_SEC, API_RATE_LIMIT_SEC, API_CONCURRENT_RATE_LIMIT_SEC
from c_log import UnifiedLogger

from .validator import OrderValidator, APIResponse

logger = UnifiedLogger("BINANCE_API")

class BinanceClient:

    def __init__(
        self,
        api_key: Optional[str],
        api_secret: Optional[str],
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.validator = OrderValidator(logger)

        self.create_order_url = "https://fapi.binance.com/fapi/v1/order"
        self.cancel_order_url = self.create_order_url
        self.cancel_all_url   = "https://fapi.binance.com/fapi/v1/allOpenOrders"
        self.positions_url    = "https://fapi.binance.com/fapi/v2/account"
        self.position_mode_url = "https://fapi.binance.com/fapi/v1/positionSide/dual"
        self.balance_url      = "https://fapi.binance.com/fapi/v2/balance"
        self.user_trades_url  = "https://fapi.binance.com/fapi/v1/userTrades"
        self.set_leverage_url = "https://fapi.binance.com/fapi/v1/leverage"
        self.set_margin_url   = "https://fapi.binance.com/fapi/v1/marginType"

        # ===== SESSION MANAGER =====
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
        # ===== RATE LIMITER =====
        self._api_lock = asyncio.Lock()
        self._last_send_time = 0.0

    # ==================================================
    # SESSION MANAGER
    # ==================================================

    async def _get_session(self) -> aiohttp.ClientSession:

        # предполагается, что lock уже взят
        if self._session and not self._session.closed:
            return self._session

        timeout_cfg = aiohttp.ClientTimeout(total=REQ_TIMEOUT_SEC)
        self._session = aiohttp.ClientSession(timeout=timeout_cfg)

        return self._session

    async def _close_session(self):
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    async def shutdown(self):
        await self._close_session()

    # ==================================================
    # INTERNAL
    # ==================================================

    def _sign(self, params: dict) -> dict:
        # Binance signature MUST be computed over the EXACT query string that is sent.
        # Therefore we keep insertion-order of params and avoid sorting keys.
        if not self.api_secret:
            raise RuntimeError("API_SECRET is missing")

        params = {k: v for k, v in (params or {}).items() if v is not None}
        params["timestamp"] = int(time.time() * 1000)

        # IMPORTANT: use the same order we will send to aiohttp (dict insertion order).
        query = "&".join(f"{k}={params[k]}" for k in params.keys())

        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self.api_key} if self.api_key else {}
    
    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        signed: bool = False,
        concurrent_mode: bool = False,
    ) -> APIResponse:
        limit = API_CONCURRENT_RATE_LIMIT_SEC if concurrent_mode else API_RATE_LIMIT_SEC
        
        async with self._api_lock:
            elapsed = time.monotonic() - self._last_send_time
            if elapsed < limit:
                await asyncio.sleep(limit - elapsed)
            self._last_send_time = time.monotonic()
            
        params = params or {}

        if signed:
            params = self._sign(params)

        # чтобы в мету/логи не утекала signature
        def _safe_params(p: dict) -> dict:
            try:
                out = dict(p or {})
                if "signature" in out:
                    out["signature"] = "***"
                return out
            except Exception:
                return {}

        safe_params = _safe_params(params)

        try:
            async with self._session_lock:
                session = await self._get_session()

            async with session.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                ) as resp:

                    http_status = int(resp.status)

                    try:
                        data = await resp.json()
                    except Exception:
                        # иногда прилетает html/текст от прокси/Cloudflare и т.п.
                        try:
                            text = await resp.text()
                        except Exception:
                            text = ""

                        return APIResponse(
                            success=False,
                            error_code=-1,
                            error_msg="INVALID_JSON",
                            meta={
                                "http_status": http_status,
                                "method": method,
                                "url": url,
                                "params": safe_params,
                                "text": (text or "")[:300],
                            }
                        )

                    is_success = True
                    error_code = None
                    error_msg = None

                    if isinstance(data, dict) and "code" in data:
                        try:
                            code_val = int(data["code"])
                            if code_val < 0:
                                is_success = False
                                error_code = code_val
                                error_msg = data.get("msg")
                        except ValueError:
                            pass
                            
                    return APIResponse(
                        success=is_success,
                        data=data,
                        error_code=error_code,
                        error_msg=error_msg,
                        meta={
                            "http_status": http_status,
                            "method": method,
                            "url": url,
                            "params": safe_params,
                        }
                    )

        except asyncio.TimeoutError:
            return APIResponse(
                success=False,
                error_code=-1,
                error_msg="TIMEOUT",
                meta={"method": method, "url": url, "params": safe_params}
            )

        except Exception as e:
            return APIResponse(
                success=False,
                error_code=-1,
                error_msg=f"EXCEPTION {type(e).__name__}: {e}",
                meta={"method": method, "url": url, "params": safe_params}
            )

    # ==================================================
    # ORDER
    # ==================================================
    async def make_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        position_side: str,
        market_type: str = "MARKET",
        price: Optional[float] = None,
        reduce_only: bool = False,   # NEW
        concurrent_mode: bool = False,
    ) -> APIResponse:

        params = {
            "symbol": symbol,
            "side": side,
            "type": market_type,
            "quantity": abs(qty),
            "positionSide": position_side,
            "recvWindow": 20000,
            "newOrderRespType": "RESULT",
        }

        if market_type == "LIMIT":
            params.update({
                "price": price,
                "timeInForce": "GTC",
            })

        data = await self._request(
            "POST",
            self.create_order_url,
            params=params,
            signed=True,
            concurrent_mode=concurrent_mode,
        )

        return self.validator.validate_order_create(
            data,
            market_type=market_type,
        )

    # ==================================================
    # CANCEL BY IDS
    # ==================================================
    async def cancel_limit_orders(
        self,
        symbol: str,
        order_id_list: List[int],
    ) -> APIResponse:

        if not order_id_list:
            return APIResponse(success=True, data=[])

        results = []
        errors = []

        for oid in order_id_list:
            data = await self._request(
                "DELETE",
                self.cancel_order_url,
                params={
                    "symbol": symbol,
                    "orderId": int(oid),
                    "recvWindow": 20000,
                },
                signed=True,
            )

            res = self.validator.validate_cancel(data)
            results.append(res)

            if not res.success:
                errors.append(res)

        if errors:
            return APIResponse(
                success=False,
                data=results,
                error_msg="CANCEL_ERRORS"
            )

        return APIResponse(
            success=True,
            data=results
        )

    # ==================================================
    # CANCEL ALL
    # ==================================================
    async def cancel_all_orders(self, symbol: str) -> APIResponse:
        """Отменить все открытые ордера по символу."""
        data = await self._request(
            "DELETE",
            self.cancel_all_url,
            params={"symbol": symbol},
            signed=True,
        )

        return self.validator.validate_cancel_all(data)

    # ==================================================
    # CANCEL FOR SPECIFIC SIDE
    # ==================================================
    async def cancel_orders_for_side(self, symbol: str, position_side: str):
        """Отменяет все открытые ордера по символу для указанной стороны (LONG или SHORT)."""
        open_orders = await self.fetch_open_orders(symbol)
        if not open_orders:
            return APIResponse(success=True, data=[])
            
        ids_to_cancel = []
        for order in open_orders:
            if order.get("positionSide") == position_side:
                ids_to_cancel.append(order.get("orderId"))
                
        if not ids_to_cancel:
            return APIResponse(success=True, data=[])
            
        logger.info(f"[{symbol}] {position_side} Found {len(ids_to_cancel)} active orders. Canceling...")
        return await self.cancel_limit_orders(symbol, ids_to_cancel)

    # ==================================================
    # ACCOUNT INFO
    # ==================================================
    async def fetch_account_info(self) -> APIResponse:
        params = {"recvWindow": 20000}
        return await self._request(
            "GET",
            self.positions_url,
            params=params,
            signed=True,
        )

    # ==================================================
    # POSITIONS
    # ==================================================
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[dict]:
        # NOTE: /fapi/v2/account does NOT support symbol param.
        # We always fetch full positions list and optionally filter locally.
        params = {"recvWindow": 20000}

        res = await self._request(
            "GET",
            self.positions_url,
            params=params,
            signed=True,
        )

        if res.success and isinstance(res.data, dict) and "positions" in res.data:
            positions = res.data.get("positions", [])
            if symbol:
                sym = (symbol or "").upper()
                try:
                    return [p for p in positions if (p.get("symbol") or "").upper() == sym]
                except Exception:
                    return positions
            return positions
        return []
    
    # ==================================================
    # OPEN ORDERS
    # ==================================================
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[dict]:

        params = {"recvWindow": 20000}

        if symbol:
            params["symbol"] = symbol

        res = await self._request(
            "GET",
            "https://fapi.binance.com/fapi/v1/openOrders",
            params=params,
            signed=True,
        )

        if res.success and isinstance(res.data, list):
            return res.data

        return []

    # ==================================================
    # LEVERAGE
    # ==================================================
    async def set_leverage(self, symbol: str, leverage: int) -> APIResponse:

        return await self._request(
            "POST",
            self.set_leverage_url,
            params={
                "symbol": symbol,
                "leverage": leverage,
                "recvWindow": 20000,
            },
            signed=True,
        )

    # ==================================================
    # MARGIN TYPE
    # ==================================================
    async def set_margin_type(self, symbol: str, margin_type: str) -> APIResponse:

        return await self._request(
            "POST",
            self.set_margin_url,
            params={
                "symbol": symbol,
                "marginType": margin_type,
                "recvWindow": 20000,
            },
            signed=True,
        )

    # ==================================================
    # REALIZED PNL
    # ==================================================
    async def get_realized_pnl(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Optional[float]:

        params = {
            "symbol": symbol,
            "recvWindow": 20000,
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        res = await self._request(
            "GET",
            self.user_trades_url,
            params=params,
            signed=True,
        )

        if not res.success or not isinstance(res.data, list):
            return None

        rows = res.data

        pnl_usdt = 0.0
        matched = False

        for r in rows:
            ts = int(r.get("time", 0))
            if start_time and ts < (start_time - int(TIME_SLACK_SEC * 1000)):
                continue

            pnl_usdt += float(r.get("realizedPnl", 0.0))
            matched = True

        if not matched:
            return None

        return round(pnl_usdt, 4)