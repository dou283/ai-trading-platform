import pytest
from src.portfolio_engine import PortfolioEngine
from src.news_fetcher import score_headline, fetch_latest_news
from src.autonomous_bot import AutonomousTradingBot

def test_full_capital_deployment(tmp_path):
    """Tam sermaye modunda 10.000 TL'nin boşta kalmadan yatırıldığını doğrular."""
    test_state = tmp_path / "full_cap_state.json"
    engine = PortfolioEngine(state_file=test_state)

    # 1. Alım (3 slottan biri: 10.000 / 3 = 3.333 TL)
    ok1, msg1 = engine.buy_position(
        symbol="BTC-USD",
        price_try=3000000.0,
        reason="1. Güçlü Fırsat",
        stop_loss_try=2900000.0,
        take_profit_try=3200000.0,
        confidence=0.9
    )
    assert ok1 is True
    assert engine.positions["BTC-USD"]["total_cost_try"] > 3000.0

    # 2. Alım (Kalan 6.666 TL'nin 2 slota bölünmesi: ~3.333 TL)
    ok2, msg2 = engine.buy_position(
        symbol="ETH-USD",
        price_try=150000.0,
        reason="2. Güçlü Fırsat",
        stop_loss_try=140000.0,
        take_profit_try=165000.0,
        confidence=0.85
    )
    assert ok2 is True

    # 3. Alım (Kalan tüm nakdin yatırılması)
    ok3, msg3 = engine.buy_position(
        symbol="THYAO.IS",
        price_try=300.0,
        reason="3. Güçlü Fırsat",
        stop_loss_try=290.0,
        take_profit_try=325.0,
        confidence=0.8
    )
    assert ok3 is True
    # Kullanılabilir nakit sıfıra yakın olmalı (tüm para yatırıldı)
    assert engine.cash_try < 100.0
    assert engine.get_positions_value_try() > 9900.0

def test_news_sentiment_scoring():
    """Haber başlıklarının duygu ve spekülasyon puanlamasını test eder."""
    pos_score, pos_tag = score_headline("Bitcoin Surges Past New All-Time Record High with Massive Rally")
    assert pos_score > 0.3
    assert "POZİTİF" in pos_tag

    neg_score, neg_tag = score_headline("Crypto Market Plunges Amid Heavy Selloff and Crash Worries")
    assert neg_score < -0.3
    assert "NEGATİF" in neg_tag

    trap_score, trap_tag = score_headline("Guaranteed 100x Pump and Get Rich Quick Scheme")
    assert trap_score < -0.5
    assert "SPEKÜLATİF" in trap_tag

def test_autonomous_bot_state():
    """Otopilot botunun durum yönetimini test eder."""
    bot = AutonomousTradingBot()
    status = bot.get_status()
    assert "is_running" in status
    assert status["interval_seconds"] == 60
