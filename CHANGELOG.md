# Changelog

All notable changes to this project. Versions follow [semver](https://semver.org) with this policy:

- **major** — could change what an invoice is accepted or rejected for, or what gets sent: a new
  blocking rule, a changed formula, or a change to the send flow or its safety checks.
- **minor** — new features, references, warnings or scripts; never looser safety.
- **patch** — fixes that bring behaviour back to what the docs already say.

Before 1.0.0, a minor bump may also include changes of the "major" kind; they are listed
under **Changed** with the word *behaviour*.

## [0.2.0] — unreleased

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

### Changed
- Layout: one plugin with two skills, `skills/moadian-invoice` and `skills/moadian-send`
  (SKILL.md was above the ~1.5k-token budget, and sending has its own triggers and risk).
- Sample ids in examples now pass their check digits (`10101234565`, `0012345679`).

### Fixed
- All scripts crashed with `UnicodeEncodeError` when their output was piped on Windows
  (cp1252); stdout is now UTF-8 everywhere.
- `build_invoice.py` wrote `sstt: ""` (invalid) when no description was given.

## [0.1.0] — 2026-10-21

### Added
- `moadian-invoice` skill: sourced field dictionary (RC_IITP.IS_V7.8), invoice types and
  per-pattern matrix, arithmetic rules, 88 error codes, workflow notes.
- `validate_invoice.py`, `build_invoice.py` (wrapper over moadian-full with every library
  defect corrected and listed), `taxid.py` (official algorithm), `explain_error.py`.
- Trigger and scenario evals with recorded results.
