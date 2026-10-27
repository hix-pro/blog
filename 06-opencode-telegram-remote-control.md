---
title: Remote-controlling OpenCode from Telegram
published: false
tags: python, telegram, ai, automation
---

Coding agents have a workflow problem: they work when you sit in front of them. You kick off a task, and then you wait — refreshing a terminal, checking whether the agent hit a permission prompt, re-reading output you cannot interact with. The moment you step away from the desk, the agent either stalls on an approval or finishes and sits idle until you come back.

[OpenCode Telegram](https://github.com/hix-pro/opencode-telegram) is a bridge that puts a local OpenCode server in your pocket. It is an independent community tool — not built by the OpenCode team — that talks to the server's local HTTP API. From Telegram you get live streaming of what the agent is doing (the message edits in place as tokens arrive), session switching, model and agent switching, file and shell commands, and — the important one — permission approvals from your phone: the bridge pings you with inline Yes/No buttons when the agent wants to do something your policy does not auto-answer.

## Architecture in one paragraph

`bridge.py` long-polls Telegram on the main thread and runs five background workers: a worker that dispatches queued prompts one turn at a time, an events thread holding one SSE connection to `/api/event` for live text deltas, a watcher that answers permission requests per your policy (auto-approving what you allowed, pinging with buttons for the rest), and a scheduler for due `/schedule` prompts. Each running turn gets its own thread. Because commands run on the main thread, `/abort`, `/yes`, and `/no` still respond instantly while the agent is mid-turn — the exact moment you need them.

The instruction to the machine is one line in spirit: nothing the agent does may block the chat, and nothing you type may block the agent.

## Setup is four commands

```bash
# 1. Create a bot with @BotFather, copy the token
# 2. Message the bot once, then read your chat id:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"

# 3. Configure
cp .env.example .env
chmod 600 .env          # it holds a bot token
$EDITOR .env            # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 4. Install and run
./install.sh
```

`install.sh` checks prerequisites, generates systemd user units from repo templates (any checkout location works, spaces included), and starts the service. It is safe to re-run after an upgrade and never overwrites your `.env` or state. The bridge warns at startup if your `.env` is group- or world-readable. Send `/doctor` and it reports the server, session, policy, event stream, permission watcher, and scheduler in one message — every subsystem answers, so misconfiguration is a diagnosis rather than an evening. On start the bridge also publishes its command list to Telegram, so every `/` autocompletes with a description and a persistent main menu (Status · Sessions · New · Abort · Help) attaches to the chat.

## The testing lesson worth stealing

Here is the bug that shaped the project's test suite. The original hermetic suite faked the OpenCode HTTP API — and everything was green. It was also wrong: the fake ignored a query parameter, and the bridge worked flawlessly against the fake and not at all against the real server. Green tests, broken product, because the tests validated the mock's idea of the protocol instead of the protocol. The fix ships in the repo: a **live** suite, opt-in via `pytest -m live`, that talks to a real OpenCode server — creates a throwaway session in a temporary directory, exercises prompt, streaming, shell, filesystem, concurrency, and abort behavior, then deletes the session. Hermetic tests still cover the logic; the live suite exists precisely for the assumptions hermetic tests cannot check. If you build against someone else's HTTP API, build the second suite too.

## Security posture

The bridge assumes one trusted operator and enforces it: `TELEGRAM_CHAT_ID` is an allowlist, and messages from any other chat are ignored before parsing. The bot token lives in a `chmod 600` file. Path handling for file commands is guarded (no `..` escapes outside the configured root), permission policy is explicit and inspected (`/policy` to view it), and the hardening docs cover running the bridge under a dedicated user with systemd sandboxing. Everything runs on your machine; Telegram is the transport, not the brain.

## What it will not do

It is a bridge, not a wrapper: no prompt rewriting, no extra model calls, no message history of its own beyond the state file that tracks sessions and schedules. It requires a running OpenCode server on localhost and Telegram's Bot API — no webhooks, so no public endpoint to expose; the bridge polls outward. Long turns edit one message live rather than spamming new ones, with rate-limit-aware throttling. Python 3 with no exotic dependencies, MIT-licensed, and the systemd units ship hardened out of the box.

It is one of seven tools in the [hix tools](https://github.com/hix-pro#readme) suite — local-first, no backend, CI-ready. If this one made you look at your workflow tooling, [RepoRace](https://github.com/hix-pro/reporace) ranks GitHub repositories by momentum, and the rest of the suite covers the pre-production checklist: [EnvAudit](https://github.com/hix-pro/env-audit), [Migration Guard](https://github.com/hix-pro/migration-guard), [API Watch](https://github.com/hix-pro/api-watch), [ActionLens](https://github.com/hix-pro/action-lens), [ComposeMap](https://github.com/hix-pro/compose-map).
