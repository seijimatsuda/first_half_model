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
