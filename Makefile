.PHONY: format format-check check check-cicd check-full release publish publish-feature

check:
	uv run --frozen python -m scripts.cicd check

format:
	uv run --frozen python -m scripts.cicd format

format-check:
	uv run --frozen python -m scripts.cicd format-check

check-cicd:
	uv run --frozen python -m unittest discover -s test/cicd -p 'test_*.py' -v

check-full:
	uv run --frozen python -m scripts.cicd check --full

release:
	uv run --frozen python -m scripts.cicd release

publish:
	uv run --frozen python -m scripts.cicd publish

publish-feature:
	uv run --frozen python -m scripts.cicd publish-feature
