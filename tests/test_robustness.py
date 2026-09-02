import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from src.agents import (
    TrendFollowerAgent,
    MomentumAgent,
    VolatilityBreakoutAgent,
    MacroSentimentAgent,
    SpeculationAndTrapAgent,
    MasterRiskArbiterAgent
)
from src.portfolio_engine import PortfolioEngine
from src.data_fetcher import calculate_indicators
from src.config import MAX_OPEN_POSITIONS

@pytest.fixture
def clean_engine(tmp_path):
    test_state = tmp_path / "robustness_portfolio.json"
    return PortfolioEngine(state_file=test_state)

def test_missing_data_resilience():
    arbiter = MasterRiskArbiterAgent()
    corrupted_snapshot = {
        "symbol": "CORRUPT.IS",
        "category": "BIST",
        "price_try": 50.0,
        "price_native": 50.0,
        "is_try_native": True,
        "daily_change_pct": 0.0,
        "latest": {},
        "prev": {}
    }
    
    res = arbiter.evaluate_symbol("CORRUPT.IS", corrupted_snapshot)
    assert res["consensus_action"] in ["AL", "SAT", "TUT"]
    assert res["stop_loss_try"] > 0
    assert res["take_profit_try"] > res["price_try"]

def test_macro_sentiment_agent_regimes():
    macro_agent = MacroSentimentAgent()
    
    bull_snapshot = {
        "daily_change_pct": 4.5,
        "latest": {
            "Close": 100.0,
            "ADX_14": 35.0,
            "ADX_POS": 30.0,
            "ADX_NEG": 10.0,
            "ATR_14": 1.5
        }
    }
    sig_bull = macro_agent.analyze("BULL_ASSET", bull_snapshot)
    assert sig_bull.score > 0.35
    assert sig_bull.action == "AL"

    bear_snapshot = {
        "daily_change_pct": -4.0,
        "latest": {
            "Close": 100.0,
            "ADX_14": 38.0,
            "ADX_POS": 8.0,
            "ADX_NEG": 32.0,
            "ATR_14": 6.0
        }
    }
    sig_bear = macro_agent.analyze("BEAR_ASSET", bear_snapshot)
    assert sig_bear.score < -0.35
    assert sig_bear.action == "SAT"

def test_max_position_and_cash_exhaustion(clean_engine):
    """Maksimum pozisyon limitine ulaşıldığında ve nakit bitince yeni alımların engellendiğini doğrular."""
    symbols = [f"SYM_{i}" for i in range(MAX_OPEN_POSITIONS)]
    for sym in symbols:
        ok, msg = clean_engine.buy_position(
            symbol=sym,
            price_try=100.0,
            reason="Test",
            stop_loss_try=95.0,
            take_profit_try=110.0,
            category="TEST",
            confidence=0.8
        )
        assert ok is True

    assert len(clean_engine.positions) == MAX_OPEN_POSITIONS

    # Limit aşımı testi
    ok_extra, msg_extra = clean_engine.buy_position(
        symbol="SYM_EXTRA",
        price_try=100.0,
        reason="Test Extra",
        stop_loss_try=95.0,
        take_profit_try=110.0,
        category="TEST"
    )
    assert ok_extra is False
    assert "Maksimum açık pozisyon limitine" in msg_extra or "Yetersiz nakit" in msg_extra

def test_portfolio_fee_and_pnl_math(clean_engine):
    initial_cash = clean_engine.cash_try
    
    clean_engine.buy_position(
        symbol="MATH_TEST",
        price_try=100.0,
        reason="Matematik Testi",
        stop_loss_try=90.0,
        take_profit_try=120.0,
        confidence=1.0
    )
    
    clean_engine.sell_position("MATH_TEST", price_try=110.0, exit_reason="Kâr Alındı")
    
    assert len(clean_engine.trade_history) == 1
    trade = clean_engine.trade_history[0]
    assert trade["realized_pnl_try"] > 0
    assert trade["return_pct"] > 9.0
    assert clean_engine.cash_try > initial_cash

def test_indicator_calculation_synthetic_df():
    dates = pd.date_range("2026-01-01", periods=60)
    prices = np.linspace(100, 150, 60) + np.random.normal(0, 1, 60)
    df = pd.DataFrame({
        "Open": prices * 0.99,
        "High": prices * 1.02,
        "Low": prices * 0.98,
        "Close": prices,
        "Volume": np.random.randint(1000, 50000, 60)
    }, index=dates)

    calc_df = calculate_indicators(df)
    assert "EMA_9" in calc_df.columns
    assert "RSI_14" in calc_df.columns
    assert "ADX_14" in calc_df.columns
    assert "BB_HIGH" in calc_df.columns
    assert "UPPER_WICK_RATIO" in calc_df.columns
    assert not calc_df["RSI_14"].isna().any()
    assert not calc_df["EMA_50"].isna().any()
