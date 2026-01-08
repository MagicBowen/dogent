from __future__ import annotations

import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool

from .. import __version__

DOGENT_WEB_ALLOWED_TOOLS = ["mcp__dogent__web_search", "mcp__dogent__web_fetch"]
DOGENT_WEB_TOOL_DISPLAY_NAMES = {
    "mcp__dogent__web_search": "dogent_web_search",
    "mcp__dogent__web_fetch": "dogent_web_fetch",
}


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes


def _http_get(url: str, *, headers: dict[str, str], timeout_s: float) -> HttpResponse:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        status = getattr(resp, "status", None)
        if status is None:
            status = int(resp.getcode())
        headers_out = {k: v for k, v in resp.headers.items()}
        body = resp.read()
        return HttpResponse(url=resp.geturl(), status=status, headers=headers_out, body=body)


def _default_user_agent(web_profile_cfg: dict[str, Any]) -> str:
    configured = str(web_profile_cfg.get("user_agent") or "").strip()
    if not configured:
        return f"dogent/{__version__}"
    lowered = configured.lower()
    if lowered in {"dogent", "replace-me"}:
        return f"dogent/{__version__}"
    if lowered.startswith("dogent/") and lowered.split("/", 1)[1].strip() == "":
        return f"dogent/{__version__}"
    return configured


def _sanitize_filename(name: str) -> str:
    trimmed = name.strip().replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", trimmed)
    cleaned = cleaned.strip("._")
    return cleaned or "asset"


def _resolve_output_dir(root: Path, output_dir: str) -> Path:
    """Resolve a workspace-relative output directory, preventing traversal outside root."""
    raw = str(output_dir or "").strip()
    if not raw:
        raise ValueError("Missing required field: output_dir")
    path = Path(raw)
    if path.is_absolute():
        raise ValueError("output_dir must be a workspace-relative path (not absolute).")
    root_resolved = root.resolve()
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root_resolved)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("output_dir must stay within the workspace.") from exc
    return resolved


def _readable_output_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "nav", "footer", "header", "aside", "form"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "nav", "footer", "header", "aside", "form"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"p", "div", "li", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._skip_depth:
            return
        text = unescape(data)
        if text.strip():
            self._chunks.append(text)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def extract_text_from_html(html: str) -> str:
    parser = _HtmlTextExtractor()
    parser.feed(html)
    return parser.get_text()


def parse_google_cse_results(payload: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    items = payload.get("items") or []
    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if mode == "image":
            image = item.get("image") if isinstance(item.get("image"), dict) else {}
            results.append(
                {
                    "title": item.get("title") or "",
                    "image_url": item.get("link") or "",
                    "page_url": image.get("contextLink") or "",
                    "thumbnail_url": image.get("thumbnailLink") or "",
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
            )
        else:
            results.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("link") or "",
                    "snippet": item.get("snippet") or "",
                }
            )
    return results


def parse_bing_results(payload: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if mode == "image":
        items = (payload.get("value") or []) if isinstance(payload.get("value"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": item.get("name") or "",
                    "image_url": item.get("contentUrl") or "",
                    "page_url": item.get("hostPageUrl") or "",
                    "thumbnail_url": item.get("thumbnailUrl") or "",
                    "width": item.get("width"),
                    "height": item.get("height"),
                }
            )
        return results

    web_pages = payload.get("webPages") if isinstance(payload.get("webPages"), dict) else {}
    items = (web_pages.get("value") or []) if isinstance(web_pages.get("value"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("name") or "",
                "url": item.get("url") or "",
                "snippet": item.get("snippet") or "",
            }
        )
    return results


def parse_brave_results(payload: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if mode == "image":
        images = payload.get("images") if isinstance(payload.get("images"), dict) else {}
        items = (images.get("results") or []) if isinstance(images.get("results"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": item.get("title") or item.get("name") or "",
                    "image_url": item.get("url") or item.get("image") or "",
                    "page_url": item.get("page_url") or item.get("source") or item.get("source_url") or "",
                    "thumbnail_url": item.get("thumbnail") or item.get("thumbnail_url") or "",
                    "width": item.get("width"),
                    "height": item.get("height"),
                }
            )
        return results

    web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
    items = (web.get("results") or []) if isinstance(web.get("results"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title") or item.get("name") or "",
                "url": item.get("url") or "",
                "snippet": item.get("description") or item.get("snippet") or "",
            }
        )
    return results


def create_dogent_web_tools(
    *,
    root: Path,
    web_profile_name: Optional[str],
    web_profile_cfg: dict[str, Any],
    http_get: Callable[[str, dict[str, str], float], HttpResponse] | None = None,
) -> list[SdkMcpTool[Any]]:
    def _adapter(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
        return _http_get(url, headers=headers, timeout_s=timeout_s)

    http_get = http_get or _adapter

    web_search_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query text"},
            "mode": {"type": "string", "description": "web or image", "default": "web"},
            "num_results": {"type": "integer", "description": "1-10", "default": 5},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    web_fetch_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s) URL to fetch"},
            "mode": {"type": "string", "description": "auto, text, or image", "default": "auto"},
            "max_chars": {"type": "integer", "description": "Max returned text chars", "default": 12000},
            "output_dir": {
                "type": "string",
                "description": "Workspace-relative directory to save images (required for image downloads).",
            },
            "filename": {"type": "string", "description": "Optional filename when downloading an image"},
        },
        "required": ["url"],
        "additionalProperties": False,
    }

    @tool(
        "web_search",
        "Search the web (and images) via a user-configured search API in ~/.dogent/dogent.json",
        web_search_schema,
    )
    async def web_search(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query") or "").strip()
        mode = str(args.get("mode") or "web").strip().lower()
        num_results = int(args.get("num_results") or 5)
        num_results = max(1, min(num_results, 10))

        if not query:
            return {
                "content": [{"type": "text", "text": "Missing required field: query"}],
                "is_error": True,
            }
        if mode not in {"web", "image"}:
            return {
                "content": [{"type": "text", "text": "mode must be 'web' or 'image'"}],
                "is_error": True,
            }
        if not web_profile_name:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "No web_profile configured. Set 'web_profile' in .dogent/dogent.json and configure "
                            "~/.dogent/dogent.json (web_profiles)."
                        ),
                    }
                ],
                "is_error": True,
            }
        provider = str(web_profile_cfg.get("provider") or "").strip().lower()
        if not provider:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Web profile '{web_profile_name}' is missing 'provider' in ~/.dogent/dogent.json (web_profiles).",
                    }
                ],
                "is_error": True,
            }

        timeout_s = float(web_profile_cfg.get("timeout_s") or 20)
        user_agent = _default_user_agent(web_profile_cfg)
        headers = {"User-Agent": user_agent}

        try:
            if provider in {"google", "google_cse"}:
                api_key = str(web_profile_cfg.get("api_key") or "").strip()
                cse_id = str(web_profile_cfg.get("cse_id") or web_profile_cfg.get("cx") or "").strip()
                if not api_key or "replace" in api_key.lower() or not cse_id or "replace" in cse_id.lower():
                    raise ValueError(
                        f"Web profile '{web_profile_name}' requires api_key and cse_id (Google Custom Search)."
                    )
                params = {"key": api_key, "cx": cse_id, "q": query, "num": str(num_results)}
                if mode == "image":
                    params["searchType"] = "image"
                url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
                resp = http_get(url, headers, timeout_s)
                if resp.status >= 400:
                    raise ValueError(f"HTTP {resp.status} from Google Custom Search API")
                payload = json.loads(resp.body.decode("utf-8", errors="replace"))
                results = parse_google_cse_results(payload, mode=mode)
            elif provider == "bing":
                api_key = str(web_profile_cfg.get("api_key") or web_profile_cfg.get("subscription_key") or "").strip()
                if not api_key or "replace" in api_key.lower():
                    raise ValueError(
                        f"Web profile '{web_profile_name}' requires api_key (Bing Search v7)."
                    )
                endpoint = str(web_profile_cfg.get("endpoint") or "https://api.bing.microsoft.com/v7.0").rstrip("/")
                path = "/images/search" if mode == "image" else "/search"
                url = endpoint + path + "?" + urlencode({"q": query, "count": str(num_results)})
                headers = {"User-Agent": user_agent, "Ocp-Apim-Subscription-Key": api_key}
                resp = http_get(url, headers, timeout_s)
                if resp.status >= 400:
                    raise ValueError(f"HTTP {resp.status} from Bing Search API")
                payload = json.loads(resp.body.decode("utf-8", errors="replace"))
                results = parse_bing_results(payload, mode=mode)
            elif provider == "brave":
                api_key = str(web_profile_cfg.get("api_key") or web_profile_cfg.get("token") or "").strip()
                if not api_key or "replace" in api_key.lower():
                    raise ValueError(
                        f"Web profile '{web_profile_name}' requires api_key (Brave Search API)."
                    )
                endpoint = str(web_profile_cfg.get("endpoint") or "https://api.search.brave.com/res/v1").rstrip("/")
                path = "/images/search" if mode == "image" else "/web/search"
                url = endpoint + path + "?" + urlencode({"q": query, "count": str(num_results)})
                headers = {"User-Agent": user_agent, "X-Subscription-Token": api_key}
                resp = http_get(url, headers, timeout_s)
                if resp.status >= 400:
                    raise ValueError(f"HTTP {resp.status} from Brave Search API")
                payload = json.loads(resp.body.decode("utf-8", errors="replace"))
                results = parse_brave_results(payload, mode=mode)
            else:
                raise ValueError(
                    f"Unsupported provider '{provider}'. Use 'google_cse', 'bing', or 'brave'."
                )
        except Exception as exc:  # noqa: BLE001
            return {
                "content": [{"type": "text", "text": f"WebSearch failed: {exc}"}],
                "is_error": True,
            }

        output = {
            "query": query,
            "mode": mode,
            "provider": provider,
            "profile": web_profile_name,
            "results": results,
        }
        return {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}]}

    @tool(
        "web_fetch",
        "Fetch a URL. Extract readable text for HTML, or download images into output_dir and return a Markdown link.",
        web_fetch_schema,
    )
    async def web_fetch(args: dict[str, Any]) -> dict[str, Any]:
        url = str(args.get("url") or "").strip()
        mode = str(args.get("mode") or "auto").strip().lower()
        max_chars = int(args.get("max_chars") or 12000)
        output_dir = str(args.get("output_dir") or "").strip()
        filename = str(args.get("filename") or "").strip()

        if not url:
            return {"content": [{"type": "text", "text": "Missing required field: url"}], "is_error": True}
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {
                "content": [{"type": "text", "text": "Only http/https URLs are supported."}],
                "is_error": True,
            }
        if mode not in {"auto", "text", "image"}:
            return {"content": [{"type": "text", "text": "mode must be auto, text, or image"}], "is_error": True}

        timeout_s = float(web_profile_cfg.get("timeout_s") or 25)
        user_agent = _default_user_agent(web_profile_cfg)
        headers = {"User-Agent": user_agent, "Accept": "*/*"}

        try:
            resp = http_get(url, headers, timeout_s)
        except Exception as exc:  # noqa: BLE001
            return {"content": [{"type": "text", "text": f"WebFetch failed: {exc}"}], "is_error": True}
        if resp.status >= 400:
            return {
                "content": [{"type": "text", "text": f"WebFetch failed: HTTP {resp.status}"}],
                "is_error": True,
            }

        content_type = str(resp.headers.get("Content-Type") or "").lower()
        body = resp.body
        if str(resp.headers.get("Content-Encoding") or "").lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except Exception:
                body = resp.body

        is_image = content_type.startswith("image/")
        if mode == "image" or (mode == "auto" and is_image):
            try:
                out_dir = _resolve_output_dir(root, output_dir)
            except ValueError as exc:
                return {"content": [{"type": "text", "text": str(exc)}], "is_error": True}
            out_dir.mkdir(parents=True, exist_ok=True)

            ext = ""
            if content_type.startswith("image/"):
                ext = content_type.split("image/", 1)[1].split(";", 1)[0].strip()
            ext_map = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp", "svg+xml": ".svg"}
            suffix = ext_map.get(ext, f".{ext}" if ext and "+" not in ext else ".img")

            if filename:
                base = _sanitize_filename(filename)
            else:
                base = _sanitize_filename(Path(urlparse(resp.url).path).name)
            if not base or base == "asset":
                url_hash = hashlib.sha1(resp.url.encode("utf-8")).hexdigest()[:10]  # noqa: S324
                base = f"image_{url_hash}"
            if not base.lower().endswith(suffix.lower()):
                base = base + suffix
            target = out_dir / base
            if target.exists():
                url_hash = hashlib.sha1(resp.url.encode("utf-8")).hexdigest()[:10]  # noqa: S324
                target = out_dir / f"{target.stem}_{url_hash}{target.suffix}"
            target.write_bytes(body)

            display_path = _readable_output_path(root, target)
            markdown = f"![image]({display_path})"
            text = "\n".join(
                [
                    f"Saved image to: {display_path}",
                    f"Source URL: {resp.url}",
                    f"Markdown: {markdown}",
                ]
            )
            return {"content": [{"type": "text", "text": text}]}

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"
        decoded = body.decode(charset, errors="replace")

        title = ""
        match = re.search(r"<title[^>]*>(.*?)</title>", decoded, re.IGNORECASE | re.DOTALL)
        if match:
            title = unescape(re.sub(r"\s+", " ", match.group(1)).strip())
        if "text/html" in content_type or "<html" in decoded.lower():
            extracted = extract_text_from_html(decoded)
        else:
            extracted = re.sub(r"\s+\n", "\n", decoded).strip()

        truncated = False
        if max_chars > 0 and len(extracted) > max_chars:
            extracted = extracted[:max_chars].rstrip() + "\n\n[Truncated]"
            truncated = True

        lines = [f"URL: {resp.url}"]
        if title:
            lines.append(f"Title: {title}")
        if content_type:
            lines.append(f"Content-Type: {content_type}")
        if truncated:
            lines.append("Note: content was truncated.")
        lines.append("")
        lines.append(extracted or "(no readable text extracted)")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    return [web_search, web_fetch]


def create_dogent_web_mcp_server(
    *,
    root: Path,
    web_profile_name: Optional[str],
    web_profile_cfg: dict[str, Any],
    http_get: Callable[[str, dict[str, str], float], HttpResponse] | None = None,
):
    tools = create_dogent_web_tools(
        root=root,
        web_profile_name=web_profile_name,
        web_profile_cfg=web_profile_cfg,
        http_get=http_get,
    )
    return create_sdk_mcp_server(name="dogent-web", version=__version__, tools=tools)
