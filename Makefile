VENV_DIR := $(HOME)/goinfre/.cache_agent_smith/venv

install:
	uv sync

# Redirect the .venv into ~/goinfre/
install_goinfre:
	mkdir -p $(VENV_DIR)
	rm -rf .venv
	ln -s $(VENV_DIR) .venv
	uv sync

run:
	# uv run 42-agent-smith
	uv run python -m agent_smith

nvim:
	uv run nvim .

clean:
	find . -name .venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache

fclean: clean
	rm -rf $(VENV_DIR) .venv

lint:
	uv run flake8 src
	uv run mypy src

.PHONY: install install_goinfre run nvim clean fclean lint
