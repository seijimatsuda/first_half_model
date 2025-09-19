live: python -m src.daemons.live_sync --poll-seconds 30 --odds-refresh-seconds 120
preds: python -m src.models.predict --universe window:6h --market 1H_OU --write-db --loop 3600
scan: python -m src.fh_over.service.scan_cli --from now --to +12h --edge-threshold 0.03 --loop 300
