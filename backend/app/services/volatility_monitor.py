import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np

@dataclass
class MarketAlert:
    symbol: str
    type: str  # "pump" | "dump" | "volume_spike"
    severity: str # "low", "medium", "high"
    change_percent: float
    timeframe: str  # "1m", "5m"
    timestamp: float
    message: str

class VolatilityMonitor:
    """
    Real-time Volatility and Volume Monitor
    
    Tracks recent price and volume history to detect:
    1. Sudden price pumps/dumps
    2. Abnormal volume spikes (often preceding price moves)
    """
    
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        
        # History: { symbol: deque([(timestamp, price, volume), ...]) }
        # stores (ts, price, volume_since_last_tick)
        # MED-4 Fix: Limit history size to prevent memory leaks
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Cooldown: { symbol: (last_alert_timestamp, last_alert_type) }
        self.alert_state: Dict[str, tuple] = {}
        self.COOLDOWN_SECONDS = 60

    def add_tick(self, symbol: str, price: float, volume: float, timestamp: float = None):
        """Add a new tick. Volume should be the volume *delta* since last tick ideally, or accumulated."""
        if timestamp is None:
            timestamp = time.time()
            
        # We need volume delta. If the source gives accumulated volume, we might need to diff it.
        # Assuming for now 'volume' passed here is "volume traded in this brief interval" or we treat it as sample.
        # Check main.py integration: it passes kline volume? Or ticker volume?
        # Ticker returns 24h volume usually. We need K-line volume or AggTrades.
        # If we only get price from ticker (main.py), we can't detect volume spikes easily without AggTrades.
        # For this implementation, we will assume reasonable effort to get volume or skip volume if not available.
        
        self.history[symbol].append((timestamp, price, volume))
        self._prune_history(symbol, timestamp)

    def _prune_history(self, symbol: str, current_time: float):
        q = self.history[symbol]
        while q and (current_time - q[0][0] > self.window_seconds):
            q.popleft()

    def check_volatility(self, symbol: str) -> Optional[MarketAlert]:
        q = self.history[symbol]
        if len(q) < 5:
            return None
            
        current_time = q[-1][0]
        current_price = q[-1][1]
        current_vol = q[-1][2] # Volume of the latest tick/interval
        
        # smart cooldown check
        last_alert_ts, last_alert_type = self.alert_state.get(symbol, (0, ""))
        
        check_points = [
            (30, "30s", 0.005),  # 0.5% in 30s (Very sensitive)
            (60, "1m", 0.01),    # 1% in 1m
            (180, "3m", 0.02),   # 2% in 3m
            (300, "5m", 0.03)    # 3% in 5m
        ]
        
        # 1. Price Volatility Check
        for seconds_ago, tf_label, threshold in check_points:
            target_time = current_time - seconds_ago
            
            # Find tick
            ref_tick = None
            for tick in q:
                if tick[0] >= target_time:
                    ref_tick = tick
                    break
            
            if not ref_tick: continue
            if current_time - ref_tick[0] < (seconds_ago * 0.5): continue # Too recent
            
            ref_price = ref_tick[1]
            change = (current_price - ref_price) / ref_price
            abs_change = abs(change)
            
            if abs_change >= threshold:
                direction = "pump" if change > 0 else "dump"
                
                # Severity
                severity = "low"
                if abs_change >= threshold * 2: severity = "high"
                elif abs_change >= threshold * 1.5: severity = "medium"
                
                # Check cooldown (allow reversal)
                # If last was pump and this is dump -> allow immediately
                # If last was pump and this is pump -> check cooldown
                time_since_last = current_time - last_alert_ts
                is_reversal = (last_alert_type == "pump" and direction == "dump") or \
                              (last_alert_type == "dump" and direction == "pump")
                
                if not is_reversal and time_since_last < self.COOLDOWN_SECONDS:
                    # B-MED-1 修复: continue 而非 return，允许检测更大时间窗口
                    continue
                    
                msg = f"{symbol} {direction.upper()}! {change*100:+.2f}% in {tf_label}"
                
                self.alert_state[symbol] = (current_time, direction)
                return MarketAlert(symbol, direction, severity, change, tf_label, current_time, msg)

        # 2. Volume Spike Check (Simple Moving Average)
        # Calculate avg volume of last 5 mins (excluding last tick)
        # Note: This relies on 'volume' being per-tick or per-interval volume volume.
        # If 'volume' is 0 or not reliable, skip.
        if current_vol > 0:
            past_vols = [Tick[2] for Tick in list(q)[:-1]]
            if len(past_vols) > 10:
                avg_vol = sum(past_vols) / len(past_vols)
                if avg_vol > 0 and current_vol > avg_vol * 5: # 5x volume spike
                    # Volume spike cooldown
                    if current_time - last_alert_ts > self.COOLDOWN_SECONDS:
                         self.alert_state[symbol] = (current_time, "volume_spike")
                         return MarketAlert(
                             symbol=symbol,
                             type="volume_spike",
                             severity="low", # Volume spike is usually a "warning" (Low/Medium)
                             change_percent=0.0,
                             timeframe="1s",
                             timestamp=current_time,
                             message=f"{symbol} 交易量激增! (5x Average)"
                         )

        return None
