"""Thin wrapper around the Facebook Graph API.

Every call goes through `GraphClient`, which only talks to graph.facebook.com
with an access token the operator already owns. Nothing here simulates a
browser, imitates a session, or side-steps Meta's terms of service.
"""

import os
from typing import Any, Dict, Iterable, List, Optional

import requests

GRAPH_URL = "https://graph.facebook.com"

# Default API version. Overridable with FBGRAM_API_VERSION in the environment
# or --version on the CLI. Pin one you have permission for in your Meta app.
DEFAULT_API_VERSION = "v21.0"

# Fields the Graph API exposes for a public Page without special permissions.
PAGE_FIELDS = (
    "id,name,category,category_list,fan_count,followers_count,link,"
    "about,description,website,emails,phone,verification_status,"
    "created_time,style,talking_about_count,were_here_count,cover"
)

POST_FIELDS = (
    "id,message,story,created_time,permalink_url,type,"
    "shares,comments.summary(true).limit(0),reactions.summary(true).limit(0)"
)


def token_from_env() -> Optional[str]:
    """Read the token from FBGRAM_TOKEN or FB_ACCESS_TOKEN."""
    return os.environ.get("FBGRAM_TOKEN") or os.environ.get("FB_ACCESS_TOKEN") or None


class GraphError(RuntimeError):
    """Raised for any non-success response from the Graph API."""

    def __init__(self, message: str, status: int, raw: Dict[str, Any]):
        super().__init__(message)
        self.status = status
        self.raw = raw


class GraphClient:
    def __init__(self, token: str, api_version: str = DEFAULT_API_VERSION):
        if not token:
            raise GraphError(
                "No access token. Export FBGRAM_TOKEN or pass --token.", 0, {}
            )
        self.token = token
        self.version = api_version.lstrip("v")
        self.session = requests.Session()

    def get(
        self,
        path: str,
        fields: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        paginate: bool = False,
        max_items: Optional[int] = None,
    ) -> Any:
        """GET an endpoint. With paginate=True, follow `next` links and return
        a flat list of edge items (used for posts, comments, search results)."""
        params = dict(params or {})
        params["access_token"] = self.token
        if fields:
            params["fields"] = fields

        def call(url: str, p: Dict[str, Any]) -> Dict[str, Any]:
            resp = self.session.get(url, params=p, timeout=30)
            body: Dict[str, Any]
            try:
                body = resp.json()
            except ValueError:
                raise GraphError(
                    f"Non-JSON response (HTTP {resp.status_code})", resp.status_code, {}
                )
            if resp.status_code != 200 or "error" in body:
                err = body.get("error", {})
                raise GraphError(
                    err.get("message", f"HTTP {resp.status_code}"),
                    resp.status_code,
                    body,
                )
            return body

        url = f"{GRAPH_URL}/{self.version}/{path.lstrip('/')}"
        body = call(url, params)

        if not paginate:
            return body

        items: List[Dict[str, Any]] = []
        while True:
            data = body.get("data", [])
            if isinstance(data, dict):  # /search can return a dict-of-dicts
                data = list(data.values())
            for entry in data:
                items.append(entry)
                if max_items is not None and len(items) >= max_items:
                    return items
            nxt = body.get("paging", {}).get("next")
            if not nxt:
                return items
            body = call(nxt, {})

    # ---- convenience methods -------------------------------------------------

    def me(self, fields: str = "id,name,first_name,last_name,link,email,birthday,gender,locale,location") -> Dict[str, Any]:
        return self.get("me", fields=fields)

    def page(self, page_id: str) -> Dict[str, Any]:
        return self.get(page_id, fields=PAGE_FIELDS)

    def user(self, user_id: str, fields: str = "id,name,link") -> Dict[str, Any]:
        return self.get(user_id, fields=fields)

    def page_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get(
            "search",
            params={"q": query, "type": "page", "limit": limit},
            paginate=True,
            max_items=limit,
        )

    def page_posts(self, page_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self.get(
            f"{page_id}/posts",
            fields=POST_FIELDS,
            params={"limit": 25},
            paginate=True,
            max_items=limit,
        )

    def post_comments(self, post_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self.get(
            f"{post_id}/comments",
            fields="from{id,name}",
            params={"limit": 100},
            paginate=True,
            max_items=limit,
        )

    def debug_token(self) -> Dict[str, Any]:
        """Token metadata: who it belongs to, scopes, expiry. Useful safety net
        before doing anything else."""
        info = self.get("/debug_token", params={"input_token": self.token})
        return info.get("data", info)
