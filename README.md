# Galactic Media Group — YouTube Acquisition Tools

A Streamlit web app that bundles:
- Channel Valuation Calculator
- Transcript Processor

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.headless true
```

Open the local URL that Streamlit prints in your terminal.

## App features

### Channel Valuation Calculator
- Inputs: monthly revenue, monthly views, subscribers, channel age, niche
- Output: valuation range, revenue multiple, and key factor explanations

### Transcript Processor
- Input: transcript upload (.txt or .md)
- Output: meeting date, participants, summary, decisions, and action items

## Deployment notes

- Works on Streamlit Community Cloud, Render, and most Docker platforms.
- Set the entry command to:

```bash
streamlit run app.py --server.headless true
```

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Exclusions

`channel_lookup.py` is intentionally not wired into the UI yet because it requires API key setup.
