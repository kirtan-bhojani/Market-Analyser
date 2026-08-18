#!/usr/bin/env bash
# Phase 12 Task 2: dispatch to web / worker / all by $PROCESS_TYPE.
set -e

case "$PROCESS_TYPE" in
  web)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
    ;;
  worker)
    exec arq app.worker.WorkerSettings
    ;;
  ingest)
    # Live crypto ingestion: seed the universe, subscribe to Binance WS, write
    # closed candles to the DB and fan out over Redis pub/sub. Runs until killed.
    exec python -m app.ingest.runner
    ;;
  all)
    # Single-container hosts (e.g. Hugging Face Spaces) run web + worker + the
    # live crypto ingester together. Migrate, start the worker and ingester in
    # the background, then run the web server in the foreground. If ANY of the
    # three exits, the container exits (host restarts it) so a dead ingester
    # can't silently leave the platform without live candles.
    alembic upgrade head
    arq app.worker.WorkerSettings &
    WORKER_PID=$!
    python -m app.ingest.runner &
    INGEST_PID=$!
    trap 'kill "$WORKER_PID" "$INGEST_PID" 2>/dev/null' EXIT INT TERM
    uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" &
    WEB_PID=$!
    # Exit as soon as any process dies so the host's restart policy kicks in.
    wait -n "$WORKER_PID" "$INGEST_PID" "$WEB_PID"
    ;;
  *)
    echo "Unknown PROCESS_TYPE: ${PROCESS_TYPE}" >&2
    exit 1
    ;;
esac
