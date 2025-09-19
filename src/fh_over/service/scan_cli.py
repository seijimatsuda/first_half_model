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
