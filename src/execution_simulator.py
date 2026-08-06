"""
execution_simulator.py — Execution simulation layer for backtest.

Bu modul, backtest motorunun entry/exit emirlerini gercekci bir sekilde
simule etmek icin kullanilir. Strateji sinyalini degistirmez, sadece
fiyat, gecikme, kismi dolma ve reddetme modellerini uygular.

Kullanim:
    from execution_simulator import ExecutionSimulator, ExecutionConfig
    
    sim = ExecutionSimulator(profiles_path="sniper/output/execution_profiles.json")
    result = sim.submit_entry(
        symbol="UNIUSDT",
        side="long",
        signal_price=3.532,
        requested_qty=282.0,
        sl=3.528,
        tp=3.560,
        bar_timestamp=1784428140000,
        atr=0.01,
        mode="deterministic"
    )
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("execution_simulator")

# ── Paths ────────────────────────────────────────────────────────
_BACKTEST_DIR = Path(__file__).resolve().parent
_PROFILES_PATH = _BACKTEST_DIR.parent.parent / "sniper" / "output" / "execution_profiles.json"


class OrderStatus(str, Enum):
    QUEUED = "QUEUED"
    ACCEPTED = "ACCEPTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RejectReason(str, Enum):
    MIN_QTY = "MIN_QTY"
    MIN_NOTIONAL = "MIN_NOTIONAL"
    INVALID_PRICE = "INVALID_PRICE"
    IMMEDIATE_TRIGGER = "IMMEDIATE_TRIGGER"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    NETWORK_ERROR = "NETWORK_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    EXCHANGE_ERROR = "EXCHANGE_ERROR"
    PROTECTION_TIMEOUT = "PROTECTION_TIMEOUT"


@dataclass(frozen=True)
class MarketSnapshot:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread_bps: float = 0.0
    available_liquidity: float = 0.0


@dataclass
class SimulatedOrder:
    order_id: str
    symbol: str
    side: str
    order_type: str
    requested_qty: float
    requested_price: float | None
    status: OrderStatus
    filled_qty: float = 0.0
    average_fill_price: float | None = None
    submitted_at: int = 0
    accepted_at: int | None = None
    filled_at: int | None = None
    rejected_reason: str | None = None
    fees: float = 0.0
    slippage_bps: float = 0.0
    delay_bars: int = 0


@dataclass(frozen=True)
class ExecutionConfig:
    seed: int = 42
    entry_delay_bars_min: int = 0
    entry_delay_bars_max: int = 1
    protection_delay_bars: int = 0
    cancel_replace_delay_bars: int = 0
    base_slippage_bps: float = 1.0
    volatility_slippage_mult: float = 0.5
    spread_bps: float = 2.0
    reject_probability: float = 0.0
    protection_reject_probability: float = 0.0
    partial_fill_probability: float = 0.0
    partial_fill_ratio_min: float = 0.25
    partial_fill_ratio_max: float = 0.90
    max_order_age_bars: int = 2
    fee_rate: float = 0.0005


class ExecutionSimulator:
    """Execution simulation layer for backtest engine."""

    def __init__(self, profiles_path: str | None = None, mode: str = "deterministic"):
        self.mode = mode
        self.profiles: dict[str, dict[str, Any]] = {}
        self.global_config = ExecutionConfig()
        self._rng = random.Random(self.global_config.seed)
        self._order_counter = 0

        if profiles_path and os.path.isfile(profiles_path):
            self._load_profiles(profiles_path)
        elif _PROFILES_PATH.exists():
            self._load_profiles(str(_PROFILES_PATH))

    def _load_profiles(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.profiles = data
            logger.info(f"Loaded {len(data)} execution profiles from {path}")
        except Exception as e:
            logger.warning(f"Failed to load execution profiles: {e}")

    def _get_profile(self, symbol: str) -> dict[str, Any]:
        if symbol in self.profiles:
            return self.profiles[symbol]
        return {
            "spread_bps": 2.0,
            "base_slippage_bps": 1.0,
            "volatility_slippage_mult": 0.5,
            "reject_probability": 0.002,
            "protection_reject_probability": 0.01,
            "partial_fill_probability": 0.0,
            "partial_fill_ratio_min": 0.25,
            "partial_fill_ratio_max": 0.90,
            "fee_rate": 0.0005,
        }

    def _create_order_id(self) -> str:
        self._order_counter += 1
        return f"sim-{self._order_counter:06d}"

    def _sample_delay(self, cfg: ExecutionConfig, symbol: str) -> int:
        profile = self._get_profile(symbol)
        min_d = cfg.entry_delay_bars_min
        max_d = cfg.entry_delay_bars_max
        if self.mode == "deterministic":
            return min_d
        return self._rng.randint(min_d, max_d)

    def _sample_slippage_bps(self, cfg: ExecutionConfig, symbol: str, atr: float, signal_price: float) -> float:
        profile = self._get_profile(symbol)
        base = profile.get("base_slippage_bps", cfg.base_slippage_bps)
        vol_mult = profile.get("volatility_slippage_mult", cfg.volatility_slippage_mult)
        
        if self.mode == "deterministic":
            return base
        
        volatility_component = 0.0
        if atr > 0 and signal_price > 0:
            atr_pct = (atr / signal_price) * 10000
            volatility_component = atr_pct * vol_mult
        
        total_bps = base + volatility_component
        return max(0.0, total_bps)

    def _sample_partial_fill(self, cfg: ExecutionConfig, symbol: str) -> tuple[float, bool]:
        profile = self._get_profile(symbol)
        pfp = profile.get("partial_fill_probability", cfg.partial_fill_probability)
        
        if self.mode == "deterministic" or pfp <= 0:
            return 1.0, False
        
        if self._rng.random() < pfp:
            ratio_min = profile.get("partial_fill_ratio_min", cfg.partial_fill_ratio_min)
            ratio_max = profile.get("partial_fill_ratio_max", cfg.partial_fill_ratio_max)
            ratio = self._rng.uniform(ratio_min, ratio_max)
            return ratio, True
        return 1.0, False

    def _check_reject(self, cfg: ExecutionConfig, symbol: str, order_type: str = "entry") -> tuple[bool, str | None]:
        profile = self._get_profile(symbol)
        if order_type == "protection":
            prob = profile.get("protection_reject_probability", cfg.protection_reject_probability)
        else:
            prob = profile.get("reject_probability", cfg.reject_probability)
        
        if self.mode == "deterministic" or prob <= 0:
            return False, None
        
        if self._rng.random() < prob:
            reasons = [
                RejectReason.MIN_QTY,
                RejectReason.MIN_NOTIONAL,
                RejectReason.INVALID_PRICE,
                RejectReason.IMMEDIATE_TRIGGER,
                RejectReason.INSUFFICIENT_MARGIN,
                RejectReason.NETWORK_ERROR,
                RejectReason.RATE_LIMIT,
                RejectReason.EXCHANGE_ERROR,
            ]
            return True, self._rng.choice(reasons).value
        return False, None

    def submit_entry(
        self,
        symbol: str,
        side: str,
        signal_price: float,
        requested_qty: float,
        sl: float | None = None,
        tp: float | None = None,
        bar_timestamp: int = 0,
        atr: float = 0.0,
        mode: str | None = None,
    ) -> SimulatedOrder:
        """Submit an entry order and simulate execution."""
        cfg = self.global_config
        sim_mode = mode or self.mode
        order_id = self._create_order_id()
        order = SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type="MARKET",
            requested_qty=requested_qty,
            requested_price=signal_price,
            status=OrderStatus.QUEUED,
            submitted_at=bar_timestamp,
        )

        # ── Step 1: Check for rejection ──
        rejected, reason = self._check_reject(cfg, symbol, "entry")
        if rejected:
            order.status = OrderStatus.REJECTED
            order.rejected_reason = reason
            logger.debug(f"[{symbol}] Entry rejected: {reason}")
            return order

        # ── Step 2: Simulate delay ──
        delay_bars = self._sample_delay(cfg, symbol)
        order.delay_bars = delay_bars
        order.accepted_at = bar_timestamp + delay_bars * 15 * 60 * 1000

        # ── Step 3: Calculate fill price with spread and slippage ──
        slippage_bps = self._sample_slippage_bps(cfg, symbol, atr, signal_price)
        spread_bps = self._get_profile(symbol).get("spread_bps", cfg.spread_bps)
        total_slippage_bps = spread_bps + slippage_bps
        slippage_mult = total_slippage_bps / 10000.0

        if side == "long":
            fill_price = signal_price * (1.0 + slippage_mult)
        else:
            fill_price = signal_price * (1.0 - slippage_mult)

        order.slippage_bps = total_slippage_bps

        # ── Step 4: Partial fill simulation ──
        fill_ratio, is_partial = self._sample_partial_fill(cfg, symbol)
        filled_qty = requested_qty * fill_ratio
        order.filled_qty = filled_qty

        if is_partial and filled_qty < requested_qty:
            order.status = OrderStatus.PARTIAL
        else:
            order.status = OrderStatus.FILLED
            filled_qty = requested_qty
            order.filled_qty = filled_qty

        order.average_fill_price = fill_price
        order.filled_at = order.accepted_at

        # ── Step 5: Calculate fees ──
        fee_rate = self._get_profile(symbol).get("fee_rate", cfg.fee_rate)
        order.fees = fill_price * filled_qty * fee_rate

        logger.debug(
            f"[{symbol}] Entry filled: side={side}, price={fill_price:.6f}, "
            f"qty={filled_qty:.2f}/{requested_qty:.2f}, slippage={total_slippage_bps:.2f}bps"
        )

        return order

    def submit_protection_orders(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        filled_qty: float,
        sl: float | None,
        tp: float | None,
        bar_timestamp: int = 0,
        mode: str | None = None,
    ) -> tuple[SimulatedOrder | None, SimulatedOrder | None]:
        """Submit SL and TP protection orders."""
        cfg = self.global_config
        sim_mode = mode or self.mode
        
        sl_order = None
        tp_order = None

        if sl is not None and filled_qty > 0:
            sl_order = self._submit_single_protection(
                symbol, side, "STOP_MARKET", sl, filled_qty, bar_timestamp, "sl"
            )

        if tp is not None and filled_qty > 0:
            tp_order = self._submit_single_protection(
                symbol, side, "TAKE_PROFIT_MARKET", tp, filled_qty, bar_timestamp, "tp"
            )

        return sl_order, tp_order

    def _submit_single_protection(
        self,
        symbol: str,
        side: str,
        order_type: str,
        trigger_price: float,
        qty: float,
        bar_timestamp: int,
        kind: str,
    ) -> SimulatedOrder | None:
        cfg = self.global_config
        order_id = self._create_order_id()
        
        rejected, reason = self._check_reject(cfg, symbol, "protection")
        if rejected:
            order = SimulatedOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_qty=qty,
                requested_price=trigger_price,
                status=OrderStatus.REJECTED,
                submitted_at=bar_timestamp,
                rejected_reason=reason,
            )
            logger.debug(f"[{symbol}] {kind.upper()} rejected: {reason}")
            return order

        delay = self._sample_delay(cfg, symbol)
        order = SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_qty=qty,
            requested_price=trigger_price,
            status=OrderStatus.FILLED,
            filled_qty=qty,
            average_fill_price=trigger_price,
            submitted_at=bar_timestamp,
            accepted_at=bar_timestamp + delay * 15 * 60 * 1000,
            filled_at=bar_timestamp + delay * 15 * 60 * 1000,
            delay_bars=delay,
        )
        return order

    def get_execution_adjusted_exit(
        self,
        symbol: str,
        side: str,
        exit_price: float,
        exit_type: str,
        bar: Any,
        mode: str | None = None,
    ) -> tuple[float, float]:
        """Calculate execution-adjusted exit price and fee."""
        cfg = self.global_config
        profile = self._get_profile(symbol)
        spread_bps = profile.get("spread_bps", cfg.spread_bps)
        base_slippage_bps = profile.get("base_slippage_bps", cfg.base_slippage_bps)
        
        total_slippage_bps = spread_bps + base_slippage_bps
        slippage_mult = total_slippage_bps / 10000.0
        
        if side == "long":
            if exit_type == "TP":
                adjusted_price = exit_price * (1.0 - slippage_mult * 0.5)
            else:
                adjusted_price = exit_price * (1.0 - slippage_mult)
        else:
            if exit_type == "TP":
                adjusted_price = exit_price * (1.0 + slippage_mult * 0.5)
            else:
                adjusted_price = exit_price * (1.0 + slippage_mult)

        fee_rate = profile.get("fee_rate", cfg.fee_rate)
        return adjusted_price, fee_rate

    def zero_friction_entry(
        self,
        symbol: str,
        side: str,
        signal_price: float,
        requested_qty: float,
        bar_timestamp: int = 0,
    ) -> SimulatedOrder:
        """Zero-friction entry for baseline comparison."""
        order_id = self._create_order_id()
        return SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type="MARKET",
            requested_qty=requested_qty,
            requested_price=signal_price,
            status=OrderStatus.FILLED,
            filled_qty=requested_qty,
            average_fill_price=signal_price,
            submitted_at=bar_timestamp,
            accepted_at=bar_timestamp,
            filled_at=bar_timestamp,
            fees=0.0,
            slippage_bps=0.0,
            delay_bars=0,
        )


# ── Convenience function ─────────────────────────────────────────
def create_execution_simulator(
    profiles_path: str | None = None,
    mode: str = "deterministic",
    seed: int = 42,
) -> ExecutionSimulator:
    """Create an execution simulator instance."""
    sim = ExecutionSimulator(profiles_path=profiles_path, mode=mode)
    sim.global_config = ExecutionConfig(seed=seed)
    sim._rng = random.Random(seed)
    return sim
