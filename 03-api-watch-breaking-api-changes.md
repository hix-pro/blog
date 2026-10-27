---
title: Breaking API changes you didn't know you shipped
published: false
tags: api, openapi, ci, rust
---

A vendor ships a new version of their API. The changelog says "minor improvements." Your integration breaks on Tuesday because a field your code depends on moved from optional to required — technically announced, practically invisible. Or the mirror image: you are the vendor, a refactor quietly makes a response field optional, and three customers find out before you do. OpenAPI specs are supposed to prevent this by being a contract, but nothing enforces the contract between versions. The diff between two spec files is where the truth lives, and nobody wants to read a 400-line diff by hand.

[API Watch](https://github.com/hix-pro/api-watch) is a Rust CLI that does it for you. It flattens a spec — OpenAPI 3.x, Swagger 2.0, or plain JSON — into a set of contract facts, stores a baseline in a local SQLite database, and classifies every subsequent fetch against that baseline. The classifier is directional: it knows that removing a request parameter is breaking while adding one is compatible, that a response field becoming optional is breaking while a request field becoming optional is not, and that enum values move in opposite directions on each side of the wire.

## What a run looks like

```console
$ apiwatch add https://petstore3.swagger.io/api/v3/openapi.json --name petstore
Added petstore
  URL       https://petstore3.swagger.io/api/v3/openapi.json

Next: apiwatch check petstore

$ apiwatch check petstore
petstore · OpenAPI · Swagger Petstore - OpenAPI 3.0 1.0.28
baseline saved · 515 facts · 19 endpoints · HTTP 200

$ apiwatch check petstore
petstore · OpenAPI · Swagger Petstore - OpenAPI 3.0 1.0.28
no contract changes · 515 facts · 19 endpoints · HTTP 304
  not modified (ETag matched)
```

The ETag handling matters for the monitoring case: point it at a spec that changes rarely, run it on a schedule, and unchanged days cost one conditional request. When the spec does change, `check --fail-on-breaking` exits `2` if any classified-breaking change was introduced, `0` on clean or compatible-only changes, and `1` on errors — including the honest cold-start case where the database is empty and there is nothing to compare yet (`no targets yet`).

## The direction is the hard part

A tool that treats every change as breaking is unusable — endpoints grow legitimately. The interesting rules are asymmetric:

| Change | Classification |
| --- | --- |
| New required request parameter | **Breaking** |
| New optional request parameter | Compatible |
| Response property removed | **Breaking** |
| Response property added | Compatible |
| Request enum value removed | **Breaking** |
| Response enum value added | **Breaking** |
| Field type changes (`string` → `integer`) | **Breaking** |
| Format added to a request field (`string` → `uuid`) | **Breaking** |
| Format removed from a response field | **Breaking** |
| Descriptions, examples, summaries, tags | Ignored |

Note the enum rows: a request may lose enum values only in a breaking release (your callers might send them), but a response may gain enum values only in a breaking release (your parsers might not know them). Same for `format` — tightening a request format breaks callers with looser data; loosening a response format breaks parsers expecting the strict one. Getting these backwards is exactly the kind of bug that survives a code review.

## CI with a persistent baseline

The database is the state, so it has to survive between runs:

```yaml
- uses: actions/checkout@v4
- uses: actions/cache@v4
  with:
    path: ~/.apiwatch
    key: apiwatch-${{ runner.os }}
- uses: hix-pro/api-watch@v0.3.0
  with:
    spec: https://internal.example.com/openapi.json
    check-args: --fail-on-breaking
```

Passing `spec` makes cache eviction self-healing: on a warm cache the target already exists and re-adding is a no-op; on a cold cache it restores the tracking entry so the first check records a fresh baseline and exits `0`. The action downloads a prebuilt binary and falls back to compiling. Specs behind auth use static headers (no OAuth flows — see limits below).

## What it will not do

Static headers only — no OAuth2 flows, no mTLS. External `$ref`s are not fetched (unresolved ones are counted and surfaced). `allOf`/`oneOf`/`anyOf` are traversed with required-field merging, but composition is not fully proven. And the deepest limit, stated without apology: **specs are the source of truth**. A server that changes behavior without changing its spec is invisible to this tool — that is not a flaw in the tool so much as a fact about trust. The fix is vendors who treat their spec as a contract, and tools like this one make the incentive to do so explicit.

The test suite covers the classifier end to end — enum direction, required-field changes, cascade suppression, redirect header policy — which is exactly the part you want tested when the tool's job is to be right about breaking.

`apiwatch` is MIT-licensed, bundles its own SQLite, and has no system dependencies. Install from source with `cargo install --path . --locked`, or skip compiling: every release ships prebuilt binaries for Linux, macOS (Apple Silicon), and Windows with SHA-256 checksums.

It is part of the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. Siblings: [Migration Guard](https://github.com/hix-pro/migration-guard) for dangerous SQL migrations, [EnvAudit](https://github.com/hix-pro/env-audit) for environment drift, [ActionLens](https://github.com/hix-pro/action-lens) for workflow review.
