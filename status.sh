#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== 🤖 Sistem ve Otopilot Durumu ==="
if pgrep -f "streamlit run app.py" > /dev/null; then
    echo "🟢 Web Paneli: ÇALIŞIYOR (http://localhost:8501)"
else
    echo "🔴 Web Paneli: KAPALI"
fi

if [ -f data/autonomous_state.json ]; then
    echo "📊 Otopilot Durum Dosyası:"
    cat data/autonomous_state.json
fi
