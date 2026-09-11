.PHONY: check check-cicd check-full release publish

check:
	uv run --frozen python -m scripts.cicd check

check-cicd:
	uv run --frozen python -m unittest discover -s test/cicd -p 'test_*.py' -v

check-full:
	uv run --frozen python -m scripts.cicd check --full

release:
	uv run --frozen python -m scripts.cicd release

publish:
	uv run --frozen python -m scripts.cicd publish
