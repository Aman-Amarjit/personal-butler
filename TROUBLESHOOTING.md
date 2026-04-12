# JARVIS AI Assistant - Troubleshooting Guide

## Audio Issues

### Wake word not detected
- Check microphone is set as default recording device in Windows Sound settings
- Ensure microphone permissions are granted: Settings → Privacy → Microphone
- Try increasing `voice.wake_word_confidence` threshold in config.json (lower = more sensitive)
- Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list audio devices

### No speech output (TTS silent)
- Check speaker/headphone is set as default playback device
- Verify pyttsx3 is installed: `pip install pyttsx3`
- Try a different voice: set `voice.tts_voice` in config.json

### High microphone CPU usage
- Reduce audio sample rate in `src/voice/wake_word_detector.py`
- Switch to a smaller wake word model

## Ollama Issues

### "Ollama unavailable" error
- Ensure Ollama is running: open a terminal and run `ollama serve`
- Check the port: default is 11434, verify in config.json
- Test connectivity: `curl http://localhost:11434/api/tags`

### Slow responses
- Switch to a smaller model: set `ollama.model_size` to `3b` in config.json
- Ensure no other GPU-intensive applications are running
- Check available RAM: 7B model requires ~8 GB RAM

### Model not found
- Pull the model: `ollama pull mistral:7b`
- List available models: `ollama list`

## UI Issues

### Overlay not visible
- Check if another window is covering it (overlay is always-on-top)
- Verify PyQt6 is installed: `pip install PyQt6`
- Try running with administrator privileges

### Slime body not animating
- Ensure OpenGL drivers are up to date
- Check GPU drivers in Device Manager
- Try disabling hardware acceleration in config.json

### Wrong monitor
- Set `ui.monitor_id` in config.json (0 = primary, 1 = secondary, etc.)

## Security Issues

### Audit log integrity check fails
- Do not manually edit the SQLite database
- If the database is corrupted, delete `data/jarvis.db` and restart (logs will be reset)

### Encryption key error
- If you changed your password, old encrypted data cannot be decrypted
- Delete `data/` directory to reset all encrypted storage

### Windows Defender events not detected
- Run JARVIS as Administrator for Event Log access
- Verify Windows Defender is enabled and running

## Performance Issues

### High CPU in standby
- Reduce animation FPS: set `ui.animation_fps` to 30 in config.json
- Disable weather widget if not needed
- Check for background processes consuming CPU

### Memory growing over time
- Restart JARVIS to clear caches
- Reduce `performance.cache_size_mb` in config.json
- Check for memory leaks with `python -m tracemalloc`

## Common Error Messages

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: PyQt6` | PyQt6 not installed | `pip install PyQt6` |
| `OSError: [Errno -9996]` | No audio device | Connect microphone |
| `ConnectionRefusedError` | Ollama not running | Run `ollama serve` |
| `PermissionError: audit_log` | No write access to data/ | Run as admin or fix permissions |
| `CircuitBreakerError` | Recursion limit hit | Restart JARVIS |
