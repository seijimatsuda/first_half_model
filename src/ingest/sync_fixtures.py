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
