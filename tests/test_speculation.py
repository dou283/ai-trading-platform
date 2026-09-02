import pytest
from src.agents import SpeculationAndTrapAgent, MasterRiskArbiterAgent

def test_bull_trap_veto_trigger():
    """Hacimsiz yapay yükselişte (Boğa Tuzağı) alımın VETO edildiğini test eder."""
    arbiter = MasterRiskArbiterAgent()
    
    # Trend ve Momentum AL dese bile, hacim yoksa spekülasyon kalkanı devreye girmeli
    bull_trap_snapshot = {
        "symbol": "FAKE_PUMP.IS",
        "category": "BIST",
        "price_try": 100.0,
        "price_native": 100.0,
        "is_try_native": True,
        "daily_change_pct": 4.5,  # %4.5 Yükseliş
        "latest": {
            "Close": 100.0,
            "EMA_9": 98.0,
            "EMA_21": 95.0,
            "EMA_50": 90.0,
            "EMA_200": 80.0,
            "MACD": 2.0,
            "MACD_SIGNAL": 1.0,
            "MACD_DIFF": 1.0,
            "RSI_14": 55.0,
            "BB_HIGH": 102.0,
            "BB_LOW": 88.0,
            "BB_MID": 95.0,
            "BB_WID": 0.1,
            "VOL_RATIO": 0.35,  # Hacim yerlerde (%35) -> BOĞA TUZAĞI!
            "UPPER_WICK_RATIO": 0.1,
            "LOWER_WICK_RATIO": 0.1,
            "ATR_14": 2.0
        },
        "prev": {"Close": 95.5, "RSI_14": 50.0}
    }

    eval_res = arbiter.evaluate_symbol("FAKE_PUMP.IS", bull_trap_snapshot)
    
    # Alım kararı VETO edilerek TUT veya SAT yapılmalı
    assert eval_res["is_vetoed"] is True
    assert eval_res["consensus_action"] in ["TUT", "SAT"]
    assert "BOĞA TUZAĞI" in eval_res["signals"]["speculation"].reason

def test_pump_and_dump_anomaly_veto():
    """Aşırı parabolik yükselişte tepe fiyattan girmemek için vetoyu test eder."""
    agent = SpeculationAndTrapAgent()
    pump_snapshot = {
        "daily_change_pct": 18.0,  # Tek günde %18 artış
        "latest": {
            "Close": 100.0,
            "VOL_RATIO": 2.5,
            "UPPER_WICK_RATIO": 0.2,
            "LOWER_WICK_RATIO": 0.1,
            "ATR_14": 2.0
        }
    }
    sig = agent.analyze("PUMP_COIN", pump_snapshot)
    assert sig.metrics["is_veto_active"] is True
    assert sig.metrics["trap_type"] == "PUMP_DUMP"
    assert sig.score < -0.8

def test_stop_hunt_wick_detection():
    """Balinaların stop patlatıp alttan topladığı fitilli mumu doğru analiz ettiğini test eder."""
    agent = SpeculationAndTrapAgent()
    stop_hunt_snapshot = {
        "daily_change_pct": -0.5,
        "latest": {
            "Close": 100.0,
            "VOL_RATIO": 1.2,
            "UPPER_WICK_RATIO": 0.1,
            "LOWER_WICK_RATIO": 0.65,  # %65 alt fitil -> Stop hunt dip dönüşü
            "ATR_14": 2.5
        }
    }
    sig = agent.analyze("HUNTED_ASSET", stop_hunt_snapshot)
    assert sig.score > 0.5
    assert "STOP-HUNT" in sig.reason

def test_healthy_organic_volume_breakout():
    """Gerçek hacimli sağlıklı alımlarda kalkanın onay verdiğini test eder."""
    agent = SpeculationAndTrapAgent()
    healthy_snapshot = {
        "daily_change_pct": 2.5,
        "latest": {
            "Close": 100.0,
            "VOL_RATIO": 1.8,  # Güçlü hacim (1.8x)
            "UPPER_WICK_RATIO": 0.15,  # Temiz gövde
            "LOWER_WICK_RATIO": 0.1,
            "ATR_14": 2.0
        }
    }
    sig = agent.analyze("HEALTHY_ASSET", healthy_snapshot)
    assert sig.score >= 0.5
    assert sig.metrics["is_veto_active"] is False
    assert "ORGANİK BALİNA DESTEĞİ" in sig.reason
