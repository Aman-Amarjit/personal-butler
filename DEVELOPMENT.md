# JARVIS Development Guide

## Development Workflow

### 1. Before Starting Work
```bash
# Activate virtual environment
venv\Scripts\activate

# Update dependencies if needed
pip install -r requirements.txt --upgrade
```

### 2. Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_slime_body.py -v

# Run specific test
pytest tests/test_slime_body.py::TestSlimeBody::test_initialization -v
```

### 3. Code Quality

#### Linting (when added)
```bash
# Will add pylint/flake8 later
```

#### Type Checking (when added)
```bash
# Will add mypy later
```

### 4. Running the Application

#### Development Mode
```bash
python -m src.main --dev --debug
```

#### Production Mode
```bash
python -m src.main
```

#### Custom Resolution
```bash
python -m src.main --width 2560 --height 1440
```

## Code Style Guidelines

### Python Style
- Follow PEP 8
- Use type hints for all functions
- Document all classes and public methods with docstrings
- Use meaningful variable names

### Example Function
```python
def apply_force(self, force: Vector2, position: Vector2) -> None:
    """
    Apply a force to the slime body.

    Args:
        force: Force vector
        position: Position where force is applied

    Returns:
        None
    """
    # Implementation
```

### Example Class
```python
class MyComponent:
    """
    Brief description of the component.
    
    Longer description explaining what it does,
    how it works, and any important details.
    """

    def __init__(self, param: str) -> None:
        """Initialize the component."""
        self.param = param
```

## Testing Guidelines

### Unit Tests
- Test individual functions and methods
- Use descriptive test names: `test_<function>_<scenario>`
- Aim for >80% code coverage
- Test both success and failure cases

### Example Test
```python
def test_apply_force_increases_velocity(self):
    """Test that applying force increases velocity"""
    slime = SlimeBody((100, 100))
    force = Vector2(100, 0)
    
    slime.apply_force(force, Vector2(0, 0))
    
    assert slime.velocity.x > 0
```

### Integration Tests
- Test component interactions
- Test end-to-end workflows
- Add to `tests/` directory with `test_integration_*.py` naming

## Adding New Features

### 1. Create Feature Branch
```bash
git checkout -b feature/my-feature
```

### 2. Implement Feature
- Write tests first (TDD approach)
- Implement the feature
- Ensure all tests pass

### 3. Update Documentation
- Update README.md if user-facing
- Update docstrings
- Update tasks.md with progress

### 4. Commit and Push
```bash
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

### 5. Create Pull Request
- Describe changes
- Link to related issues
- Ensure CI passes

## Project Structure

### src/ui/
- `slime_body.py` - Physics engine and blob simulation
- `overlay.py` - Desktop overlay rendering

### src/core/
- Will contain: Ollama integration, command processing, response generation

### src/security/
- Will contain: Encryption, audit logging, threat detection

### src/memory/
- Will contain: Episodic, semantic, procedural memory systems

### tests/
- `test_slime_body.py` - Tests for physics engine
- Add more test files as features are implemented

## Common Tasks

### Add a New Test
1. Create test function in appropriate test file
2. Use descriptive name: `test_<component>_<scenario>`
3. Run: `pytest tests/test_file.py::TestClass::test_function -v`

### Add a New Module
1. Create file in appropriate `src/` subdirectory
2. Add `__init__.py` if creating new package
3. Add unit tests in `tests/`
4. Update imports in `src/__init__.py` if needed

### Update Configuration
1. Edit `config/config.json`
2. Add corresponding code to read the config
3. Document the new setting in README.md

### Add a Dependency
1. Add to `requirements.txt` with version
2. Run: `pip install -r requirements.txt`
3. Test that it works
4. Commit changes

## Debugging

### Enable Debug Logging
```bash
python -m src.main --debug
```

### Check Logs
```bash
# View recent logs
type logs\jarvis.log

# Follow logs in real-time (PowerShell)
Get-Content logs\jarvis.log -Wait
```

### Debug in IDE
- Use PyCharm, VS Code, or your preferred IDE
- Set breakpoints in code
- Run with debugger

### Common Issues

#### Import Errors
- Ensure virtual environment is activated
- Check that all dependencies are installed
- Verify file paths are correct

#### Physics Issues
- Check Vector2 calculations
- Verify deformation values are in expected range
- Test with simple inputs first

#### Rendering Issues
- Check PyQt6 installation
- Verify graphics drivers are up to date
- Test with different window sizes

## Performance Optimization

### Profiling
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Optimization Targets
- Slime body rendering: 60 FPS
- Physics updates: <1ms per frame
- Memory usage: <4GB
- CPU usage (standby): <5%

## Version Control

### Commit Messages
- Use present tense: "Add feature" not "Added feature"
- Be descriptive: "Add slime body physics" not "Update code"
- Reference issues: "Fix #123: Add slime body physics"

### Branch Naming
- Feature: `feature/description`
- Bugfix: `bugfix/description`
- Hotfix: `hotfix/description`

## Release Checklist

- [ ] All tests pass
- [ ] Code coverage >80%
- [ ] Documentation updated
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Release notes written
- [ ] Tagged in git

## Resources

- [Python Documentation](https://docs.python.org/3/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pytest Documentation](https://docs.pytest.org/)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)

## Getting Help

1. Check existing documentation
2. Search GitHub issues
3. Check test files for examples
4. Ask in team chat/discussions
5. Create an issue with detailed description

Happy coding! 🚀
