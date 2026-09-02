import pytest
from pathlib import Path
from src.portfolio_engine import PortfolioEngine
from src.agents import TrendFollowerAgent, MomentumAgent, VolatilityBreakoutAgent, MasterRiskArbiterAgent
from src.config import MAX_OPEN_POSITIONS, INITIAL_BALANCE_TRY

@pytest.fixture
def temp_portfolio(tmp_path):
    state_file = tmp_path / "test_portfolio.json"
    engine = PortfolioEngine(state_file=state_file)
    return engine

def test_initial_portfolio_balance(temp_portfolio):
    summary = temp_portfolio.get_portfolio_summary()
    assert summary["cash_try"] == INITIAL_BALANCE_TRY
    assert summary["total_equity_try"] == INITIAL_BALANCE_TRY
    assert summary["open_positions_count"] == 0
    assert summary["total_pnl_try"] == 0.0

def test_buy_position_respects_limits(temp_portfolio):
    success, msg = temp_portfolio.buy_position(
        symbol="THYAO.IS",
        price_try=300.0,
        reason="Test Alımı",
        stop_loss_try=290.0,
        take_profit_try=320.0,
        category="BIST",
        confidence=0.8
    )
    assert success is True
    assert "THYAO.IS" in temp_portfolio.positions
    pos = temp_portfolio.positions["THYAO.IS"]
    assert pos["total_cost_try"] > 0
    assert temp_portfolio.cash_try < INITIAL_BALANCE_TRY

def test_stop_loss_trigger(temp_portfolio):
    temp_portfolio.buy_position(
        symbol="ASELS.IS",
        price_try=100.0,
        reason="Test Alımı",
        stop_loss_try=95.0,
        take_profit_try=110.0,
        category="BIST",
        confidence=0.8
    )
    assert "ASELS.IS" in temp_portfolio.positions

    # Price drops below stop loss (94.0 < 95.0)
    price_map = {"ASELS.IS": 94.0}
    triggers = temp_portfolio.check_stop_loss_take_profit(price_map)

    assert len(triggers) == 1
    assert triggers[0]["type"] == "STOP_LOSS"
    assert "ASELS.IS" not in temp_portfolio.positions
    assert len(temp_portfolio.trade_history) == 1
    assert temp_portfolio.trade_history[0]["realized_pnl_try"] < 0

def test_take_profit_trigger(temp_portfolio):
    temp_portfolio.buy_position(
        symbol="BTC-USD",
        price_try=3000000.0,
        reason="Test Alımı",
        stop_loss_try=2900000.0,
        take_profit_try=3200000.0,
        category="KRIPTO",
        confidence=0.9
    )
    assert "BTC-USD" in temp_portfolio.positions

    # Price goes above take profit
    price_map = {"BTC-USD": 3250000.0}
    triggers = temp_portfolio.check_stop_loss_take_profit(price_map)

    assert len(triggers) == 1
    assert triggers[0]["type"] == "TAKE_PROFIT"
    assert "BTC-USD" not in temp_portfolio.positions
    assert len(temp_portfolio.trade_history) == 1
    assert temp_portfolio.trade_history[0]["realized_pnl_try"] > 0

def test_agent_evaluations():
    arbiter = MasterRiskArbiterAgent()
    dummy_snapshot = {
        "symbol": "TEST.IS",
        "category": "BIST",
        "price_try": 100.0,
        "price_native": 100.0,
        "is_try_native": True,
        "daily_change_pct": 2.5,
        "latest": {
            "Close": 100.0,
            "EMA_9": 98.0,
            "EMA_21": 95.0,
            "EMA_50": 90.0,
            "EMA_200": 80.0,
            "MACD": 1.5,
            "MACD_SIGNAL": 0.8,
            "MACD_DIFF": 0.7,
            "RSI_14": 28.0,
            "BB_HIGH": 105.0,
            "BB_LOW": 85.0,
            "BB_MID": 95.0,
            "BB_WID": 0.2,
            "VOL_RATIO": 1.5,
            "UPPER_WICK_RATIO": 0.1,
            "LOWER_WICK_RATIO": 0.1,
            "ATR_14": 2.5
        },
        "prev": {
            "Close": 97.5,
            "RSI_14": 25.0
        }
    }

    eval_result = arbiter.evaluate_symbol("TEST.IS", dummy_snapshot)
    assert eval_result["consensus_action"] == "AL"
    assert eval_result["composite_score"] > 0.35
    assert eval_result["stop_loss_try"] < 100.0
    assert eval_result["take_profit_try"] > 100.0
