# hix tools — writing

**Live site: [hix-pro.github.io/blog](https://hix-pro.github.io/blog/)**

Seven practical posts on local-first developer tools that catch what CI misses: env drift, dangerous SQL migrations, breaking API contracts, GitHub Actions risk, Docker Compose red flags, remote-controlling a coding agent, and star velocity.

| # | Post | Tool |
|---|------|------|
| 01 | Catching env var drift before it breaks prod | EnvAudit |
| 02 | Static SQL migration analysis without a database | Migration Guard |
| 03 | Breaking API changes you didn't know you shipped | API Watch |
| 04 | 16 things to check in your GitHub Actions workflows | ActionLens |
| 05 | Docker Compose red flags before you deploy | ComposeMap |
| 06 | Remote-controlling OpenCode from Telegram | OpenCode Telegram |
| 07 | Momentum, not stars: ranking GitHub repos by acceleration | RepoRace |

## The site

The site is generated from the markdown in this repo into `docs/` and served by GitHub Pages from `main:/docs`.

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_site.py
```

Then commit `docs/` with the post change. The generator writes the index, post pages, RSS feed, sitemap, and 404 page; covers are copied from `covers/`.

## Publishing

`published: false` in the front matter is the **dev.to** flag, not the site flag — the site publishes all seven posts. Leave it false until each post is cross-posted, then flip it there; set the canonical URL to the post on this site.

The import and cross-posting steps are in [`00-PUBLISHING-CHECKLIST.md`](00-PUBLISHING-CHECKLIST.md).

## License

MIT for the code in `scripts/`; the posts and covers are © hix.
