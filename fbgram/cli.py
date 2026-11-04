"""Command-line interface for fbgram.

Usage:
  python -m fbgram <command> [options]

Environment:
  FBGRAM_TOKEN / FB_ACCESS_TOKEN — a Facebook Graph API access token.
"""

import argparse
import json
import sys
from collections import Counter
from typing import Any, Dict, List

import requests

from . import __version__
from .api import (
    DEFAULT_API_VERSION,
    GraphClient,
    GraphError,
    token_from_env,
)


# ---------------------------------------------------------------------------
# output helpers

def kv(data: Dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
        return
    for key, value in data.items():
        if isinstance(value, dict):
            text = json.dumps(value, default=str)
        elif isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.append(item.get("name", json.dumps(item, default=str)))
                else:
                    parts.append(str(item))
            text = ", ".join(parts)
        else:
            text = "" if value is None else str(value)
        print(f"{key:<24} {text}")


def table(rows: List[Dict[str, Any]], columns: List[str], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(rows, indent=2, default=str))
        return
    widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(row.get(c, ""))))
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns))


def summarize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    interactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares = post.get("shares", {}).get("count", 0)
    message = (post.get("message") or post.get("story") or "").replace("\n", " ")[:80]
    return {
        "created": (post.get("created_time") or "")[:10],
        "msg": message,
        "react": interactions,
        "comments": comments,
        "shares": shares,
        "id": post.get("id"),
    }


# ---------------------------------------------------------------------------
# passive (no token) checks

def check_usernames(usernames: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for name in usernames:
        url = f"https://www.facebook.com/{name}"
        status = ""
        verdict = "unknown"
        try:
            resp = requests.get(
                url,
                allow_redirects=False,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (compatible; fbgram)"},
            )
            status = str(resp.status_code)
            location = resp.headers.get("Location", "")
            if resp.status_code == 404:
                verdict = "not found"
            elif resp.status_code == 200:
                # Facebook returns 200 with a hard wall for many pages and for
                # some non-existent usernames, so this is only a hint.
                verdict = "may exist (HTTP 200 — verify manually)"
            elif resp.status_code in (301, 302) and "login" in location.lower():
                verdict = "inconclusive (Facebook redirects to login)"
            else:
                verdict = f"inconclusive (HTTP {status})"
        except requests.RequestException as exc:
            status = f"error: {exc.__class__.__name__}"
            verdict = "network error"
        rows.append({"username": name, "status": status, "verdict": verdict, "url": url})
    return rows


def client_for(args: argparse.Namespace) -> GraphClient:
    token = args.token or token_from_env()
    return GraphClient(token=token or "", api_version=args.api_version)


# ---------------------------------------------------------------------------
# command implementations

def cmd_whoami(args: argparse.Namespace) -> None:
    kv(client_for(args).me(), as_json=args.json)


def cmd_token(args: argparse.Namespace) -> None:
    kv(client_for(args).debug_token(), as_json=args.json)


def cmd_page(args: argparse.Namespace) -> None:
    kv(client_for(args).page(args.page), as_json=args.json)


def cmd_user(args: argparse.Namespace) -> None:
    kv(client_for(args).user(args.user), as_json=args.json)


def cmd_search(args: argparse.Namespace) -> None:
    results = client_for(args).page_search(args.query, limit=args.limit)
    rows = [
        {
            "name": r.get("name"),
            "id": r.get("id"),
            "category": r.get("category"),
            "fans": r.get("fan_count") or r.get("followers_count"),
        }
        for r in results
    ]
    if args.json:
        out(rows, as_json=True)
    else:
        table(rows, ["name", "id", "category", "fans"])


def cmd_posts(args: argparse.Namespace) -> None:
    posts = client_for(args).page_posts(args.page, limit=args.limit)
    rows = [summarize_post(p) for p in posts]
    if args.json:
        out(posts, as_json=True)
    else:
        table(rows, ["created", "msg", "react", "comments", "shares", "id"])


def cmd_audience(args: argparse.Namespace) -> None:
    """Osintgram-style: who engages with this page. Aggregates commenters from
    the page's recent posts. Needs a token that can read the posts."""
    client = client_for(args)
    posts = client.page_posts(args.page, limit=args.limit)
    counts: Counter = Counter()
    ids_by_name: Dict[str, str] = {}
    for post in posts:
        comments = client.post_comments(post["id"], limit=args.comment_limit)
        for comment in comments:
            who = comment.get("from") or {}
            name = who.get("name")
            if not name:
                continue
            counts[name] += 1
            if who.get("id"):
                ids_by_name[name] = who["id"]

    rows = [
        {
            "name": name,
            "comments": n,
            "user_id": ids_by_name.get(name, ""),
        }
        for name, n in counts.most_common(min(args.top, len(counts)))
    ]
    if args.json:
        out(rows, as_json=True)
    else:
        table(rows, ["name", "comments", "user_id"])
        print(f"\n{len(counts)} distinct commenters across {len(posts)} posts.")


def cmd_checkuser(args: argparse.Namespace) -> None:
    rows = check_usernames(args.usernames)
    if args.json:
        out(rows, as_json=True)
    else:
        table(rows, ["username", "status", "verdict", "url"])


# ---------------------------------------------------------------------------
# parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fbgram",
        description="Facebook OSINT through the official Graph API.",
    )
    parser.add_argument("--version", action="version", version=f"fbgram {__version__}")
    parser.add_argument("--token", help="Graph API access token (or set FBGRAM_TOKEN).")
    parser.add_argument(
        "--json", action="store_true", help="print raw JSON instead of tables"
    )
    parser.add_argument(
        "--api-version", default=DEFAULT_API_VERSION,
        help=f"Graph API version (default {DEFAULT_API_VERSION}).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("whoami", help="profile the token belongs to")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("token", help="inspect token scopes and expiry")
    p.set_defaults(func=cmd_token)

    p = sub.add_parser("page", help="dump info for a Page id or handle")
    p.add_argument("page", help="Page id or vanity name")
    p.set_defaults(func=cmd_page)

    p = sub.add_parser("user", help="public fields Meta allows for a user id")
    p.add_argument("user", help="User id; note that public lookups are very limited")
    p.set_defaults(func=cmd_user)

    p = sub.add_parser("search", help="search public Pages by keyword")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("posts", help="recent posts of a Page with engagement stats")
    p.add_argument("page", help="Page id or vanity name")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_posts)

    p = sub.add_parser("audience", help="aggregate commenters on a Page's recent posts")
    p.add_argument("page", help="Page id or vanity name")
    p.add_argument("--limit", type=int, default=10, help="posts to scan")
    p.add_argument("--comment-limit", type=int, default=100, help="comments per post")
    p.add_argument("--top", type=int, default=25, help="show this many")
    p.set_defaults(func=cmd_audience)

    p = sub.add_parser(
        "checkuser",
        help="passive existence check for facebook.com/<username> (no token)",
    )
    p.add_argument("usernames", nargs="+")
    p.set_defaults(func=cmd_checkuser)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.json = getattr(args, "json", False)

    try:
        args.func(args)
    except GraphError as exc:
        hint = ""
        if exc.status == 401 or "access token" in str(exc).lower():
            hint = " — check the token with: python -m fbgram token"
        elif exc.status == 403 or exc.status == 190:
            hint = " — the app/permission does not cover this data"
        print(f"error: {exc}{hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
