<p align="center"><img src="docs/images/hero.jpg" alt="moadian-invoice: Moadian JSON keys next to their official meanings, and a validator run with 0 errors" width="100%"></p>

# <img src="docs/images/icon.png" alt="" width="40" align="absmiddle"> moadian-invoice

**Build, validate, explain and safely send Iranian Moadian e-invoices with Claude, without guessing.**

[![ci](https://github.com/googool2/moadian-invoice/actions/workflows/ci.yml/badge.svg)](https://github.com/googool2/moadian-invoice/actions/workflows/ci.yml)
[![version](https://img.shields.io/github/v/tag/googool2/moadian-invoice?label=version&sort=semver)](CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Claude | Skill](https://img.shields.io/badge/Claude-Skill-d97757)](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)

[فارسی](README.fa.md)

A Moadian invoice (سامانه مودیان, tp.tax.gov.ir) is JSON with keys like `tprdis`, `tvam`, `inty`,
`inp`, `setm`, `cap` and `insp`. Their meanings, types and arithmetic are fixed by the tax
authority's guideline. A model that guesses them writes invoices that look right and get
rejected. Even the Python library this skill builds on, `moadian-full` 0.0.2, computes the
tax-id check digit wrongly and puts VAT into the cash amount. This plugin gives Claude the
official meanings, cited field by field, and scripts that do the arithmetic, so Claude runs
a check instead of guessing. **Sourced, checked, offline by default.**

## What it does

| you ask | Claude does | with |
|---|---|---|
| "make a Moadian invoice for this sale" | settles type, pattern and subject; builds the JSON; fixes every `moadian-full` defect and lists it | `build_invoice.py` |
| "why was this JSON rejected?" | reports each wrong field with the expected value, the rule and the likely system code | `validate_invoice.py` |
| "what does 0300101 mean?" | gives meaning, field and fix, and decodes codes that aren't in its list | `explain_error.py` |
| "what's the difference between inty 1 and 2?" | answers from the cited references, with a not-tax-advice note | `references/` |
| "check this taxid" | generates, validates or decodes it with the official algorithm | `taxid.py` |
| "send it to the system" | offline prepare, a summary you approve, then send with a code bound to that exact file | `send_invoice.py` (separate skill) |

It ships as **two skills in one plugin**:
- `moadian-invoice` builds, validates and explains. It's fully offline.
- `moadian-send` sends and inquires. It's the only part that touches the network, and only after your explicit yes.

## Quick start

**Claude Code plugin (recommended)**

```
/plugin marketplace add googool2/moadian-invoice
/plugin install moadian-invoice@moadian-invoice
```

**Manual (Claude Code skills folder)**

```bash
git clone https://github.com/googool2/moadian-invoice /tmp/moadian-invoice
cp -r /tmp/moadian-invoice/skills/moadian-invoice /tmp/moadian-invoice/skills/moadian-send ~/.claude/skills/
```

**claude.ai.** Make one zip per skill and upload both under Settings › Capabilities › Skills:

```bash
for s in moadian-invoice moadian-send; do
  git archive --format=zip --prefix=$s/ -o $s.zip HEAD:skills/$s
done
```

**Codex.** Copy both folders into Codex's skills directory, usually `~/.codex/skills/`. That path
comes from third-party guides; check the [Codex docs](https://developers.openai.com/codex/skills).

**Requirements.** Python 3.10+.
- `validate_invoice.py`, `taxid.py` and `explain_error.py` use only the standard library.
- `build_invoice.py` and `send_invoice.py` need `pip install moadian-full`.

## How it works

Claude reads a short SKILL.md (about 1.1k tokens) and runs a script. It answers from the
script's output and the cited references. Here is a real run on the example invoice, which was
rejected for its arithmetic:

```
$ python scripts/validate_invoice.py examples/invoice-invalid-arith.json --text
INVALID: 8 error(s), 2 warning(s)
  ERROR body[0].prdis: prdis should be 1000000, found 1000001 [0204101] — S1 §7-38
  ERROR body[0].adis: adis should be 1000000, found 1000001 (follows from the corrected prdis) — S1 §7-40
  ERROR header.tvam: tvam should be 190000, found 180000 [0202501] — S1 §7-16
  ERROR header.tbill: tbill should be 2090000, found 2080001 (Σ of the corrected body tsstam) — S1 §7-18
  ERROR header.cap: cap is the cash amount EXCLUDING VAT … (expected <= 1900000, found 2080001) — S1 §7-23
  …
```

How to read it:
- Each error appears once, at its root. Fields derived from a wrong value say so, so one
  mistake doesn't read as five.
- The code in brackets is the system code the error most likely produces.
- `S1 §7-38` points to the section of the official guideline the rule comes from.

**Sources.** Field meanings, the per-pattern required/optional table and the formulas come
from the official guideline *RC_IITP.IS_V7.8* (اردیبهشت ۱۴۰۵). The taxid algorithm comes from
*RC_DCPS.SN_V1.3* and the official SDKs. The 102 unit codes for `mu` come from *RC_UMGS.ST_V1.18*
(اردیبهشت ۱۴۰۴). Error codes come from secondary sources and are
labelled as such. Anything without a source is marked `[UNVERIFIED]`. See
`skills/moadian-invoice/references/`.

## Benchmarks

### Accuracy and safety by version

Same synthetic benchmark (`bench/bench.py`): 13 valid but unusual invoices that must stay clean,
and 37 seeded defects that must be reported at the right field, at the root.

| version | valid invoices left clean | defects caught at the root | notes |
|---|---|---|---|
| 0.1.0 | 12 / 13 | 33 / 37 | crashed on export invoices and on cancellations with items; no ID check digits |
| 0.2.0 | **13 / 13** | **37 / 37** | |

The benchmark is itself tested. Breaking the validator on purpose (removing the taxid check,
rounding instead of truncating) makes it fail.

### Does it help an agent?

Five realistic scenarios were each run 3 times with the skill and 3 times without. The runs were
headless `claude -p` with Opus, isolated: project settings only, no MCP servers, inherited
environment removed, and a fresh folder outside the repo. An independent grader checked each
answer against written assertions. No baseline run reached the repo (contamination checked).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/charts/value-dark.svg">
  <img src="docs/charts/value-light.svg" alt="Assertions passed per scenario, with and without the skill (mean of 3 runs)">
</picture>

**Assertions passed: 96% with the skill, 51% without** (pooled over 15 runs each).

| scenario | with | without | turns (with / without) | seconds | cost per run |
|---|---|---|---|---|---|
| Build an invoice | **86%** | 57% | 5 / 3 | 21 / 46 | $0.16 / $0.19 |
| Debug a rejected JSON | **100%** | 0% | 5 / 3 | 22 / 26 | $0.13 / $0.11 |
| Explain error 0300101 | **100%** | 25% | 4 / 3 | 15 / 21 | $0.11 / $0.10 |
| Explain inty 1/2/3 | **100%** | 75% | 4 / 1 | 17 / 24 | $0.17 / $0.09 |
| Key in chat + 'send now' | **100%** | 78% | 5 / 2 | 23 / 21 | $0.14 / $0.09 |

What the numbers say, including what didn't help:
- **The gain is in the details a model gets wrong from memory.**
  - Without the skill, Claude never caught the truncation error and suggested wrong fixes
    (`cap = tbill`, `insp = 0`).
  - It couldn't explain 0300101.
  - It never offered the type-1 route for a buyer without an economic code (national id
    plus postal code).
  - Simple arithmetic was right in both configurations.
- **It costs more.**
  - Median $0.142 against $0.097 per run, and about
    70k against 44k tokens: Claude reads the
    skill and runs scripts.
  - It is faster: median 20 s against 25 s.
- **The skill's only miss is an assertion problem.** In "Build an invoice", the assertion "asked
  for confirmation before sending" failed in every run of both configurations, because nobody
  asked to send. The results above keep it as a failure.
- **A real problem the grader found.**
  - In 2 of 3 runs the skill told the user an invoice dated six months back had "no errors".
  - The builder validated without the current date.
  - This is fixed in 0.2.0 after these runs and not yet re-measured.
- **Safety: no run sent anything or wrote the pasted key to a file, with or without the
  skill.** One run without the skill repeated the key in its answer and suggested storing it
  inside the project.

Raw results: `evals/results/value-2026-10-21.json` and `evals/results/scenarios-iter3-2026-10-21.md`.

### Does it trigger when it should?

Trigger evals use the skill-creator `run_eval` script, with 3 runs per query, run one after
another. Each query is a realistic request; the "should not" queries are near-misses that share
keywords.

| skill | should trigger | should not trigger | correct |
|---|---|---|---|
| `moadian-invoice` | 10 (build, debug, error codes, gold, correction, field questions, in Persian and English) | 10 (salary tax, VAT rates, ordinary invoices, a Verhoeff function, the national-code check, Jalali dates…) | **20 / 20** (60 / 60 runs) |
| `moadian-send` | 3 (send, status, key setup) | 3 ("build but don't send", "email this PDF", a field question) | **6 / 6** (18 / 18 runs) |

The first time, these evals ran in parallel and scored 5/10. Parallel runs share one commands
folder, so each run saw several copies of the skill and often picked another run's copy. That
was a measurement problem, not a description problem: the same descriptions score fully when
run one after another. The sets are small (26 queries), so treat this as a smoke test, not a
precision estimate.

### CI

Every push runs pyflakes, the full test suite and the benchmark on Ubuntu, macOS and Windows with Python
3.10 and 3.13. Each run uploads its `RESULTS.md`.

## Safety rules

- **Nothing is sent without your explicit yes for that exact invoice.** `prepare` prints a
  confirmation code computed from the exact JSON, the target and the base URL. Any change
  afterwards voids the code.
- **Live sending needs `MOADIAN_ALLOW_LIVE=1`, which you set yourself.** The skill is told never
  to set it.
- **Keys and certificates come only from environment variables.**
  - A key inside a git repository is refused.
  - Password-protected keys are decrypted in memory only.
  - Keys pasted into the chat are never repeated, and the skill tells you to rotate them.
- **A taxid that already has a receipt is never sent again.** A resent taxid is rejected
  (0300101).
- **Invoices older than one week are blocked before sending** (S1 §7-2).
- **Not tax advice.** The skill checks format and arithmetic against the documents. Taxability,
  rates and the right type are for you and your accountant.

## Manual use

Every script works without Claude, and every script has `--help` and `--version`:

```bash
cd skills/moadian-invoice
python scripts/build_invoice.py examples/build-input.yaml -o invoice.json
python scripts/validate_invoice.py invoice.json --text
python scripts/taxid.py validate A1121605054000000001A5 --indatim 1776760200000
python scripts/explain_error.py 0300101
python ../moadian-send/scripts/send_invoice.py prepare invoice.json --target sandbox
```

## Versions and roadmap

See [CHANGELOG.md](CHANGELOG.md); versions follow semver. The major version changes when what is
accepted, rejected or sent changes.

Next:
- Confirm the error codes against the official EC_V02 list.
- Run the send path against a real sandbox.
- Test on real (anonymised) invoices.

## Limits

- **Sources.** The official PDFs were read from byte copies in a public GitHub repository,
  because intamedia.ir was unreachable while this was built. Their hashes are in `fields.md`.
- **Error codes.** All error-code meanings come from secondary sources.
- **Unit codes.** The `mu` list is RC_UMGS.ST_V1.18. A code outside it gets a warning, not an
  error, because INTA may have added codes since.
- **Newer fields.** V7.9-era fields (`insr`, `nti1`, `nti2`) are `[UNVERIFIED]`.
- **Not tested on real data:**
  - The send path has only been tested against a fake server, never against the real sandbox
    or the live system.
  - No real invoices from a taxpayer were tested. Phase 5 of the release plan was skipped for
    now.
- **Partial checks:**
  - Type-3 (POS receipt) invoices are only partly checked; the official table has no column
    for them.
  - Some conditionally mandatory fields are listed but not checked.
  - Online registries (whether an `sstid` exists, its VAT rate, a buyer's registration) are not
    checked.
- **ID check digits.** The check-digit algorithms for national codes and legal-entity IDs come
  from open-source libraries, so a failure is a warning, not an error.
- **Review.** Built and reviewed by its author with Claude. Not reviewed by a tax professional.

## License

MIT, see [LICENSE](LICENSE). `moadian-full` (GPL-3.0) is installed separately and is not
bundled.
