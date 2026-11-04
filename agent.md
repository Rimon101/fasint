# AGENTS.md — fbgram

Guidance for AI agents (and humans) working in this repository. Read this
before changing anything.

## What this project is

**fbgram** is a Facebook OSINT command-line tool in the spirit of
[Osintgram](https://github.com/datalux/osintgram): subcommand-driven CLI with
table (default) or `--json` output, focused on public data collection.

The defining architectural decision — **do not fight it**:

- Osintgram drives a logged-in Instagram session. **Facebook has no such
  surface.** Meta bans scraping and session automation; it also breaks fast
  and creates legal exposure (CFAA, GDPR) for the operator.
- Therefore fbgram works only through **official channels**:
  1. the **Facebook Graph API** using an access token the operator owns
     (from their own Meta developer app), and
  2. **passive HTTPS checks** that require no login (username probes).
- It intentionally does NOT collect data about private individuals beyond
  what Meta exposes publicly. Personal-profile digging (friends, photos,
  emails, phones) is impossible by design — do not try to "add" it by
  scraping, spoofing sessions, or bundling credential harvesting. Features
  must fit inside Graph API + passive-public checks.

## Repository layout

```
requirements.txt        only pinned dep: requests
README.md               user-facing docs: setup, token, commands, limits
fbgram/
  __init__.py           version, one-paragraph rationale
  api.py                Graph API client (no CLI logic here)
  cli.py                argparse CLI + output formatting + passive checker
                        (place aggregation: place_of / summarize_places)
  __main__.py           entry point: python -m fbgram
agent.md                this file
```

## How the pieces fit

`cli.py` owns everything user-facing: argparse parser, per-command
implementations (`cmd_*`), output formatting, and `check_usernames()` (the
only function that touches the network without a token). `api.py` owns
everything Graph-API: `GraphClient` (token, version pin, `get()` with
optional `paginate=True` edge-walking) plus thin typed methods (`me()`,
`page()`, `page_posts()`, `post_comments()`, `page_search()`, `debug_token()`).

Conventions when extending:

- New Graph endpoints: add a method on `GraphClient`; never `requests` in
  cli.py except for the passive `checkuser` path.
- Field lists live as module constants in api.py (`PAGE_FIELDS`,
  `POST_FIELDS`) — keep them there, not inline in commands.
- Every command is a small `cmd_x(args)`; register it in `build_parser()`
  with `sub.add_parser(...)` and `set_defaults(func=...)`. Respect `args.json`
  for machine-readable output, and use the `kv`/`table` helpers rather than
  ad-hoc print layouts so output stays consistent.
- Errors: raise/propagate `GraphError` from api.py; `main()` maps status
  codes (401/190/403) to actionable hints on stderr. Don't swallow errors or
  print stack traces; exit non-zero on failure.
- The Graph API version is pinned via `DEFAULT_API_VERSION` (currently
  `v21.0`), overridable with `--api-version` or the `FBGRAM_API_VERSION`
  idea/env. Keep the default in sync with what is documented in README.md.

## Token / auth model

- Token read order: `--token` flag → `env FBGRAM_TOKEN` → `env
  FB_ACCESS_TOKEN` (`token_from_env()`).
- No tokens are ever stored, fetched, or exchanged by the tool itself.
- Never log, echo, or write the token anywhere. In code review, flag any
  `print`/`log` that could include it.

## Known product limits (state them, don't paper over them)

- `user <id>` usually returns only `id`, `name`, `link` — Meta design.
- `search` needs `Page Public Content Access` (+ app review in production);
  may error with a plain token. The tool reports the API error verbatim.
- `checkuser` is heuristic: Facebook serves HTTP 200 even for some
  nonexistent handles and redirects others to login. **Only a 404 is a
  definitive "not found"** — code comments and README agree on this wording;
  keep it that way.

## Verification

There is no test suite (yet). Minimum bar after any change:

```bash
python -m pip install -q -r requirements.txt
python -m py_compile fbgram/*.py
python -m fbgram --help            # all 9 subcommands listed
python -m fbgram checkuser <any-handle>   # token-free live path
```

Token-using commands can't be exercised without a real token; don't fake it —
state that they were code-reviewed but not run live.

## Non-goals

No scraping, no browser automation, no session impersonation, no proxies for
bypassing rate limits, no storage of collected data beyond stdout. Fixes
should stay minimal rather than growing the tool's data-collection surface.
