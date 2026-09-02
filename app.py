import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.auth import register_user, login_user, get_user_by_id, init_db
from src.engine import TradingSimulationEngine
from src.autonomous_bot import get_bot_for_user
from src.news_fetcher import fetch_latest_news
from src.config import DEFAULT_SYMBOLS, AUTONOMOUS_INTERVAL_SECONDS

# Veritabanını başlat
init_db()

st.set_page_config(
    page_title="🤖 AI Yatırım Platformu",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── GLOBAL STİLLER ───────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size:2.1rem; font-weight:800; color:#38bdf8; margin-bottom:2px; }
    .sub-header  { color:#94a3b8; font-size:0.95rem; margin-bottom:20px; }
    .auth-card   {
        background:#1e293b; border-radius:16px; padding:2rem 2.5rem;
        box-shadow: 0 4px 32px #0005; max-width:420px; margin:4rem auto;
    }
    .auth-title  { font-size:1.6rem; font-weight:700; color:#38bdf8; text-align:center; margin-bottom:0.3rem; }
    .auth-sub    { color:#64748b; font-size:0.9rem; text-align:center; margin-bottom:1.5rem; }
    .badge-buy   { background:#10b981; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:.85rem; }
    .badge-sell  { background:#ef4444; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:.85rem; }
    .badge-hold  { background:#64748b; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:.85rem; }
    .badge-veto  { background:#f59e0b; color:black; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:.85rem; }
    .agent-box   { background:#1e293b; border-left:4px solid #38bdf8; padding:8px 12px; margin:4px 0; border-radius:4px; font-size:.88rem; }
    .trap-box    { background:#451a03; border-left:4px solid #f59e0b; padding:10px 14px; margin:6px 0; border-radius:4px; color:#fef3c7; font-size:.9rem; }
    .news-card   { background:#1e222d; border:1px solid #2a2e39; border-radius:8px; padding:12px 16px; margin-bottom:8px; }
    .user-badge  { background:#0f172a; border:1px solid #334155; border-radius:8px; padding:6px 12px; color:#94a3b8; font-size:0.85rem; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
#   SESSION MANAGEMENT
# ══════════════════════════════════════════════════
def _init_session():
    for key, default in [
        ("user_id",      None),
        ("username",     None),
        ("last_report",  None),
        ("symbols_dict", dict(DEFAULT_SYMBOLS)),
        ("auth_tab",     "login"),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

_init_session()


def _is_logged_in() -> bool:
    return st.session_state.user_id is not None


def _logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.last_report = None
    st.session_state.symbols_dict = dict(DEFAULT_SYMBOLS)
    st.rerun()


# ══════════════════════════════════════════════════
#   AUTH SAYFASI  (Login / Register)
# ══════════════════════════════════════════════════
def render_auth_page():
    st.markdown("""
    <div style='text-align:center; padding-top:2rem;'>
        <div style='font-size:3rem;'>🤖</div>
        <div style='font-size:1.8rem; font-weight:800; color:#38bdf8;'>AI Yatırım Platformu</div>
        <div style='color:#64748b; margin-top:4px;'>5 Ajan · Barbell Strateji · 1dk Otopilot</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])

    with col_m:
        tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])

        # ── Giriş ──────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                st.markdown("### Hesabına Giriş Yap")
                username = st.text_input("Kullanıcı Adı", placeholder="kullanici_adi")
                password = st.text_input("Şifre", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("🔑 Giriş Yap", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Lütfen tüm alanları doldurun.")
                else:
                    result = login_user(username, password)
                    if result["success"]:
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.toast(result["message"], icon="✅")
                        st.rerun()
                    else:
                        st.error(result["message"])

        # ── Kayıt ──────────────────────────────────
        with tab_register:
            with st.form("register_form"):
                st.markdown("### Yeni Hesap Oluştur")
                new_username = st.text_input("Kullanıcı Adı", placeholder="en az 3 karakter", key="reg_user")
                new_email    = st.text_input("E-posta (opsiyonel)", placeholder="ornek@mail.com", key="reg_email")
                new_password = st.text_input("Şifre", type="password", placeholder="en az 6 karakter", key="reg_pass")
                new_password2= st.text_input("Şifre Tekrar", type="password", placeholder="şifreyi tekrar girin", key="reg_pass2")
                reg_submitted = st.form_submit_button("📝 Kayıt Ol", use_container_width=True, type="primary")

            if reg_submitted:
                if not new_username or not new_password:
                    st.error("Lütfen kullanıcı adı ve şifre girin.")
                elif new_password != new_password2:
                    st.error("Şifreler eşleşmiyor.")
                else:
                    result = register_user(new_username, new_password, new_email)
                    if result["success"]:
                        st.success(f"✅ {result['message']} Şimdi giriş yapabilirsin.")
                    else:
                        st.error(result["message"])


# ══════════════════════════════════════════════════
#   ANA DASHBOARD  (Giriş Sonrası)
# ══════════════════════════════════════════════════
def render_dashboard():
    user_id  = st.session_state.user_id
    username = st.session_state.username

    # Kullanıcıya özel engine ve bot al
    bot      = get_bot_for_user(user_id)
    engine   = bot.engine
    portfolio = engine.portfolio
    summary  = portfolio.get_portfolio_summary()
    bot_status = bot.get_status()
    settings = portfolio.settings

    # ── SIDEBAR ────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div class="user-badge">👤 <b>{username}</b></div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Çıkış Yap", use_container_width=True):
            _logout()

        st.divider()
        st.markdown("### 💰 Sermaye & Bütçe Yönetimi")

        custom_cap = st.number_input(
            "Başlangıç Sermayesi (TL)",
            min_value=1000.0, max_value=100_000_000.0,
            value=float(portfolio.initial_capital), step=1000.0, format="%.2f"
        )
        if st.button("💵 Sermayeyi Güncelle ve Başlat", use_container_width=True):
            portfolio.reset_portfolio(custom_cap)
            st.toast(f"Sermaye {custom_cap:,.2f} TL olarak güncellendi!", icon="✅")
            st.rerun()

        st.divider()
        st.markdown("### 🎯 Hedef Kâr & Zarar Ayarları")
        tp_val = st.slider("Kâr Al (Take-Profit %)", 2.0, 25.0, float(settings.get("take_profit_pct", 6.0)), 0.5)
        sl_val = st.slider("Zarar Durdur (Stop-Loss %)", 1.0, 10.0, float(settings.get("stop_loss_pct", 3.0)), 0.5)

        if tp_val != settings.get("take_profit_pct") or sl_val != settings.get("stop_loss_pct"):
            settings["take_profit_pct"] = tp_val
            settings["stop_loss_pct"]   = sl_val
            portfolio._save_settings()

        st.divider()
        st.markdown("#### ⏱️ 1 Dakikalık Otopilot")
        is_running = bot_status.get("is_running", False)

        if not is_running:
            if st.button("▶️ Otopilotu Başlat", type="primary", use_container_width=True):
                bot.start()
                st.toast("1 Dakikalık Otopilot Botu Başlatıldı!", icon="🚀")
                st.rerun()
        else:
            st.success(f"🟢 Otopilot Aktif (#{bot_status.get('total_cycles', 0)} Döngü)", icon="⚡")
            st.caption(f"Son Çalışma: {bot_status.get('last_run', 'Yeni')}")
            if st.button("⏹️ Otopilotu Durdur", use_container_width=True):
                bot.stop()
                st.toast("Otopilot Durduruldu.", icon="🛑")
                st.rerun()

        st.divider()
        if st.button("🚀 Manuel Piyasayı Tara", use_container_width=True):
            with st.spinner("5 uzman ajan ve canlı haberler taranıyor..."):
                report = engine.run_cycle(st.session_state.symbols_dict)
                st.session_state.last_report = report
                st.rerun()

        st.divider()
        st.markdown("#### ➕ Yeni Varlık Ekle")
        new_category = st.selectbox("Kategori", ["BIST", "KRIPTO", "KRIPTO_SPEKULATIF", "GLOBAL"])
        new_symbol   = st.text_input("Sembol (Örn: TCELL.IS, PEPE-USD, AMZN)").upper().strip()
        if st.button("Listeye Ekle", use_container_width=True):
            if new_symbol and new_symbol not in st.session_state.symbols_dict.get(new_category, []):
                st.session_state.symbols_dict.setdefault(new_category, []).append(new_symbol)
                st.toast(f"{new_symbol} {new_category} listesine eklendi!", icon="✅")
                st.rerun()

    # ── HEADER ─────────────────────────────────────
    st.markdown('<div class="main-header">⚡ AI Çoklu-Ajanlı Yatırım Platformu</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">👤 <b>{username}</b> · Bütçe: <b>{portfolio.initial_capital:,.2f} TL</b> '
        f'· TP: <b>+%{tp_val:.1f}</b> · SL: <b>-%{sl_val:.1f}</b> · 1 dk Otopilot</div>',
        unsafe_allow_html=True
    )

    # ── KPI METRICS ─────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    total_eq     = summary["total_equity_try"]
    total_pnl    = summary["total_pnl_try"]
    pnl_pct      = summary["total_pnl_pct"]
    cash         = summary["cash_try"]
    positions_val= summary["positions_value_try"]
    win_rate     = summary["win_rate_pct"]

    with col1:
        st.metric("Toplam Portföy Değeri", f"{total_eq:,.2f} TL", f"{total_pnl:+,.2f} TL (%{pnl_pct:+.2f})")
    with col2:
        st.metric("Kullanılabilir Nakit", f"{cash:,.2f} TL", f"%{(cash/total_eq*100):.1f} Boşta" if total_eq > 0 else "0%")
    with col3:
        st.metric("Yatırımdaki Tutar", f"{positions_val:,.2f} TL", f"{summary['open_positions_count']} Aktif Pozisyon")
    with col4:
        st.metric("Kazanma Oranı (Win Rate)", f"%{win_rate:.1f}", f"{summary['winning_trades_count']} Kârlı / {summary['closed_trades_count']} İşlem")
    with col5:
        st.metric("Hedef Kâr / Zarar", f"+%{tp_val:.1f} / -%{sl_val:.1f}", "Dinamik ATR Destekli")

    # Son döngü işlemleri
    if st.session_state.last_report and st.session_state.last_report.get("trades_executed"):
        st.markdown("#### ⚡ Son Döngüde Gerçekleştirilen İşlemler")
        for trade_msg in st.session_state.last_report["trades_executed"]:
            st.info(trade_msg, icon="🔔")

    # ── TABS ───────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Portföy & Performans",
        "🧠 5 Ajan Analizleri",
        "🎯 Al-Sat Kuralları",
        "📰 Canlı Haberler",
        "📜 İşlem Geçmişi"
    ])

    # === TAB 1 ===
    with tab1:
        st.markdown("### 💼 Portföy Durumu")
        col_chart1, col_chart2 = st.columns([3, 2])

        with col_chart1:
            eq_history = portfolio.equity_history
            if len(eq_history) > 1:
                df_eq = pd.DataFrame(eq_history)
                fig_line = px.line(df_eq, x="timestamp", y="total_equity_try",
                                   title="📈 Portföy Değer Gelişimi (TL)",
                                   labels={"timestamp": "Zaman", "total_equity_try": "Portföy (TL)"})
                fig_line.add_hline(y=portfolio.initial_capital, line_dash="dash", line_color="gray",
                                   annotation_text=f"Başlangıç ({portfolio.initial_capital:,.2f} TL)")
                fig_line.update_layout(template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20), height=320)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("💡 Grafik işlem döngüleri koşturuldukça çizilecektir.")

        with col_chart2:
            alloc_data = [{"Varlık": "Nakit (TRY)", "Değer": cash}]
            for sym, pos in portfolio.positions.items():
                alloc_data.append({"Varlık": sym, "Değer": pos["amount"] * pos["current_price_try"]})
            df_alloc = pd.DataFrame(alloc_data)
            fig_pie = px.pie(df_alloc, names="Varlık", values="Değer", title="🍰 Varlık Dağılımı (TL)", hole=0.45)
            fig_pie.update_layout(template="plotly_dark", margin=dict(l=20,r=20,t=40,b=20), height=320)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.markdown("### 🟢 Açık Pozisyonlar")
        if not portfolio.positions:
            st.markdown("*Açık pozisyon yok. Otopilotu başlatın veya manuel tarama yapın.*")
        else:
            pos_list = []
            for sym, pos in portfolio.positions.items():
                curr_val = pos["amount"] * pos["current_price_try"]
                pos_list.append({
                    "Varlık": sym, "Kategori": pos.get("category","DIGER"),
                    "Adet": f"{pos['amount']:.4f}",
                    "Giriş Fiyatı": f"{pos['entry_price_try']:,.2f} TL",
                    "Güncel Fiyat": f"{pos['current_price_try']:,.2f} TL",
                    "Yatırılan": f"{pos['total_cost_try']:,.2f} TL",
                    "Güncel Değer": f"{curr_val:,.2f} TL",
                    "Kâr/Zarar": f"{pos['unrealized_pnl_try']:+,.2f} TL (%{pos['pnl_pct']:+.2f})",
                    "Stop-Loss": f"{pos['stop_loss_try']:,.2f} TL",
                    "Take-Profit": f"{pos['take_profit_try']:,.2f} TL",
                    "Giriş Tarihi": pos["entry_time"],
                    "Gerekçe": pos.get("agent_reason","")
                })
            st.dataframe(pd.DataFrame(pos_list), use_container_width=True, hide_index=True)

            st.markdown("##### 🖐️ Manuel Pozisyon Kapat")
            col_m1, col_m2 = st.columns([3,1])
            with col_m1:
                sym_to_close = st.selectbox("Kapatılacak Pozisyon:", list(portfolio.positions.keys()))
            with col_m2:
                st.write(""); st.write("")
                if st.button("🔴 Seçili Pozisyonu Sat", use_container_width=True):
                    curr_p = portfolio.positions[sym_to_close]["current_price_try"]
                    success, msg = portfolio.sell_position(sym_to_close, curr_p, "Manuel Kullanıcı Satışı")
                    if success:
                        st.toast(msg, icon="✅")
                        st.rerun()

    # === TAB 2 ===
    with tab2:
        st.markdown("### 🧠 5 Uzman Ajanın Piyasa Analizi")
        if not st.session_state.last_report or not st.session_state.last_report.get("evaluations"):
            st.info("🔍 Piyasa analizini görmek için **'Piyasayı Tara'** butonuna basın veya **Otopilotu** başlatın.")
        else:
            evals = st.session_state.last_report["evaluations"]
            cat_filter = st.radio("Filtrele:", ["TÜMÜ","BIST","KRIPTO","KRIPTO_SPEKULATIF","GLOBAL"], horizontal=True)
            filtered_evals = [e for e in evals if cat_filter == "TÜMÜ" or e.get("category") == cat_filter]

            for item in filtered_evals:
                sym    = item["symbol"]
                action = item["consensus_action"]
                score  = item["composite_score"]
                price_try = item["price_try"]
                chg    = item["daily_change_pct"]
                signals= item["signals"]
                is_vetoed = item.get("is_vetoed", False)

                if is_vetoed:
                    badge_class, display_action = "badge-veto", f"🚨 VETO ({action})"
                elif action == "AL":
                    badge_class, display_action = "badge-buy", "AL"
                elif action == "SAT":
                    badge_class, display_action = "badge-sell", "SAT"
                else:
                    badge_class, display_action = "badge-hold", "TUT"

                expander_title = f"**{sym}** ({item.get('category')}) — {price_try:,.2f} TL ({chg:+.2f}%) | Karar: {display_action} (Skor: {score:+.2f})"
                with st.expander(expander_title):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f"**Karar:** <span class='{badge_class}'>{display_action}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Skor:** `{score:+.3f}` / 1.00")
                        st.markdown(f"**Güven:** `%{item['confidence_pct']}`")
                    with c2:
                        st.markdown(f"**Stop-Loss:** `{item['stop_loss_try']:,.2f} TL` (-%{item['stop_loss_pct']})")
                        st.markdown(f"**Take-Profit:** `{item['take_profit_try']:,.2f} TL` (+%{item['take_profit_pct']})")
                    with c3:
                        st.markdown(f"**📈 Trend (%25):** `{signals['trend'].action}` ({signals['trend'].score:+.2f})")
                        st.caption(signals['trend'].reason)
                        st.markdown(f"**⚡ Momentum (%25):** `{signals['momentum'].action}` ({signals['momentum'].score:+.2f})")
                        st.caption(signals['momentum'].reason)
                    with c4:
                        st.markdown(f"**💥 Volatilite (%20):** `{signals['volatility'].action}` ({signals['volatility'].score:+.2f})")
                        st.caption(signals['volatility'].reason)
                        st.markdown(f"**🌐 Makro (%15):** `{signals['macro'].action}` ({signals['macro'].score:+.2f})")
                        st.caption(signals['macro'].reason)

                    spec_sig = signals['speculation']
                    css = 'trap-box' if is_vetoed or spec_sig.score < -0.3 else 'agent-box'
                    icon = '🚨' if is_vetoed else '🛡️'
                    st.markdown(f"<div class='{css}'>{icon} <b>Spekülasyon Kalkanı ({spec_sig.action}):</b> {spec_sig.reason}</div>", unsafe_allow_html=True)

    # === TAB 3 ===
    with tab3:
        st.markdown("### 🎯 Yapay Zeka Ne Zaman Alır, Ne Zaman Satar?")
        st.markdown(f"""
#### 🟢 Alım Koşulları
* 5 Ajanın ağırlıklı skoru **+{settings.get('min_signal', 0.15):.2f} üzerine** çıktığında
* Spekülasyon Kalkanı tuzak veya manipülasyon tespit etmediğinde
* **Barbell Stratejisi:** 4 slot → en iyi fırsat, 1 slot → spekülatif kripto (KRIPTO_SPEKULATIF)
* Seçtiğin sermaye (`{portfolio.initial_capital:,.2f} TL`) 5 eşit parçaya bölünür (5 × {portfolio.initial_capital/5:,.0f} TL)

---

#### 🔴 Satış / Çıkış Koşulları
* **🎯 Take-Profit (+%{tp_val:.1f}):** Fiyat hedef kâra ulaştığında otomatik satış
* **🛑 Stop-Loss (-%{sl_val:.1f}):** Zararda koruma kesimi
* **📉 5 Ajan SAT Kararı:** Tüm ajanlar birlikte SAT sinyali verdiğinde pozisyondan çıkış

---

#### 🚀 Spekülatif Kripto Stratejisi (%20 Kasa)
* Toplam sermayenin **%20'si** (yani {portfolio.initial_capital * 0.2:,.0f} TL) ayrılır
* PEPE, SHIB, FLOKI, WIF, BONK, DOGE gibi hacimli altcoinler izlenir
* Pump & dump anomalisinde Spekülasyon Kalkanı otomatik veto koyar
        """)

    # === TAB 4 ===
    with tab4:
        st.markdown("### 📰 Canlı Finans Haberleri & Duygu Analizi")
        news_data = fetch_latest_news()
        c_n1, c_n2 = st.columns([1,2])
        with c_n1:
            st.metric("Genel Haber Duygusu", f"{news_data['score']:+.2f}",
                      "Pozitif" if news_data['score'] > 0.1 else ("Negatif" if news_data['score'] < -0.1 else "Nötr"))
            st.caption(f"Taranan: {news_data['article_count']} haber")
        with c_n2:
            st.info("💡 Ajanlar her dakika haber başlıklarını tarayarak boğa/ayı eğilimini ve tuzak kelimelerini anında hesaplar.")

        st.markdown("#### 🌐 Son Dakika Başlıkları")
        for article in news_data.get("articles", []):
            tag   = article.get("tag","NÖTR")
            score = article.get("sentiment_score", 0.0)
            tc    = "#10b981" if "POZİTİF" in tag else ("#ef4444" if "NEGATİF" in tag else "#f59e0b")
            st.markdown(f"""
            <div class="news-card">
                <span style="background:{tc};color:white;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:bold;">{tag} ({score:+.2f})</span>
                <span style="color:#64748b;font-size:.8rem;margin-left:8px;">{article.get('date','')}</span>
                <div style="font-weight:600;font-size:.95rem;margin-top:4px;">
                    <a href="{article.get('link','#')}" target="_blank" style="color:#e2e8f0;text-decoration:none;">{article.get('title')}</a>
                </div>
            </div>""", unsafe_allow_html=True)

    # === TAB 5 ===
    with tab5:
        st.markdown("### 📜 Tamamlanan İşlemler Geçmişi")
        trades = portfolio.trade_history
        if not trades:
            st.markdown("*Henüz kapanmış işlem yok.*")
        else:
            display_trades = [{
                "İşlem ID": f"#{t['id']}",
                "Varlık": t["symbol"],
                "Kategori": t.get("category","DIGER"),
                "Giriş": f"{t['entry_price_try']:,.2f} TL",
                "Çıkış": f"{t['exit_price_try']:,.2f} TL",
                "Maliyet": f"{t['cost_try']:,.2f} TL",
                "Net Gelir": f"{t['revenue_try']:,.2f} TL",
                "Kâr/Zarar": f"{t['realized_pnl_try']:+,.2f} TL (%{t['return_pct']:+.2f})",
                "Çıkış Nedeni": t["exit_reason"],
                "Kapanış": t["exit_time"]
            } for t in trades]
            st.dataframe(pd.DataFrame(display_trades), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════
#   ANA YÖNLENDIRME
# ══════════════════════════════════════════════════
if _is_logged_in():
    render_dashboard()
else:
    render_auth_page()
