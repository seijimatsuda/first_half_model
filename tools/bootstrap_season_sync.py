#!/usr/bin/env python3
"""
Bootstrap Season Sync for FH Over project.

What this does (idempotent):
1) Creates/updates a strongly-typed config model (providers/keys/scanner).
2) Ensures a sane config.yaml with your current providers.
3) Patches scan.py to reference self.config.providers.* and self.config.keys.*.
4) Adds small CLI wrappers for: sync_leagues, sync_fixtures, sync_odds, live_sync, predict, scan.
5) Writes a Procfile and a minimal DB schema (SQL).
6) Prints exact commands to:
   - sync current season leagues/fixtures/odds
   - run live daemon + predictions + scanner.

Safe to re-run; it won't clobber custom code (backs up originals).
"""

import os
import re
import sys
import textwrap
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
SRC = ROOT / "src"
CONFIG_DIR = SRC / "config"
SERVICE_SCAN = SRC / "fh_over" / "service" / "scan.py"
TOOLS_DIR = SRC / "tools"
INGEST_DIR = SRC / "ingest"
FEATURES_DIR = SRC / "features"
MODELS_DIR = SRC / "models"
DAEMONS_DIR = SRC / "daemons"
SCRIPTS_DIR = ROOT / "scripts"

def ensure_dirs():
    for d in [
        CONFIG_DIR, TOOLS_DIR, INGEST_DIR, FEATURES_DIR, MODELS_DIR,
        DAEMONS_DIR, SCRIPTS_DIR
    ]:
        d.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str, overwrite=False, backup=True):
    if path.exists() and not overwrite:
        return False
    if path.exists() and backup:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = path.with_suffix(path.suffix + f".bak.{ts}")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(content, encoding="utf-8")
    return True

def write_if_missing(path: Path, content: str):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    return False

def upsert_yaml_key(yaml_path: Path, key_path: list, default_value: str):
    """
    Very lightweight YAML upsert without PyYAML; tries to keep existing file intact.
    If missing, append at the end.
    """
    if not yaml_path.exists():
        yaml_path.write_text(default_config_yaml(), encoding="utf-8")
        return

    content = yaml_path.read_text(encoding="utf-8")
    joined = ".".join(key_path)
    if re.search(rf"(?m)^\s*{key_path[0]}\s*:", content) is None:
        # Append entire block if top-level missing
        content = content.rstrip() + "\n\n" + default_config_yaml()
        yaml_path.write_text(content, encoding="utf-8")
        return

    # crude: if any leaf token appears, assume present
    leaf = key_path[-1]
    if re.search(rf"(?m)^\s*{leaf}\s*:\s*", content):
        return
    # Append default at end (simple)
    content = content.rstrip() + f"\n# Added by bootstrap for {joined}\n{default_value}\n"
    yaml_path.write_text(content, encoding="utf-8")

def default_config_model_py():
    return textwrap.dedent("""\
    from pydantic import BaseModel
    from typing import Optional, List

    class ProviderFlags(BaseModel):
        sportradar_enabled: bool = False
        opta_enabled: bool = False
        sportmonks_enabled: bool = False
        api_football_enabled: bool = True
        theoddsapi_enabled: bool = True
        betfair_enabled: bool = False

    class ProviderKeys(BaseModel):
        sportradar_api_key: Optional[str] = None
        opta_api_key: Optional[str] = None
        sportmonks_api_key: Optional[str] = None
        api_football_key: Optional[str] = None
        theoddsapi_key: Optional[str] = None
        betfair_app_key: Optional[str] = None
        betfair_cert_path: Optional[str] = None

    class ScannerSettings(BaseModel):
        leagues_allowlist: List[int] = []
        min_kickoff_utc: Optional[str] = None
        max_kickoff_utc: Optional[str] = None
        poll_seconds: int = 30
        odds_refresh_seconds: int = 120
        max_backfill_days: int = 14
        timezone: str = "UTC"

    class AppConfig(BaseModel):
        providers: ProviderFlags
        keys: ProviderKeys
        scanner: ScannerSettings
        db_url: str
        env: str = "prod"
    """)

def default_loader_py():
    return textwrap.dedent("""\
    import os
    import json
    from typing import Any
    from pydantic import BaseModel
    from .model import AppConfig, ProviderFlags, ProviderKeys, ScannerSettings

    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None

    def load_config(path: str = "config.yaml") -> AppConfig:
        if yaml is None:
            raise RuntimeError("PyYAML not installed. `pip install pyyaml`")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return AppConfig(**data)
    """)

def default_config_yaml():
    return textwrap.dedent("""\
    providers:
      api_football_enabled: true
      theoddsapi_enabled: true
      betfair_enabled: false
      sportradar_enabled: false
      opta_enabled: false
      sportmonks_enabled: false

    keys:
      api_football_key: "PUT_YOUR_API_FOOTBALL_KEY_HERE"
      theoddsapi_key: "PUT_YOUR_THEODDSAPI_KEY_HERE"
      betfair_app_key: null
      betfair_cert_path: null

    scanner:
      leagues_allowlist: []
      min_kickoff_utc: null
      max_kickoff_utc: null
      poll_seconds: 30
      odds_refresh_seconds: 120
      max_backfill_days: 14
      timezone: "UTC"

    db_url: "postgresql+psycopg://user:pass@localhost:5432/footy"
    env: "prod"
    """)

def patch_scan_py():
    if not SERVICE_SCAN.exists():
        print(f"[warn] {SERVICE_SCAN} not found; skipping patch.")
        return

    src = SERVICE_SCAN.read_text(encoding="utf-8")
    original = src

    # Replace provider flags access: self.config.<flag>_enabled -> self.config.providers.<flag>_enabled
    provider_flags = [
        "sportradar", "opta", "sportmonks", "api_football", "theoddsapi", "betfair"
    ]
    for name in provider_flags:
        # flags
        src = re.sub(
            rf"\bself\.config\.{name}_enabled\b",
            f"self.config.providers.{name}_enabled",
            src
        )

    # Replace API keys access: self.config.<provider>_api_key -> self.config.keys.<provider>_api_key
    key_names = [
        "sportradar_api_key", "opta_api_key", "sportmonks_api_key",
        "api_football_key", "theoddsapi_key", "betfair_app_key", "betfair_cert_path"
    ]
    for key in key_names:
        src = re.sub(
            rf"\bself\.config\.{key}\b",
            f"self.config.keys.{key}",
            src
        )

    if src != original:
        write_file(SERVICE_SCAN, src, overwrite=True, backup=True)
        print("[ok] Patched scan.py to use self.config.providers.* and self.config.keys.*")
    else:
        print("[ok] scan.py already looks correct; no changes made.")

def write_helpers_and_clis():
    # print_config
    write_if_missing(
        TOOLS_DIR / "print_config.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import json
        if __name__ == "__main__":
            cfg = load_config("config.yaml")
            print(cfg.model_dump_json(indent=2))
        """)
    )

    # ingest: sync_leagues
    write_if_missing(
        INGEST_DIR / "sync_leagues.py",
        textwrap.dedent("""\
        # Minimal wrapper to your real logic; adjust imports if needed.
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--current-only", action="store_true")
            ap.add_argument("--write-db", action="store_true")
            args = ap.parse_args()

            cfg = load_config("config.yaml")
            # TODO: call your actual implementation
            print("[stub] sync_leagues --current-only=%s --write-db=%s" % (args.current_only, args.write_db))

        if __name__ == "__main__":
            main()
        """)
    )

    # ingest: sync_fixtures
    write_if_missing(
        INGEST_DIR / "sync_fixtures.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--league", type=int)
            ap.add_argument("--season", type=int)
            ap.add_argument("--from", dest="date_from", type=str)
            ap.add_argument("--to", dest="date_to", type=str)
            ap.add_argument("--write-db", action="store_true")
            args = ap.parse_args()
            cfg = load_config("config.yaml")
            # TODO: call your actual implementation
            print(f"[stub] sync_fixtures league={args.league} season={args.season} from={args.date_from} to={args.date_to} write={args.write_db}")

        if __name__ == "__main__":
            main()
        """)
    )

    # ingest: sync_odds
    write_if_missing(
        INGEST_DIR / "sync_odds.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--fixture-id", type=int)
            ap.add_argument("--providers", type=str, default="theoddsapi,api_football")
            ap.add_argument("--markets", type=str, default="1H,FT")
            ap.add_argument("--write-db", action="store_true")
            args = ap.parse_args()
            cfg = load_config("config.yaml")
            # TODO: call your actual implementation
            print(f"[stub] sync_odds fixture_id={args.fixture_id} providers={args.providers} markets={args.markets} write={args.write_db}")

        if __name__ == "__main__":
            main()
        """)
    )

    # daemons: live_sync
    write_if_missing(
        DAEMONS_DIR / "live_sync.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import time, argparse

        def once(cfg):
            # TODO: call your real live fixtures + odds refresh here
            print("[stub] live_sync tick")

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--poll-seconds", type=int, default=30)
            ap.add_argument("--odds-refresh-seconds", type=int, default=120)
            ap.add_argument("--once", action="store_true")
            args = ap.parse_args()

            cfg = load_config("config.yaml")
            if args.once:
                once(cfg); return

            t0 = time.time()
            t1 = time.time()
            while True:
                now = time.time()
                if now - t0 >= args.poll_seconds:
                    once(cfg); t0 = now
                if now - t1 >= args.odds_refresh_seconds:
                    # TODO: odds refresh
                    print("[stub] odds refresh")
                    t1 = now
                time.sleep(1)

        if __name__ == "__main__":
            main()
        """)
    )

    # features: build
    write_if_missing(
        FEATURES_DIR / "build.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--from", dest="date_from", type=str)
            ap.add_argument("--to", dest="date_to", type=str)
            ap.add_argument("--leagues", type=str, default="top30")
            ap.add_argument("--write-db", action="store_true")
            args = ap.parse_args()
            cfg = load_config("config.yaml")
            # TODO: implement your feature build
            print(f"[stub] features.build from={args.date_from} to={args.date_to} leagues={args.leagues} write={args.write_db}")

        if __name__ == "__main__":
            main()
        """)
    )

    # models: predict
    write_if_missing(
        MODELS_DIR / "predict.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--universe", type=str, default="upcoming")
            ap.add_argument("--market", type=str, default="1H_OU")
            ap.add_argument("--write-db", action="store_true")
            ap.add_argument("--write-csv", type=str)
            ap.add_argument("--loop", type=int)  # seconds
            args = ap.parse_args()
            cfg = load_config("config.yaml")

            def run_once():
                # TODO: call your model predict; write to DB/CSV
                print(f"[stub] predict universe={args.universe} market={args.market} -> {args.write_csv or 'DB'}")

            if args.loop:
                import time
                while True:
                    run_once()
                    time.sleep(args.loop)
            else:
                run_once()

        if __name__ == "__main__":
            main()
        """)
    )

    # fh_over.service.scan CLI wrapper (if not already integrated)
    write_if_missing(
        SRC / "fh_over" / "service" / "scan_cli.py",
        textwrap.dedent("""\
        from src.config.loader import load_config
        import argparse

        def main():
            ap = argparse.ArgumentParser()
            ap.add_argument("--from", dest="date_from", type=str, default="now")
            ap.add_argument("--to", dest="date_to", type=str, default="+24h")
            ap.add_argument("--stake-mode", type=str, default="flat")
            ap.add_argument("--edge-threshold", type=float, default=0.03)
            ap.add_argument("--min-sample-size", type=int, default=8)
            ap.add_argument("--dry-run", action="store_true")
            ap.add_argument("--loop", type=int)
            args = ap.parse_args()
            cfg = load_config("config.yaml")

            def run_once():
                # TODO: import and call your real scan() here
                print(f"[stub] scan from={args.date_from} to={args.date_to} edge>{args.edge_threshold} stake={args.stake_mode} dry={args.dry_run}")

            if args.loop:
                import time
                while True:
                    run_once()
                    time.sleep(args.loop)
            else:
                run_once()

        if __name__ == "__main__":
            main()
        """)
    )

def write_procfile_and_make():
    write_if_missing(
        ROOT / "Procfile",
        textwrap.dedent("""\
        live: python -m src.daemons.live_sync --poll-seconds 30 --odds-refresh-seconds 120
        preds: python -m src.models.predict --universe window:6h --market 1H_OU --write-db --loop 3600
        scan: python -m src.fh_over.service.scan_cli --from now --to +12h --edge-threshold 0.03 --loop 300
        """)
    )
    write_if_missing(
        ROOT / "Makefile",
        textwrap.dedent("""\
        .PHONY: season backfill live preds scan

        season:
\tpython -m src.ingest.sync_leagues --current-only --write-db
\tpython -m src.ingest.sync_fixtures --from "2025-07-01" --to "2025-10-01" --write-db
\tpython -m src.ingest.sync_odds --providers theoddsapi,api_football --markets "1H,FT" --write-db

        backfill:
\tpython -m src.ingest.sync_fixtures --from "$(FROM)" --to "$(TO)" --write-db

        live:
\tpython -m src.daemons.live_sync --poll-seconds 30 --odds-refresh-seconds 120

        preds:
\tpython -m src.models.predict --universe window:6h --market 1H_OU --write-db --loop 3600

        scan:
\tpython -m src.fh_over.service.scan_cli --from now --to +12h --edge-threshold 0.03 --loop 300
        """)
    )

def write_db_schema():
    write_if_missing(
        ROOT / "db_schema.sql",
        textwrap.dedent("""\
        -- Minimal schema; extend as needed.
        CREATE TABLE IF NOT EXISTS fixtures (
          fixture_id BIGINT PRIMARY KEY,
          league_id INT NOT NULL,
          season INT NOT NULL,
          kickoff_utc TIMESTAMPTZ,
          status TEXT,
          home_team_id INT,
          away_team_id INT,
          ht_home_goals INT,
          ht_away_goals INT,
          ft_home_goals INT,
          ft_away_goals INT,
          last_update TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS odds (
          id BIGSERIAL PRIMARY KEY,
          fixture_id BIGINT REFERENCES fixtures(fixture_id),
          provider TEXT,
          market TEXT,
          selection TEXT,
          price NUMERIC,
          line NUMERIC,
          ts TIMESTAMPTZ DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_odds_fixture_ts ON odds (fixture_id, ts);
        """)
    )

def main():
    ensure_dirs()

    # 1) Config model + loader
    write_file(CONFIG_DIR / "model.py", default_config_model_py(), overwrite=False)
    write_file(CONFIG_DIR / "loader.py", default_loader_py(), overwrite=False)

    # 2) config.yaml (create if missing)
    cfg_yaml = ROOT / "config.yaml"
    if not cfg_yaml.exists():
        cfg_yaml.write_text(default_config_yaml(), encoding="utf-8")
        print("[ok] Wrote config.yaml (fill in your API keys).")
    else:
        # Gentle ensure of blocks
        upsert_yaml_key(cfg_yaml, ["providers"], textwrap.dedent("providers:\n  api_football_enabled: true\n"))
        upsert_yaml_key(cfg_yaml, ["keys"], textwrap.dedent("keys:\n  api_football_key: \"PUT_YOUR_API_FOOTBALL_KEY_HERE\""))
        upsert_yaml_key(cfg_yaml, ["scanner"], textwrap.dedent("scanner:\n  poll_seconds: 30\n  odds_refresh_seconds: 120\n"))
        print("[ok] Verified config.yaml sections exist.")

    # 3) Patch scan.py
    patch_scan_py()

    # 4) Helpers + CLIs
    write_helpers_and_clis()

    # 5) Procfile + Makefile
    write_procfile_and_make()

    # 6) DB schema
    write_db_schema()

    print("\n✅ Bootstrap complete.")
    print("\nNext steps (exact commands):")
    print("1) Install deps (if needed):")
    print("   pip install pydantic pyyaml")
    print("2) Add your API keys in config.yaml (api_football_key, theoddsapi_key, etc.).")
    print("3) (Optional) Apply DB schema:")
    print("   psql $YOUR_CONN_STRING -f db_schema.sql")
    print("4) Quick config sanity check:")
    print("   python -m src.tools.print_config | python -m json.tool")
    print("5) Seed THIS SEASON + upcoming week:")
    print('   python -m src.ingest.sync_leagues --current-only --write-db')
    print('   python -m src.ingest.sync_fixtures --from "2025-07-01" --to "2025-10-01" --write-db')
    print('   python -m src.ingest.sync_odds --providers theoddsapi,api_football --markets "1H,FT" --write-db')
    print("6) Start live + preds + scanner (choose one):")
    print("   foreman start   # if you use Procfile")
    print("   # or individually:")
    print("   python -m src.daemons.live_sync --poll-seconds 30 --odds-refresh-seconds 120")
    print("   python -m src.models.predict --universe window:6h --market 1H_OU --write-db --loop 3600")
    print("   python -m src.fh_over.service.scan_cli --from now --to +12h --edge-threshold 0.03 --loop 300")
    print("\nIf any of your real modules already exist with different names, just update the small wrappers in src/ingest/*.py, src/daemons/live_sync.py, src/features/build.py, src/models/predict.py, or src/fh_over/service/scan_cli.py to call your actual implementations.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[error] {e}")
        sys.exit(1)
