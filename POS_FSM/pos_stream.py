# ==============================================================================
# Path: FSM/pos_stream.py
# Role: Подключение к User Data Stream и менеджер Listen Key
# ==============================================================================

import asyncio
import aiohttp
import json
from typing import Optional, Callable, Set
from POS_FSM.pos_stream_monitor import PositionMonitor
from c_utils import Utils
from c_log import UnifiedLogger

logger = UnifiedLogger("FSM_Stream")
IS_SHOW_SIGNAL = True

class BinanceListenKeyManager:
    """
    Менеджер User Data Stream Listen Key.
    Единственное место, где используется API KEY.
    WS сюда не лезет.
    """
    KEEPALIVE_INTERVAL = 25 * 60  # Binance рекомендует < 30 мин

    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session
        self.listen_key: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    async def create(self) -> str:
        async with self.session.post(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": self.api_key},
        ) as r:
            data = await r.json()
            self.listen_key = data["listenKey"]

        await self.session.put(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": self.api_key},
        )

        logger.info("[BINANCE] listenKey created & activated")
        return self.listen_key

    async def _keepalive_loop(self):
        while True:
            await asyncio.sleep(self.KEEPALIVE_INTERVAL)
            try:
                await self.session.put(
                    "https://fapi.binance.com/fapi/v1/listenKey",
                    headers={"X-MBX-APIKEY": self.api_key},
                )
                logger.debug("[BINANCE] listenKey keepalive")
            except Exception as e:
                logger.warning(f"[BINANCE] listenKey keepalive failed: {e}")

    def start_keepalive(self):
        if not self._task:
            self._task = asyncio.create_task(self._keepalive_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

class PositionStream:
    """
    BINANCE FUTURES USER DATA STREAM
    
    Стримом парсим только ендпоинт открытых позиций (ACCOUNT_UPDATE).
    """
    def __init__(
        self,
        *,
        api_key: str,
        stop_flag: Callable[[], bool],
        monitor: PositionMonitor,
        target_symbols: Optional[Set[str]] = None,
    ):
        self.api_key = api_key
        self.stop_flag = stop_flag
        self.monitor = monitor
        self.target_symbols = {s.upper() for s in target_symbols} if target_symbols else set()

        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.listen_mgr: Optional[BinanceListenKeyManager] = None

        self.ws_url: Optional[str] = None
        self.ready = False
        self.is_connected = False
        self._external_stop = False

    def stop(self):
        self._external_stop = True
        self.ready = False
        logger.info("PositionStream: stop requested")

    async def _create_session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(total=None)
        logger.info("[MASTER WS] direct connection")
        return aiohttp.ClientSession(timeout=timeout, trust_env=False)

    async def _connect(self) -> bool:
        try:
            logger.info("[MASTER WS] connecting...")
            self.websocket = await self.session.ws_connect(
                self.ws_url,
                autoping=True,
                max_msg_size=0,
                timeout=15,
            )
            self.is_connected = True
            logger.info("[MASTER WS] connected")
            return True
        except Exception as e:
            logger.warning(f"[MASTER WS] connect failed: {e}")
            return False

    async def _disconnect(self):
        self.is_connected = False
        self.ready = False

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
            self.websocket = None

        if self.listen_mgr:
            await self.listen_mgr.stop()
            self.listen_mgr = None

        logger.info("PositionStream: WS disconnected")

    async def _handle_account_update(self, data: dict):
        acc = data.get("a", {})
        positions = acc.get("P", [])

        for p in positions:
            raw_symbol = p.get("s", "")
            symbol = Utils.normalize_symbol(raw_symbol)
            if not symbol:
                continue

            pos_side_raw = (p.get("ps") or "").upper()
            pos_amt = p.get("pa")
            ep_raw = p.get("ep") or p.get("bep") or "0"

            if not pos_side_raw or pos_amt is None:
                continue

            if pos_side_raw not in ("LONG", "SHORT"):
                continue

            if self.target_symbols and symbol not in self.target_symbols:
                continue

            try:
                pos_amt_f = float(pos_amt)
                avg_price_f = float(ep_raw)
            except (ValueError, TypeError):
                continue

            self.monitor.update_from_stream(
                symbol=symbol,
                side=pos_side_raw,
                pos_amt=pos_amt_f,
                entry_price=avg_price_f
            )

    async def _handle_messages(self):
        while not self._external_stop and not self.stop_flag():
            try:
                msg = await asyncio.wait_for(
                    self.websocket.receive(),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                continue

            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                logger.warning(f"[MASTER WS] socket closed: {msg.type}")
                raise RuntimeError("ws_closed")

            if msg.type != aiohttp.WSMsgType.TEXT:
                continue

            try:
                data = json.loads(msg.data)
            except Exception as e:
                logger.warning(f"[MASTER WS] invalid JSON: {e}")
                continue

            etype = data.get("e")
            if not etype:
                continue

            if IS_SHOW_SIGNAL:
                logger.debug(f"[MASTER WS] EVENT {etype}")

            if etype == "ACCOUNT_UPDATE":
                await self._handle_account_update(data)

    async def start(self):
        self._external_stop = False
        try:
            while not self._external_stop and not self.stop_flag():
                self.session = await self._create_session()
                try:
                    self.listen_mgr = BinanceListenKeyManager(
                        api_key=self.api_key,
                        session=self.session,
                    )
                    listen_key = await self.listen_mgr.create()
                    self.listen_mgr.start_keepalive()

                    self.ws_url = f"wss://fstream.binance.com/ws/{listen_key}"

                    if not await self._connect():
                        raise RuntimeError("ws_connect_failed")

                    self.ready = True
                    await self._handle_messages()

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"[MASTER WS] cycle failed: {e}")

                finally:
                    self.ready = False
                    await self._disconnect()

                    if self.session:
                        try:
                            await self.session.close()
                        except Exception:
                            pass
                        self.session = None

                    if not self._external_stop:
                        await asyncio.sleep(1.0)
        finally:
            self.ready = False
