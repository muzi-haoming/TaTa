import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
config_path = CONFIG_DIR / "config.yaml"

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)