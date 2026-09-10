.PHONY: check check-full release publish

check:
	uv run --frozen python -m scripts.cicd check

check-full:
	uv run --frozen python -m scripts.cicd check --full

release:
	uv run --frozen python -m scripts.cicd release

publish:
	uv run --frozen python -m scripts.cicd publish
