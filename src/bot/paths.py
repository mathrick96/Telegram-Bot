from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "users.db"
