.PHONY: backend-sync backend-lock-check backend-preflight backend-check test test-e2e smoke-live run

UV ?= uv

backend-sync:
	cd backend && $(UV) sync --locked --extra dev

backend-lock-check:
	cd backend && $(UV) lock --check

backend-preflight:
	cd backend && $(UV) run --locked --extra dev python ../scripts/check_async_runtime.py --loop all

backend-check: backend-lock-check backend-preflight
	cd backend && $(UV) run --locked --extra dev pytest

test: backend-check
	cd frontend && npm test -- --run

test-e2e:
	@echo "Starting backend with cache-first Tushare Pro data..."
	cd backend && $(UV) run --locked --extra dev python ../scripts/check_async_runtime.py --loop uvloop
	cd backend && $(UV) run --locked --extra dev uvicorn quantlab.main:app --port 8000 --loop uvloop & \
	BACKEND_PID=$$!; \
	cd frontend && npx playwright test; \
	PLAYWRIGHT_EXIT=$$?; \
	kill $$BACKEND_PID; \
	exit $$PLAYWRIGHT_EXIT

smoke-live:
	cd backend && $(UV) run --locked --extra dev python ../scripts/smoke_live_data.py

run:
	./start.sh
