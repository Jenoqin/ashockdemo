.PHONY: test test-e2e smoke-live run

test:
	cd backend && .venv/bin/pytest
	cd frontend && npm test -- --run

test-e2e:
	@echo "Starting backend with cache-first Tushare Pro data..."
	cd backend && .venv/bin/uvicorn quantlab.main:app --port 8000 & \
	BACKEND_PID=$$!; \
	cd frontend && npx playwright test; \
	PLAYWRIGHT_EXIT=$$?; \
	kill $$BACKEND_PID; \
	exit $$PLAYWRIGHT_EXIT

smoke-live:
	cd backend && .venv/bin/python ../scripts/smoke_live_data.py

run:
	@echo "Starting full stack..."
	cd backend && .venv/bin/uvicorn quantlab.main:app --port 8000 & \
	cd frontend && npm run dev
