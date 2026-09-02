#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

mkdir -p logs

# Stop existing processes if any
./stop_daemon.sh > /dev/null 2>&1

echo "🚀 Çoklu-Ajanlı Borsa & Kripto Otopilotu Arka Planda Başlatılıyor..."

# Start Streamlit Dashboard in Background
nohup "$DIR/.venv/bin/streamlit" run app.py --server.port 8501 --server.headless true > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > logs/streamlit.pid

echo "✅ Web Paneli Arka Planda Çalışıyor (PID: $STREAMLIT_PID)"
echo "📍 Adres: http://localhost:8501"
echo "📄 Loglar: $DIR/logs/streamlit.log"
