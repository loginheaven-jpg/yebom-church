#!/usr/bin/env python3
"""추출된 공개 Wix Groups 게시물을 Git 관리용 Markdown 파일로 생성한다.

Ricos 원본 JSON은 migration/extracted/group-posts.json에 보존하고,
Markdown은 일반 텍스트·이미지·영상 링크를 사람이 수정하기 쉬운 형태로 제공한다.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "migration" / "extracted" / "group-posts.json"
DESTINATION = ROOT / "src" / "content" / "posts"
MANIFEST = ROOT / "migration" / "manifests" / "post-markdown.json"


def quoted(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def markdown_for(post: dict) -> str:
    frontmatter = [
        "---",
        f"title: {quoted(post['title'])}",
        f"legacyId: {quoted(post['legacyId'])}",
        f"group: {quoted(post['groupSlug'])}",
        f"publishedAt: {quoted(post.get('publishedAt'))}",
        f"updatedAt: {quoted(post.get('updatedAt'))}",
        f"legacyUrl: {quoted(post['legacyUrl'])}",
        f"videos: {quoted(post.get('videos', []))}",
        f"images: {quoted(post.get('images', []))}",
        f"attachments: {quoted(post.get('attachments', []))}",
        "---",
        "",
    ]
    body: list[str] = []
    for paragraph in post.get("bodyText", []):
        paragraph = paragraph.strip()
        if paragraph:
            body.extend([paragraph, ""])
    for image in post.get("images", []):
        if image.get("url"):
            body.extend([f"![{image.get('alt', '')}]({image['url']})", ""])
    for video in post.get("videos", []):
        if video.get("url"):
            label = video.get("title") or "영상 보기"
            body.extend([f"[{label}]({video['url']})", ""])
    for attachment in post.get("attachments", []):
        if attachment.get("url"):
            body.extend([f"[첨부 파일]({attachment['url']})", ""])
    return "\n".join(frontmatter + body).rstrip() + "\n"


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    files = []
    for post in source["posts"]:
        directory = DESTINATION / post["groupSlug"]
        directory.mkdir(parents=True, exist_ok=True)
        file = directory / f"{post['legacyId']}.md"
        file.write_text(markdown_for(post), encoding="utf-8")
        files.append(str(file.relative_to(ROOT)))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"source": str(SOURCE.relative_to(ROOT)), "postCount": len(files), "files": files}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(files)} Markdown posts in {DESTINATION.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
