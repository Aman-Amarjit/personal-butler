# JARVIS AI Assistant - Developer Documentation

## Architecture Overview

```
jarvis-ai-assistant/
├── src/
│   ├── core/           # Command processing, Ollama, config, logging, DB
│   ├── voice/          # Wake word, STT, TTS
│   ├── ui/             # Overlay, slime body, visual indicators
│   ├── security/       # Encryption, audit logging, capability gate, circuit breaker, Defender
│   └── emotion/        # Phase 2-4 research: OCC, PAD, EPITOME, metacognition
├── tests/              # Unit and integration tests
├── config/             # JSON configuration files
└── data/               # SQLite databases, cached audio
```

## Key Components

### Core Pipeline

```
WakeWordDetector → SpeechToTextEngine → CommandInterpreter
    → CommandExecutor → ResponseGenerator → TextToSpeechEngine
```

### Security Stack

```
CapabilityGate (trust tiers 0-3)
    → AuditLogger (HMAC-SHA256 signed SQLite)
    → EncryptionManager (AES-256 / PBKDF2)
    → CircuitBreaker (max depth 10, max iterations 100)
    → EventLogMonitor (Windows Defender events)
```

### UI Stack

```
DesktopOverlay (PyQt6 + OpenGL)
    → SlimeBody (32-segment physics)
    → VisualIndicators (camera, processing, alert, privacy)
    → InformationDisplay (weather, calendar, system, time)
```

## API Reference

### CommandInterpreter

```python
interpreter = CommandInterpreter()
result = interpreter.interpret("open calculator")
# result = {"intent": "app_launch", "entities": {"app": "calculator"}, ...}
```

### EncryptionManager

```python
em = EncryptionManager(password="your-password")
encrypted = em.encrypt("sensitive data")
decrypted = em.decrypt(encrypted)
```

### EmotionSynthesizer (Phase 2, opt-in)

```python
synth = EmotionSynthesizer()
synth.enable()  # explicit opt-in required
result = synth.appraise(desirability=0.8, likelihood=0.9, expectedness=0.5)
```

### EPITOMEFramework (Phase 4, opt-in)

```python
framework = EPITOMEFramework()
framework.enable()
response, context = framework.process("I'm worried", EmotionCategory.FEAR)
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_security_components.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Configuration Profiles

| File | Purpose |
|---|---|
| `config/config.json` | Base configuration |
| `config/config.production.json` | Production overrides |
| `config/local.json` | Local developer overrides (gitignored) |

Set `JARVIS_ENV=production` environment variable to use production profile.

## Adding a New Command

1. Add intent pattern in `src/core/command_interpreter.py`
2. Add handler in `src/core/command_executor.py`
3. Add response template in `src/core/response_generator.py`
4. Add unit test in `tests/test_command_processing.py`

## Performance Targets

| Metric | Target | Measured |
|---|---|---|
| Standby CPU | < 5% | ~2-3% |
| Memory baseline | < 4 GB | ~200 MB |
| Wake word latency | < 2s | ~1.2s |
| Command processing | < 5s | ~2.5s |
| Rendering | 60 FPS | 60 FPS |
