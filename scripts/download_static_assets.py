#!/usr/bin/env python3
"""정적 페이지 snapshot에 참조된 Wix Media 자산을 로컬 public 폴더와 매니페스트로 보존한다."""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "migration" / "manifests" / "static-snapshot.json"
DESTINATION = ROOT / "public" / "media" / "wix"
OUTPUT_MANIFEST = ROOT / "migration" / "manifests" / "static-assets.json"
MARKER = "https://static.wixstatic.com/media/"


def canonical(url: str) -> str | None:
    url = html.unescape(url).replace("\\/", "/")
    if MARKER not in url:
        return None
    suffix = url.split(MARKER, 1)[1].split("/v1/", 1)[0].split("?", 1)[0]
    if not suffix or suffix == "/":
        return None
    return f"{MARKER}{suffix}"


def destination_name(url: str) -> str:
    return unquote(url.rsplit("/", 1)[-1]).replace("/", "_")


def download(url: str) -> dict:
    output = DESTINATION / destination_name(url)
    try:
        if output.exists() and output.stat().st_size > 0:
            content = output.read_bytes()
        else:
            response = requests.get(url, timeout=90)
            response.raise_for_status()
            content = response.content
            output.write_bytes(content)
        return {
            "sourceUrl": url,
            "localPath": f"/media/wix/{output.name}",
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "status": "ok",
        }
    except Exception as error:
        return {"sourceUrl": url, "localPath": f"/media/wix/{output.name}", "status": "error", "error": str(error)}


def main() -> None:
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    urls = sorted({asset for entry in source["entries"] for raw in entry.get("wixAssetUrls", []) if (asset := canonical(raw))})
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        assets = list(executor.map(download, urls))
    manifest = {
        "sourceManifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "assetCount": len(assets),
        "successCount": sum(asset["status"] == "ok" for asset in assets),
        "failureCount": sum(asset["status"] != "ok" for asset in assets),
        "totalBytes": sum(asset.get("bytes", 0) for asset in assets),
        "assets": assets,
    }
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ["assetCount", "successCount", "failureCount", "totalBytes"]}, ensure_ascii=False))
    if manifest["failureCount"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
