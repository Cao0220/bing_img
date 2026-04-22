import datetime
import json
from pathlib import Path
import time
import random
import os

import requests
import yaml

COUNTRIES = [
    "ar",
    "at",
    "au",
    "be",
    "br",
    "ca",
    "ch",
    "cl",
    "cn",
    "de",
    "dk",
    "es",
    "fi",
    "fr",
    "hk",
    "ie",
    "in",
    "it",
    "jp",
    "kr",
    "nl",
    "no",
    "nz",
    "ph",
    "pt",
    "ru",
    "se",
    "sg",
    "tw",
    "uk",
]

BING_API = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&video=1&cc={cc}"
DEFAULT_LOCAL_ROOT = "/root/bing_img"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_local_root(config_path: Path = DEFAULT_CONFIG_PATH) -> Path:
    if not config_path.exists():
        return Path(DEFAULT_LOCAL_ROOT)
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    local = config.get("local") or {}
    root = local.get("root") or DEFAULT_LOCAL_ROOT
    return Path(root)


def day_dir(root: Path, day: datetime.date) -> Path:
    return root / day.strftime("%Y") / day.strftime("%m") / day.strftime("%d")


def json_path(root: Path, day: datetime.date) -> Path:
    return day_dir(root, day) / f"{day.strftime('%Y-%m-%d')}.json"


def fetch_country_images(country_code: str) -> list:
    response = requests.get(BING_API.format(cc=country_code), timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("images", [])


def append_run_log(root: Path, day: datetime.date) -> None:
    log_file = root / "readme.md"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(f"{day.strftime('%Y-%m-%d')}\n----------------\n")


def main() -> int:
    today = datetime.date.today()
    root = load_local_root()

    target_dir = day_dir(root, today)
    target_dir.mkdir(parents=True, exist_ok=True)

    print("------------------------")
    print(datetime.datetime.now().strftime("%Y-%m-%d %a %H:%M:%S") + " bing.py")
    print("========================")

    append_run_log(root, today)

    metadata = {}
    for country in COUNTRIES:
        metadata[country] = fetch_country_images(country)

    target_json = json_path(root, today)
    with target_json.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, sort_keys=False, indent=4, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved metadata to: {target_json}")
    
    # time.sleep(random.randint(0,21600))
    os.system('day=`date +%Y-%m-%d` && cd /root/bing_img/ && /usr/bin/git add . && /usr/bin/git commit -m $day &&/usr/bin/git push -u origin main')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
