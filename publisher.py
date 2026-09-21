from __future__ import annotations

import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

X_POSTS = re.compile(r"<!-- X_START -->\s*(.*?)\s*<!-- X_END -->", re.DOTALL)


def extract_x_posts(markdown: str) -> list[str]:
    match = X_POSTS.search(markdown)
    if not match:
        raise ValueError("草稿缺少 X_START/X_END 发布标记，请先重新生成或修改草稿")
    posts = [part.strip() for part in match.group(1).split("---THREAD---")]
    if not all(posts) or len(posts) > 6:
        raise ValueError("X thread 必须包含 1-6 条非空帖子")
    too_long = [index for index, text in enumerate(posts, 1) if len(text) > 280]
    if too_long:
        raise ValueError(f"X 帖子超过 280 字符：{too_long}")
    return posts


def create_x_post(text: str, token: str, reply_to: str | None = None) -> str:
    payload: dict[str, object] = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    request = Request(
        "https://api.x.com/2/tweets",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        detail = error.read().decode(errors="replace")[:500]
        raise RuntimeError(f"X API 发布失败（HTTP {error.code}）：{detail}") from error
    try:
        return str(result["data"]["id"])
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"X API 返回了无法识别的结果：{result}") from error


def publish_x_thread(posts: list[str], token: str) -> list[str]:
    ids: list[str] = []
    for post in posts:
        ids.append(create_x_post(post, token, ids[-1] if ids else None))
    return ids
