import datetime
import json
import os
from pathlib import Path
import random
import re
import time

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
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IMAGE_KEY_RE = re.compile(r"OHR\.([^_]+)_", re.IGNORECASE)


def parse_date(value: str) -> datetime.date:
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


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


def load_day_metadata(root: Path, day: datetime.date) -> dict:
    path = json_path(root, day)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_image_key(urlbase: str) -> str:
    if not urlbase:
        return ""
    match = IMAGE_KEY_RE.search(urlbase)
    if match:
        return match.group(1)
    return urlbase


def discover_all_metadata_dates(root: Path) -> list[datetime.date]:
    dates = set()
    for file_path in root.rglob("*.json"):
        stem = file_path.stem
        if not DATE_RE.fullmatch(stem):
            continue
        try:
            dates.add(parse_date(stem))
        except ValueError:
            continue
    return sorted(dates)


def build_history_urls_for_day(root: Path, day: datetime.date) -> list[str]:
    today_data = load_day_metadata(root, day)
    if not today_data:
        return []

    yesterday_data = load_day_metadata(root, day - datetime.timedelta(days=1))
    seen = set()
    for region in yesterday_data.keys():
        images = yesterday_data.get(region) or []
        if not images:
            continue
        key = extract_image_key(images[0].get("urlbase", ""))
        if key:
            seen.add(key)

    urls = []
    for region in today_data.keys():
        images = today_data.get(region) or []
        if not images:
            continue
        urlbase = images[0].get("urlbase", "")
        if not urlbase:
            continue
        key = extract_image_key(urlbase)
        if key in seen:
            continue
        seen.add(key)
        urls.append(f"https://www.bing.com{urlbase}_UHD.jpg")
    return urls


def read_last_history_date(history_path: Path) -> datetime.date | None:
    if not history_path.exists():
        return None
    last_date = None
    with history_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not DATE_RE.fullmatch(text):
                continue
            try:
                last_date = parse_date(text)
            except ValueError:
                continue
    return last_date


def append_history_day(history_path: Path, day: datetime.date, urls: list[str]) -> None:
    prefix = ""
    if history_path.exists() and history_path.stat().st_size > 0:
        with history_path.open("rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                prefix = "\n"

    day_text = day.strftime("%Y-%m-%d")
    lines = [day_text, "----------------"]
    for index, url in enumerate(urls):
        lines.append(f"![{day_text}-{index}]({url})")

    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(prefix + "\n".join(lines) + "\n")


def sync_history(root: Path) -> None:
    history_path = root / "history.md"
    metadata_dates = discover_all_metadata_dates(root)
    if not metadata_dates:
        print("No metadata found for history sync.")
        return

    last_date = read_last_history_date(history_path)
    if last_date is None:
        pending_dates = metadata_dates
    else:
        pending_dates = [day for day in metadata_dates if day > last_date]

    if not pending_dates:
        print("History already up to date.")
        return

    for day in pending_dates:
        urls = build_history_urls_for_day(root, day)
        append_history_day(history_path, day, urls)
        print(f"History appended: {day.strftime('%Y-%m-%d')} images={len(urls)}")


def fetch_country_images(country_code: str) -> list:
    response = requests.get(BING_API.format(cc=country_code), timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("images", [])


def main() -> int:
    today = datetime.date.today()
    root = load_local_root()

    target_dir = day_dir(root, today)
    target_dir.mkdir(parents=True, exist_ok=True)

    print("------------------------")
    print(datetime.datetime.now().strftime("%Y-%m-%d %a %H:%M:%S") + " bing.py")
    print("========================")

    metadata = {}
    for country in COUNTRIES:
        metadata[country] = fetch_country_images(country)

    target_json = json_path(root, today)
    with target_json.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, sort_keys=False, indent=4, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved metadata to: {target_json}")

    sync_history(root)

    time.sleep(random.randint(0, 21600))
    os.system(
        "day=`date +%Y-%m-%d` && cd /root/bing_img/ && /usr/bin/git add . && /usr/bin/git commit -m $day &&/usr/bin/git push -u origin main"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
