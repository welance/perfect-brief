.PHONY: up down logs build test test-site test-e2e test-all test-llm-multilingual lint fmt typecheck dev score rules health
COMPOSE ?= docker compose
# use the project venv when it exists, so `make test` works without activating
PYTEST ?= $(shell [ -x .venv/bin/pytest ] && echo .venv/bin/pytest || echo pytest)

up:            ## build + start the service and redis
	$(COMPOSE) up --build -d
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f api
build:
	$(COMPOSE) build

dev:           ## run locally with autoreload (needs local redis or none)
	uvicorn app.main:app --reload --port 8000

test:          ## fixture corpus (CI gate) + API + contract tests, all on the mock judge
	$(PYTEST)
test-site:     ## engine tests for site/pricing.js (dev-only, needs node)
	node --test tests/site/pricing.test.mjs
test-e2e:      ## end-to-end: the real service, both calculators, 8 languages (needs node)
	npx playwright test -c tests/e2e/playwright.config.mjs
test-all:      ## everything that runs offline: python + engine + e2e
	$(MAKE) test && $(MAKE) test-site && $(MAKE) test-e2e
test-llm-multilingual: ## the judge's language guarantee (needs PB_ANTHROPIC_API_KEY; not in offline CI)
	$(PYTEST) tests/test_multilingual_llm.py -v
lint:
	ruff check .
fmt:
	ruff check --fix . && ruff format .
typecheck:
	mypy app perfect_brief

health:
	curl -s localhost:8000/v1/healthz | python -m json.tool
rules:
	curl -s localhost:8000/v1/rules | python -m json.tool
score:         ## demo: a high-quality brief that leaks a brand -> blocked
	curl -s -X POST localhost:8000/v1/score -H 'content-type: application/json' \
	  -d '{"brief":"# Booking tool\nProblem: restaurants lose bookings because staff cant update availability. Budget band 25-40k. Ship before spring. Integrates with our Stripe account; contact mara@acme.it.","judge":"mock"}' \
	  | python -m json.tool
