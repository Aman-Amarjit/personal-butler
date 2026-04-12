# JARVIS AI Assistant - Installation Guide

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 64-bit | Windows 11 64-bit |
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 |
| RAM | 8 GB | 16 GB |
| GPU | Any (CPU fallback) | NVIDIA with 6 GB VRAM |
| Storage | 10 GB free | 20 GB free |
| Python | 3.10 | 3.11+ |
| Microphone | Required | USB/headset recommended |

## Step 1: Install Python

1. Download Python 3.10+ from https://python.org/downloads
2. During installation, check **"Add Python to PATH"**
3. Verify: open Command Prompt and run `python --version`

## Step 2: Install Ollama

1. Download from https://ollama.ai
2. Run the installer
3. Open Command Prompt and run:
   ```
   ollama pull mistral:7b
   ```
   This downloads the 7B language model (~4 GB).

## Step 3: Install JARVIS

```bash
git clone https://github.com/Aman-Amarjit/personal-butler.git
cd personal-butler
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4: Configure

Copy the example config if needed:
```bash
copy config\config.json config\local.json
```

Edit `config/local.json` to set your preferences (this file is gitignored).

## Step 5: First Run

1. Start Ollama in a separate terminal:
   ```
   ollama serve
   ```

2. Start JARVIS:
   ```
   venv\Scripts\activate
   python src/main.py
   ```

3. Say **"Hey JARVIS"** to test the wake word.

## Optional: Run as Windows Service

To start JARVIS automatically at login, create a scheduled task:

1. Open Task Scheduler
2. Create Basic Task → "JARVIS AI Assistant"
3. Trigger: "When I log on"
4. Action: Start a program
   - Program: `C:\path\to\personal-butler\venv\Scripts\python.exe`
   - Arguments: `src/main.py`
   - Start in: `C:\path\to\personal-butler`

## Updating

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## Uninstalling

1. Delete the `personal-butler` directory
2. Remove the scheduled task (if created)
3. Optionally uninstall Ollama from Windows Settings → Apps
