<div align="center">

# 🕵️ fbgram

**A Facebook OSINT tool — in the spirit of [Osintgram](https://github.com/datalux/osintgram), built for what Facebook actually allows.**

[![python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![deps](https://img.shields.io/badge/dependencies-1%20(requests)-green.svg)](requirements.txt)
[![cli](https://img.shields.io/badge/interface-CLI-informational.svg)](#-commands)
[![license](https://img.shields.io/badge/license-unlicensed-lightgrey.svg)](#-ethics--legal)

</div>

---

## ✨ What it does

You give it a target — a public **Page**, a keyword, or a username — and it
pulls together everything Facebook officially exposes about it:

| | |
| --- | --- |
| 🔎 **Page dossiers** | category, followers, about text, website, contact fields, verified status, creation date |
| 🧭 **Page discovery** | keyword search over all public Pages |
| 📊 **Content analysis** | recent posts with reactions, comments and shares — see what performs |
| ⏱️ **Engagement analytics** | posting cadence (best hour / weekday, page-local) and per-post engagement rate — see *what* and *when* performs |
| 👥 **Audience mapping** | who actually *engages* — commenters aggregated across a Page's posts, with names and user IDs |
| 🪪 **Identity checks** | does `facebook.com/<username>` exist? passive probe, no token needed |
| 🔐 **Self-verification** | exactly what your access token can and can't see, before you start |

Think *Osintgram's UX — `page`, `audience`, `checkuser` — applied to
Facebook's open surface: public Pages, not private people. See
[Why not like Osintgram?](#-why-not-like-osintgram).

---

## ⚙️ Quick start

```bash
git clone <this-repo> && cd fbgram
pip install -r requirements.txt
```

Grab a token (once):

1. Create an app at <https://developers.facebook.com/apps> — type **Business** or **Consumer**.
2. Get a short-lived token in the [Graph API Explorer](https://developers.facebook.com/tools/explorer).
3. Exchange it for a **long-lived token** (Meta docs → *"Long-Lived Access Tokens"*).
4. `export FBGRAM_TOKEN="EAAB..."`

Then:

```bash
python -m fbgram token    # sanity check: scopes + expiry + app
python -m fbgram whoami   # who the token belongs to
```

> 💡 `checkuser` works **right now, with no token**:
> `python -m fbgram checkuser zuck`

---

## 📟 Commands

```
usage: fbgram [-h] [--token TOKEN] [--json | --csv] [--api-version V]
              {whoami,token,page,user,search,posts,engagement,locations,audience,checkuser} ...
```

| command | what it gives you |
| --- | --- |
| **`whoami`** | the identity the token belongs to |
| **`token`** | scopes, expiry, and app behind the token — run this first |
| **`page <id-or-handle>`** | full public metadata: category, fans, about, website, emails, phone, verification |
| **`search <query>`** | public Pages matching a keyword |
| **`posts <page> [--limit N]`** | recent posts + reactions / comments / shares per post |
| **`posts <page> [--limit N]`** | recent posts + reactions / comments / shares per post |
| **`engagement <page> [--limit N]`** | ⭐ posting cadence (best hour/day, page-local) + per-post engagement ranked by interactions |
| **`audience <page>`** | ⭐ aggregate commenters (`name` + `user_id`) across recent posts |
| **`locations <page>`** | tagged places from recent posts, ranked, with lat/long — the entity's physical footprint |
| **`user <id>`** | the narrow fields Meta allows for a user id |
| **`checkuser <name> ... [--jobs N]`** | passive existence check for `facebook.com/<name>` — no token; `--jobs N` probes in parallel |

Global flags: `--token`, `--api-version` (default `v21.0`), and `--json` or
`--csv` for machine-readable output in every command (mutually exclusive).

### Examples

```bash
python -m fbgram search "coffee london" --limit 15
python -m fbgram page nasa
python -m fbgram posts nasa --limit 5
python -m fbgram engagement nasa --limit 100
python -m fbgram audience nasa --limit 10 --top 30
python -m fbgram locations nasa --limit 50 --top 10
python -m fbgram posts nasa --json | jq '.[0]'
python -m fbgram posts nasa --csv > posts.csv
python -m fbgram checkuser user1 user2 user3 --jobs 8
```

### What output looks like

**`audience`** — ranked, deduplicated engagement:

```
name                    comments  user_id
----------------------  --------  --------------------
Jane Q. Researcher      14        100001234567890
gizmo_fan_1994          9         100099887766554
...
42 distinct commenters across 10 posts.
```

**`checkuser`** — the anti-bot reality of Facebook, honestly reported:

```
username  status  verdict                                 url
--------  ------  --------------------------------------  --------------------------
zuck      200     may exist (HTTP 200 — verify manually)  https://www.facebook.com/…
```

> ⚠️ Facebook serves HTTP 200 for many handles — real or not. **Only a 404
> is a definitive "not found"**; anything else is a lead, not proof.

---

## 🚧 Honest limits

Read before filing issues — these are **by design**, in Meta's API, not bugs
to fix:

| limit | why |
| --- | --- |
| Personal profiles return almost nothing via `user <id>` — usually just `id`, `name`, `link` | Meta exposes strangers' data to *no one's* token; friends / photos / emails require the person's own consent |
| `search` may error with a plain token | public Page search needs the `Page Public Content Access` permission and, in production, an app review by Meta |
| Rate limits apply | official API, official throttling — fbgram retries transient throttling (HTTP 429/5xx, Graph codes 4/17/32) with backoff, but don't hammer it |
| `checkuser` can say "inconclusive" | Facebook's login wall + anti-bot responses make some probes unresolvable from outside |

### 🙃 Why not like Osintgram?

Osintgram drives a **logged-in Instagram session** through semi-private
endpoints. Facebook has no equivalent: scraping or session automation gets
the operator's account restricted within days and creates real legal
exposure (CFAA, GDPR) — and it breaks constantly. So fbgram deliberately
does the *narrower, working* version:

- ✅ official Graph API with a token **you** own
- ✅ passive public HTTPS checks (Sherlock-style)
- ❌ no scraping, no fake sessions, no credential harvesting

Where you'd have used Osintgram's `fwers` / `follow_type` on a person, the
Facebook answer is **`audience` on a Page** — or the
[lockfale OSINT-Framework](https://github.com/lockfale/OSINT-Framework) for
the things outside Meta entirely (breaches, email traces, face search).

---

## 🧰 Troubleshooting

| symptom | fix |
| --- | --- |
| `No access token…` | export `FBGRAM_TOKEN` or pass `--token` |
| `error: ...` with hint *— check the token* (HTTP 401/190) | token expired or invalid; refresh it, run `token` to inspect |
| `...does not cover this data` (HTTP 403) | your app lacks the permission; see [Honest limits](#-honest-limits) |
| empty `search` results | likely permission issue — see above |
| Windows console mojibake in tables | `chcp 65001` or `set PYTHONIOENCODING=utf-8` |

---

## 🐚 OS common pitfalls (Windows users)

```bash
# always forward slashes in bam; bash-on-windows is POSIX
cd C:/Users/you/fbgram        # ✅   not  C:\Users\you\fbgram
```

---

## 📁 Project layout

```
fbgram/
  api.py      Graph API client — auth, pagination, typed errors, field sets
  cli.py      argparse CLI, command implementations, output formatting,
              passive checkuser probe (the only token-free network call)
  __main__.py `python -m fbgram` entry point
README.md     ← you are here
agent.md      conventions for agents/contributors extending the tool
```

---

## ⚖️ Ethics & legal

This tool collects **only** what Meta officially exposes to the token *you*
authorized. Please use it for research you're permitted to do: public Pages,
your own accounts, lawful due diligence.

**Do not** use it to profile individuals, harvest personal data at scale, or
work around the limits listed above — that's against Meta's Terms of Service
and, depending on where you live, the law. "It broke my account" is a
supported issue; "it got me sued" is not.

---

<div align="center">
<sub>Inspired by <a href="https://github.com/datalux/osintgram">datalux/osintgram</a>
· framework reference: <a href="https://github.com/lockfale/OSINT-Framework">lockfale/OSINT-Framework</a></sub>
</div>
