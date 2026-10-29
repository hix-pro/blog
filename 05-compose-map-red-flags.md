---
title: Docker Compose red flags before you deploy
published: false
description: ComposeMap turns a Docker Compose file into a service graph and a plain-English risk review, entirely in your browser.
tags: docker, devops, security, webdev
series: hix tools — local-first dev tools
cover_image: https://raw.githubusercontent.com/hix-pro/blog/main/covers/05-composemap.png
---

A Compose file is easy to write and hard to read back. `depends_on` hides startup order behind a YAML list. Long-form `ports:` syntax hides what is actually exposed to the host. And a literal database password in `environment:` looks exactly like every other line on the screen. Most Compose files get reviewed once — when they are written — and then quietly grow: a healthcheck forgotten, an image tag drifting to `latest`, a `docker.sock` mount added "temporarily" to make some tool work.

[ComposeMap](https://github.com/hix-pro/compose-map) turns a `docker-compose.yml` into a service graph and a plain-English review before `docker compose up` ever reaches a server. It runs entirely in the browser — no backend, no account, no upload; the file never leaves the tab. Live demo: <https://hix-pro.github.io/compose-map/>.

## The red flags

Fourteen rules, three severities. The critical ones are the "this is how a container becomes a host" set:

- `docker-socket` — mounting `/var/run/docker.sock` turns a container compromise into a host compromise. The container can now talk to the Docker daemon as root.
- `privileged` — `privileged: true` gives a container almost all host capabilities. Almost nothing legitimately needs this.
- `literal-secret` — a secret-looking value (or a URL with embedded credentials) committed right in the file. Deliberately conservative: values containing `${...}` are treated as references, never reported.
- `no-image`, `missing-dependency`, `dependency-cycle` — a service that cannot start, a `depends_on` pointing at nothing, and a cycle that can never reach a healthy state.

The warning tier is the "works today, fails surprisingly" set: `latest-image` and `unpinned-image` (the tag can change without your Compose file changing), `host-network` and `host-network-ports` (host networking bypasses Compose isolation, and `ports:` is silently ignored under it), and `no-healthcheck` (a running container is not necessarily a ready one). The info tier catches `no-restart` (the service stays down after a crash or reboot), `all-interfaces` (a published port binds every host interface unless an IP is given — the difference between a service on your LAN and one on the internet), and `container-name` (a fixed name prevents scaling beyond one replica).

Each finding names the service, explains why it matters, and proposes a concrete fix.

## Reading the graph

The graph answers a question the YAML makes tedious: what waits for what? An edge points from a service to something it depends on; severity indicators show where the findings cluster. Click a node to inspect it — ports, volumes, networks, dependencies, and its findings. The inspector shows environment **keys only** (values are hidden), so a screenshot of the app cannot leak a credential. Focus mode narrows the review to one service or one severity, which matters once the file is past a dozen services.

## Comparing two revisions

The riskiest Compose change is usually not the one that adds a service. It is the one-line edit buried in a large diff: `image: postgres:16.4` becomes `latest`, `127.0.0.1:8080:80` becomes `8080:80`, or a `privileged: true` appears in a file that was clean yesterday. Reviewing the new file on its own forces you to hold the old one in your head.

**Compare** in ComposeMap takes the previous revision on the left and the proposed one on the right. It parses both with the same parser and runs the same 14 rules against each, then shows the delta:

- Services added, removed, and changed, down to individual fields: image, build, command, ports, volumes, environment, `env_file`, `depends_on`, networks, healthcheck, restart policy, and privilege.
- Findings introduced, resolved, and re-graded. A warning that becomes critical is called out instead of looking like the same finding.
- Top-level network and volume changes.

Environment values that look like secrets are redacted in the comparison, so a token change shows as `•••• (hidden)` rather than printing the credential into a screenshot or a shared screen. Short and long port/volume syntax are compared semantically, so reformatting a file does not produce noise. If you want to compare what Docker will actually run rather than the raw file, run `docker compose config` first and paste the normalized output into either side.

The comparison is still static review: it tells you which risks changed, not whether the new stack is safe, and it cannot resolve `${VAR}` references. It is a review aid for the diff, not a substitute for one.



Three fixtures ship with the app. `saas-starter` (web, worker, Postgres, Redis) is mostly healthy — it shows what a reasonable stack looks like when reviewed. `leaky-stack` is deliberately broken and fires nearly every rule; it is the default sample, which makes the tool self-demonstrating on first load. `media-homelab` (Jellyfin, Sonarr, qBittorrent, Watchtower) is a realistic hobby stack with the specific smells hobby stacks actually have — host networking for discovery, Watchtower on unpinned images. The same fixtures pass `docker compose config`, so you can diff the tool's reading against Docker's.

Exports cover Mermaid (README diagrams), Markdown (PR descriptions), SVG/PNG (docs and slides), and JSON — the schema is stable and includes rule id, severity, service, message, and fix for every finding.

## What it will not do

Static review only: it does not start containers, read Docker daemon settings, resolve image contents, scan for CVEs, or see runtime behavior. `${VAR}` references are not resolved — the tool cannot know what your `.env` contains, only that the file references a variable. A clean review means these 14 rules found nothing, not that the stack is safe. Orchestrator behavior (Swarm, Kubernetes, ECS) is out of scope. The parser handles short and long port/volume syntax, environment maps and lists, `env_file`, and both map and list forms of `depends_on`; YAML anchors and merge keys are handled by the YAML library rather than custom code. The rule engine and exporters are pure functions with 46 unit tests behind them.

ComposeMap is MIT-licensed and client-side only. Run it locally with `npm install && npm run dev`, or open the hosted demo — same code, no install.

It is one of ten tools in the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. If you are hardening infrastructure config, [ActionLens](https://github.com/hix-pro/action-lens) reviews the GitHub Actions workflows around that stack, [EnvAudit](https://github.com/hix-pro/env-audit) catches the env vars it references but never documents, and [PlanGuard](https://github.com/hix-pro/planguard) reviews the Terraform plan before apply.
