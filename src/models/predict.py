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
