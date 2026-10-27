# Publishing checklist

Seven posts, ready to publish after review. All have dev.to front matter with `published: false` — import and flip the flag when ready.

Each post ships with: a `description` (meta/SEO summary), `tags`, `series: hix tools — local-first dev tools`, and a branded `cover_image` (2400×1260, per-tool accent color) served from this repo's `covers/` directory.

## The posts

| # | File | Tool | Hook |
|---|------|------|------|
| 01 | 01-env-audit-env-var-drift.md | EnvAudit | Catching env var drift before it breaks prod |
| 02 | 02-migration-guard-static-sql-analysis.md | Migration Guard | Static SQL migration analysis without a database |
| 03 | 03-api-watch-breaking-api-changes.md | API Watch | Breaking API changes you didn't know you shipped |
| 04 | 04-action-lens-16-workflow-checks.md | ActionLens | 16 things to check in your GitHub Actions workflows |
| 05 | 05-compose-map-red-flags.md | ComposeMap | Docker Compose red flags before you deploy |
| 06 | 06-opencode-telegram-remote-control.md | OpenCode Telegram | Remote-controlling OpenCode from Telegram |
| 07 | 07-reporace-momentum-not-stars.md | RepoRace | Momentum, not stars |

## Import steps (dev.to)

1. New post → paste the markdown body (or use the frontend GitHub repo import if configured).
2. Move the front-matter title/tags/description into the dev.to editor fields; the cover image is picked up from `cover_image` automatically on API/frontend import (or upload from `covers/`).
3. Preview → flip `published` in the front matter, or just publish from the editor.
4. Canonical URL: leave empty on the platform you publish first (original content).
5. Cross-posting later (dev.to ↔ Hashnode, or Medium): set `canonical_url` on the copy to the URL of the post published first.

Hashnode alternative: paste markdown, tags map 1:1, front matter otherwise ignored — set the subtitle from the post's `description` and upload the matching `covers/*.png` manually. Publish one platform first and canonicalize the other.

## Recommended posting order

Browser tools first — the live demos convert best because readers try the tool in 10 seconds without installing anything:

1. **04 ActionLens** (demo: hix-pro.github.io/action-lens) — broadest audience; everyone has workflows
2. **05 ComposeMap** (demo: hix-pro.github.io/compose-map) — docker audience, high engagement
3. **01 EnvAudit** — the "secret in .env" hook is the strongest CLI story
4. **02 Migration Guard** — postgres audience, very shareable rule table
5. **03 API Watch** — narrower (spec-driven teams) but deep
6. **07 RepoRace** — fun/data post, good palate cleanser
7. **06 OpenCode Telegram** — the AI-agent audience is loud on dev.to right now

Cadence: 2 per week. A single-burst dump underperforms and floods followers.

## Post-live actions (per post)

- Add a "Featured in" link under each repo's README badges (needs the real URL first — that is why it is not done yet).
- Repo social preview images: set in repo Settings → Social preview.
- Show HN for 04 and 05 (browser demos do best on HN); r/devops for 01/02; r/docker for 05; r/SideProject for 07.
- awesome-list submissions after 2-3 posts are live (awesome-github-actions, awesome-compose, awesome-postgres).
- Cross-link: once 2+ posts are live, add "prev/next post" links at the bottom.

## Consistency notes (already handled)

- All posts: dev.to front matter, `published: false`, `description`, `series`, and a per-tool branded `cover_image`.
- Covers live in [`covers/`](covers/) — one accent color per tool (green EnvAudit, amber Migration Guard, orange API Watch, blue ActionLens, cyan ComposeMap, Telegram blue, purple RepoRace).
- Rust CLI posts reference `@v0.3.0` actions (current release, prebuilt-binary fast path) and mention prebuilt binaries in the install line.
- Every post ends with the hix tools suite footer + cross-links to siblings.
- Terminal output blocks are taken from committed README/fixture output (version banners updated to 0.3.0).
- Voice: dry, practical, honest-limits section in every post. Limitations stated before a reader finds them.
