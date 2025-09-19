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
