from src.config.loader import load_config
import json
if __name__ == "__main__":
    cfg = load_config("config.yaml")
    print(cfg.model_dump_json(indent=2))
