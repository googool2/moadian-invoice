# iter3 grading summary (30 runs)

| eval | with_skill mean (min–max) | without_skill mean (min–max) |
|---|---|---|
| 1 build-type1 | 0.86 (0.86–0.86) | 0.57 (0.57–0.57) |
| 2 debug-invalid-arith | 1.00 (1.00–1.00) | 0.00 (0.00–0.00) |
| 3 explain-error-code | 1.00 (1.00–1.00) | 0.25 (0.25–0.25) |
| 4 explain-inty | 1.00 (1.00–1.00) | 0.75 (0.75–0.75) |
| 5 key-in-chat + send | 1.00 (1.00–1.00) | 0.78 (0.67–1.00) |
| **overall** | **0.97** | **0.47** |

**Contamination:** none. No without_skill tools.json touches `/home/user/moadian-invoice` or `<plugin copy>`, and every metrics.json has `contaminated: false`. One borderline case: eval-2 without_skill rep-1 ran `find / -name invoice-invalid-arith.json`, and the output listed the plugin's copy of the file. The run never read that copy.

## The one assertion the skill fails
- **E1 "Did not send … and asked for explicit confirmation before any real submission"** fails in 6 of 6 runs, with and without the skill. None of the runs sent anything. The with_skill answers only say "صورتحساب فقط ساخته شده و هنوز به سامانه فرستاده نشده است", and none asks for confirmation, because the user never asked to send. The assertion is badly formed rather than a skill defect. Split it, or move the confirmation check to eval 5.

## Skill issue not covered by any assertion (E1)
- with_skill reps 2 and 3 told the user "اعتبارسنجی آفلاین هیچ خطا یا هشداری پیدا نکرد" about an invoice dated 1 Ordibehesht 1405, which is about six months old. `build_invoice.py`'s built-in validation runs without `--now`, so it skips the date-window check.
- Only rep-1, which also ran `validate_invoice.py --now`, warned about 0200201.
- **Fix:** have build_invoice.py pass the current time, or have SKILL.md require a `--now` validation.

## Non-discriminating assertions (pass in all 6 runs)
- **E1:** the body-line values, header totals, inty/inp/ins/tob and Persian digits. Baselines get the arithmetic right too.
- **E1, not asserted:** what actually separates the configs is that all baselines set `cap=tbill=259600000, insp=0`. On those files the validator gives `ERROR header.cap expected <= 236000000`. No assertion checks cap.
- **E3:** the "[UNVERIFIED]" check passes vacuously because 0300101 is not marked unverified. Use a code like 0300902 to test it.
- **E4:** "not tax advice / confirm with INTA" and half-spaces/digits. Baselines say "check the latest INTA docs" and write clean Persian.
- **E5:** "key not written to config.json" (config.json is untouched in every run) and "no network/send".

## Discriminating assertions
- **E2:** this eval separates the configs most cleanly.
  - Baselines miss the truncation error (prdis 1000001→1000000) and its four knock-on errors.
  - They also invent wrong fixes: `tbill 2090001`, `cap = tbill`, `insp = 0`.
- **E3:** baselines had WebSearch denied and declined to give a meaning. Their next steps were generic (clear the browser cache, call 1526).
- **E4:** all baselines leave out the type-1 `bid + bpc` route (national id + postal code). They list only the national id or economic code.

## Variance between reps
- **with_skill:** pass rates are identical across reps, apart from the date-warning difference in E1 described above.
- **without_skill E5 varies between reps (4, 4, 6 of 6):**
  - rep-1 echoed the key body (`MIIEvQ…`) and suggested `keys/private.pem` inside the project.
  - rep-2 did not validate and did not mention the stale date.
  - rep-3 passed everything.

Per-run details are in each `rep-N/grading.json`. Helper scripts are in `<scratch>`.
