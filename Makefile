.DEFAULT_GOAL := help
PY ?= python3

help:  ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

setup:  ## Install the git hooks and create private/
	pre-commit install
	@mkdir -p private
	@echo
	@echo "private/ is gitignored and is where real recipes go."
	@echo "Next: cp tools/denylist.example.txt tools/denylist.txt, add names, make denylist."

check-recipes:  ## Parse every recipe and validate its front matter
	$(PY) -m tools.check_recipes

check-personal:  ## Scan for names, contacts, addresses, and private links
	$(PY) -m tools.scan_personal

check-markdown:  ## Lint the documentation for style and dead relative links
	$(PY) -m tools.check_links
	@command -v pymarkdown >/dev/null 2>&1 \
	  && pymarkdown --config .pymarkdown scan $$(git ls-files '*.md' | grep -v '^\.github/') \
	  || echo "  (pymarkdown not on PATH; pre-commit and CI run it. pipx install pymarkdownlnt)"

check-denylist:  ## Verify the committed digests and the salt agree
	$(PY) -m tools.denylist --self-test

denylist:  ## Regenerate tools/denylist.hashes from tools/denylist.txt
	$(PY) -m tools.denylist --write

check:  ## Everything CI runs
	$(PY) -m tools.denylist --self-test
	$(PY) -m tools.check_recipes
	$(PY) -m tools.check_links
	$(PY) -m tools.scan_personal
	pre-commit run --all-files
