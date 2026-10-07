#!/usr/bin/env python3
"""Capture public Wix page network requests through Chrome DevTools Protocol."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
import websocket

DEBUG_PORT = 9223
TARGET_URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.yebom.org/file-share"
OUT_DIR = Path("migration/logs")
OUT_JSON = OUT_DIR / "fileshare-network.json"
OUT_URLS = OUT_DIR / "fileshare-network-urls.txt"


def create_target() -> dict:
    response = requests.put(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{quote('about:blank', safe='')}", timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = create_target()
    ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=2, origin="http://localhost")
    sequence = 0

    def send(method: str, params: dict | None = None) -> int:
        nonlocal sequence
        sequence += 1
        payload = {"id": sequence, "method": method}
        if params:
            payload["params"] = params
        ws.send(json.dumps(payload))
        return sequence

    send("Network.enable", {"maxTotalBufferSize": 10_000_000, "maxResourceBufferSize": 1_000_000})
    send("Page.enable")
    send("Page.navigate", {"url": TARGET_URL})

    requests_by_id: dict[str, dict] = {}
    body_commands: dict[int, dict] = {}
    scroll_sent = False
    scroll_at = time.monotonic() + 8
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if not scroll_sent and time.monotonic() >= scroll_at:
            send("Runtime.evaluate", {"expression": "window.scrollTo(0, document.documentElement.scrollHeight);"})
            scroll_sent = True
        try:
            event = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            continue
        if event.get("id") in body_commands:
            target = body_commands[event["id"]]
            result = event.get("result", {})
            if "body" in result:
                target["responseBody"] = result["body"]
            continue
        method = event.get("method")
        params = event.get("params", {})
        if method == "Network.requestWillBeSent":
            request = params.get("request", {})
            request_id = params.get("requestId")
            requests_by_id[request_id] = {
                "url": request.get("url"),
                "method": request.get("method"),
                "resourceType": params.get("type"),
                "initiator": params.get("initiator", {}).get("type"),
                "requestHeaders": request.get("headers", {}),
            }
        elif method == "Network.responseReceived":
            item = requests_by_id.get(params.get("requestId"))
            if item is not None:
                response = params.get("response", {})
                item.update({
                    "status": response.get("status"),
                    "mimeType": response.get("mimeType"),
                    "responseHeaders": response.get("headers", {}),
                })
                if "/api/v1/file-sharing/" in item.get("url", ""):
                    command_id = send("Network.getResponseBody", {"requestId": params.get("requestId")})
                    body_commands[command_id] = item

    ws.close()
    try:
        requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/close/{target['id']}", timeout=5)
    except requests.RequestException:
        pass

    captured = sorted(requests_by_id.values(), key=lambda item: item.get("url") or "")
    OUT_JSON.write_text(json.dumps({"target": TARGET_URL, "requestCount": len(captured), "requests": captured}, ensure_ascii=False, indent=2), encoding="utf-8")
    urls = sorted({item["url"] for item in captured if item.get("url")})
    OUT_URLS.write_text("\n".join(urls) + "\n", encoding="utf-8")

    candidates = [url for url in urls if any(token in url.lower() for token in ("wixapis", "file", "share", "media"))]
    print(f"Captured {len(captured)} requests and {len(urls)} unique URLs")
    print("Candidate data endpoints:")
    for url in candidates:
        print(url)


if __name__ == "__main__":
    main()
