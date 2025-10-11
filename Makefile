.PHONY: test cov install-dev clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  make test        - Run tests quickly with minimal output"
	@echo "  make test-v      - Run tests with verbose output"
	@echo "  make cov         - Run tests with coverage report"
	@echo "  make install-dev - Install development dependencies"
	@echo "  make clean       - Remove test artifacts"

# Run tests quietly
test:
	pytest -q

# Run tests with verbose output
test-v:
	pytest -v

# Run tests with coverage
cov:
	pytest --cov=scripts --cov=tests --cov-report=term-missing --cov-report=html -q

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
