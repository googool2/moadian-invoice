# moadian-invoice

An [Agent Skill](https://agentskills.io) that helps Claude build, validate, explain and debug
electronic invoices for Iran's **Moadian** tax system (سامانه مودیان, tp.tax.gov.ir).
[فارسی](README.fa.md)

## The problem

A Moadian invoice is JSON with short, cryptic keys: `inty`, `inp`, `ins`, `tob`, `tprdis`,
`tadis`, `tvam`, `tbill`, `setm`, `cap`, `insp`, … Without a reference, a model guesses what
they mean, and the guesses are plausible but wrong. For example:

- `dis` is the discount for the whole line, not per unit.
- `cap` and `insp` exclude VAT and are only used for mixed cash/credit settlement.
- `tob` 1 means a natural person.
- Amounts are truncated, never rounded.

Even the Python library this skill builds on, [`moadian-full`](https://pypi.org/project/moadian-full/)
0.0.2, gets several of these wrong, and its tax-id check digit fails every official example.

This skill removes the guessing:

- **Sourced references.** Every field meaning, type, enumeration and formula is cited to the
  official INTA guideline *RC_IITP.IS_V7.8* (اردیبهشت ۱۴۰۵) or another named source. Anything
  unsourced is marked `[UNVERIFIED]`.
- **Deterministic scripts.** These are offline Python scripts with no LLM, no network and only the
  standard library, plus `moadian-full` for the builder:

  | script | does |
  |---|---|
  | `scripts/validate_invoice.py` | checks structure, types, enums, per-pattern required fields, conditional rules, truncation arithmetic and the taxid; prints readable JSON (or `--text`) |
  | `scripts/build_invoice.py` | thin wrapper over moadian-full's `InvoiceBuilder`: simple YAML/JSON in, invoice JSON out, every library defect corrected and listed |
  | `scripts/taxid.py` | generates, validates and decodes the 22-character taxid with the official algorithm |
  | `scripts/explain_error.py` | turns an error code into its meaning and fix, and decodes the code structure when the code is not in the list |

- **Guard rails.** Keys are read only from files or environment variables. Nothing is sent
  without the user's explicit confirmation. The skill says plainly that it is not tax advice.

## Install

The scripts need Python 3.10+. Only `build_invoice.py` needs the library:

```bash
pip install moadian-full
```

**Claude Code (personal skill)**

```bash
git clone https://github.com/googool2/moadian-invoice ~/.claude/skills/moadian-invoice
```

**Claude Code (plugin marketplace)**

```
/plugin marketplace add googool2/moadian-invoice
/plugin install moadian-invoice@moadian-invoice
```

**claude.ai.** Build a zip that holds only the skill files, then upload it under
Settings › Capabilities › Skills:

```bash
git archive --format=zip --prefix=moadian-invoice/ -o moadian-invoice.zip HEAD \
  SKILL.md LICENSE references scripts examples
```

In claude.ai's sandbox the validator, taxid and error scripts work as they are. The builder
works only if `pip install moadian-full` is possible there.

**Codex.** Clone or copy the folder into Codex's skills directory, commonly
`~/.codex/skills/moadian-invoice`. That path comes from third-party guides; check the
[Codex skills docs](https://developers.openai.com/codex/skills).

## Before and after

Prompt: *“Build a Moadian invoice: 2 printers at 120,000,000 rial each, 4,000,000 rial discount
on the line, 10% VAT, cash, legal-entity buyer.”*

**Without the skill.** Claude wrote the JSON by hand. The arithmetic was right, but the header
carried `"cap": 259600000` (= tbill) and `"indati2m"`. The validator says:

```
INVALID: 1 error(s), 2 warning(s)
  ERROR header.cap: cap is the cash amount EXCLUDING VAT and other taxes, so it cannot exceed
        tbill − tvam − todam (expected <= 236000000, found 259600000) — S1 §7-23
```

**With the skill.** Claude ran `build_invoice.py` and got a valid invoice. The report also shows
what `moadian-full` alone would have sent:

```
header.taxid   A1121605054000000001A6 -> A1121605054000000001A5   official check digit
body[0].dis    8000000 -> 4000000     dis is the line total; the library multiplied it by am
header.cap     255200000 -> null      cash amount excl. VAT; only for setm=3
header.insp    232000000 -> null      CREDIT amount; this is a cash invoice
validation: ok, 0 errors, 0 warnings
```

## Repository layout

```
SKILL.md            instructions Claude follows (English, ~150 lines)
references/         fields.md, invoice-types.md, arithmetic-rules.md, errors.md, workflow.md
scripts/            the four CLIs + helpers (_spec.py = machine-readable field spec)
examples/           valid minimal/full invoices, an invoice with arithmetic errors, builder inputs
tests/              pytest suite (pip install pytest moadian-full; pytest)
evals/              triggers.json (trigger eval), outputs.json (scenario eval), results/
.claude-plugin/     plugin.json + marketplace.json
```

## Evaluation

- **Trigger eval** (`evals/triggers.json`, 5 should-trigger and 5 should-not prompts, skill-creator
  `run_eval`, 3 runs each): 10/10 correct. See `evals/results/`. The prompts must be run
  sequentially; parallel runs share one commands folder and under-report triggering.
- **Scenario eval** (`evals/outputs.json`). Three of the five scenarios were run with and
  without the skill; the results are summarised in the project report.

## Limitations

- **Source access.** The official PDFs could not be downloaded from intamedia.ir while this was
  written. They were read from byte copies in a public GitHub repository (hashes in
  `references/fields.md`).
- **Newer fields.** V7.9-era fields (`insr`, `nti1`, `nti2`, `hs`) are `[UNVERIFIED]`.
- **Error codes.** Every entry in `references/errors.md` comes from secondary sources: developer
  digests of the official list, vendor help pages and sandbox logs. Treat the meanings as strong
  hints, not as the official text.
- **Partial checks.** Type-3 invoices (POS receipts) are only partly checked, because the
  official requirements table has no column for them. Some conditionally mandatory fields
  (e.g. other taxes and waybill details) are listed but not machine-checked.
- **Online data not checked.** The skill cannot check online registries: whether an `sstid`
  exists, its VAT rate, or a buyer's economic code.
- **No signing or sending.** The scripts never sign or send. Sending goes through moadian-full's
  client after explicit confirmation; see `references/workflow.md`.
- **Licence.** `moadian-full` is GPL-3.0. This skill is MIT and does not bundle it; it imports
  it at run time.
- **Not tax advice.** The skill checks format and arithmetic against INTA documents. It does not
  decide what is taxable or which rate applies.

## License

MIT — see [LICENSE](LICENSE).
