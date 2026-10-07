#!/usr/bin/env python3
"""기존 raw snapshot을 건너뛰고 누락된 Wix Groups 게시물만 재수집한다.

Node 일괄 수집이 중단된 경우에 사용한다. HTML 본문을 메모리에 누적하지 않고,
URL별로 즉시 디스크에 기록해 대량 게시물 이관에서도 메모리 사용량을 제한한다.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = "https://www.yebom.org/group-posts-sitemap.xml"
RAW = ROOT / "migration" / "raw" / "group-posts"
MANIFEST = ROOT / "migration" / "manifests" / "group-posts-snapshot.json"


def locations(xml: str) -> list[str]:
    return [value.strip().replace("&amp;", "&") for value in re.findall(r"<loc>([\s\S]*?)</loc>", xml, re.I) if value.strip().startswith("https://")]


def filename_for(url: str, index: int) -> str:
    path = re.sub(r"^https?://[^/]+", "", url).strip("/") or "home"
    readable = re.sub(r"[^\w._-]+", "_", path, flags=re.UNICODE)
    readable = re.sub(r"_+", "_", readable)[:140] or "home"
    return f"{index + 1:04d}-{readable}.html"


def fetch_missing(item: tuple[int, str, Path]) -> tuple[int, str, Path, str | None]:
    index, url, destination = item
    for attempt in range(3):
        try:
            response = requests.get(url, headers={"User-Agent": "YebomChurchMigrationAudit/1.0"}, timeout=70)
            response.raise_for_status()
            temporary = destination.with_suffix(".part")
            temporary.write_bytes(response.content)
            temporary.replace(destination)
            return index, url, destination, None
        except Exception as error:
            if attempt == 2:
                return index, url, destination, str(error)
            time.sleep(1.5 * (attempt + 1))
    return index, url, destination, "unexpected retry state"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    xml = requests.get(SITEMAP, timeout=45).text
    urls = locations(xml)
    expected = [(index, url, RAW / filename_for(url, index)) for index, url in enumerate(urls)]
    missing = [item for item in expected if not item[2].exists() or item[2].stat().st_size == 0]
    print(f"Discovered {len(urls)} URLs; cached {len(expected) - len(missing)}; fetching {len(missing)} missing URLs.", flush=True)

    failures: dict[int, str] = {}
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for index, url, destination, error in executor.map(fetch_missing, missing):
            completed += 1
            if error:
                failures[index] = error
                print(f"FAIL {index + 1}/{len(urls)} {url}: {error}", flush=True)
            if completed % 5 == 0 or completed == len(missing):
                print(f"Recovery progress: {completed}/{len(missing)} missing URLs processed; failures={len(failures)}", flush=True)

    entries = []
    for index, url, destination in expected:
        if destination.exists() and destination.stat().st_size > 0:
            entries.append({"url": url, "filename": str(destination.relative_to(ROOT)), "bytes": destination.stat().st_size, "status": "ok"})
        else:
            entries.append({"url": url, "filename": str(destination.relative_to(ROOT)), "status": "error", "error": failures.get(index, "missing snapshot")})

    manifest = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "origin": "https://www.yebom.org",
        "scope": "group-posts",
        "sitemapUrl": SITEMAP,
        "sitemapUrlCount": len(urls),
        "snapshottedUrlCount": len(urls),
        "successCount": sum(entry["status"] == "ok" for entry in entries),
        "failureCount": sum(entry["status"] == "error" for entry in entries),
        "entries": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ["sitemapUrlCount", "successCount", "failureCount"]}, ensure_ascii=False), flush=True)
    if manifest["failureCount"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
