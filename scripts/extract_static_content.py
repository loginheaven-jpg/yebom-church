#!/usr/bin/env python3
"""Wix 정적 페이지 snapshot에서 텍스트·이미지·링크의 재사용 가능한 콘텐츠 기준선을 추출한다."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "migration" / "manifests" / "static-snapshot.json"
OUTPUT_PATH = ROOT / "migration" / "extracted" / "static-pages.json"


def normalized_text(value: str) -> str:
    return " ".join(value.replace("\u200b", " ").split())


def normalized_asset_url(value: str) -> str:
    value = html.unescape(value).replace("\\/", "/")
    marker = "https://static.wixstatic.com/media/"
    if marker in value:
        identifier = value.split(marker, 1)[1].split("/v1/", 1)[0].split("?", 1)[0]
        return f"{marker}{identifier}"
    return value


def parse_page(entry: dict) -> dict:
    source = ROOT / entry["filename"]
    soup = BeautifulSoup(source.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    main = soup.select_one("#PAGES_CONTAINER") or soup
    blocks = []
    seen = set()
    for tag in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "img", "a"]):
        if tag.name == "img":
            src = tag.get("src", "")
            if not src or "wixstatic" not in src:
                continue
            block = {
                "type": "image",
                "src": normalized_asset_url(src),
                "alt": normalized_text(tag.get("alt", "")),
            }
        elif tag.name == "a":
            href = tag.get("href", "")
            text = normalized_text(tag.get_text(" ", strip=True))
            if not text or not href:
                continue
            block = {"type": "link", "text": text, "href": html.unescape(href)}
        else:
            text = normalized_text(tag.get_text(" ", strip=True))
            if not text:
                continue
            block = {"type": tag.name, "text": text}

        fingerprint = json.dumps(block, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        blocks.append(block)

    video_urls = sorted(
        {
            match.replace("\\/", "/")
            for match in re.findall(r"https?:\\?/\\?/(?:www\\.)?(?:youtube\\.com|youtu\\.be|vimeo\\.com)[^\"'\\\s<]+", source.read_text(encoding="utf-8"))
        }
    )

    return {
        "url": entry["url"],
        "sourceSnapshot": entry["filename"],
        "characters": len(normalized_text(main.get_text(" ", strip=True))),
        "blocks": blocks,
        "externalVideos": video_urls,
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pages = [parse_page(entry) for entry in manifest["entries"] if entry["status"] == "ok"]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "generatedFrom": str(MANIFEST_PATH.relative_to(ROOT)),
                "sourceOrigin": manifest["origin"],
                "pageCount": len(pages),
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(pages)} pages to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
