.PHONY: up down logs build test lint fmt typecheck dev score rules health
COMPOSE ?= docker compose

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

test:          ## fixture corpus (CI gate) + API tests, all on the mock judge
	pytest
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
