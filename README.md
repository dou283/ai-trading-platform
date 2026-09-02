# 🤖 Çoklu-Ajanlı Sanal Borsa & Kripto Portföy Yöneticisi (Paper Trading)

Bu proje, **10.000 TL sanal bütçe** ile Borsa İstanbul (BIST), Kripto Para (BTC, ETH, SOL vb.) ve Global ABD piyasalarını (AAPL, NVDA vb.) gerçek zamanlı piyasa verileriyle izleyen, teknik analiz ve risk yönetimi kurallarına göre otomatik sanal alım-satım yapan **Çoklu-Ajanlı (Multi-Agent)** bir simülasyon sistemidir.

---

## 🏗️ Sistem Mimarisi ve Ajanlar

1. **📈 Trend Ajanı (%35 Ağırlık):**
   - EMA (9, 21, 50, 200) dizilimlerini ve MACD momentumunu inceler.
2. **⚡ Momentum Ajanı (%35 Ağırlık):**
   - RSI (14) aşırı alım (>70) ve aşırı satım (<30) dip/tepe dönüşlerini analiz eder.
3. **💥 Volatilite & Kırılım Ajanı (%30 Ağırlık):**
   - 20 periyotluk Bollinger Bantları ve Hacim patlamalarını (Volume Ratio) takip eder.
4. **🛡️ Risk Yöneticisi ve Hakem Ajanı (Arbiter):**
   - Ajanların puanlarını birleştirip **-1.0 (Güçlü Sat)** ile **+1.0 (Güçlü Al)** arası kompozit karar üretir.
   - Maksimum pozisyon büyüklüğü: Portföyün en fazla **%20'si (2.000 TL)**.
   - Maksimum eşzamanlı pozisyon sayısı: **5 Varlık**.
   - Otomatik **Stop-Loss** (%2.5) ve **Take-Profit** (%5.0) tetikleyicileri.

---

## 🚀 Başlatma ve Çalıştırma

### 1. Sanal Ortamı Aktif Etme
```bash
cd /Users/dogus/.gemini/antigravity/scratch/paper-trading-agents
source .venv/bin/activate
```

### 2. Streamlit Web Dashboard'u Başlatma
```bash
streamlit run app.py
```
Tarayıcınızda otomatik olarak `http://localhost:8501` adresi açılacaktır.

### 3. Komut Satırından Simülasyon Çalıştırma
```bash
PYTHONPATH=. .venv/bin/python -m src.engine
```

### 4. Testleri Çalıştırma
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```
