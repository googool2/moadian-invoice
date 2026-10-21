---
name: moadian-invoice
description: 'Iranian Moadian e-invoices (سامانه مودیان، صورتحساب الکترونیکی، tp.tax.gov.ir), offline: build invoice JSON from a sale, validate or debug a rejected invoice, explain error codes (e.g. 0300101), fields and invoice types, and generate or check the 22-character taxid (شماره منحصر به فرد مالیاتی) with bundled scripts. Field meanings, required fields and truncation rules come from the official INTA guideline and are easy to get wrong from memory, so consult this skill first — before answering, reading or editing the invoice — whenever a message mentions مودیان or moadian, صورتحساب الکترونیکی, شماره مالیاتی or taxid, a Moadian error code, or keys such as inty, inp, ins, tob, tprdis, tadis, tvam, tbill, sstid, setm, cap, insp, even in casual Persian ("چرا سامانه رد کرد"). For actually sending, use the moadian-send skill. Not for payroll or income tax, general VAT-rate questions, or ordinary invoices that are not for Moadian.'
---

# Moadian e-invoice

The Moadian JSON uses cryptic keys (`tprdis`, `tvam`, `inty`, `inp`, `ins`, …) whose meanings,
types and arithmetic are fixed by INTA documents; guesses get rejected.

**Say little, run the script.** Scripts compute and check; you pick inputs, run them, and explain
the output briefly. No invoice arithmetic in your head, no field meanings from memory.

Scripts are in `scripts/` next to this file (use its absolute path); Python 3.10+. All are
offline. `build_invoice.py` needs `pip install moadian-full`; the others need only the standard
library. `scripts/_moadian.py` loads moadian-full (its `import moadian_full` is broken) without
its network code; never edit site-packages.

| user wants | go to |
|---|---|
| an invoice from a sale | §1 |
| why a JSON is rejected / check one | §2 |
| an error code explained | §3 |
| a field, type or pattern explained | §4 |
| a taxid generated or checked | §5 |
| to send or inquire | the **moadian-send** skill (needs explicit confirmation) |

## §1 Build
1. **Fix the type first:** `inty`, `inp`, `ins` from `references/invoice-types.md`. If the deciding
   facts are missing (buyer's economic code? legal or natural person? export, gold, contracting?
   original or correction?), ask one short question. Don't pick a type the facts don't support.
2. Collect: memory id, seller economic code, date, buyer (type + `tinb`, or national id + postal
   code), and per line `sstid` (13 digits), quantity, unit price in **rial**, the **line's total
   discount**, VAT rate. Convert toman (×10) only if the user said toman, and say so.
3. Write a small YAML (format: docstring of `scripts/build_invoice.py`; example
   `examples/build-input.yaml`), then `python scripts/build_invoice.py input.yaml -o invoice.json`.
   Use `--serial` only for the user's own serial sequence.
4. If the report's `ok` is false, fix the input and rebuild; never hand-edit numbers. Tell the user
   type/pattern, taxid, `tbill` and every warning — above all an `indatim` older than a week (the
   system will likely reject it). Two or three lines. Building is not sending.

## §2 Validate or debug
`python scripts/validate_invoice.py invoice.json --text` (add `--now <epoch-ms>` for the date window).
- Report each error's path, expected and actual value and source as given; add nothing the
  validator didn't report. `notes` list what is not machine-checked — label them as such.
- `code_hint` is a *likely* system code, not a certainty.
- `id-check-digit` warning: a national code / legal id fails its check digit (open-source
  algorithm). Ask the user to re-check the number; never change digits yourself.
- Fix by rebuilding from source data, or by correcting only the named fields, then re-run the
  validator and show it passes. moadian-full output has known defects: `references/fields.md` §4.

## §3 Explain an error code
`python scripts/explain_error.py 0300101` or `--from-response inquiry.json`. Give meaning, field
and fix from the output. If `found` is false, say so, give only the `structure` decode and quote
the system's raw message. Entries are from secondary sources; pass on `[UNVERIFIED]` labels. For
0300101 also run `taxid.py validate` (§5).

## §4 Explain fields, types, rules
Answer from the references and cite the section (e.g. "S1 §7-39"): `references/fields.md`
(every field, Persian name, type, required), `references/invoice-types.md` (inty/inp/ins, enums,
per-pattern matrix), `references/arithmetic-rules.md` (formulas, truncation, settlement),
`references/units.md` (`mu` unit codes: 1627 عدد, 164 کیلوگرم, …). Not in
the references → say there is no sourced answer. Often guessed wrong: `dis` is the line total;
`cap`/`insp` exclude VAT and are only for `setm=3`; `tob` 1 = natural, 2 = legal; truncate, never round.

## §5 taxid
`python scripts/taxid.py generate --memory-id A11216 --date 2026-04-21T12:00:00+03:30 --serial 26`,
`… validate <taxid> --indatim <ms> --inno <hex>`, `… decode <taxid>`. Algorithm:
`references/workflow.md` §2. Never use moadian-full's `TaxIdGenerator` (wrong check digits).

## Rules you must not bend
- **Keys:** never ask for, echo or store a key or certificate. If one is pasted, don't store it
  and tell the user to rotate it.
- **Not tax advice:** taxability, rates and the legally right type are for the user and their
  accountant; say so whenever you recommend a type, pattern or rate.
- **No invented meanings:** references or `[UNVERIFIED]`.

## Output style
Lead with the result, then a few lines; point to files instead of pasting JSON. If the user
writes Persian, answer in Persian: Persian digits for amounts and counts in prose (۲۳۶٬۰۰۰٬۰۰۰
ریال); Latin digits for anything the user may copy or search — error codes (0300101), field
names, taxid, sstid, JSON and commands; correct half-spaces (می‌شود، صورتحساب‌ها); «صورتحساب».
