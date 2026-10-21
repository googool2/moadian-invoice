---
name: moadian-invoice
description: 'Iranian Moadian e-invoices (سامانه مودیان، صورتحساب الکترونیکی، tp.tax.gov.ir): build invoice JSON from a sale, validate or debug a rejected invoice, explain Moadian error codes (e.g. 0300101), fields and invoice types, and generate or check the 22-character taxid (شماره منحصر به فرد مالیاتی) with bundled offline scripts. Field meanings, required fields and truncation rules come from the official INTA guideline and are easy to get wrong from memory, so consult this skill first — before answering, reading or editing the invoice — whenever a message mentions مودیان or moadian, صورتحساب الکترونیکی, شماره مالیاتی or taxid, a Moadian error code, or JSON keys such as inty, inp, ins, tob, tprdis, tadis, tvam, tbill, sstid, setm, cap, insp, even in casual Persian ("فاکتور رو برای مودیان بفرستم", "چرا سامانه رد کرد"). Not for payroll or income tax, general VAT-rate questions, or ordinary invoices that are not for Moadian.'
---

# Moadian e-invoice

The Moadian JSON uses short cryptic keys (`tprdis`, `tvam`, `inty`, `inp`, `ins`, …) whose
meanings, types and arithmetic are fixed by INTA documents. Guessing them produces invoices the
system rejects. This skill replaces guessing with sourced references and offline scripts.

**Core principle: say little, run the script.** The scripts compute and check; you choose the
inputs, run them, and explain their output briefly. Do not do invoice arithmetic in your head or
in the chat, and do not explain a field from memory.

## Setup

Scripts live in `scripts/` next to this file (use the skill's absolute path). Python 3.10+.

- `validate_invoice.py`, `taxid.py`, `explain_error.py` need only the standard library.
- `build_invoice.py` needs `pip install moadian-full`. Its package folder is named
  `moadian-full`, so `import moadian_full` fails; `scripts/_moadian.py` loads it correctly and
  without importing any network code. Never "fix" this by editing site-packages.
- Only `send_invoice.py` touches the network, and only through its `send`, `inquiry` and
  `fiscal-info` commands (§6). Its `prepare` command and every other script are offline.

## Decide what the user needs

| user wants | do this |
|---|---|
| an invoice from a sale / factor | §1 Build |
| to know why a JSON is rejected, or to check one | §2 Validate |
| the meaning of an error code | §3 Explain error |
| the meaning of a field / type / pattern | §4 Explain fields |
| a taxid generated or checked | §5 taxid |
| to actually send or inquire | §6 Send — needs explicit confirmation |

## §1 Build an invoice

1. **Fix the type first.** Settle `inty` (type 1/2/3), `inp` (pattern) and `ins` (subject) before
   anything else, using `references/invoice-types.md`. If the facts that decide it are missing
   (does the buyer have an economic code? legal entity or person? is it export, gold,
   contracting…? original or correction?), ask one short question. Do not pick a type the user
   has not supported with facts.
2. Collect the minimum: memory id (6 chars), seller economic code, date, buyer (type plus `tinb`, or
   national id plus postal code), and for each line `sstid` (13 digits), quantity, unit price in
   **rial**, the **line's total discount**, and VAT rate. Convert toman to rial only if the user
   clearly said toman (×10), and say that you did.
3. Write a small YAML input (format in the docstring of `scripts/build_invoice.py`; example in
   `examples/build-input.yaml`) and run:

   ```bash
   python scripts/build_invoice.py input.yaml -o invoice.json
   ```

   Pass `--serial` only if the user has their own serial sequence. Otherwise moadian-full's
   SerialManager picks one (stored in `~/.moadian-invoice/`).
4. The report lists `corrections_to_moadian_full` and the validation result. If `ok` is false, fix
   the input and rebuild; do not hand-edit numbers. Tell the user in two or three lines: type and
   pattern, taxid, total (`tbill`), and any warnings. Mention the library corrections only if the
   user is a developer or asked.
5. Stop there. Building is not sending (§6).

## §2 Validate or debug a JSON

```bash
python scripts/validate_invoice.py invoice.json --text            # or JSON output without --text
python scripts/validate_invoice.py invoice.json --now <epoch-ms>   # also checks the date window
```

- Report each error with its path, expected and actual value, and source as the validator gives
  them. Do not add problems the validator did not report. You may point out things it lists as
  "not machine-checked" (the `notes`), clearly labelled as such.
- `code_hint` is the system code the error most likely produces (derived from the code scheme).
  Call it "likely code", not a certainty.
- An `id-check-digit` warning means a national code or legal-entity id fails its check digit
  (algorithm from open-source libraries, not INTA). Ask the user to re-check that number; never
  "fix" it by changing digits yourself.
- To fix: if the user has the source data, rebuild with `build_invoice.py`; otherwise correct only
  the fields the validator named, then **run the validator again** and show it passes.
- If the user's JSON came from moadian-full, its typical defects are listed in
  `references/fields.md` §4 (wrong taxid check digit, `dis × am`, `cap = tbill`, `insp = tadis`).

## §3 Explain an error code

```bash
python scripts/explain_error.py 0300101
python scripts/explain_error.py --from-response inquiry.json   # every code in an API response
```

Give the meaning, the field, and the fix from the output. If `found` is false, say the code is
not in the skill's list, give only the `structure` decode (error vs warning, check type, field),
and quote the raw message the system returned. All error entries come from secondary sources
(listed in `references/errors.md`); say so when it matters, and say "[UNVERIFIED]" when an entry
is marked that way. For 0300101, also run `taxid.py validate` (§5).

## §4 Explain fields, types and rules

Read the relevant reference and answer from it, citing the section (for example "S1 §7-39"):

- `references/fields.md`: every field, its Persian name, meaning, type, and whether it is
  required. It also lists where moadian-full disagrees with the documents.
- `references/invoice-types.md`: inty, inp and ins, the enumerations, and the full
  required/optional matrix per type and pattern.
- `references/arithmetic-rules.md`: formulas, truncation, settlement amounts, with a worked example.

If a field or rule is not in the references, say you do not have a sourced answer. Anything
marked `[UNVERIFIED]` must be passed on with that label. Points that are often guessed wrong:
- `dis` is the line total, not per unit.
- `cap` and `insp` exclude VAT and are needed only when `setm=3`.
- `tob` 1 is a natural person and 2 is a legal entity.
- Amounts are truncated, not rounded.

## §5 taxid

```bash
python scripts/taxid.py generate --memory-id A11216 --date 2026-04-21T12:00:00+03:30 --serial 26
python scripts/taxid.py validate A1121605054000000001A5 --indatim 1776760200000 --inno 000000001A
python scripts/taxid.py decode A1121605054000000001A5
```

The official algorithm is in `references/workflow.md` §3. moadian-full's own `TaxIdGenerator`
produces wrong check digits, so never use it directly.

## §6 Sending and inquiry

Read `references/workflow.md` first. Sending is two steps with `scripts/send_invoice.py`:

1. `python scripts/send_invoice.py prepare invoice.json --target sandbox` (or `live`). This is
   offline: it validates (including the one-week date window), refuses a taxid that already has
   a receipt, and prints a summary and a confirmation code bound to this exact file and target.
2. Show the user the summary: type and pattern, buyer, tbill, taxid, and sandbox or live. Ask
   whether to send. Their original request ("build and send") does not count as confirmation;
   confirm each send separately.
3. Only after an explicit yes, run
   `python scripts/send_invoice.py send invoice.json --target sandbox --confirm <code>`.
   - If the file or target changed after `prepare`, the code no longer matches and nothing is sent.
   - Keys come only from environment variables (`MOADIAN_MEMORY_ID`, `MOADIAN_PRIVATE_KEY_PATH`,
     `MOADIAN_CERT_PATH`). If they are missing, tell the user which ones to set in their own
     shell. Never ask for the key contents.
   - `--target live` also needs `MOADIAN_ALLOW_LIVE=1`. The user sets it themselves; never set
     it for them in a command.
   - `--target sandbox` needs `MOADIAN_SANDBOX_BASE_URL`, which the user gets from their
     trusted company or INTA. There is no sourced sandbox URL to suggest.
4. Report the uid and reference number. Processing is asynchronous: check later with
   `send_invoice.py inquiry --target … --uid <uid>`. If the status is FAILED, follow §3.
   If `send` fails with a network error, run `inquiry` before considering a resend.

## Rules you must not bend

- **Keys and certificates.** Load them only from a file path or an environment variable. Never
  ask for a key in the chat, never echo one, never write one into the repo, examples, config or
  logs. If a user pastes a key, do not store it, and tell them to rotate it.
- **No send without explicit confirmation**, as described in §6.
- **Not tax advice.** The skill checks format and arithmetic against INTA documents. Whether a
  sale is taxable, which VAT rate applies, or which type is legally right is for the user and
  their accountant. Say this whenever you recommend a type, pattern or rate.
- **No invented meanings.** Every field meaning comes from the references or is marked
  `[UNVERIFIED]`.

## Output style

- Be brief. Lead with the result (valid or not, or the built invoice's taxid and total), then at
  most a few lines. Do not paste the whole JSON unless asked; point to the file.
- If the user writes Persian, answer in Persian:
  - Use Persian digits in prose (۲۳۶٬۰۰۰٬۰۰۰ ریال, نوع ۱) and Latin digits inside JSON, code,
    commands and identifiers (taxid, sstid, field names).
  - Use correct half-spaces (ZWNJ): می‌شود, صورتحساب‌ها, شناسه‌ها.
  - Use the official spelling «صورتحساب».
- Name the source when you state a rule ("طبق دستورالعمل V7.8، بند ۷-۳۹ …").
