# fbgram

A Facebook OSINT command-line tool in the spirit of
[Osintgram](https://github.com/datalux/osintgram) — table output, subcommand
style, focused on public data collection.

## Why it works differently from Osintgram

Osintgram drives a logged-in Instagram account through Instagram's
semi-private endpoints. **Facebook has no equivalent**, and Meta actively bans
scraping or session automation: doing it gets the operator's account
restricted and breaks within days at best. In some jurisdictions
(unauthorised access laws like the CFAA, GDPR for personal data collection)
it is also a legal risk for you, the operator.

So fbgram does something narrower and honest — it only uses what Facebook
officially exposes:

1. **The Graph API**, with an access token from *your* Meta developer app.
   This covers public **Pages** (businesses, orgs, creators) — which are the
   Facebook entities with genuinely public data.
2. **Passive public checks** over plain HTTPS, no login, no account —
   username-existence probes in the style of
   [Sherlock](https://github.com/sherlock-project/sherlock).
3. The [lockfale OSINT-Framework](https://github.com/lockfale/OSINT-Framework)
   remains useful for the parts Facebook intentionally does not expose:
   breach-data lookup, breach-email search, face-search and so on all live
   outside of Meta's API by design. fbgram does not try to replicate those.

It collects and reports only data Meta exposes to the token you authorized.

## Install

```bash
pip install -r requirements.txt
```

## Get a token

1. Create an app at <https://developers.facebook.com/apps> (type "Business"
   or "Consumer").
2. Get a short-lived token at
   <https://developers.facebook.com/tools/explorer>, then exchange it for a
   long-lived one (see Meta docs: "Long-Lived Access Tokens").
3. Export it:

```bash
export FBGRAM_TOKEN="EAAB..."
```

## Commands

| command | what it does |
| --- | --- |
| `whoami` | the identity the token belongs to |
| `token` | scopes, expiry and app of the token (good first sanity check) |
| `page <id-or-handle>` | full metadata for a public Page (category, fans, about, contact fields, verification) |
| `search <query>` | search public Pages by keyword |
| `posts <page> [--limit N]` | recent Page posts with reactions / comments / shares |
| `audience <page>` | aggregate the commenters (`name` + `user_id`) across the Page's recent posts — the closest analog to Osintgram's targeted-user lookups |
| `user <id>` | the very limited public fields Meta allows for a user id |
| `checkuser <username>...` | passive: does `facebook.com/<username>` exist? no token needed |

Global flags: `--token`, `--api-version` (default v21.0), `--json`.

Examples:

```bash
python -m fbgram token
python -m fbgram whoami
python -m fbgram search "coffee london" --limit 15
python -m fbgram page nasa
python -m fbgram posts nasa --limit 5
python -m fbgram audience nasa --limit 10 --top 30
python -m fbgram checkuser zuck some_hypothetical_handle
```

## Honest limits

- **Personal profiles are intentionally locked-down.** `user <id>` will
  usually return only `id`, `name` and `link`/`picture` at most, if the token
  owner is allowed to see the profile. Anything more (friends, photos, likes
  on friends' content, email/phone) requires the *data subject's* consent via
  Login deliverables like `user_friends`; you cannot look those up about a
  stranger. This is by design, not a bug to work around.
- **Page search** requires `Page Public Content Access` and (in production)
  an app review by Meta; with a plain app token or the Graph API Explorer
  token it may return an error. Instagram has equivalent tokens; the tool
  won't fake it around.
- Rate limits apply; don't hammer the API.
- `checkuser` is a heuristic — Facebook's anti-bot wall returns 200 for many
  handles (real or not) and redirects to login for others, so "not found" is
  the only definitive verdict it can give; anything else is a lead, not proof.

## Ethics

Use this only for OSINT on entities you are permitted to research (public
Pages, your own accounts, research with a lawful basis). Do not use it to
harvest personal data at scale or to target individuals; Meta's ToS and most
privacy laws prohibit it. Missing any of this changes — feel free to ask.
