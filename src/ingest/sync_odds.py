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
