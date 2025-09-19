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
