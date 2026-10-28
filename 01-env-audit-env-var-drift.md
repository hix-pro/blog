---
title: Catching env var drift before it breaks prod
published: false
description: EnvAudit scans a repo for env vars that are missing, undocumented, unused, or exposed as secrets — and fails CI when code and configuration disagree.
tags: devops, rust, ci, security
series: hix tools — local-first dev tools
cover_image: https://raw.githubusercontent.com/hix-pro/blog/main/covers/01-envaudit.png
---

Every deploy script is a bet that your code and your configuration agree about the world. Code reads `DEPLOY_REGION`; the deployment environment sets `DEPLOY_REGION_V2` after someone renamed it in March. Locally, everything works because your `.env` has a value the example file never mentioned. In staging, the process starts and falls back to a default region three timezones away. None of this shows up in tests, because tests run with the developer's own environment. Env drift is invisible by construction — it only exists at the boundary between two machines that were configured by different people at different times.

[EnvAudit](https://github.com/hix-pro/env-audit) is a local-first Rust CLI that makes that boundary explicit. It scans a repository and finds the four ways code and configuration disagree: variables used but never declared (`missing`), declared but absent from your example file (`undocumented`), declared but never read by any code (`unused`), and secrets sitting in files that `.gitignore` does not cover (`secret`). It also flags the same variable declared twice with different values, which is its own quiet disaster.

## What a run looks like

The repo ships a deliberately broken fixture project, so the output is reproducible in ten seconds:

```console
$ cd examples/fixture-project
$ envaudit scan .
EnvAudit · 0.3.1
Scanned 7 files under .

critical (1)
  secret        STRIPE_SECRET_KEY
    found in .env:3
    A likely secret value is stored in .env, which is not ignored by .gitignore.
    fix: Remove the value from .env, rotate the credential, and add .env to .gitignore.

error (1)
  missing       DEPLOY_REGION
    used at src/server.ts:8
    Referenced in scanned code but not declared in any env file, Compose environment, or workflow env map.
    fix: Add DEPLOY_REGION to .env.example and the deployment environment, or remove the reference.

warning (2)
  undocumented  LEGACY_SMTP_HOST
    declared at .env:4
    Set in runtime configuration but absent from the example env file.
    fix: Add LEGACY_SMTP_HOST to .env.example so new contributors can discover it.
  unused        UNUSED_LEGACY_FLAG
    declared at .env.example:8
    Declared in an example env file but never referenced in scanned code.
    fix: Remove UNUSED_LEGACY_FLAG from the example file or add the code that reads it.

info (1)
  duplicate     DATABASE_URL
    declared at:
      .env:1
      .env.local:1
```

Every finding names the file and line, explains why it is a finding, and proposes the fix. The tool never applies fixes itself — more on that below.

## How it decides

EnvAudit cross-references three sources: declarations (`.env`, `.env.example`, Compose `environment:` maps, workflow `env:` blocks), usages (`process.env.X`, `os.Getenv`, `std::env::var` and friends in scanned source files), and `.gitignore` coverage. A variable that is used but declared nowhere is `missing`. One declared in a real env file but absent from the example file is `undocumented`. The inverse is `unused`. A secret-shaped value in a file your `.gitignore` fails to cover is `critical`, because that is the "one bad `git push` away from leaking" case.

By default the tool is a report: it prints findings and exits `0`. The `--fail-on any|missing|secret` flag opts into gating: exit `2` when matching findings exist, exit `1` on scan errors like malformed dotenv lines. Report-only by default is deliberate — you can point it at years of accumulated legacy code on day one, read the report, and only wire CI to fail once you have decided what the baseline is. `--json` emits a stable, versioned document (`schema_version: 1`, deterministically sorted, secret values never serialized) and `--markdown` produces a paste-ready pull request comment. Both exist because "the humans can read the terminal output" stops being true the moment you want a bot to react to it.

## The CI recipe is two steps

```yaml
- uses: actions/checkout@v4
- uses: hix-pro/env-audit@v0.3.1
  with:
    fail-on: any
```

The action downloads a prebuilt binary for the runner (no Rust compilation) and falls back to building from source if needed. Start with `fail-on: secret` if the full report looks overwhelming. Fixing "a credential is one bad push away from leaking" is worth doing before you care about documentation drift.

## Run it with the suite

The CLI tools share a runner. [`hix`](https://github.com/hix-pro/hix) looks for the tools installed on `PATH`, applies a check plan, and prints one table with one exit code:

```sh
pipx install git+https://github.com/hix-pro/hix.git
hix check
```

It installs nothing and sends no telemetry. A tool that is missing or needs configuration is reported as skipped, with the command that fixes it; commit a `.hix.toml` when you want the plan to be explicit.

## What it will not do

There is no auto-fix, no environment expansion, and no secret rotation — on principle. A tool that silently rewrites your `.env.example` is a tool that can silently corrupt it. EnvAudit tells you the fix and lets you decide. Files over 1 MiB, symlinks, `node_modules`, `target`, and `vendor` are skipped, and monorepos should scan each service directory separately so example files stay scoped correctly. The dotenv parser handles `KEY=VALUE` lines with single-line quoting; anything exotic exits `1` rather than guessing.

EnvAudit is MIT-licensed, needs Rust 1.85+ to build from source, and skips compiling entirely if you prefer: every release ships prebuilt binaries for Linux, macOS (Apple Silicon), and Windows with SHA-256 checksums. The fixture project has committed expected output, so you can see all finding kinds fire in ten seconds.

It is one of eight tools in the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. The siblings cover the rest of the pre-production checklist: [Migration Guard](https://github.com/hix-pro/migration-guard) catches dangerous SQL migrations statically, [API Watch](https://github.com/hix-pro/api-watch) catches breaking API contract changes, and [ActionLens](https://github.com/hix-pro/action-lens) reviews your GitHub Actions workflows before they reach `main`.
