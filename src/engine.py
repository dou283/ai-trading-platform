import logging
from datetime import datetime
from typing import Dict, List, Optional
from src.data_fetcher import fetch_all_markets, get_usd_try_rate
from src.news_fetcher import fetch_latest_news
from src.agents import MasterRiskArbiterAgent
from src.portfolio_engine import PortfolioEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TradingSimulationEngine:
    """
    5 uzman ajan, canlı haber duygu analizi ve tam sermaye yürütme motoru.
    user_id verildiğinde her kullanıcı için izole portföy kullanır.
    """

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.arbiter = MasterRiskArbiterAgent()
        self.portfolio = PortfolioEngine(user_id=user_id)

    def run_cycle(self, custom_symbols_dict: Optional[Dict[str, list]] = None) -> Dict:
        logger.info("=== 5-Ajanlı + Canlı Haber Korumalı Piyasa Döngüsü Başlatılıyor ===")
        cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trades_executed = []

        # 1. Canlı Haber ve Duygu Analizini Çek
        news_report = fetch_latest_news()
        logger.info(f"Canlı Haberler: {news_report['article_count']} adet, Duygu Puanı: {news_report['score']:+.2f}")

        # 2. Piyasa Verilerini Çek
        market_snapshots = fetch_all_markets(custom_symbols_dict)
        if not market_snapshots:
            logger.warning("Piyasa verisi çekilemedi.")
            return {
                "timestamp": cycle_time,
                "status": "error",
                "message": "Piyasa verilerine ulaşılamadı.",
                "news": news_report,
                "evaluations": [],
                "trades_executed": [],
                "triggered_exits": [],
                "portfolio_summary": self.portfolio.get_portfolio_summary()
            }

        # 3. Fiyat haritası oluştur ve portföyü güncelle
        price_map_try = {sym: snap["price_try"] for sym, snap in market_snapshots.items()}
        self.portfolio.update_market_prices(price_map_try)

        # 4. Otomatik Stop-Loss / Take-Profit Kontrolleri
        triggered_exits = self.portfolio.check_stop_loss_take_profit(price_map_try)
        for exit_item in triggered_exits:
            trades_executed.append(exit_item["msg"])

        # 5. Tüm Varlıkları 5 Ajanla Değerlendir (Haber duygu puanını da ekle)
        evaluations = []
        for symbol, snap in market_snapshots.items():
            # Snap içine güncel haber skorunu da ekle
            snap["news_sentiment_score"] = news_report["score"]
            evaluation = self.arbiter.evaluate_symbol(symbol, snap)
            evaluations.append(evaluation)

        # 6. Açık Pozisyonlar İçin Ajan Satış Sinyali Kontrolü
        for symbol in list(self.portfolio.positions.keys()):
            eval_item = next((e for e in evaluations if e["symbol"] == symbol), None)
            if eval_item and eval_item["consensus_action"] == "SAT":
                curr_price_try = eval_item["price_try"]
                reason = f"📉 5 Ajan Ortak Satışı (Skor: {eval_item['composite_score']:+.2f})"
                success, msg = self.portfolio.sell_position(symbol, curr_price_try, reason)
                if success:
                    trades_executed.append(msg)

        # 7. ⚡ BARBELL STRATEJİSİ:
        #    - SPEKULATIF_RESERVED_SLOTS (2) adet slot → spekülatif kriptolara (her biri ~%10 bütçe)
        #    - Kalan slotlar (4 adet) → en iyi skora göre genel varlıklara
        from src.config import MAX_OPEN_POSITIONS, FULL_CAPITAL_MODE, CATEGORY_LIMITS_PCT, SPEKULATIF_RESERVED_SLOTS

        buy_candidates = [
            e for e in evaluations
            if e["consensus_action"] == "AL" and e["symbol"] not in self.portfolio.positions and not e["is_vetoed"]
        ]
        buy_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        available_slots = max(0, MAX_OPEN_POSITIONS - len(self.portfolio.positions))

        # Mevcut spekülatif pozisyon sayısını say
        current_spek_count = sum(
            1 for pos in self.portfolio.positions.values()
            if pos.get("category", "").upper() == "KRIPTO_SPEKULATIF"
        )
        spek_slots_needed = max(0, SPEKULATIF_RESERVED_SLOTS - current_spek_count)

        spek_candidates     = [c for c in buy_candidates if c.get("category", "").upper() == "KRIPTO_SPEKULATIF"]
        non_spek_candidates = [c for c in buy_candidates if c.get("category", "").upper() != "KRIPTO_SPEKULATIF"]

        candidates_to_buy: list = []

        if available_slots > 0:
            if spek_slots_needed > 0 and len(spek_candidates) >= 1:
                # N slot spekülatif için rezerve et (en fazla kaç sinyal varsa o kadar)
                reserved_spek  = spek_candidates[:spek_slots_needed]
                general_slots  = available_slots - len(reserved_spek)
                general_picks  = non_spek_candidates[:general_slots]
                candidates_to_buy = general_picks + reserved_spek
                logger.info(
                    f"Barbell Strateji: {len(general_picks)} genel + {len(reserved_spek)} spekülatif kripto slot "
                    f"(toplam {available_slots} slot, her spekülatif ~%{100/MAX_OPEN_POSITIONS:.0f} bütçe)."
                )
            else:
                # Spekülatif slotlar zaten dolu ya da sinyal yok → tümü genel
                candidates_to_buy = buy_candidates[:available_slots]
                logger.info(
                    f"Barbell Strateji: Spekülatif slotlar dolu/sinyal yok, {available_slots} genel slot kullanılıyor."
                )


        # Spekülatif ve genel slotlar için bütçe hesapla
        total_eq = self.portfolio.get_total_equity_try()
        spek_limit_try    = total_eq * CATEGORY_LIMITS_PCT.get("KRIPTO_SPEKULATIF", 0.20)
        spek_alloc_each   = round(spek_limit_try / SPEKULATIF_RESERVED_SLOTS, 2)   # Her spek coin için: 20.000/2 = 10.000 TL
        total_spek_alloc  = spek_alloc_each * len(reserved_spek) if 'reserved_spek' in dir() else 0.0
        remaining_cash    = self.portfolio.cash_try - total_spek_alloc
        general_count     = len(general_picks) if 'general_picks' in dir() else len(candidates_to_buy)
        general_alloc_each= round(remaining_cash / general_count, 2) if general_count > 0 else self.portfolio.cash_try

        def _execute_buy(candidate: dict, explicit_alloc: float = None) -> None:
            symbol = candidate["symbol"]
            price_try = candidate["price_try"]
            category = candidate["category"]
            confidence = candidate["confidence_pct"] / 100.0
            sigs = candidate["signals"]
            reasons_summary = (
                f"T:{sigs['trend'].action} | M:{sigs['momentum'].action} | "
                f"V:{sigs['volatility'].action} | R:{sigs['macro'].action} | "
                f"🛡️Kalkan:{sigs['speculation'].action} (Skor: {candidate['composite_score']:+.2f})"
            )
            success, msg = self.portfolio.buy_position(
                symbol=symbol,
                price_try=price_try,
                reason=reasons_summary,
                stop_loss_try=candidate["stop_loss_try"],
                take_profit_try=candidate["take_profit_try"],
                category=category,
                confidence=confidence,
                explicit_alloc_try=explicit_alloc
            )
            if success:
                trades_executed.append(msg)

        # Önce genel adayları, sonra spekülatif adayları çalıştır
        spek_symbols = {c["symbol"] for c in (reserved_spek if 'reserved_spek' in dir() else [])}
        for candidate in candidates_to_buy:
            if candidate["symbol"] in spek_symbols:
                _execute_buy(candidate, explicit_alloc=spek_alloc_each)
            else:
                _execute_buy(candidate, explicit_alloc=general_alloc_each)


        # 8. Nihai Rapor
        summary = self.portfolio.get_portfolio_summary()
        logger.info(f"Döngü Tamamlandı. Toplam Portföy: {summary['total_equity_try']} TL, Açık Pozisyon: {summary['open_positions_count']}")

        return {
            "timestamp": cycle_time,
            "status": "success",
            "news": news_report,
            "evaluations": evaluations,
            "trades_executed": trades_executed,
            "triggered_exits": triggered_exits,
            "portfolio_summary": summary,
            "positions": self.portfolio.positions,
            "trade_history": self.portfolio.trade_history
        }
