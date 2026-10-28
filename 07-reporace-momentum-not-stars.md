---
title: "Momentum, not stars: ranking GitHub repos by acceleration"
published: false
description: RepoRace ranks GitHub repositories by acceleration, not raw stars — momentum and breakout leaderboards backed by local SQLite.
tags: opensource, data, javascript, sqlite
series: hix tools — local-first dev tools
cover_image: https://raw.githubusercontent.com/hix-pro/blog/main/covers/07-reporace.png
---

GitHub's trending page is a black box. A raw star count mostly measures age — a project with 100,000 stars accumulated them over years, and the number says nothing about whether anyone cares this week. The signal people actually want from "trending" is acceleration: which repositories are gaining stars *right now*. And GitHub's API cannot give you that, because historical star counts are simply not exposed — the old stargazer-timestamp endpoint returns 404 for ordinary tokens, and GraphQL's `stargazers` connection does not provide timestamps.

[RepoRace](https://github.com/hix-pro/reporace) works around the missing data the only honest way: **it collects its own history**. A collector snapshots exact star and fork counts via GraphQL for every tracked repo. Each run diffs the new total against the previous snapshot and records the delta against a UTC day. Velocity appears after the second snapshot; the chart fills in from there. Rank by stars gained in the last 24 hours, 7 days, or 30 days, and a new project gaining 800 stars a day outranks a famous one that added 600 — even when the famous one has 100× more total stars.

## Two leaderboards, on purpose

- **Momentum** — rank by total stars gained in the range. The headline number.
- **Breakout** — rank by percent growth relative to repo size. This is where a 2,000-star repo growing 15% in a week beats a 200,000-star repo growing 0.3%, and it is the closest thing to a "discover it early" list that does not depend on an opaque algorithm.

Both work over three ranges — 24h, 7d, 30d — so "spiking today" and "climbing all month" are separate questions with separate answers. Repo detail pages show the cumulative star chart, daily gains, current pace, rank, and topics.

## The demo-data honesty rule

A velocity product has a cold-start problem: with one snapshot there is nothing to rank. RepoRace resolves it without lying. `npm run demo` generates 30 days of history, and the UI badges it with an orange **DEMO DATA** banner. Live data gets a green **LIVE** badge. Running the collector deletes the demo history and switches the mode flag — there is no code path that quietly upgrades generated rows into live ones. Star totals in the seed are real; the daily history is not; the interface never blurs the distinction. If you borrow this pattern for anything else — generated metrics, sample data, seeded dashboards — steal the badge, not just the data.

## Stack and structure

Node.js 24+ (the built-in `node:sqlite` module — no native dependency), Vite + React on the front, a small API server on 8787 that Vite proxies. Data lives in one SQLite file with four tables: `repos`, `snapshots`, `star_daily`, and `meta`. Snapshots are timestamped; daily rows are keyed by repo + UTC day; one collection run is wrapped in a single transaction, so a crash mid-collect leaves the previous state intact. The API computes rankings by summing daily deltas for the selected range and sorting — momentum by absolute delta, breakout by delta divided by size.

Setup is three commands and a GitHub token with public-read access (the GitHub CLI's `gh auth login` works if you would rather not copy tokens):

```bash
npm install
npm run seed     # fetch real metadata + star totals for the tracked repos
npm run dev      # API + dashboard on localhost:5173
```

Then `npm run collect` on a schedule (cron example included in the repo) to accumulate real history.

## What it will not do

It does not predict anything. Velocity is a description of the past 24/7/30 days, not a forecast — trending-page placement, maintainer announcements, and HN front-page cycles all make the numbers jumpy, and RepoRace presents them without smoothing. It ranks only the repos it tracks (seeded list, editable); it is not a GitHub-wide search. Backfilling history it did not observe is impossible by design — the tool will not fabricate the past, which is the same honesty rule as the demo badge. And star velocity is one signal: it measures attention, not quality, not maintenance health, not security posture. Use it as a discovery surface, then do the actual evaluation yourself.

RepoRace is MIT-licensed. The ranking math, day-boundary handling, and GitHub response validation are covered by unit tests — the kind of edges (month boundaries, unparseable rows, inclusive ranges) that quietly produce wrong leaderboards when untested.

It is one of nine tools in the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. The rest of the suite is pre-production tooling: [EnvAudit](https://github.com/hix-pro/env-audit) for environment drift, [Migration Guard](https://github.com/hix-pro/migration-guard) for dangerous SQL migrations, [API Watch](https://github.com/hix-pro/api-watch) for API contract changes, [ActionLens](https://github.com/hix-pro/action-lens) for workflow review, [ComposeMap](https://github.com/hix-pro/compose-map) for Compose files, and [OpenCode Telegram](https://github.com/hix-pro/opencode-telegram) for running coding agents from your phone.
