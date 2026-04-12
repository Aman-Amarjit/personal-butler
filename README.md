# JARVIS AI Assistant

A comprehensive AI assistant system for Windows laptops with voice interaction, local AI processing, and a slime-like visual interface.

## Features

- **Voice Interaction**: Wake word detection and natural language command processing
- **Local AI**: Ollama integration for privacy-focused LLM processing
- **Slime Body UI**: Interactive blob-shaped AI avatar with physics simulation
- **Desktop Overlay**: Wallpaper-integrated interface with real-time information
- **Security**: Windows Defender integration, audit logging, and encryption
- **Emotion Synthesis**: Multi-phase emotion framework (MVP to advanced)

## Project Structure

```
jarvis-ai-assistant/
├── src/
│   ├── core/           # Core AI processing components
│   ├── ui/             # UI and visualization (slime body)
│   ├── security/       # Security and privacy
│   ├── memory/         # Memory and knowledge management
│   └── __init__.py
├── tests/              # Test suite
├── config/             # Configuration files
├── data/               # Data storage
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── .gitignore         # Git ignore rules
```

## Installation

### Prerequisites

- Python 3.10+
- Windows 10/11
- Ollama (for local LLM)
- 4-8GB RAM minimum

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd jarvis-ai-assistant
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure Ollama:
```bash
# Download and install Ollama from https://ollama.ai
# Pull a model: ollama pull mistral (or your preferred model)
```

5. Initialize database:
```bash
python -m src.core.database init
```

## Development

### Running Tests

```bash
pytest tests/ -v --cov=src
```

### Starting Development Server

```bash
python -m src.main --dev
```

### Configuration

Edit `config/config.json` to customize:
- Ollama model size (3b, 7b, 13b)
- Wake word and voice settings
- UI theme and slime body colors
- Security and performance parameters

## Architecture

### Core Components

1. **Voice I/O Layer**: Wake word detection, STT, TTS
2. **AI Processing**: Ollama integration, command interpretation
3. **Memory System**: Episodic, semantic, and procedural memory
4. **UI Layer**: Slime body rendering with physics simulation
5. **Security**: Encryption, audit logging, threat detection

### Slime Body Physics

The slime body features:
- Blob deformation responding to interactions
- Jiggle/breathing animation in idle state
- Ripple effects on user interaction
- Customizable color gradients with glow effects
- Particle system for visual feedback

## Performance Targets

- Standby CPU: <5%
- Memory usage: <4GB
- Wake word latency: <2 seconds
- Command processing: <5 seconds

## Security

- All data processed locally by default
- AES-256 encryption for sensitive data
- Cryptographic audit logging
- Windows Defender integration
- Process monitoring and anomaly detection

## Phases

### Phase 1 (MVP): Core Voice Interaction (Weeks 1-12)
- Voice I/O layer
- Command processing
- Desktop overlay with slime body
- Security and logging

### Phase 2-4: Advanced Features (Research)
- Emotion synthesis (OCC, PAD, EPITOME)
- Multimodal emotion recognition
- Advanced metacognitive layer

## Contributing

See CONTRIBUTING.md for development guidelines.

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
