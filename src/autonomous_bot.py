import time
import threading
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from src.engine import TradingSimulationEngine

try:
    from src.config import AUTONOMOUS_INTERVAL_SECONDS
except ImportError:
    AUTONOMOUS_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)

# Kullanıcı başına bot instance havuzu: { user_id -> AutonomousTradingBot }
_user_bots: Dict[str, "AutonomousTradingBot"] = {}
_bots_lock = threading.Lock()


def get_bot_for_user(user_id: str) -> "AutonomousTradingBot":
    """Her kullanıcı için izole bir bot instance döner (varsa mevcut olanı, yoksa yeni oluşturur)."""
    with _bots_lock:
        if user_id not in _user_bots:
            _user_bots[user_id] = AutonomousTradingBot(user_id=user_id)
        return _user_bots[user_id]


class AutonomousTradingBot:
    """
    1 Dakikalık Kesintisiz Otopilot Botu:
    Her 60 saniyede bir piyasa verilerini ve haberleri tarayarak otonom al-sat yapar.
    Her kullanıcı için ayrı bir instance oluşturulur — portföyler tamamen izoledir.
    """

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.engine = TradingSimulationEngine(user_id=user_id)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Durum dosyası kullanıcıya özel
        if user_id:
            from src.auth import get_user_data_dir
            self._state_file = get_user_data_dir(user_id) / "autonomous_state.json"
        else:
            DATA_DIR = Path(__file__).resolve().parent.parent / "data"
            self._state_file = DATA_DIR / "autonomous_state.json"

    def get_status(self) -> Dict:
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Thread gerçekten çalışıyor mu kontrol et
                data["is_running"] = bool(self._thread and self._thread.is_alive())
                return data
            except Exception:
                pass

        return {
            "is_running": False,
            "interval_seconds": AUTONOMOUS_INTERVAL_SECONDS,
            "last_run": None,
            "total_cycles": 0,
            "last_log": "Otopilot henüz başlatılmadı."
        }

    def _save_status(self, is_running: bool, last_log: str, total_cycles: int):
        status = {
            "is_running": is_running,
            "interval_seconds": AUTONOMOUS_INTERVAL_SECONDS,
            "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_cycles": total_cycles,
            "last_log": last_log
        }
        try:
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Otopilot durum kaydı hatası: {e}")

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.info(f"[{self.user_id}] Otopilot zaten çalışıyor.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"[{self.user_id}] 1 Dakikalık Otopilot Botu Başlatıldı.")

    def stop(self):
        self._stop_event.set()
        self._save_status(is_running=False, last_log="Otopilot kullanıcı tarafından durduruldu.", total_cycles=0)
        logger.info(f"[{self.user_id}] Otopilot botu durduruldu.")

    def _run_loop(self):
        total_cycles = 0
        while not self._stop_event.is_set():
            total_cycles += 1
            start_time = time.time()
            now_str = datetime.now().strftime("%H:%M:%S")

            try:
                report = self.engine.run_cycle()
                trades = report.get("trades_executed", [])
                log_msg = f"[{now_str}] Döngü #{total_cycles} Tamamlandı. {len(trades)} işlem yapıldı."
                self._save_status(is_running=True, last_log=log_msg, total_cycles=total_cycles)
            except Exception as e:
                err_msg = f"[{now_str}] Döngü #{total_cycles} hatası: {e}"
                logger.error(err_msg)
                self._save_status(is_running=True, last_log=err_msg, total_cycles=total_cycles)

            elapsed = time.time() - start_time
            sleep_time = max(1.0, AUTONOMOUS_INTERVAL_SECONDS - elapsed)
            self._stop_event.wait(timeout=sleep_time)
