# Trading Journal — ICT/SMC

Flask-based trading journal with AI analysis, stats, and PDF export.

## Features
- Trade log karo — entry, SL, TP, P&L, setup, emotion
- AI Analysis (Anthropic API) — Hinglish mein feedback
- Chart screenshot attach karo
- Stats — win rate, avg RR, setup performance, emotion tracker, session stats
- PDF export
- SQLite database — data kabhi lose nahi hoga

## Setup (Docker — Recommended)

```bash
# 1. Is folder mein aao
cd trading_journal

# 2. Docker image build karo
docker build -t trading-journal .

# 3. Run karo
docker run -d -p 5001:5001 -v trading_journal_data:/app/instance --name trading-journal trading-journal

# 4. Browser mein kholo
# http://localhost:5001
```

## Setup (Without Docker)

```bash
# 1. Install karo
pip install -r requirements.txt

# 2. Run karo
python app.py

# 3. Browser mein kholo
# http://localhost:5001
```

## AI Analysis Setup
1. https://console.anthropic.com pe jao
2. API key lo (sk-ant-...)
3. Journal mein API key field mein daalo — browser mein save ho jaayega

## Data Backup
Database file: `instance/journal.db`
Is file ko copy karke backup le sakte ho.
