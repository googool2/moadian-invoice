# Arithmetic and consistency rules

Read this to explain *why* a number is wrong. To find *which* numbers are wrong, run
`python scripts/validate_invoice.py invoice.json` — do not recompute totals by hand in the chat.
S1 = RC_IITP.IS_V7.8 (official). Notation as in S1: As=am, Cs=fee, Es=prdis, Gs=dis, Is=adis,
J=vra, Ks=vam, Ks2=odam, Ks3=olam, Os=tsstam, Xs=tbill, W=tvam, W2=todam, C=cap, Cr=insp,
RV=ssrv, TAs=tcpbs.

## 1. Rounding: truncate, never round (R1–R3)

- R1 «تمامی مقادیر ریالی و ارزی می‌بایست، با احتساب رقم اعشار ذکر شده در سند و با روش قطع کردن محاسبه و در صورتحساب ثبت گردد.» (S1 general rule 1)
- R2 Currency amounts keep 4 decimals, truncated (S1 footnote p.42).
- R3 Rial amounts (prdis, dis, adis, vam, odam, olam, tsstam, all header totals, cap, insp, tvop,
  tax17, cop, vop, pv, ssrv, sovat) are `dec(18,0)`, i.e. whole rials. am, fee, exr, cpr allow 8
  decimals; cfee, sscv, tocv 4; vra, odr, olr 2 (S1 §7 tables).

Example: adis = 99,999, vra = 10 → 9,999.9 → **vam = 9,999** (rounding to 10,000 is rejected;
a sandbox log shows half-up rounding answered with 0204501, errors.md E10).

## 2. Line formulas (body)

| # | rule | formula | source |
|---|---|---|---|
| R4 | amount before discount | `prdis = am × fee`; currency sale (P2) `cfee × exr`; airline (P6) `fee` | S1 §7-38 |
| R5 | discount bounds | `0 ≤ dis ≤ prdis`. **dis is the discount for the whole line**, not per unit and not a rate | S1 §7-39 |
| R6 | amount after discount | `adis = prdis − dis`; gold (P3) `prdis + tcpbs − dis` | S1 §7-40 |
| R7 | VAT | `vam = adis × vra / 100`; gold `(tcpbs × 10/100) + (prdis × vra/100)`; currency sale `sovat × vra / 100`; petroleum with a base amount `am × vba`; export `ssrv × vra / 100` | S1 §7-42 |
| R8 | other taxes / levies | `odam = adis × odr / 100` (`olam` with olr) when a rate exists, otherwise a fixed amount; export base ssrv, gold base tcpbs. If vra = 0 they are 0 | S1 §7-43 |
| R9 | line total | `tsstam = adis + vam + odam + olam`; export `ssrv + vam + odam + olam` | S1 §7-51 |
| R18 | currency amount | `cfee = fee / exr` (patterns other than P2) | S1 §7-33 |
| R19 | gold | `tcpbs = consfee + bros + spro`; each part < tcpbs; consfee < prdis | S1 §7-44…47 |
| R22 | fixed VAT rate | vra cannot change in corrections/returns/cancellations; vra = 0 for P7, P11, P14 | S1 §7-41 |

For the gold VAT formula S1 does not say whether each term is truncated separately; the validator
accepts either `trunc(a + b)` or `trunc(a) + trunc(b)`.

## 3. Header totals (R10–R11)

| header | equals | source |
|---|---|---|
| tprdis | Σ prdis (must be > 0) | S1 §7-13 |
| tdis | Σ dis | S1 §7-14 |
| tadis | Σ adis | S1 §7-15 |
| tvam | Σ vam | S1 §7-16 |
| todam | Σ odam + Σ olam | S1 §7-17 |
| tbill | Σ tsstam (export: torv + tvam + todam) | S1 §7-18 |
| tonw / torv / tocv | Σ nw / Σ ssrv / Σ sscv | S1 §7-19…21 |
| tvop | Σ vop | S1 §7-25 |

R11: `tbill = tadis + tvam + todam` is not printed in S1; it follows from R9 + R10 (derived).

## 4. Settlement amounts (R12–R16)

- R12 `cap = tbill − todam − tvam − insp`, `0 < cap < tbill` (S1 §7-23)
- R13 `insp = tbill − todam − tvam − cap`, `0 < insp < tbill` (S1 §7-24)
- R14 so **`cap + insp = tbill − tvam − todam`** (= tadis outside export). Both **exclude VAT**.
  They are mandatory only when setm = 3; S1 does not say what to send for setm 1 or 2. The official
  setm = 2 example (S2) omits them, and secondary logs show 14029/14030 warnings when they are sent
  anyway (errors.md E2). moadian-full's `cap = tbill, insp = tadis` contradicts R12–R14.
- R15 `cop = tsstam × cap / tadis` (multiply first, then divide; S1 §7-48)
- R16 `vop = vam × cap / tadis`; 0 when vra = 0 (S1 §7-49)
- R17 `tax17 ≤ tvam` (S1 §7-26)
- R20 `pv ≤ tbill`; pv = 0 when setm = 2 (S1 §7-60; S1 prints `Pv >= tbill` in one place but its text says ≤)

## 5. Dates and identifiers (R21)

- indatim: Unix **ms**, same UTC day as the taxid date part, not in the future (secondary: ~30 s
  tolerance, errors.md E1), sent within one week (S1 §7-2; secondary logs saw type 1 accepted up
  to ~13 days, E4). For ins 2/3/4 later than the reference invoice.
- cdcd, asd: Unix **days**; pdt: ms at day precision (S1 §7-11, §7-80, §7-59).
- taxid / inno: see workflow.md §3.

## 6. Worked example (S2, official connection spec)

```
body:   am 2, fee 10000 → prdis 20000; dis 500 → adis 19500; vra 9 → vam 1755; tsstam 21255
header: tprdis 20000, tdis 500, tadis 19500, tvam 1755, todam 0, tbill 21255, setm 2 (no cap/insp)
```

`dis` = 500 for a 2-unit line gives adis 19 500 — so dis is the line total (a per-unit reading
would give 19 000).
