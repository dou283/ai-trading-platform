#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🛑 Servisler Durduruluyor..."

# Kill Streamlit process
if [ -f logs/streamlit.pid ]; then
    PID=$(cat logs/streamlit.pid)
    kill -9 $PID > /dev/null 2>&1
    rm -f logs/streamlit.pid
fi

# Kill any lingering streamlit on 8501
pkill -f "streamlit run app.py" > /dev/null 2>&1

echo "✅ Tüm servisler güvenle durduruldu."
