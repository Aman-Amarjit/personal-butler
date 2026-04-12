# JARVIS AI Assistant - Deployment Checklist

## Pre-Release Verification

- [ ] All unit tests pass: `python -m pytest tests/ -v`
- [ ] Code coverage > 80%: `python -m pytest tests/ --cov=src`
- [ ] No critical security vulnerabilities in dependencies
- [ ] config.json has `"environment": "production"` and `"debug": false`
- [ ] All sensitive data uses EncryptionManager
- [ ] Audit logging is enabled
- [ ] Circuit breaker limits are configured

## Deployment Steps

### 1. Prepare Environment

```bash
git clone https://github.com/Aman-Amarjit/personal-butler.git
cd personal-butler
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Production

```bash
set JARVIS_ENV=production
```

Or create `config/local.json`:
```json
{
  "environment": "production",
  "debug": false,
  "logging": { "level": "WARNING" }
}
```

### 3. Initialize Database

```bash
python -c "from src.core.db_init import init_database; init_database()"
```

### 4. Start Ollama

```bash
ollama serve
```

### 5. Launch JARVIS

```bash
python src/main.py
```

## Post-Deployment Verification

- [ ] Wake word responds within 2 seconds
- [ ] Slime body renders at 60 FPS
- [ ] Voice commands execute correctly
- [ ] Audit log is being written to `data/jarvis.db`
- [ ] CPU usage in standby < 5%
- [ ] Memory usage < 4 GB

## Rollback Plan

1. Stop JARVIS (Ctrl+C or close window)
2. Checkout previous version: `git checkout v0.0.9`
3. Reinstall dependencies: `pip install -r requirements.txt`
4. Restart JARVIS

## Monitoring

- Check `logs/jarvis.log` for INFO-level events
- Check `logs/jarvis_errors.log` for errors
- Query audit log: `python -c "from src.security.audit_logger import AuditLogger; ..."`

## Security Checklist

- [ ] Encryption key is stored securely (not in config files)
- [ ] Audit log integrity verified on startup
- [ ] Windows Defender is enabled and up to date
- [ ] Trust level starts at 0 for new installations
- [ ] Circuit breaker limits are not disabled
