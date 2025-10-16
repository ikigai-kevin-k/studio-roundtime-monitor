# Studio Round Time Monitor Makefile

.PHONY: help install test lint format clean run demo

# Default target
help:
	@echo "Studio Round Time Monitor - Available targets:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean build artifacts"
	@echo "  run         - Run monitor service"
	@echo "  demo        - Run demo"
	@echo "  setup       - Setup development environment"

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black isort mypy flake8

# Run tests
test:
	pytest tests/ -v --cov=studio_roundtime_monitor --cov-report=html --cov-report=term-missing

# Run linting
lint:
	flake8 studio_roundtime_monitor/ tests/
	mypy studio_roundtime_monitor/

# Format code
format:
	black studio_roundtime_monitor/ tests/ examples/
	isort studio_roundtime_monitor/ tests/ examples/

# Clean build artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf build/ dist/ .eggs/

# Create directories
setup-dirs:
	mkdir -p data logs config exports

# Setup development environment
setup: setup-dirs
	pip install -e .
	python -m studio_roundtime_monitor.main --create-config

# Run monitor service
run:
	python -m studio_roundtime_monitor.main --config config/monitor_config.yaml

# Run demo
demo:
	python examples/roulette_integration.py
	python examples/sicbo_integration.py

# Validate configuration
validate-config:
	python -m studio_roundtime_monitor.main --validate-config

# Show status
status:
	python -m studio_roundtime_monitor.main --status

# Build package
build:
	python -m build

# Install package
install-package: build
	pip install dist/*.whl

# Run all checks
check: lint test

# Quick setup for development
dev-setup: install-dev setup-dirs
	python -m studio_roundtime_monitor.main --create-config
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make run' to start the monitor service"
