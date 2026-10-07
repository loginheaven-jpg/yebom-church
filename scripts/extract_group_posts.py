#!/usr/bin/env python3
"""Wix Groups SSR snapshot에서 공개 게시물 원문과 Ricos 구조를 추출한다.

개인 프로필, 댓글, 반응, 조회수는 출력하지 않는다. 게시물 본문과 공개 첨부·영상만 보존한다.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "migration" / "manifests" / "group-posts-snapshot.json"
OUTPUT_PATH = ROOT / "migration" / "extracted" / "group-posts.json"
SUMMARY_PATH = ROOT / "migration" / "extracted" / "group-posts-summary.json"


def balanced_json_object(source: str, start: int) -> str:
    """`start` 위치의 `{`부터 JSON 객체 끝까지, 문자열 escape를 고려해 자른다."""
    if source[start] != "{":
        raise ValueError("JSON object must begin with '{'")
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError("Unterminated JSON object")


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200b", " ")).strip()


def feed_item_from_snapshot(html: str, legacy_id: str) -> dict:
    marker = f'"feedItem":{{"feedItemId":"{legacy_id}","entity":'
    marker_start = html.find(marker)
    if marker_start < 0:
        raise ValueError(f"feedItem marker not found for {legacy_id}")
    start = marker_start + len('"feedItem":')
    return json.loads(balanced_json_object(html, start))


def walk_nodes(node: object, paragraphs: list[str], videos: list[dict], images: list[dict]) -> str:
    if not isinstance(node, dict):
        return ""
    node_type = node.get("type", "")
    children = node.get("nodes", [])
    child_text = "".join(walk_nodes(child, paragraphs, videos, images) for child in children)

    if node_type == "TEXT":
        return node.get("textData", {}).get("text", "")

    if node_type == "VIDEO":
        data = node.get("videoData", {})
        video = data.get("video", {})
        source = video.get("src", {}).get("url", "")
        thumbnail = data.get("thumbnail", {}).get("src", {}).get("url", "")
        if source:
            videos.append({
                "url": source,
                "thumbnail": thumbnail,
                "title": data.get("title", ""),
                "duration": video.get("duration"),
            })
        return ""

    if node_type == "IMAGE":
        data = node.get("imageData", {})
        image = data.get("image", {})
        source = image.get("src", {}).get("url") or image.get("src", {}).get("id") or ""
        if source and not source.startswith(("http://", "https://")):
            source = f"https://static.wixstatic.com/media/{source}"
        if source:
            images.append({"url": source, "alt": data.get("altText", "")})
        return ""

    if node_type in {"PARAGRAPH", "HEADING", "LIST_ITEM", "BLOCKQUOTE"}:
        text = normalized_text(child_text)
        if text:
            paragraphs.append(text)
        return ""

    return child_text


def parse_rich_content(value: str) -> tuple[list[str], list[dict], list[dict], dict]:
    if not value:
        return [], [], [], {}
    rich = json.loads(value)
    paragraphs: list[str] = []
    videos: list[dict] = []
    images: list[dict] = []
    for node in rich.get("nodes", []):
        remaining = normalized_text(walk_nodes(node, paragraphs, videos, images))
        if remaining:
            paragraphs.append(remaining)
    return paragraphs, videos, images, rich


def extract_entry(entry: dict) -> dict:
    source_path = ROOT / entry["filename"]
    html = source_path.read_text(encoding="utf-8")
    legacy_id = entry["url"].rstrip("/").split("/")[-1]
    feed_item = feed_item_from_snapshot(html, legacy_id)
    entity = feed_item.get("entity", {})
    body = entity.get("body", {})
    paragraphs, videos, images, rich = parse_rich_content(body.get("content", ""))
    parsed_url = urlparse(entry["url"])
    segments = parsed_url.path.strip("/").split("/")
    group_slug = segments[1] if len(segments) >= 2 and segments[0] == "group" else "unknown"

    attachments = []
    for attachment in body.get("attachments", []):
        uri = attachment.get("uri")
        if uri:
            attachments.append({"url": uri, "mediaType": attachment.get("mediaType", "")})

    return {
        "legacyId": legacy_id,
        "legacyUrl": entry["url"],
        "groupSlug": group_slug,
        "title": entity.get("title") or "제목 없음",
        "publishedAt": feed_item.get("createdAt"),
        "updatedAt": feed_item.get("updatedAt"),
        "bodyText": paragraphs or [normalized_text(body.get("rawText", ""))],
        "videos": videos,
        "images": images,
        "attachments": attachments,
        "richContent": rich,
        "sourceSnapshot": entry["filename"],
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    posts, failures = [], []
    for entry in manifest["entries"]:
        if entry["status"] != "ok":
            failures.append({"url": entry["url"], "error": entry.get("error", "snapshot failure")})
            continue
        try:
            posts.append(extract_entry(entry))
        except Exception as error:  # 통계/매니페스트에서 실패를 명시적으로 유지한다.
            failures.append({"url": entry["url"], "error": str(error), "sourceSnapshot": entry["filename"]})

    posts.sort(key=lambda post: (post["publishedAt"] or "", post["legacyId"]), reverse=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({"postCount": len(posts), "posts": posts, "failures": failures}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "snapshotManifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "expectedSnapshotCount": manifest["snapshottedUrlCount"],
        "postCount": len(posts),
        "failureCount": len(failures),
        "groups": dict(sorted(Counter(post["groupSlug"] for post in posts).items())),
        "videoPostCount": sum(bool(post["videos"]) for post in posts),
        "imagePostCount": sum(bool(post["images"]) for post in posts),
        "attachmentPostCount": sum(bool(post["attachments"]) for post in posts),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
