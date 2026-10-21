# moadian-invoice — design (playbook Phase 1)

## Job
Help Claude build, validate, explain and send Iranian Moadian e-invoices without guessing field
meanings. Users: Iranian developers integrating an ERP, and accountants debugging a rejected JSON.

## Triggers
مودیان / moadian, صورتحساب الکترونیکی, سامانه مودیان, شماره مالیاتی / taxid, tp.tax.gov.ir, a Moadian
error code (0300101…), invoice JSON keys (inty, inp, tprdis, tvam…). Not: payroll tax, general
VAT questions, ordinary invoices.

## Numbers that prove it works (measured, published as-is)
| # | metric | target | how |
|---|---|---|---|
| 1 | trigger accuracy | ≥ 90 % on 20 queries (10 near-miss negatives) | skill-creator `run_eval`, sequential, 3 runs each |
| 2 | validator recall on seeded defects | 100 % of defect kinds, each reported at its root | `bench/bench.py` mutation corpus |
| 3 | validator false alarms on valid "traps" | 0 errors | same corpus: gold, export, setm 3, cancellation, type 2, decimals… |
| 4 | taxid / id check digits | 100 % on official + library vectors | unit tests (exists) |
| 5 | agent value | pass rate with vs without skill, ≥ 3 reps per scenario; plus turns, tokens, seconds | headless `claude -p` (Phase 6) |
| 6 | send safety | 0 sends without a matching confirmation across adversarial prompts | fake-server tests + headless "send now" prompts |

## Safety design (the only parts that act on the outside world)
- **build** writes only the `-o` file and `~/.moadian-invoice/` (serial history); never the repo.
- **send** = plan / apply, no undo: `prepare` (offline dry run, prints a code bound to the exact
  JSON + target) → `send --confirm <code>` (apply). The real "undo" is a cancellation invoice
  (`ins=3`) that `build_invoice.py` can make; the skill must say this before any live send.
- No answer means no send. Live needs `MOADIAN_ALLOW_LIVE=1` set by the user. Keys only from env,
  never inside a git repo. A taxid with a receipt is never sent again.
- Protected: the skill never writes keys, `.env*`, `.git`, or files outside its output paths.

## Skill vs plugin
SKILL.md is ~1.9k tokens (above the ~1.5k guideline) and sending has different triggers
("بفرست", "ارسال به سامانه") and a different risk level. Proposal: one plugin, two skills —
`moadian-invoice` (build / validate / explain, offline) and `moadian-send` (prepare / send /
inquiry). Layout becomes `skills/<name>/SKILL.md` (playbook Phase 7); `git clone` into
`~/.claude/skills/` changes to copying `skills/moadian-invoice` (and `skills/moadian-send`).

## Adapting the playbook (it was written for a file-cleanup skill)
| phase | here |
|---|---|
| 2 Build | `--version` on every script; UTF-8 stdout (scripts crash on Windows pipes today — reproduced with cp1252); Python 3.10 floor tested |
| 3 Benchmark | mutation corpus: seeded defects (expected path + likely code) and traps that must stay clean; `RESULTS.md` + `results.json`, non-zero exit on any miss |
| 4 CI | GitHub Actions: ubuntu / macos / windows × Python 3.10 / 3.13, tests + bench, upload RESULTS.md |
| 5 Real-world | your real invoices (accepted and rejected), copied, validated, every finding labelled correct / debatable / wrong; output kept out of the repo |
| 6 Value | headless runs with `--setting-sources project --strict-mcp-config`, run in a copy outside the repo (iteration 2 had a baseline that found the repo); quota estimate first |
| 7–10 | packaging + CHANGELOG (major = changes what is accepted, rejected or sent), README with charts, privacy pass over every commit, tagged release — each public step asked first |
