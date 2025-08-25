.PHONY: setup

# Setup for Render build: install deps and Playwright Chromium with system deps
setup:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	PLAYWRIGHT_BROWSERS_PATH=$$(pwd)/.pw-browsers python -m playwright install


