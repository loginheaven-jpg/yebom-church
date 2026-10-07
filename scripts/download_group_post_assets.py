#!/usr/bin/env python3
"""추출된 공개 그룹 게시물의 Wix Media 이미지를 로컬 public 자산으로 복사한다."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import threading
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "migration" / "extracted" / "group-posts.json"
DESTINATION = ROOT / "public" / "media" / "wix"
MANIFEST = ROOT / "migration" / "manifests" / "group-post-assets.json"
MARKER = "https://static.wixstatic.com/media/"


def filename_for(url: str) -> str:
    return unquote(url.split(MARKER, 1)[1].split('/v1/', 1)[0].split('?', 1)[0].rsplit('/', 1)[-1])


def download(url: str) -> dict:
    destination = DESTINATION / filename_for(url)
    try:
        if destination.exists() and destination.stat().st_size > 0:
            content = destination.read_bytes()
        else:
            response = requests.get(url, timeout=90)
            response.raise_for_status()
            content = response.content
            temporary = destination.with_suffix(destination.suffix + '.part')
            temporary.write_bytes(content)
            temporary.replace(destination)
        return {
            "sourceUrl": url,
            "localPath": f"/media/wix/{destination.name}",
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "status": "ok",
        }
    except Exception as error:
        return {"sourceUrl": url, "localPath": f"/media/wix/{destination.name}", "status": "error", "error": str(error)}


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    urls = sorted({image["url"] for post in data["posts"] for image in post.get("images", []) if image.get("url", "").startswith(MARKER)})
    DESTINATION.mkdir(parents=True, exist_ok=True)
    print(f"Copying {len(urls)} public group-post images to {DESTINATION.relative_to(ROOT)}", flush=True)
    completed = 0
    assets: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for asset in executor.map(download, urls):
            assets.append(asset)
            completed += 1
            if completed % 10 == 0 or completed == len(urls):
                failures = sum(item["status"] != "ok" for item in assets)
                print(f"Asset progress: {completed}/{len(urls)}; failures={failures}", flush=True)

    manifest = {
        "source": str(SOURCE.relative_to(ROOT)),
        "assetCount": len(assets),
        "successCount": sum(asset["status"] == "ok" for asset in assets),
        "failureCount": sum(asset["status"] != "ok" for asset in assets),
        "totalBytes": sum(asset.get("bytes", 0) for asset in assets),
        "assets": assets,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ["assetCount", "successCount", "failureCount", "totalBytes"]}, ensure_ascii=False), flush=True)
    if manifest["failureCount"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
