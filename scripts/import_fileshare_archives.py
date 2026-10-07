#!/usr/bin/env python3
"""Extract exported Wix File Share archives into public downloads and build a safe manifest."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "migration/raw/fileshare-archives"
STAGING_DIR = ROOT / "migration/raw/fileshare-unpacked"
DOWNLOAD_DIR = ROOT / "public/downloads/bulletins"
DATA_PATH = ROOT / "src/data/fileshare.json"
MANIFEST_PATH = ROOT / "migration/manifests/fileshare-assets.json"
R2_CONFIG_PATH = ROOT / "migration/r2-public-assets.json"
EXPECTED_COUNT = 335
EXPECTED_SOURCE_BYTES = 278_987_806


def safe_filename(name: str, existing: set[str]) -> str:
    name = Path(name).name.replace("\x00", "").strip()
    if not name or name in {".", ".."}:
        raise ValueError(f"Invalid ZIP entry filename: {name!r}")
    candidate = name
    stem = Path(name).stem
    suffix = Path(name).suffix
    number = 2
    while candidate in existing:
        candidate = f"{stem} ({number}){suffix}"
        number += 1
    existing.add(candidate)
    return candidate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def year_for(filename: str) -> str:
    match = re.search(r"(?:19|20)\d{2}", filename)
    return match.group(0) if match else "기타"


def load_r2_assets() -> dict[str, dict]:
    if not R2_CONFIG_PATH.is_file():
        return {}
    config = json.loads(R2_CONFIG_PATH.read_text(encoding="utf-8"))
    assets = config.get("assets", {})
    for filename, asset in assets.items():
        if not isinstance(asset.get("url"), str) or not asset["url"].startswith("https://"):
            raise SystemExit(f"R2 asset {filename!r} has no usable public URL")
        if not isinstance(asset.get("size"), int) or not isinstance(asset.get("sha256"), str):
            raise SystemExit(f"R2 asset {filename!r} requires verified size and SHA-256")
    return assets


def main() -> None:
    archives = sorted(ARCHIVE_DIR.glob("*.zip"))
    if len(archives) != 2:
        raise SystemExit(f"Expected two source archives, found {len(archives)} in {ARCHIVE_DIR}")

    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    r2_assets = load_r2_assets()
    existing: set[str] = set()
    files: list[dict] = []
    for archive in archives:
        archive_stage = STAGING_DIR / archive.stem
        archive_stage.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zip_file:
            for item in zip_file.infolist():
                if item.is_dir():
                    continue
                filename = safe_filename(item.filename, existing)
                staged = archive_stage / filename
                with zip_file.open(item) as source, staged.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                source_size = staged.stat().st_size
                source_sha256 = sha256(staged)
                r2_asset = r2_assets.get(filename)
                if r2_asset:
                    if source_size != r2_asset["size"] or source_sha256 != r2_asset["sha256"]:
                        raise SystemExit(f"R2 source verification failed for {filename}")
                    delivery_path = r2_asset["url"]
                    hosting = "cloudflare-r2"
                    object_key = r2_asset.get("objectKey")
                else:
                    target = DOWNLOAD_DIR / filename
                    shutil.copy2(staged, target)
                    delivery_path = f"/downloads/bulletins/{quote(filename)}"
                    hosting = "cloudflare-pages"
                    object_key = None
                files.append({
                    "name": filename,
                    "path": delivery_path,
                    "size": source_size,
                    "extension": staged.suffix.lower().removeprefix(".") or "file",
                    "year": year_for(filename),
                    "sha256": source_sha256,
                    "sourceArchive": archive.name,
                    "hosting": hosting,
                    "objectKey": object_key,
                })

    files.sort(key=lambda item: item["name"], reverse=True)
    total_bytes = sum(item["size"] for item in files)
    if len(files) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} files, extracted {len(files)}")
    if total_bytes != EXPECTED_SOURCE_BYTES:
        raise SystemExit(f"Expected {EXPECTED_SOURCE_BYTES} bytes, extracted {total_bytes}")

    by_year = Counter(item["year"] for item in files)
    app_data = {
        "title": "예봄 자료실",
        "folder": "예봄주보",
        "source": "Wix File Share",
        "fileCount": len(files),
        "totalBytes": total_bytes,
        "years": dict(sorted(by_year.items(), reverse=True)),
        "files": [{key: value for key, value in item.items() if key not in {"sha256", "sourceArchive", "objectKey"}} for item in files],
    }
    manifest = {
        "source": "Wix File Share archive export",
        "archiveFiles": [{"name": archive.name, "sha256": sha256(archive), "size": archive.stat().st_size} for archive in archives],
        "fileCount": len(files),
        "totalBytes": total_bytes,
        "files": files,
    }
    DATA_PATH.write_text(json.dumps(app_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fileCount": len(files), "totalBytes": total_bytes, "years": app_data["years"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
