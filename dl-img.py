import argparse
import datetime
import json
import random
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IMAGE_KEY_RE = re.compile(r"OHR\.([^_]+)_", re.IGNORECASE)
DEFAULT_LOCAL_ROOT = "/root/bing_img"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


@dataclass
class JobStats:
    days: int = 0
    planned: int = 0
    remote_exists: int = 0
    uploaded: int = 0
    removed_local: int = 0
    failures: int = 0


@dataclass
class ImageEntry:
    index: int
    image_key: str
    image_url: str


class WebDavClient:
    def __init__(self, base_url: str, username: str, password: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.auth = (username, password)
        self._ensured_dirs = set()

    def _url(self, remote_path: str) -> str:
        if not remote_path.startswith("/"):
            remote_path = "/" + remote_path
        return f"{self.base_url}{quote(remote_path, safe='/-_.~')}"

    def ensure_dir(self, remote_dir: str) -> None:
        clean_dir = normalize_remote_root(remote_dir)
        if clean_dir == "/":
            return
        parts = [part for part in clean_dir.strip("/").split("/") if part]
        current = ""
        for part in parts:
            current = f"{current}/{part}"
            if current in self._ensured_dirs:
                continue
            response = self.session.request("MKCOL", self._url(current), timeout=self.timeout_seconds)
            if response.status_code not in {200, 201, 204, 301, 302, 405}:
                raise RuntimeError(
                    f"MKCOL failed for {current}, status={response.status_code}, body={response.text[:200]}"
                )
            self._ensured_dirs.add(current)

    def exists(self, remote_file: str) -> bool:
        response = self.session.head(self._url(remote_file), timeout=self.timeout_seconds, allow_redirects=True)
        if response.status_code == 404:
            return False
        if 200 <= response.status_code < 300:
            return True
        if response.status_code == 405:
            probe = self.session.get(
                self._url(remote_file),
                headers={"Range": "bytes=0-0"},
                stream=True,
                timeout=self.timeout_seconds,
            )
            if probe.status_code == 404:
                return False
            if probe.status_code in {200, 206}:
                return True
            raise RuntimeError(
                f"GET range probe failed for {remote_file}, status={probe.status_code}, body={probe.text[:200]}"
            )
        raise RuntimeError(
            f"HEAD failed for {remote_file}, status={response.status_code}, body={response.text[:200]}"
        )

    def upload_file(self, local_file: Path, remote_file: str) -> None:
        with local_file.open("rb") as fh:
            response = self.session.put(self._url(remote_file), data=fh, timeout=self.timeout_seconds)
        if response.status_code not in {200, 201, 204}:
            raise RuntimeError(
                f"PUT failed for {remote_file}, status={response.status_code}, body={response.text[:200]}"
            )


def normalize_remote_root(remote_root: str) -> str:
    value = remote_root.strip()
    if not value:
        raise ValueError("webdav.remote_root is required")
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/") or "/"


def parse_date(value: str) -> datetime.date:
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def day_dir(root: Path, day: datetime.date) -> Path:
    return root / day.strftime("%Y") / day.strftime("%m") / day.strftime("%d")


def json_path(root: Path, day: datetime.date) -> Path:
    return day_dir(root, day) / f"{day.strftime('%Y-%m-%d')}.json"


def legacy_day_dir(root: Path, day: datetime.date) -> Path:
    return root / day.strftime("%Y-%m-%d")


def load_day_metadata(root: Path, day: datetime.date) -> dict:
    modern = json_path(root, day)
    if modern.exists():
        with modern.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    legacy = legacy_day_dir(root, day) / f"{day.strftime('%Y-%m-%d')}.json"
    if legacy.exists():
        with legacy.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    return {}


def extract_image_key(urlbase: str) -> str:
    if not urlbase:
        return ""
    match = IMAGE_KEY_RE.search(urlbase)
    if match:
        return match.group(1)
    return urlbase


def build_entries_for_day(root: Path, day: datetime.date) -> list[ImageEntry]:
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

    entries = []
    index = 0
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
        entries.append(
            ImageEntry(
                index=index,
                image_key=key,
                image_url=f"https://www.bing.com{urlbase}_UHD.jpg",
            )
        )
        index += 1

    return entries


def remote_year_dir(remote_root: str, day: datetime.date) -> str:
    return f"{remote_root}/{day.strftime('%Y')}"


def remote_file_path(remote_root: str, day: datetime.date, index: int) -> str:
    return f"{remote_root}/{day.strftime('%Y')}/{day.strftime('%m-%d')}_{index}.jpg"


def local_image_path(root: Path, day: datetime.date, index: int) -> Path:
    return day_dir(root, day) / f"{index}.jpg"


def download_image(image_url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(image_url, stream=True, timeout=30) as response:
        response.raise_for_status()
        with destination.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    fh.write(chunk)


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


def migrate_legacy_flat_dirs(root: Path, dry_run: bool) -> None:
    moved_files = 0
    removed_dirs = 0

    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        if not DATE_RE.fullmatch(candidate.name):
            continue

        try:
            day = parse_date(candidate.name)
        except ValueError:
            continue

        target_dir = day_dir(root, day)
        if candidate == target_dir:
            continue

        if dry_run:
            print(f"[DRY-RUN][MIGRATE] {candidate} -> {target_dir}")
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        for item in sorted(candidate.iterdir()):
            destination = target_dir / item.name
            if destination.exists():
                print(f"[MIGRATE][SKIP] destination exists: {destination}")
                continue
            shutil.move(str(item), str(destination))
            moved_files += 1

        try:
            candidate.rmdir()
            removed_dirs += 1
        except OSError:
            print(f"[MIGRATE][KEEP] non-empty legacy dir: {candidate}")

    if dry_run:
        print("[DRY-RUN][MIGRATE] completed")
    else:
        print(f"[MIGRATE] moved_files={moved_files}, removed_dirs={removed_dirs}")


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    local_cfg = data.get("local") or {}
    webdav_cfg = data.get("webdav") or {}
    download_cfg = data.get("download") or {}

    base_url = str(webdav_cfg.get("base_url", "")).strip()
    username = str(webdav_cfg.get("username", "")).strip()
    password = str(webdav_cfg.get("password", "")).strip()
    remote_root_raw = str(webdav_cfg.get("remote_root", "")).strip()

    missing = []
    if not base_url:
        missing.append("webdav.base_url")
    if not username:
        missing.append("webdav.username")
    if not password:
        missing.append("webdav.password")
    if not remote_root_raw:
        missing.append("webdav.remote_root")
    if missing:
        raise ValueError("Missing config keys: " + ", ".join(missing))

    sleep_min = float(download_cfg.get("sleep_min_seconds", 1.0))
    sleep_max = float(download_cfg.get("sleep_max_seconds", 2.0))
    if sleep_min < 0 or sleep_max < 0:
        raise ValueError("download sleep values must be non-negative")
    if sleep_min > sleep_max:
        raise ValueError("download.sleep_min_seconds cannot be greater than sleep_max_seconds")

    local_root = Path(str(local_cfg.get("root", DEFAULT_LOCAL_ROOT))).expanduser()

    return {
        "local_root": local_root,
        "webdav": {
            "base_url": base_url.rstrip("/"),
            "username": username,
            "password": password,
            "remote_root": normalize_remote_root(remote_root_raw),
        },
        "download": {
            "sleep_min_seconds": sleep_min,
            "sleep_max_seconds": sleep_max,
        },
    }


def resolve_dates(args: argparse.Namespace, root: Path) -> list[datetime.date]:
    if args.date:
        return [parse_date(args.date)]

    if args.from_date or args.to_date:
        if not args.from_date or not args.to_date:
            raise ValueError("--from and --to must be used together")
        start = parse_date(args.from_date)
        end = parse_date(args.to_date)
        if start > end:
            raise ValueError("--from cannot be later than --to")
        days = (end - start).days
        return [start + datetime.timedelta(days=offset) for offset in range(days + 1)]

    return discover_all_metadata_dates(root)


def process_day(
    root: Path,
    day: datetime.date,
    client: WebDavClient,
    remote_root: str,
    sleep_min_seconds: float,
    sleep_max_seconds: float,
    dry_run: bool,
) -> JobStats:
    stats = JobStats(days=1)

    metadata = load_day_metadata(root, day)
    if not metadata:
        print(f"[SKIP] missing metadata for {day.strftime('%Y-%m-%d')}")
        return stats

    entries = build_entries_for_day(root, day)
    stats.planned = len(entries)
    print(f"[DAY] {day.strftime('%Y-%m-%d')} planned={len(entries)}")

    for entry in entries:
        local_file = local_image_path(root, day, entry.index)
        remote_file = remote_file_path(remote_root, day, entry.index)

        try:
            remote_exists = client.exists(remote_file)
        except Exception as exc:
            stats.failures += 1
            print(f"[ERROR] check exists failed: {remote_file} ({exc})")
            continue

        if remote_exists:
            stats.remote_exists += 1
            if local_file.exists():
                if dry_run:
                    print(f"[DRY-RUN][CLEAN] would remove local: {local_file}")
                else:
                    local_file.unlink()
                    stats.removed_local += 1
                    print(f"[CLEAN] removed local: {local_file}")
            continue

        if dry_run:
            print(f"[DRY-RUN][MISSING] {remote_file} <- {entry.image_url}")
            continue

        wait_seconds = random.uniform(sleep_min_seconds, sleep_max_seconds)
        print(f"[WAIT] {wait_seconds:.2f}s before download index={entry.index}")
        time.sleep(wait_seconds)

        if not local_file.exists():
            try:
                download_image(entry.image_url, local_file)
                print(f"[DOWNLOAD] {entry.image_url} -> {local_file}")
            except Exception as exc:
                stats.failures += 1
                print(f"[ERROR] download failed: {entry.image_url} ({exc})")
                continue
        else:
            print(f"[CACHE] reuse local file: {local_file}")

        try:
            client.ensure_dir(remote_year_dir(remote_root, day))
            client.upload_file(local_file, remote_file)
            stats.uploaded += 1
            print(f"[UPLOAD] {local_file} -> {remote_file}")
        except Exception as exc:
            stats.failures += 1
            print(f"[ERROR] upload failed: {remote_file} ({exc})")
            continue

        try:
            local_file.unlink()
            stats.removed_local += 1
            print(f"[CLEAN] removed local after upload: {local_file}")
        except FileNotFoundError:
            pass

    return stats


def merge_stats(total: JobStats, delta: JobStats) -> JobStats:
    total.days += delta.days
    total.planned += delta.planned
    total.remote_exists += delta.remote_exists
    total.uploaded += delta.uploaded
    total.removed_local += delta.removed_local
    total.failures += delta.failures
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dl-img.py v2: migrate directories and sync missing images to WebDAV")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config.yaml")
    parser.add_argument("--date", help="Process one day (YYYY-MM-DD)")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Compute and print actions without side effects")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = load_config(Path(args.config))
    local_root = config["local_root"]
    local_root.mkdir(parents=True, exist_ok=True)

    migrate_legacy_flat_dirs(local_root, dry_run=args.dry_run)

    dates = resolve_dates(args, local_root)
    if not dates:
        print("[INFO] no metadata dates found")
        return 0

    webdav_cfg = config["webdav"]
    download_cfg = config["download"]

    client = WebDavClient(
        base_url=webdav_cfg["base_url"],
        username=webdav_cfg["username"],
        password=webdav_cfg["password"],
    )

    total = JobStats()
    for day in dates:
        day_stats = process_day(
            root=local_root,
            day=day,
            client=client,
            remote_root=webdav_cfg["remote_root"],
            sleep_min_seconds=download_cfg["sleep_min_seconds"],
            sleep_max_seconds=download_cfg["sleep_max_seconds"],
            dry_run=args.dry_run,
        )
        merge_stats(total, day_stats)

    print("[SUMMARY]")
    print(f"days={total.days}")
    print(f"planned={total.planned}")
    print(f"remote_exists={total.remote_exists}")
    print(f"uploaded={total.uploaded}")
    print(f"removed_local={total.removed_local}")
    print(f"failures={total.failures}")

    return 1 if total.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
