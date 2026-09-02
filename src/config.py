import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "portfolio_state.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
AUTONOMOUS_STATE_FILE = DATA_DIR / "autonomous_state.json"

# Initial Portfolio Configuration
INITIAL_BALANCE_TRY = 10000.0  # 10.000 TL Sanal Başlangıç Sermayesi
TRANSACTION_FEE_PCT = 0.001    # %0.1 Komisyon / Kayma Payı

# Risk & Capital Allocation Rules
FULL_CAPITAL_MODE = True       # Tam Sermaye Kullanımı: Boşta nakit bırakmadan tüm parayı yatır
MAX_POSITION_RATIO = 0.50      # Tek bir varlığa portföyün %50'sine kadar (veya boşta kalan tüm paraya) izin ver
MAX_OPEN_POSITIONS = 6         # 4 genel + 2 spekülatif kripto = toplam 6 pozisyon
DEFAULT_STOP_LOSS_PCT = 0.030  # %3.0 Zarar Durdur (Stop-Loss)
DEFAULT_TAKE_PROFIT_PCT = 0.060# %6.0 Kâr Al (Take-Profit)
MIN_SIGNAL_STRENGTH = 0.15     # İşlem açmak için asgari mutabakat puanı (Agresif Mod)

# Kategori Bazlı Bütçe Sınırları (Barbell Stratejisi)
CATEGORY_LIMITS_PCT = {
    "KRIPTO_SPEKULATIF": 0.20  # Spekülatif kriptolara toplam portföyün en fazla %20'si ayrılabilir
}

# Spekülatif kripto için ayrılan sabit slot sayısı (bölünmüş risk)
# Toplam 6 slot içinden 2'si spekülatif kriptoya ayrılır → 10.000 TL × 2 coin
SPEKULATIF_RESERVED_SLOTS = 2

# Autonomous 1-Minute Bot Configuration
AUTONOMOUS_INTERVAL_SECONDS = 60  # Her 60 saniyede (1 dakika) bir otomatik tarama & işlem

# Default Watched Assets
DEFAULT_SYMBOLS = {
    "BIST": [
        "THYAO.IS",
        "ASELS.IS",
        "EREGL.IS",
        "BIMAS.IS",
        "KCHOL.IS",
        "AKBNK.IS",
        "TUPRS.IS",
        "FROTO.IS",
        "SAHOL.IS",
        "SISE.IS",
        "GARAN.IS",
        "PGSUS.IS"
    ],
    "KRIPTO": [
        "BTC-USD",
        "ETH-USD",
        "SOL-USD",
        "AVAX-USD",
        "XRP-USD",
        "BNB-USD"
    ],
    "KRIPTO_SPEKULATIF": [
        "PEPE-USD",
        "SHIB-USD",
        "FLOKI-USD",
        "WIF-USD",
        "BONK-USD",
        "DOGE-USD"
    ],
    "GLOBAL": [
        "AAPL",
        "NVDA",
        "TSLA",
        "MSFT",
        "AMZN",
        "GOOGL"
    ]
}

USD_TRY_SYMBOL = "TRY=X"
