# AITrend

A lightweight daily AI trend tracker that:
- scans popular AI/news sources,
- monitors internet discourse around visionary AI leaders,
- generates an inference-based Markdown report each day.

## What it does

`aitrend_reporter.py` collects RSS headlines from:
- AI organizations and publications (OpenAI, DeepMind, Anthropic, NVIDIA, MIT Tech Review, VentureBeat AI)
- person-centric signals via Google News RSS (Sam Altman, Demis Hassabis, Jensen Huang, Yann LeCun, Andrew Ng)

Then it:
1. Filters items from the last N days (default: 1 day)
2. Scores trend themes (Agents, Model Releases, Enterprise, Hardware, Safety, etc.)
3. Produces a concise inference summary
4. Saves a full report under `reports/`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate report now

```bash
python3 aitrend_reporter.py --output-dir reports --days-back 1
```

## Run daily (cron)

Edit crontab:

```bash
crontab -e
```

Add this line (runs every day at 08:00 UTC):

```cron
0 8 * * * /bin/bash /workspace/AITrend/run_daily.sh >> /workspace/AITrend/reports/cron.log 2>&1
```

## Health check

```bash
python3 aitrend_reporter.py --healthcheck
```

