# JARVIS AI Assistant - Quick Start Guide

## Prerequisites

- Windows 10/11 (64-bit)
- Python 3.10 or higher
- 8 GB RAM minimum (16 GB recommended)
- Microphone and speakers
- [Ollama](https://ollama.ai) installed

## 1. Clone and Set Up

```bash
git clone https://github.com/Aman-Amarjit/personal-butler.git
cd personal-butler
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Start Ollama

```bash
ollama pull mistral:7b
ollama serve
```

## 3. Run JARVIS

```bash
python src/main.py
```

## 4. Wake Word

Say **"Hey JARVIS"** to activate. JARVIS will respond with a chime and the slime body will animate.

## 5. Example Commands

| Say this | What happens |
|---|---|
| "Hey JARVIS, what time is it?" | Tells you the current time |
| "Hey JARVIS, open calculator" | Launches Windows Calculator |
| "Hey JARVIS, what's the weather?" | Shows weather widget |
| "Hey JARVIS, system status" | Shows CPU/memory/disk usage |
| "Hey JARVIS, enable privacy mode" | Activates privacy mode |

## 6. Configuration

Edit `config/config.json` to customize:
- `voice.wake_word` — change the wake word
- `ui.slime_color` — change the slime body color (hex)
- `ollama.model_size` — choose `3b`, `7b`, or `13b`

## Troubleshooting

- **No audio detected**: Check microphone permissions in Windows Settings → Privacy → Microphone
- **Ollama not responding**: Ensure `ollama serve` is running in a separate terminal
- **High CPU usage**: Switch to `3b` model in config.json
