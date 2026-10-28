---
title: Static SQL migration analysis without a database
published: false
description: Migration Guard parses SQL and flags destructive statements, blocking DDL, and breaking renames statically — no database connection needed.
tags: sql, postgresql, devops, rust
series: hix tools — local-first dev tools
cover_image: https://raw.githubusercontent.com/hix-pro/blog/main/covers/02-migration-guard.png
---

The most expensive way to learn that your migration locks a table is to run it against production. `CREATE INDEX` on a large table blocks writes for the duration. `ALTER TABLE ... ALTER COLUMN ... TYPE` rewrites the table. A missing `WHERE` on a `DELETE` is self-explanatory. Every engineer eventually collects one of these scars, and the tools that try to prevent them usually want a database connection — a staging database to dry-run against, which you must keep fresh, seed, and pay for.

[Migration Guard](https://github.com/hix-pro/migration-guard) takes a different position: parse the SQL, apply rules, print findings. No connection string, no credentials, no database. It reads migration files the same way the database will — statement by statement — and reasons about them statically. That makes it fast enough to run on every pull request, and safe enough to point at anything.

## What a run looks like

```console
$ migration-guard check examples/risky.sql --fail-on risky
migration-guard 0.3.1  ·  postgres  ·  1 file

examples/risky.sql  (8 statements)
  risky        MG005  line 2
      ALTER TABLE accounts ADD COLUMN last_seen_at timestamptz NOT NULL;
      Why: Adding NOT NULL column `last_seen_at` to `accounts` without a DEFAULT can fail on existing rows or force a table rewrite.
      Fix: Add the column as nullable, backfill it, then set NOT NULL. Alternatively provide a DEFAULT if one is appropriate.

  risky        MG004  line 4
      ALTER TABLE accounts ALTER COLUMN email TYPE citext;
      Why: Changing `accounts.email` to `citext` can rewrite the table and block reads and writes while it runs.
      Fix: Create a new column with the target type, backfill in batches, then swap columns under a short lock, or use a maintenance window.

  risky        MG007  line 6
      CREATE INDEX idx_accounts_email ON accounts (email);
      Why: Building an index on `accounts` without CONCURRENTLY blocks writes for the duration of the build.
      Fix: Use CREATE INDEX CONCURRENTLY outside a transaction. If the build fails, drop the invalid index before retrying.

  risky        MG009  line 8
      ALTER TABLE orders ADD CONSTRAINT orders_account_fk FOREIGN KEY (account_id) REFERENCES accounts (id);
      Why: Adding a foreign key from `orders` to `accounts` validates every existing row while holding locks.
      Fix: Add the constraint with NOT VALID, then run ALTER TABLE ... VALIDATE CONSTRAINT as a separate step.

  warning      MG010  line 12
      ALTER TABLE accounts RENAME COLUMN email TO email_address;
      Why: Renaming `accounts.email` to `email_address` breaks queries, views, and clients that still use the old name.
      Fix: Use expand/contract: add the new name, update readers and writers, then remove the old name in a later release.

  warning      MG011  line 15
      CREATE INDEX CONCURRENTLY idx_accounts_display_name ON accounts (display_name);
      Why: PostgreSQL cannot run CREATE INDEX CONCURRENTLY inside a transaction block; this statement will fail at execution time.
      Fix: Move the concurrent index build outside BEGIN/COMMIT and make it its own migration step.

Summary: 1 file, 8 statements, 6 findings (0 destructive, 4 risky, 2 warnings)
```

Each finding carries a `Why` and a `Fix`. The fixes are the standard operational playbooks — nullable-then-backfill, `NOT VALID` then `VALIDATE CONSTRAINT`, expand/contract renames — written out where the person touching the migration will actually see them.

## The rules

Thirteen rules, three severities. `destructive` is data loss or unbounded locking: `DROP TABLE`, `TRUNCATE`, `ALTER TABLE ... DROP COLUMN` (MG001), `DELETE` or `UPDATE` without a `WHERE` (MG002, MG003). `risky` is likely downtime: column type changes (MG004), `NOT NULL` without a `DEFAULT` (MG005, MG006), PostgreSQL index builds without `CONCURRENTLY` (MG007, MG008), foreign keys validated in-place (MG009), `VACUUM FULL` and `CLUSTER` (MG012). `warning` is "works, but check intent": renames that break clients (MG010), `CONCURRENTLY` inside a transaction block where it will simply fail at execution time (MG011), and `DO` blocks or statement types outside the known rule set (MG013).

Dialect awareness keeps the advice honest. The PostgreSQL-only rules — concurrency, `NOT VALID`, `CLUSTER` — do not fire for MySQL, SQLite, or `--dialect generic`, so you never get told to add `CONCURRENTLY` to a MySQL index. Meanwhile MySQL's `MODIFY COLUMN` type changes are caught by MG004's dialect-specific variant. Statement splitting handles the nasty parts — dollar-quoted bodies, nested block comments, MySQL backticks — so a semicolon inside a string does not fabricate a statement boundary.

## Exit codes and CI

The convention is shared across the tool family: `0` is clean (or report-only), `1` is an error such as a parse failure, `2` means the `--fail-on` threshold was met. Output comes in text, `--format json` (stable, `schema_version: 1`, with a `threshold_met` field so you do not re-implement severity ordering), and `--format markdown` for pull request comments.

```yaml
on:
  pull_request:
    paths:
      - "migrations/**"

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hix-pro/migration-guard@v0.3.1
        with:
          paths: migrations
          fail-on: destructive
```

The `paths:` filter is doing real work here: the job only runs when a migration changed, so the guard costs nothing on ordinary pull requests. The action fetches a prebuilt binary and falls back to compiling if needed.

## Run it with the suite

The CLI tools share a runner. [`hix`](https://github.com/hix-pro/hix) looks for the tools installed on `PATH`, applies a check plan, and prints one table with one exit code:

```sh
pipx install git+https://github.com/hix-pro/hix.git
hix check
```

It installs nothing and sends no telemetry. A tool that is missing or needs configuration is reported as skipped, with the command that fixes it; commit a `.hix.toml` when you want the plan to be explicit.

## What it will not do

Static analysis cannot see your data volumes, your statement timeouts, or your replication topology — a `CREATE INDEX` that takes two seconds on a staging table takes twenty minutes on production, and no parser knows that. It does not connect to anything, so it cannot check whether `CONCURRENTLY` will actually succeed on your replica set, and it does not understand stored procedures beyond flagging them (MG013) as a signal to look manually. MySQL support covers the shared rule set plus dialect variants; it is not a MySQL-specific linter. What it does guarantee: every rule has unit tests, exit codes and dialect behavior have integration tests against committed fixtures, and nothing about your schema ever leaves the machine.

Migration Guard is MIT-licensed, needs Rust 1.85+ to build from source, and skips compiling entirely if you prefer: every release ships prebuilt binaries for Linux, macOS (Apple Silicon), and Windows with SHA-256 checksums.

It is part of the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. If your pre-production checklist also includes environment drift, [EnvAudit](https://github.com/hix-pro/env-audit) covers it; if you consume third-party APIs, [API Watch](https://github.com/hix-pro/api-watch) catches breaking contract changes before they reach your code; if you review Terraform, [PlanGuard](https://github.com/hix-pro/planguard) reads the plan before apply.
