from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from src.config import (
    DEFAULT_STOP_LOSS_PCT,
    DEFAULT_TAKE_PROFIT_PCT,
    MIN_SIGNAL_STRENGTH
)

@dataclass
class AgentSignal:
    agent_name: str
    symbol: str
    action: str
    score: float
    confidence: float
    reason: str
    metrics: Dict = field(default_factory=dict)

class TrendFollowerAgent:
    name = "Trend Ajanı"

    def analyze(self, symbol: str, snapshot: Dict) -> AgentSignal:
        latest = snapshot.get("latest", {})
        close = latest.get("Close", 1.0)
        ema9 = latest.get("EMA_9", close)
        ema21 = latest.get("EMA_21", close)
        ema50 = latest.get("EMA_50", close)
        ema200 = latest.get("EMA_200", close)
        macd = latest.get("MACD", 0.0)
        macd_signal = latest.get("MACD_SIGNAL", 0.0)
        macd_diff = latest.get("MACD_DIFF", 0.0)

        score = 0.0
        reasons = []

        if close > ema21 > ema50:
            score += 0.5
            reasons.append("Fiyat kısa-orta vadeli EMA'ların üzerinde (Boğa Yapısı).")
            if close > ema200:
                score += 0.2
                reasons.append("200 günlük EMA üzerinde pozitif ana trend.")
        elif close < ema21 < ema50:
            score -= 0.5
            reasons.append("Fiyat EMA'ların altında (Ayı Yapısı).")
            if close < ema200:
                score -= 0.2
                reasons.append("200 günlük EMA altında zayıf görünüm.")

        if macd > macd_signal and macd_diff > 0:
            score += 0.3
            reasons.append(f"MACD pozitif bölgede ({macd:.2f} > {macd_signal:.2f}).")
        elif macd < macd_signal and macd_diff < 0:
            score -= 0.3
            reasons.append(f"MACD negatif bölgede ({macd:.2f} < {macd_signal:.2f}).")

        score = max(-1.0, min(1.0, score))
        action = "AL" if score >= 0.35 else ("SAT" if score <= -0.35 else "TUT")

        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            action=action,
            score=round(score, 3),
            confidence=round(abs(score), 2),
            reason=" ".join(reasons) if reasons else "Trend göstergeleri nötr/yatay.",
            metrics={"EMA_21": round(ema21, 2), "EMA_50": round(ema50, 2), "MACD": round(macd, 2)}
        )

class MomentumAgent:
    name = "Momentum Ajanı"

    def analyze(self, symbol: str, snapshot: Dict) -> AgentSignal:
        latest = snapshot.get("latest", {})
        prev = snapshot.get("prev", {})
        rsi = latest.get("RSI_14", 50.0)
        prev_rsi = prev.get("RSI_14", 50.0)

        score = 0.0
        reasons = []

        if rsi < 30.0:
            score = 0.85
            reasons.append(f"RSI aşırı satım bölgesinde ({rsi:.1f} < 30). Güçlü tepki yükselişi potansiyeli.")
        elif 30.0 <= rsi <= 45.0 and rsi > prev_rsi:
            score = 0.45
            reasons.append(f"RSI dipten toparlanma eğiliminde ({rsi:.1f}).")
        elif rsi > 70.0:
            score = -0.85
            reasons.append(f"RSI aşırı alım bölgesinde ({rsi:.1f} > 70). Düzeltme ve kâr satışı riski.")
        elif 55.0 <= rsi <= 70.0 and rsi < prev_rsi:
            score = -0.45
            reasons.append(f"RSI tepe bölgesinde ivme kaybediyor ({rsi:.1f}).")
        else:
            score = 0.0
            reasons.append(f"RSI nötr dengeli bölgede ({rsi:.1f}).")

        score = max(-1.0, min(1.0, score))
        action = "AL" if score >= 0.35 else ("SAT" if score <= -0.35 else "TUT")

        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            action=action,
            score=round(score, 3),
            confidence=round(abs(score), 2),
            reason=" ".join(reasons),
            metrics={"RSI_14": round(rsi, 2), "RSI_FARKI": round(rsi - prev_rsi, 2)}
        )

class VolatilityBreakoutAgent:
    name = "Volatilite Ajanı"

    def analyze(self, symbol: str, snapshot: Dict) -> AgentSignal:
        latest = snapshot.get("latest", {})
        close = latest.get("Close", 1.0)
        bb_high = latest.get("BB_HIGH", close * 1.05)
        bb_low = latest.get("BB_LOW", close * 0.95)
        bb_wid = latest.get("BB_WID", 0.05)
        vol_ratio = latest.get("VOL_RATIO", 1.0)

        score = 0.0
        reasons = []

        if close > bb_high:
            if vol_ratio >= 1.2:
                score = 0.85
                reasons.append(f"Fiyat üst Bollinger bandını yüksek hacimle kırdı ({vol_ratio:.1f}x hacim).")
            else:
                score = 0.4
                reasons.append("Fiyat üst banda temas etti, hacim desteği ılımlı.")
        elif close < bb_low:
            if vol_ratio >= 1.2:
                score = -0.85
                reasons.append(f"Fiyat alt bandı kırdı ve satış hacmi yoğun ({vol_ratio:.1f}x hacim).")
            else:
                score = -0.4
                reasons.append("Fiyat alt bandın altında ancak hacim baskısı düşük.")
        else:
            if bb_wid < 0.05:
                reasons.append("Bollinger bantlarında sıkışma (Squeeze) var, yön kırılımı yakın.")
            else:
                reasons.append("Fiyat Bollinger bantları içinde olağan salınıyor.")

        score = max(-1.0, min(1.0, score))
        action = "AL" if score >= 0.35 else ("SAT" if score <= -0.35 else "TUT")

        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            action=action,
            score=round(score, 3),
            confidence=round(abs(score), 2),
            reason=" ".join(reasons),
            metrics={"BB_UST": round(bb_high, 2), "BB_ALT": round(bb_low, 2), "HACIM_KATI": round(vol_ratio, 2)}
        )

class MacroSentimentAgent:
    name = "Piyasa Rejimi Ajanı"

    def analyze(self, symbol: str, snapshot: Dict) -> AgentSignal:
        latest = snapshot.get("latest", {})
        close = latest.get("Close", 1.0)
        adx = latest.get("ADX_14", 20.0)
        adx_pos = latest.get("ADX_POS", 20.0)
        adx_neg = latest.get("ADX_NEG", 20.0)
        atr = latest.get("ATR_14", close * 0.02)
        daily_chg = snapshot.get("daily_change_pct", 0.0)

        atr_pct = (atr / close * 100.0) if close > 0 else 2.0
        score = 0.0
        reasons = []

        if adx >= 25.0:
            if adx_pos > adx_neg:
                score += 0.6
                reasons.append(f"Güçlü yükseliş trend rejimi (ADX: {adx:.1f}, +DI > -DI).")
            else:
                score -= 0.6
                reasons.append(f"Güçlü düşüş trend rejimi (ADX: {adx:.1f}, -DI > +DI).")
        else:
            reasons.append(f"Trend gücü zayıf/kararsız (ADX: {adx:.1f} < 25).")

        if atr_pct > 5.0:
            reasons.append(f"Yüksek volatilite rejimi (ATR: %{atr_pct:.1f}).")
        elif atr_pct < 1.5:
            reasons.append(f"Düşük volatilite/sakin rejim (ATR: %{atr_pct:.1f}).")

        if daily_chg > 3.0:
            score += 0.2
            reasons.append(f"Günlük pozitif ivme (%{daily_chg:+.2f}).")
        elif daily_chg < -3.0:
            score -= 0.2
            reasons.append(f"Günlük geri çekilme (%{daily_chg:+.2f}).")

        score = max(-1.0, min(1.0, score))
        action = "AL" if score >= 0.35 else ("SAT" if score <= -0.35 else "TUT")

        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            action=action,
            score=round(score, 3),
            confidence=round(abs(score), 2),
            reason=" ".join(reasons),
            metrics={"ADX": round(adx, 2), "ATR_YUZDE": round(atr_pct, 2)}
        )

class SpeculationAndTrapAgent:
    name = "Spekülasyon & Tuzak Kalkanı"

    def analyze(self, symbol: str, snapshot: Dict) -> AgentSignal:
        latest = snapshot.get("latest", {})
        close = latest.get("Close", 1.0)
        daily_chg = snapshot.get("daily_change_pct", 0.0)
        vol_ratio = latest.get("VOL_RATIO", 1.0)
        upper_wick = latest.get("UPPER_WICK_RATIO", 0.0)
        lower_wick = latest.get("LOWER_WICK_RATIO", 0.0)
        atr = latest.get("ATR_14", close * 0.02)
        atr_pct = (atr / close * 100.0) if close > 0 else 2.0

        score = 0.0
        reasons = []
        is_veto_active = False
        trap_type = "TUZAK_YOK"

        if daily_chg >= 2.0 and vol_ratio < 0.70:
            is_veto_active = True
            trap_type = "BULL_TRAP"
            score = -0.90
            reasons.append(f"⚠️ BOĞA TUZAĞI TESPİT EDİLDİ: Fiyat %{daily_chg:+.2f} yükseliyor fakat hacim 20 günlük ortalamanın çok altında ({vol_ratio:.2f}x). Yapay likidite çekme riski.")

        elif daily_chg >= 12.0 or (atr_pct > 0 and daily_chg > (3.5 * atr_pct)):
            is_veto_active = True
            trap_type = "PUMP_DUMP"
            score = -0.85
            reasons.append(f"⚠️ PUMP & DUMP ANOMALİSİ: Tek günde %{daily_chg:+.2f} olağandışı yükseliş (Normal oynaklığın 3.5 katı). Tepe fiyattan girmemek için alım engellendi.")

        elif upper_wick > 0.55 and daily_chg > 0:
            score = -0.50
            reasons.append(f"⚠️ TEPEDEN REDDEDİLME (Üst Fitil %{upper_wick*100:.0f}): Fiyat yukarı zorlandı ancak balinalar yüksek fiyattan satış yaptı.")

        elif lower_wick > 0.55 and daily_chg > -2.0:
            score = 0.60
            reasons.append(f"🛡️ STOP-HUNT TEMİZLİĞİ (Alt Fitil %{lower_wick*100:.0f}): Balinalar stopları patlatıp dipten güçlü alım yaptı.")

        elif daily_chg > 0.5 and vol_ratio >= 1.35 and upper_wick < 0.35:
            score = 0.70
            reasons.append(f"✅ ORGANİK BALİNA DESTEĞİ: Yükseliş güçlü hacimle ({vol_ratio:.1f}x) ve temiz mum gövdesiyle destekleniyor.")
        else:
            score = 0.0
            reasons.append("Piyasada belirgin bir manipülatif anomali veya tuzak izi görülmedi.")

        score = max(-1.0, min(1.0, score))
        action = "AL" if score >= 0.35 else ("SAT" if score <= -0.35 else "TUT")

        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            action=action,
            score=round(score, 3),
            confidence=round(abs(score), 2),
            reason=" ".join(reasons),
            metrics={
                "is_veto_active": is_veto_active,
                "trap_type": trap_type,
                "VOL_RATIO": round(vol_ratio, 2),
                "UST_FITIL": round(upper_wick, 2),
                "ALT_FITIL": round(lower_wick, 2)
            }
        )

class MasterRiskArbiterAgent:
    name = "Risk & Karar Hakemi"

    def __init__(self):
        self.trend_agent = TrendFollowerAgent()
        self.momentum_agent = MomentumAgent()
        self.volatility_agent = VolatilityBreakoutAgent()
        self.macro_agent = MacroSentimentAgent()
        self.speculation_agent = SpeculationAndTrapAgent()

    def evaluate_symbol(
        self,
        symbol: str,
        snapshot: Dict,
        target_tp_pct: Optional[float] = None,
        target_sl_pct: Optional[float] = None
    ) -> Dict:
        sig_trend = self.trend_agent.analyze(symbol, snapshot)
        sig_mom = self.momentum_agent.analyze(symbol, snapshot)
        sig_vol = self.volatility_agent.analyze(symbol, snapshot)
        sig_macro = self.macro_agent.analyze(symbol, snapshot)
        sig_spec = self.speculation_agent.analyze(symbol, snapshot)

        w_trend, w_mom, w_vol, w_macro, w_spec = 0.25, 0.25, 0.20, 0.15, 0.15
        composite_score = (
            (sig_trend.score * w_trend) +
            (sig_mom.score * w_mom) +
            (sig_vol.score * w_vol) +
            (sig_macro.score * w_macro) +
            (sig_spec.score * w_spec)
        )
        composite_score = round(max(-1.0, min(1.0, composite_score)), 3)

        if composite_score >= MIN_SIGNAL_STRENGTH:
            consensus_action = "AL"
        elif composite_score <= -MIN_SIGNAL_STRENGTH:
            consensus_action = "SAT"
        else:
            consensus_action = "TUT"

        is_vetoed = sig_spec.metrics.get("is_veto_active", False)
        veto_reason = ""
        if is_vetoed and consensus_action == "AL":
            consensus_action = "TUT"
            veto_reason = f" [🚨 SPEKÜLASYON KALKANI TARAFINDAN VETO EDİLDİ: {sig_spec.metrics.get('trap_type')}]"
            composite_score = min(0.0, composite_score - 0.5)

        # Kullanıcı Tanımlı veya Dinamik Kâr-Al & Stop-Loss Hesabı
        latest = snapshot.get("latest", {})
        price_try = snapshot.get("price_try", 1.0)
        price_native = snapshot.get("price_native", 1.0)
        atr = latest.get("ATR_14", price_native * 0.02)

        if target_sl_pct is not None:
            sl_pct = target_sl_pct
        elif atr and atr > 0 and price_native > 0:
            sl_pct = max(0.015, min(0.06, (1.5 * atr) / price_native))
        else:
            sl_pct = DEFAULT_STOP_LOSS_PCT

        if target_tp_pct is not None:
            tp_pct = target_tp_pct
        elif atr and atr > 0 and price_native > 0:
            tp_pct = max(0.03, min(0.15, (3.0 * atr) / price_native))
        else:
            tp_pct = DEFAULT_TAKE_PROFIT_PCT

        stop_loss_price_try = round(price_try * (1.0 - sl_pct), 2)
        take_profit_price_try = round(price_try * (1.0 + tp_pct), 2)

        return {
            "symbol": symbol,
            "category": snapshot.get("category", "DIGER"),
            "price_try": price_try,
            "price_native": price_native,
            "is_try_native": snapshot.get("is_try_native", False),
            "daily_change_pct": snapshot.get("daily_change_pct", 0.0),
            "consensus_action": consensus_action,
            "composite_score": composite_score,
            "confidence_pct": round(abs(composite_score) * 100, 1),
            "is_vetoed": is_vetoed,
            "veto_reason": veto_reason,
            "stop_loss_try": stop_loss_price_try,
            "take_profit_try": take_profit_price_try,
            "stop_loss_pct": round(sl_pct * 100, 2),
            "take_profit_pct": round(tp_pct * 100, 2),
            "signals": {
                "trend": sig_trend,
                "momentum": sig_mom,
                "volatility": sig_vol,
                "macro": sig_macro,
                "speculation": sig_spec
            }
        }
