# Changelog

All notable changes to this project. Versions follow [semver](https://semver.org) with this policy:

- **major** — could change what an invoice is accepted or rejected for, or what gets sent: a new
  blocking rule, a changed formula, or a change to the send flow or its safety checks.
- **minor** — new features, references, warnings or scripts; never looser safety.
- **patch** — fixes that bring behaviour back to what the docs already say.

Before 1.0.0, a minor bump may also include changes of the "major" kind; they are listed
under **Changed** with the word *behaviour*.

## [Unreleased]

### Fixed
- Digit-string fields (`tins`, `tinb`, `sstid`, `mu`, `bpc`, …) now reject Persian (۰-۹) and
  Arabic-Indic (٠-٩) digits, as the system's regex does (code shape `01FFF04`); `str.isdigit()`
  had let them pass. The error says to use Latin digits 0-9. Same fix in the check-digit helpers
  (`_ids.py`), `taxid.py` (`decode`, `validate`, and `generate`'s memory id) and the YAML reader,
  which had turned unquoted Persian digits into numbers.

## [0.2.0] — 2026-10-21

### Added
- `moadian-send` skill with `send_invoice.py`: offline `prepare` (validation, one-week date
  window, duplicate-taxid guard, confirmation code bound to the exact JSON and target) and
  `send --confirm`; read-only `inquiry` and `fiscal-info`. Keys only from environment variables;
  live sending needs `MOADIAN_ALLOW_LIVE=1` set by the user. No sandbox URL is shipped.
- Run-time fixes for moadian-full's send path: fresh `sigT` per signature, no server-key cache
  in the shared temp dir, per-target URLs, password-protected keys decrypted in memory.
- Check-digit warnings for 10-digit national codes and 11-digit legal-entity ids
  (algorithm from persian-tools; warnings because the source is not an INTA document).
- `--version` on every script; one version number in `scripts/_cli.py`.
- `bench/bench.py`: 13 valid "trap" invoices and 37 seeded defects with the expected field and
  severity; writes `bench/RESULTS.md` and `results.json`, exits non-zero on any miss.
- CI on Ubuntu, macOS and Windows × Python 3.10 and 3.13 (pyflakes, tests, benchmark).
- Measured results in `evals/results/`: 5 scenarios × 3 runs with and without the skill
  (assertions passed 96 % vs 51 %; median cost per run $0.142 vs $0.097), trigger evals
  20/20 for `moadian-invoice` and 6/6 for `moadian-send`, and the benchmark by version.
- README rewritten with hero image, icon, charts (light/dark SVG from `docs/charts/make_charts.py`)
  and an honest limits section; Persian README in step.

### Changed
- Layout: one plugin with two skills, `skills/moadian-invoice` and `skills/moadian-send`
  (SKILL.md was above the ~1.5k-token budget, and sending has its own triggers and risk).
- Sample ids in examples now pass their check digits (`10101234565`, `0012345679`).
- `build_invoice.py` validates against the current time, so the report flags an invoice older
  than one week (*behaviour*: new warning). Found by the scenario grader: 2 of 3 runs told the
  user a six-month-old invoice had no problems.
- Persian answers keep error codes, field names and ids in Latin digits.
- Scenario assertions corrected after the run: eval 1's "asked for confirmation" assertion was
  malformed (nobody asked to send); eval 1 now also checks `cap`/`insp` and the date warning.

### Fixed
- All scripts crashed with `UnicodeEncodeError` when their output was piped on Windows
  (cp1252); stdout is now UTF-8 everywhere.
- `build_invoice.py` wrote `sstt: ""` (invalid) when no description was given.
- `validate_invoice.py` crashed (`NameError`) on any invoice without `tprdis`, e.g. every export
  invoice — a missing import after the arithmetic moved to `_arith.py` in 0.1.0. Found by the
  new benchmark; pyflakes now runs in CI.
- A cancellation (`ins=3`) that omits `inty`/`inp` and still carries items got no warning.
  Found by the new benchmark.

## [0.1.0] — 2026-10-21

### Added
- `moadian-invoice` skill: sourced field dictionary (RC_IITP.IS_V7.8), invoice types and
  per-pattern matrix, arithmetic rules, 88 error codes, workflow notes.
- `validate_invoice.py`, `build_invoice.py` (wrapper over moadian-full with every library
  defect corrected and listed), `taxid.py` (official algorithm), `explain_error.py`.
- Trigger and scenario evals with recorded results.
