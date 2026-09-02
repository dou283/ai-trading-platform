import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from src.config import (
    STATE_FILE,
    SETTINGS_FILE,
    INITIAL_BALANCE_TRY,
    TRANSACTION_FEE_PCT,
    MAX_POSITION_RATIO,
    MAX_OPEN_POSITIONS,
    FULL_CAPITAL_MODE,
    DEFAULT_STOP_LOSS_PCT,
    DEFAULT_TAKE_PROFIT_PCT
)

logger = logging.getLogger(__name__)

def load_settings() -> Dict:
    """Kullanıcının belirlediği dinamik sermaye ve risk ayarlarını yükler."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "initial_balance_try": INITIAL_BALANCE_TRY,
        "take_profit_pct": DEFAULT_TAKE_PROFIT_PCT * 100.0,
        "stop_loss_pct": DEFAULT_STOP_LOSS_PCT * 100.0,
        "full_capital_mode": FULL_CAPITAL_MODE
    }

def save_settings(settings: Dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ayarlar kaydedilirken hata: {e}")

class PortfolioEngine:
    """
    Dinamik Kullanıcı Bütçesi ve Kâr Hedefleri ile Çalışan Portföy Motoru.
    user_id verildiğinde her kullanıcının verisi data/users/{user_id}/ içinde izole tutulur.
    """

    def __init__(self, state_file: Path = None, user_id: str = None):
        # Kullanıcıya özel dizin belirleme
        if user_id:
            from src.auth import get_user_data_dir
            user_dir = get_user_data_dir(user_id)
            self.state_file = user_dir / "portfolio_state.json"
            self._settings_file = user_dir / "settings.json"
        else:
            self.state_file = state_file if state_file is not None else STATE_FILE
            self._settings_file = SETTINGS_FILE

        self.user_id = user_id
        self.settings = self._load_settings()
        self.initial_capital: float = self.settings.get("initial_balance_try", INITIAL_BALANCE_TRY)
        self.cash_try: float = self.initial_capital
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.equity_history: List[Dict] = []
        self.load_state()

    def _load_settings(self) -> Dict:
        """Kullanıcıya özel ayarları yükler."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "initial_balance_try": INITIAL_BALANCE_TRY,
            "take_profit_pct": DEFAULT_TAKE_PROFIT_PCT * 100.0,
            "stop_loss_pct": DEFAULT_STOP_LOSS_PCT * 100.0,
            "full_capital_mode": FULL_CAPITAL_MODE
        }

    def _save_settings(self):
        """Kullanıcıya özel ayarları kaydeder."""
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata: {e}")


    def load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.initial_capital = data.get("initial_capital", self.initial_capital)
                    self.cash_try = data.get("cash_try", self.initial_capital)
                    self.positions = data.get("positions", {})
                    self.trade_history = data.get("trade_history", [])
                    self.equity_history = data.get("equity_history", [])
                    logger.info(f"Portföy durumu yüklendi. Sermaye: {self.initial_capital} TL")
                    return
            except Exception as e:
                logger.error(f"Portföy dosyası okunurken hata: {e}")

        self.reset_portfolio(self.initial_capital)

    def save_state(self):
        try:
            data = {
                "initial_capital": self.initial_capital,
                "cash_try": self.cash_try,
                "positions": self.positions,
                "trade_history": self.trade_history,
                "equity_history": self.equity_history,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Portföy kaydedilirken hata: {e}")

    def reset_portfolio(self, custom_capital: Optional[float] = None):
        if custom_capital is not None and custom_capital > 0:
            self.initial_capital = float(custom_capital)
            self.settings["initial_balance_try"] = self.initial_capital
            self._save_settings()

        self.cash_try = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.equity_history = [{
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_equity_try": self.initial_capital,
            "cash_try": self.initial_capital,
            "positions_value_try": 0.0,
            "total_pnl_try": 0.0,
            "total_pnl_pct": 0.0
        }]
        self.save_state()
        logger.info(f"Portföy güncellendi & sıfırlandı: {self.initial_capital:,.2f} TL")

    def get_positions_value_try(self) -> float:
        total = 0.0
        for pos in self.positions.values():
            total += pos["amount"] * pos["current_price_try"]
        return round(total, 2)

    def get_total_equity_try(self) -> float:
        return round(self.cash_try + self.get_positions_value_try(), 2)

    def get_portfolio_summary(self) -> Dict:
        positions_val = self.get_positions_value_try()
        total_equity = round(self.cash_try + positions_val, 2)
        total_pnl_try = round(total_equity - self.initial_capital, 2)
        total_pnl_pct = round((total_pnl_try / self.initial_capital) * 100.0, 2) if self.initial_capital > 0 else 0.0

        closed_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t.get("realized_pnl_try", 0) > 0)
        win_rate_pct = round((winning_trades / closed_trades * 100.0), 1) if closed_trades > 0 else 0.0

        return {
            "initial_balance_try": self.initial_capital,
            "cash_try": round(self.cash_try, 2),
            "positions_value_try": positions_val,
            "total_equity_try": total_equity,
            "total_pnl_try": total_pnl_try,
            "total_pnl_pct": total_pnl_pct,
            "open_positions_count": len(self.positions),
            "closed_trades_count": closed_trades,
            "winning_trades_count": winning_trades,
            "win_rate_pct": win_rate_pct,
            "full_capital_mode": FULL_CAPITAL_MODE
        }

    def can_open_position(self, symbol: str) -> Tuple[bool, str]:
        if symbol in self.positions:
            return False, f"{symbol} için zaten açık bir pozisyon mevcut."
        
        if len(self.positions) >= MAX_OPEN_POSITIONS:
            return False, f"Maksimum açık pozisyon limitine ({MAX_OPEN_POSITIONS}) ulaşıldı."

        min_required = max(50.0, self.initial_capital * 0.01)
        if self.cash_try < min_required:
            return False, f"Yetersiz nakit bakiye (Kalan: {self.cash_try:.2f} TL)."

        return True, "Onaylandı"

    def buy_position(
        self,
        symbol: str,
        price_try: float,
        reason: str,
        stop_loss_try: float,
        take_profit_try: float,
        category: str = "DIGER",
        confidence: float = 0.5,
        explicit_alloc_try: Optional[float] = None
    ) -> Tuple[bool, str]:
        can_buy, validation_msg = self.can_open_position(symbol)
        if not can_buy:
            return False, validation_msg

        # Kategori bazlı bütçe kalkanı (Barbell Stratejisi)
        from src.config import CATEGORY_LIMITS_PCT
        cat_upper = category.upper()
        
        # Mevcut kategori riskini hesapla
        category_exposure = sum(
            pos["amount"] * pos["current_price_try"] 
            for pos in self.positions.values() 
            if pos.get("category", "").upper() == cat_upper
        )
        
        total_eq = self.get_total_equity_try()
        cat_limit_pct = CATEGORY_LIMITS_PCT.get(cat_upper, 1.0) # Belirtilmediyse %100'üne kadar izin var
        max_cat_value = total_eq * cat_limit_pct
        remaining_cat_allowance = max(0.0, max_cat_value - category_exposure)
        
        if remaining_cat_allowance < (total_eq * 0.01):
            return False, f"{category} kategorisi bütçe limitine (Maks: %{cat_limit_pct*100}) ulaştı."

        if explicit_alloc_try is not None:
            alloc_amount_try = min(self.cash_try, explicit_alloc_try)
        else:
            remaining_slots = max(1, MAX_OPEN_POSITIONS - len(self.positions))
            if FULL_CAPITAL_MODE:
                alloc_amount_try = round(self.cash_try / remaining_slots, 2)
            else:
                total_equity = self.get_total_equity_try()
                alloc_amount_try = min(self.cash_try, total_equity * MAX_POSITION_RATIO)

        # Seçilen tahsisat tutarını kategori limiti ve nakit ile sınırla
        alloc_amount_try = min(self.cash_try, alloc_amount_try, remaining_cat_allowance)
        fee_try = alloc_amount_try * TRANSACTION_FEE_PCT
        net_buy_amount_try = alloc_amount_try - fee_try

        if price_try <= 0 or net_buy_amount_try <= 0:
            return False, "Geçersiz işlem tutarı."

        units = net_buy_amount_try / price_try
        self.cash_try -= alloc_amount_try

        self.positions[symbol] = {
            "symbol": symbol,
            "category": category,
            "amount": units,
            "entry_price_try": price_try,
            "current_price_try": price_try,
            "total_cost_try": round(alloc_amount_try, 2),
            "stop_loss_try": stop_loss_try,
            "take_profit_try": take_profit_try,
            "unrealized_pnl_try": round(-fee_try, 2),
            "pnl_pct": round(-(TRANSACTION_FEE_PCT * 100), 2),
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent_reason": reason
        }

        self.record_equity_snapshot()
        self.save_state()
        logger.info(f"ALIM: {units:.4f} adet {symbol} @ {price_try:.2f} TL alındı (Yatırılan: {alloc_amount_try:.2f} TL). Gerekçe: {reason}")
        return True, f"{symbol} için {alloc_amount_try:.2f} TL tutarında alım yapıldı."

    def sell_position(self, symbol: str, price_try: float, exit_reason: str) -> Tuple[bool, str]:
        if symbol not in self.positions:
            return False, f"{symbol} açık pozisyonlarda bulunamadı."

        pos = self.positions.pop(symbol)
        units = pos["amount"]
        gross_revenue = units * price_try
        fee_try = gross_revenue * TRANSACTION_FEE_PCT
        net_revenue = gross_revenue - fee_try

        cost = pos["total_cost_try"]
        realized_pnl = round(net_revenue - cost, 2)
        return_pct = round((realized_pnl / cost) * 100.0, 2)

        self.cash_try += net_revenue

        trade_record = {
            "id": len(self.trade_history) + 1,
            "symbol": symbol,
            "category": pos.get("category", "DIGER"),
            "entry_time": pos["entry_time"],
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price_try": round(pos["entry_price_try"], 2),
            "exit_price_try": round(price_try, 2),
            "amount": units,
            "cost_try": cost,
            "revenue_try": round(net_revenue, 2),
            "realized_pnl_try": realized_pnl,
            "return_pct": return_pct,
            "exit_reason": exit_reason,
            "agent_reason": pos.get("agent_reason", "")
        }

        self.trade_history.insert(0, trade_record)
        self.record_equity_snapshot()
        self.save_state()

        logger.info(f"SATIŞ: {symbol} @ {price_try:.2f} TL satıldı. Kâr/Zarar: {realized_pnl:+.2f} TL (%{return_pct:+.2f}). Sebep: {exit_reason}")
        return True, f"{symbol} satıldı ({exit_reason}). Kâr/Zarar: {realized_pnl:+.2f} TL (%{return_pct:+.2f})"

    def update_market_prices(self, price_map_try: Dict[str, float]):
        for symbol, pos in self.positions.items():
            if symbol in price_map_try:
                curr_price = price_map_try[symbol]
                pos["current_price_try"] = curr_price
                current_val = pos["amount"] * curr_price
                cost = pos["total_cost_try"]
                pnl = current_val - cost
                pos["unrealized_pnl_try"] = round(pnl, 2)
                pos["pnl_pct"] = round((pnl / cost) * 100.0, 2)

        self.record_equity_snapshot()
        self.save_state()

    def check_stop_loss_take_profit(self, price_map_try: Dict[str, float]) -> List[Dict]:
        triggered_actions = []
        symbols_to_check = list(self.positions.keys())

        for symbol in symbols_to_check:
            if symbol not in price_map_try:
                continue

            pos = self.positions[symbol]
            current_price = price_map_try[symbol]
            stop_loss = pos.get("stop_loss_try", 0)
            take_profit = pos.get("take_profit_try", float("inf"))

            if current_price <= stop_loss:
                reason = f"🛑 Stop-Loss Tetiklendi ({current_price:.2f} TL <= {stop_loss:.2f} TL)"
                success, msg = self.sell_position(symbol, current_price, reason)
                if success:
                    triggered_actions.append({"symbol": symbol, "type": "STOP_LOSS", "msg": msg})

            elif current_price >= take_profit:
                reason = f"🎯 Kâr Al (Take-Profit) Tetiklendi ({current_price:.2f} TL >= {take_profit:.2f} TL)"
                success, msg = self.sell_position(symbol, current_price, reason)
                if success:
                    triggered_actions.append({"symbol": symbol, "type": "TAKE_PROFIT", "msg": msg})

        return triggered_actions

    def record_equity_snapshot(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        positions_val = self.get_positions_value_try()
        total_equity = round(self.cash_try + positions_val, 2)
        total_pnl_try = round(total_equity - self.initial_capital, 2)
        total_pnl_pct = round((total_pnl_try / self.initial_capital) * 100.0, 2) if self.initial_capital > 0 else 0.0

        if self.equity_history and self.equity_history[-1]["timestamp"] == now_str:
            self.equity_history[-1] = {
                "timestamp": now_str,
                "total_equity_try": total_equity,
                "cash_try": round(self.cash_try, 2),
                "positions_value_try": positions_val,
                "total_pnl_try": total_pnl_try,
                "total_pnl_pct": total_pnl_pct
            }
        else:
            self.equity_history.append({
                "timestamp": now_str,
                "total_equity_try": total_equity,
                "cash_try": round(self.cash_try, 2),
                "positions_value_try": positions_val,
                "total_pnl_try": total_pnl_try,
                "total_pnl_pct": total_pnl_pct
            })
            if len(self.equity_history) > 500:
                self.equity_history = self.equity_history[-500:]
