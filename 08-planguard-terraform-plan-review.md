---
title: "Terraform plans hide the risk. PlanGuard reads them."
published: false
description: PlanGuard reads terraform show -json output and flags the changes a plan diff treats equally — stateful destroys, public ingress, wildcard IAM, disabled encryption, and plaintext secrets.
tags: terraform, infrastructure-as-code, devops, security
series: hix tools — local-first dev tools
cover_image: https://raw.githubusercontent.com/hix-pro/blog/main/covers/08-planguard.png
---

A Terraform plan is a diff against production, and a line diff treats every change equally. A tag update and a database replacement scroll past at the same speed. A security group rule that opens SSH to the world sits three lines below a renamed bucket. The plan is technically complete, and still easy to approve without seeing the one change that matters.

[PlanGuard](https://github.com/hix-pro/planguard) reads the structured JSON behind `terraform plan` and classifies changes by what they can break. It does not need cloud credentials, a backend, or a Terraform binary at review time. It reads one file — the output of `terraform show -json` — and reports the findings a reviewer would ask about.

## What a run looks like

```console
$ terraform plan -out=tfplan
$ terraform show -json tfplan > plan.json
$ planguard review plan.json
PlanGuard · 0.1.0
Plan      plan.json
Tooling   Terraform 1.9.5 · format 1.2
Resources 10
Changes   9 changes (4 create, 2 update, 1 delete, 2 replace)

critical (5)
  destroy             aws_db_instance.main
    deleting a stateful resource destroys data that this plan cannot recover (removed from configuration)
  public-ingress      aws_security_group.web (ingress)
    tcp/22 is open to 0.0.0.0/0
  iam-policy          aws_iam_policy.deploy (policy)
    policy allows Action "*" on every resource
  public-access       aws_db_instance.analytics (publicly_accessible)
    publicly_accessible is enabled; the database accepts connections from the internet
  public-access       aws_s3_bucket_acl.assets (acl)
    bucket ACL is public-read; anyone can read or write objects in the bucket

error (2)
  replace             aws_ebs_volume.data (lifecycle)
    replaces a stateful resource; the old object and its data are destroyed (forced by availability_zone)
  encryption          aws_db_instance.analytics (storage_encrypted)
    database storage encryption is disabled

warning (4)
  replace             aws_instance.web (lifecycle)
    replaces this resource (delete and create) (tainted)
  drift               aws_security_group.legacy
    this resource changed outside Terraform before this plan
  deletion-protection aws_dynamodb_table.sessions
    deletion protection is being turned off
  deletion-protection aws_s3_bucket.logs (force_destroy)
    force_destroy is enabled, so the bucket can be deleted with its contents

info (1)
  secret              aws_db_instance.analytics (password)
    a plaintext secret-looking value is present in the plan

Summary: 10 resources · 9 changes (4 create, 2 update, 1 delete, 2 replace) · 12 findings (5 critical, 2 errors, 4 warnings, 1 info)
Result: report only (use --fail-on critical|error|warning|any to gate CI)
```

The report never contains the secret value itself. It names the attribute path and says the value is present in the plan file.

## The severity model

PlanGuard has four severities and a deliberately small rule set:

| Kind | Severity | What it looks for |
| --- | --- | --- |
| `destroy` | critical / warning | A resource is deleted. Critical for stateful types, warning otherwise. |
| `replace` | error / warning | A resource is deleted and recreated. Error for stateful types, warning otherwise. |
| `drift` | warning | A managed resource changed outside Terraform before this plan. |
| `public-ingress` | critical / error / warning | A new internet-facing rule. Critical on sensitive ports or all traffic, error on other TCP/UDP ports, warning on other protocols. |
| `iam-policy` | critical / error / warning / info | Public principals, `Action: "*"`, service wildcards, and GCP owner/editor or public bindings. Conditions reduce severity. |
| `public-access` | critical / error / warning | Public bucket ACLs and containers, public databases, disabled public-access blocks, and public storage transitions. |
| `encryption` | error / warning | Encryption disabled on databases, volumes, file systems, caches, and clusters. |
| `deletion-protection` | warning | Deletion protection turned off, or `force_destroy` enabled on a bucket. |
| `secret` | info | A plaintext secret-looking value is present in the plan. |
| `plan-errored` | critical | The plan reports an error. |
| `plan-incomplete` | warning | The plan is incomplete and needs another round. |

Critical means "this plan can destroy data or expose a sensitive service to the internet." Error means "this is a real operability or security regression, but not necessarily unrecoverable." Warning means "a reviewer should see this; it may be intentional." Info is context, not a failure.

The stateful classification is the part that changes the most decisions. Managed databases, DynamoDB tables, EBS and EFS volumes, S3 and GCS buckets, Azure storage accounts and disks, SQS/SNS queues, KMS keys, secrets, and persistent volumes all count. So do types ending in `*_snapshot`, `*_volume`, `*_filesystem`, and `*_secret_version`. Destroying a stateless web server is usually a replace; destroying the database behind it is data loss.

## Report first, gate second

The default is report-only. `planguard review plan.json` prints the report and exits `0`, even when it finds a critical issue. Gating is explicit:

```sh
planguard review plan.json --fail-on error
```

`--fail-on` is inclusive. `error` fails on critical and error findings; `warning` adds warnings; `any` includes informational findings. Exit codes follow the family convention: `0` for success or report-only, `1` for usage, I/O, or plan parse errors, `2` when the threshold is met. The distinction matters in CI: a malformed plan is a tooling failure, not a security finding, and the job should say so.

Findings can be filtered with `--ignore`. It accepts an exact resource address, a resource type, or a finding kind, and the flag can be repeated:

```sh
planguard review plan.json \
  --ignore aws_db_instance.legacy \
  --ignore aws_s3_bucket \
  --ignore secret
```

Ignored patterns are listed in the report, so the decision stays visible. Ignores filter findings, not resources; change counts still describe the whole plan. Prefer the narrowest pattern that works: an address, then a type, then a kind.

## In CI

Generate the plan, convert it to JSON, then let the action upload SARIF to code scanning:

```yaml
name: Terraform plan review

on:
  pull_request:

permissions:
  contents: read
  security-events: write

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - uses: hashicorp/setup-terraform@v3

      - name: Terraform plan
        run: |
          terraform init
          terraform plan -out=tfplan
          terraform show -json tfplan > plan.json

      - uses: hix-pro/planguard@v0.1.0
        with:
          plan: plan.json
          fail-on: error
```

The action needs cloud credentials because Terraform needs them to create the plan. PlanGuard itself only reads `plan.json` on the runner. SARIF maps critical and error findings to `error`, warnings to `warning`, and informational findings to `note`; each result points at the plan file. Stdin input is reported as `terraform-plan.json`, and absolute plan paths use the basename.

For a local run or a non-GitHub CI system, the CLI is the same tool:

```sh
cargo install --git https://github.com/hix-pro/planguard
planguard review plan.json --markdown --fail-on error
```

`--json`, `--markdown`, and `--sarif` are mutually exclusive. JSON is stable within a major version (`schema_version: 1`) and findings are ordered by severity, kind, resource, and attribute, so diffs between runs stay small.

## Run it with the suite

PlanGuard is part of [`hix`](https://github.com/hix-pro/hix), the runner that finds the tools you have installed and applies a check plan:

```sh
pipx install git+https://github.com/hix-pro/hix.git
hix check
```

If `.planguard/plan.json`, `plan.json`, or `tfplan.json` exists, `hix` runs `planguard review <plan> --json --fail-on error` automatically. Critical and error findings fail the suite; warnings stay visible in the severity breakdown. The runner never installs anything or phones home.

## What it will not do

PlanGuard supports Terraform plan JSON format 1.x. A binary plan file must be converted with `terraform show -json`; the tool will tell you that instead of guessing. It analyzes the plan, not the configuration or provider schema — stateful detection and secret detection are name-based heuristics, not a proof about your data. Unknown values, variables, and provider defaults are whatever the plan contains; PlanGuard does not resolve them. It is a review aid, not a policy engine, and it does not replace provider-specific security controls or a human reading the plan.

The rules are conservative on purpose. They are designed to stay quiet on routine churn and to surface the changes a reviewer would ask about. When a heuristic is wrong, `--ignore` is the escape hatch, and the ignore stays in the report.

PlanGuard is MIT-licensed, has no runtime dependencies, and ships prebuilt binaries for Linux x86_64, macOS Apple Silicon, and Windows x86_64 with SHA-256 checksums. The test suite covers the analyzer, each check family, all four output formats, thresholds, ignores, stdin, and invalid input.

It is one of ten tools in the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. Siblings: [EnvAudit](https://github.com/hix-pro/env-audit) for environment drift, [Migration Guard](https://github.com/hix-pro/migration-guard) for dangerous SQL migrations, [API Watch](https://github.com/hix-pro/api-watch) for API contract changes, [ActionLens](https://github.com/hix-pro/action-lens) for workflow review, [ComposeMap](https://github.com/hix-pro/compose-map) for Compose files, [LockLens](https://github.com/hix-pro/locklens) for lockfile drift, [TypeShift](https://github.com/hix-pro/typeshift) for TypeScript semver, [RepoRace](https://github.com/hix-pro/reporace) for repository momentum, and [OpenCode Telegram](https://github.com/hix-pro/opencode-telegram) for running coding agents from your phone.
