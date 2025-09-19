        .PHONY: season backfill live preds scan

        season:
	python -m src.ingest.sync_leagues --current-only --write-db
	python -m src.ingest.sync_fixtures --from "2025-07-01" --to "2025-10-01" --write-db
	python -m src.ingest.sync_odds --providers theoddsapi,api_football --markets "1H,FT" --write-db

        backfill:
	python -m src.ingest.sync_fixtures --from "$(FROM)" --to "$(TO)" --write-db

        live:
	python -m src.daemons.live_sync --poll-seconds 30 --odds-refresh-seconds 120

        preds:
	python -m src.models.predict --universe window:6h --market 1H_OU --write-db --loop 3600

        scan:
	python -m src.fh_over.service.scan_cli --from now --to +12h --edge-threshold 0.03 --loop 300
