VENV_DIR := $(HOME)/goinfre/.cache_agent_smith/venv

install:
	uv sync

# Redirect the .venv into ~/goinfre/
install_goinfre:
	mkdir -p $(VENV_DIR)
	rm -rf .venv
	ln -s $(VENV_DIR) .venv
	uv sync

TASK   ?= mbpp_test/task_2_similar_elements.json
# TASK   ?= mbpp_test/task_3_is_not_prime.json
# TASK   ?= mbpp_test/task_4_heap_queue_largest.json
OUTPUT ?= mbpp_test/solution.json

run_gemini:
	uv run python -m agent_mbpp --task-file $(TASK) --output $(OUTPUT) \
		--model-name gemini-3.5-flash-lite \
		--provider-url https://generativelanguage.googleapis.com/v1beta/openai \
		--debug steps

nvim:
	uv run nvim .

clean:
	find . -name .venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache .pytest_cache

fclean: clean
	rm -rf $(VENV_DIR) .venv

lint:
	uv run flake8 src
	uv run mypy src

test:
	uv run pytest -v

.PHONY: install install_goinfre run_gemini nvim clean fclean lint test
