# Moadian invoice field dictionary

Use this file to answer "what does field X mean / what type / is it required". Do not explain a
field from memory: if it is not here, say so. Required-ness per type/pattern is in
`invoice-types.md`; formulas are in `arithmetic-rules.md`. `scripts/validate_invoice.py` applies
all of it (its machine-readable copy is `scripts/_spec.py`).

## Sources

| id | document | kind |
|---|---|---|
| S1 | **RC_IITP.IS_V7.8** «دستورالعمل صدور صورتحساب الکترونیکی», INTA, اردیبهشت ۱۴۰۵, 112 pp. Copy read from github.com/ali-hallaji/digi-tax-ops `docs/moadian/RC_IITP_IS_V7_8.pdf` (sha256 starts `2770f6a5`, ends `7355`) because intamedia.ir was unreachable | official |
| S2 | **RC_TICS.IS v1.6** «دستورالعمل فنی اتصال به سامانه مودیان», شهریور ۱۴۰۴ (inner pages say v1.5). Same mirror (sha256 `a506795e…ec61`). Used for its worked JSON example | official |
| S3 | **RC_DCPS.SN_V1.3** «قالب شناسه یکتای حافظه مالیاتی و شماره منحصر به فرد مالیاتی», خرداد ۱۴۰۱. Same mirror | official |
| L | moadian-full 0.0.2 source (PyPI wheel): `invoice_builder.py`, `tax_id.py`, `verhoeff.py` | library |
| X1 | github.com/mojtabahakimian/Taxation — wire JSON captured from the official .NET SDK 0.0.34 and SDK shim comments | secondary |
| X2 | github.com/Mr0Hadi/OurERP — Moadian connection guide (digest of INTA documents) | secondary |
| X3 | persian-tools: npm `@persian-tools/persian-tools` 4.0.4 (`verifyIranianNationalId`, `verifyIranianLegalId`) and PyPI `persian-tools` 0.0.11 (`national_id`, `legal_id` + tests). Check-digit algorithms for national codes and legal-entity ids; see `scripts/_ids.py` | secondary (open source) |

Notation: type `str` string, `digits` numeric string (0–9 only, sent as a JSON string), `int`
integer, `dec(a,b)` number with ≤a integer and ≤b fraction digits. `dec(18,0)` = whole rials.
"Req" summarises S1 Table 1: **M** mandatory, **O** optional, **C** mandatory under conditions,
**–** ignored («خارج از الگو»). Data-format rules apply even to optional and ignored fields
(S1 general rule 3). Use lowercase JSON keys (`indati2m`, `tax17`) as the SDK sends them (X1),
although S1 prints `Indati2m` and `Tax17` in places.

## 1. Header (`header`, «سرآمد»)

| field | فارسی | meaning | type | req | source |
|---|---|---|---|---|---|
| taxid | شماره منحصر به فرد مالیاتی | Unique tax number: memory id (6) + day (5 hex) + serial (10 hex) + Verhoeff digit. An invoice without it is invalid | str 22 | M | S1 §7-1, S3 |
| indatim | تاریخ و زمان صدور صورتحساب (میلادی) | Issue time = time of the financial event, Unix **milliseconds**. Must be the same day as taxid, not in the future, sent within one week; for ins 2/3/4 later than the reference | int ≤13 | M | S1 §7-2 |
| indati2m | تاریخ و زمان ایجاد صورتحساب (میلادی) | Creation time; only for invoices under Articles 9 and 12 of the store-terminals law. Leave out otherwise | int ≤13 | C | S1 §7-3 |
| inty | نوع صورتحساب | Invoice type 1/2/3 — see invoice-types.md | int 1 | M | S1 §7-4 |
| inno | سریال صورتحساب داخلی حافظه مالیاتی | Internal serial of the tax memory, ascending, never repeated, **hexadecimal**. Send the serial part of taxid (`taxid[11:21]`) | str 10 | O | S1 §7-5; X2 for the taxid match |
| irtaxid | شماره منحصر به فرد مالیاتی صورتحساب مرجع | taxid of the referenced invoice; mandatory when ins is 2, 3 or 4 | str 22 | C | S1 §7-6 |
| inp | الگوی صورتحساب | Invoice pattern (sale, currency, gold, …) — see invoice-types.md | int ≤2 | M | S1 §7-7 |
| ins | موضوع صورتحساب | Subject: 1 original, 2 correction, 3 cancellation, 4 sales return | int 1 | M | S1 §7-8 |
| tins | شماره اقتصادی فروشنده | Seller economic code, as registered. An 11-digit code is the legal entity's national id, whose last digit is a check digit (validator warns if it fails) | digits 11 or 14 | M | S1 §7-9; check digit X3 |
| tob | نوع شخص خریدار | Buyer type: 1 natural person, 2 legal entity, 3 civil partnership, 4 non-Iranian | int 1 | M in type 1 (most patterns) | S1 §7-9 rule 3 |
| bid | شماره/شناسه ملی/شناسه مشارکت مدنی/کد فراگیر اتباع خریدار | Buyer national number (10), national id (11), partnership id (11) or foreign-national code (12). The 10-digit national code and 11-digit legal id carry a check digit (validator warns); partnership and foreign codes are not checked | digits 10/11/12 | O/C | S1 §7-9; check digit X3 |
| tinb | شماره اقتصادی خریدار | Buyer economic code. Type 1, tob 2/3: required. Type 1, tob 1/4: tinb **or** bid+bpc. 11 digits (legal entity) carry a check digit (validator warns, except tob 3) | digits 11 or 14 | C | S1 §7-9 rules 4–5; check digit X3 |
| sbc | کد شعبه فروشنده | Seller branch code | digits 4 | O | S1 §7-9 |
| bpc | کد پستی خریدار | Buyer postal code | digits 10 | O/C | S1 §7-9 |
| bbc | کد شعبه خریدار | Buyer branch code | digits 4 | O | S1 §7-9 |
| ft | نوع پرواز | Flight type: 1 domestic, 2 international (airline pattern) | int 1 | P6 M | S1 §7-9 rules 10–11 |
| bpn | شماره گذرنامه خریدار | Buyer passport number | str ≤9 | P2/P6 C, P7 O | S1 §7-9 |
| scln | شماره پروانه گمرکی | Customs licence number | digits ≤14 | P1/P2 O | S1 §7-9 |
| scc | کد گمرک محل اظهار فروشنده | Customs office code where the seller declared | digits 5 | P1/P2/P7 O | S1 §7-9 |
| cdcn | شماره کوتاژ اظهارنامه گمرکی | Customs declaration (cottage) number | str ≤14 | P7 O | S1 §7-10 |
| cdcd | تاریخ کوتاژ اظهارنامه گمرکی | Cottage date as Unix **days** (seconds/86400, truncated) | int 5 | P7 O | S1 §7-11 |
| crn | شماره قرارداد پیمانکاری | Contracting contract number registered in کارپوشه. S1 says ≤12 digits; the sandbox enforced exactly 12 (errors.md 0102004) | digits ≤12 | P4 M | S1 §7-9 rules 8–9 |
| billid | شماره اشتراک/شناسه قبض بهره‌بردار | Utility subscription number / bill id | digits ≤19 | P5 M | S1 §7-12 |
| tprdis | مجموع مبلغ قبل از کسر تخفیف | Σ prdis; > 0 | dec(18,0) | M | S1 §7-13 |
| tdis | مجموع تخفیفات | Σ dis; ≥ 0 | dec(18,0) | O | S1 §7-14 |
| tadis | مجموع مبلغ پس از کسر تخفیف | Σ adis | dec(18,0) | M | S1 §7-15 |
| tvam | مجموع مالیات بر ارزش افزوده | Σ vam | dec(18,0) | M | S1 §7-16 |
| todam | مجموع سایر مالیات، عوارض و وجوه قانونی | Σ odam + Σ olam | dec(18,0) | M | S1 §7-17 |
| tbill | مجموع صورتحساب | Σ tsstam (= tadis + tvam + todam; export: torv + tvam + todam) | dec(18,0) | M | S1 §7-18 |
| tonw | مجموع وزن خالص | Σ nw, kg | dec(15,8) | P7 C | S1 §7-19 |
| torv | مجموع ارزش ریالی | Σ ssrv | dec(18,0) | P7 M | S1 §7-20 |
| tocv | مجموع ارزش ارزی | Σ sscv | dec(14,4) | P7 M | S1 §7-21 |
| setm | روش تسویه | Settlement: 1 cash, 2 credit (نسیه), 3 mixed. Types 2 and 3 are always cash | int 1 | M in type 1 | S1 §7-22 |
| cap | مبلغ پرداختی نقدی | **Cash-paid amount, excluding VAT and other taxes**: `cap = tbill − todam − tvam − insp`. Mandatory only when setm = 3 | dec(18,0) | C | S1 §7-23 |
| insp | مبلغ نسیه | **Credit (نسیه) amount, excluding VAT and other taxes**: `insp = tbill − todam − tvam − cap`. Mandatory only when setm = 3 | dec(18,0) | C | S1 §7-24 |
| tvop | مجموع سهم مالیات بر ارزش افزوده از پرداخت | Σ vop (VAT share of the cash payment) | dec(18,0) | O | S1 §7-25 |
| tax17 | مالیات موضوع ماده ۱۷ | "Tax under Article 17", footnote: note 1 of Art. 17 of the VAT Act 1400. Only rule: 0 ≤ tax17 ≤ tvam. Its legal meaning is not explained in S1 [UNVERIFIED] | dec(18,0) | O | S1 §7-26 |
| tinc | شماره اقتصادی آژانس | Economic code of the travel agency that sold the ticket | digits 11/14 | P6 O | S1 §7-62 |
| lno, lrno | شماره بارنامه / بارنامه مرجع | Waybill number / original waybill number | digits ≤18 | P8 M / O | S1 §7-65, §7-66 |
| ocu, dco | کشور مبدا / مقصد | Origin / destination country code (S1 §8-4) | digits 3 | P8 M | S1 §7-67, §7-69 |
| oci, dci | شهر مبدا / مقصد | Origin / destination city code; mandatory if the country is Iran | digits ≤5 | P8 C | S1 §7-68, §7-70 |
| tid, rid | شناسه/شماره ملی فرستنده / گیرنده | Sender / receiver identity | digits 10/11/12 | P8 M / C | S1 §7-71, §7-72 |
| lt | نوع بارنامه/نوع حمل | Transport: 1 road, 2 rail, 3 air, 4 sea (S1's JSON sample shows a string) | int 1 | P8 M | S1 §7-73 |
| cno | شماره ناوگان | Fleet number: VIN / train / flight / ship number | str ≤20 | P8 M | S1 §7-74 |
| did | شماره ملی/کد فراگیر راننده | Driver id (road transport) | digits 10/12 | P8 C | S1 §7-75 |
| sg[] (sgid, sgt) | کالاهای حمل شده | Carried goods: 13-digit goods id (checked against stuffid.tax.gov.ir) and description ≤400. Structure not machine-checked | array | P8 M | S1 §7-76…78 |
| asn, asd | شماره / تاریخ اعلامیه فروش بورس | Exchange sale notice number (digits ≤30) / date (Unix day, int 5) | — | P11 M | S1 §7-79, §7-80 |
| in, an | شناسه یکتای بیمه‌نامه / الحاقیه | Insurance policy id / endorsement id (from بیمه مرکزی) | digits 9–12 | P13 M / O | S1 §7-81, §7-82 |
| insr, nti1, nti2 | قاعده ارسال صورتحساب / یادداشت ۱ / ۲ | Not in V7.8. Secondary code says V7.9 added a "send rule" and two notes; the official SDK capture carries them as null [UNVERIFIED] | ? | ? | X1, X2 |

## 2. Body item (`body[]`, «بدنه»)

| field | فارسی | meaning | type | req | source |
|---|---|---|---|---|---|
| sstid | شناسه کالا/خدمت | Goods/service id; must exist on stuffid.tax.gov.ir and its VAT rate must match. P11/P14 allow one line only | digits 13 | M | S1 §7-27 |
| sstt | شرح کالا/خدمت | Description of the line | str ≤400 | O | S1 §7-28 |
| am | تعداد/مقدار | Quantity, > 0. P6 and P8: 1 per line. Ignored in P2 | dec(18,8) | M | S1 §7-29 |
| mu | واحد اندازه‌گیری | Unit-of-measure **code** from the RC_UMGS.ST list (the list itself is not in this skill [UNVERIFIED]; `1627` appears for «عدد» in secondary sources) | digits ≤8 | O (P11 M) | S1 §7-30 |
| nw | وزن خالص | Net weight in kg per customs declaration | dec(15,8) | P7 C | S1 §7-31 |
| fee | مبلغ واحد | **Unit price in rial**, > 0. P7: ssrv/am. P8: base freight | dec(18,8) | M | S1 §7-32 |
| cfee | میزان ارز | Currency amount; outside P2 `cfee = fee / exr` | dec(14,4) | O (P2 M) | S1 §7-33 |
| cut | نوع ارز | Currency, ISO 4217 code | str 3 | O (P2, P7 M) | S1 §7-34 |
| exr | نرخ برابری ارز با ریال | Rial exchange rate; in P2 the **selling** rate on the issue date | dec(18,8) | O (P2, P7 M) | S1 §7-35 |
| ssrv | ارزش ریالی کالا | Rial value of the line per customs licence | dec(18,0) | P7 M | S1 §7-36 |
| sscv | ارزش ارزی کالا | Currency value of the line per customs licence | dec(14,4) | P7 M | S1 §7-37 |
| prdis | مبلغ قبل از تخفیف | `am × fee` (P2: `cfee × exr`; P6: `fee`) | dec(18,0) | M | S1 §7-38 |
| dis | مبلغ تخفیف | **Discount amount of the whole line** (not a rate, not per unit); 0 if none; ≤ prdis. moadian-full multiplies it by am — wrong | dec(18,0) | M | S1 §7-39; S2 example; L |
| adis | مبلغ بعد از تخفیف | `prdis − dis` (gold: `prdis + tcpbs − dis`) | dec(18,0) | M | S1 §7-40 |
| vra | نرخ مالیات بر ارزش افزوده | VAT rate in **percent**; must match the sstid's registered rate; 0 for P7, P11, P14; cannot change in referring invoices | dec(3,2) | M | S1 §7-41 |
| vba | مبلغ پایه مالیات بر ارزش افزوده | Base VAT amount per litre (petroleum pattern) | dec(18,4) | P9 C | S1 §7-83 |
| vam | مبلغ مالیات بر ارزش افزوده | `adis × vra / 100`, truncated (variants in arithmetic-rules.md) | dec(18,0) | M | S1 §7-42 |
| odt, odr, odam | موضوع / نرخ / مبلغ سایر مالیات و عوارض | Other tax or duty: subject (str ≤255), rate % (dec 3,2), amount (`adis × odr / 100` or a fixed amount) | — | C | S1 §7-43 |
| olt, olr, olam | موضوع / نرخ / مبلغ سایر وجوه قانونی | Other legal levies: same structure as od* | — | C | S1 §7-43 |
| consfee | اجرت ساخت | Gold: making fee (< prdis) | dec(18,0) | P3 M | S1 §7-44 |
| spro | سود فروشنده | Gold: seller's profit | dec(18,0) | P3 M | S1 §7-45 |
| bros | حق‌العمل | Gold: commission | dec(18,0) | P3 M | S1 §7-46 |
| tcpbs | جمع کل اجرت، حق‌العمل و سود | `consfee + bros + spro` | dec(18,0) | P3 M | S1 §7-47 |
| cop | سهم نقدی از پرداخت | Line's share of the cash payment, `tsstam × cap / tadis` (definition and formula disagree slightly in S1) | dec(18,0) | O | S1 §7-48 |
| vop | سهم مالیات بر ارزش افزوده از پرداخت | Line's VAT share of the cash payment, `vam × cap / tadis`. moadian-full sets vop = vam — only right if everything is paid in cash | dec(18,0) | O | S1 §7-49 |
| bsrn | شماره قرارداد حق‌العملکاری | Commission (agency) contract number from کارپوشه | digits ≤12 | O | S1 §7-50 |
| tsstam | مبلغ کل کالا/خدمت | Line total `adis + vam + odam + olam` (export: `ssrv + vam + odam + olam`) | dec(18,0) | M | S1 §7-51 |
| cui | عیار | Gold purity, 0 < cui ≤ 1000 | dec(4,2) | P3 O | S1 §7-61 |
| cpr | نرخ خرید ارز | Currency **buying** rate on the trade day; 0 < cpr < exr | dec(18,8) | P2 M | S1 §7-63 |
| sovat | ماخذ مالیات بر ارزش افزوده در الگوی فروش ارز | VAT base in the currency-sale pattern; `cfee·(exr−cpr) ≤ sovat ≤ cfee·exr` | dec(18,0) | P2 M | S1 §7-64 |
| hs | — | Not in V7.8; appears as null in the SDK capture [UNVERIFIED] | ? | ? | X1 |

## 3. Payments (`payments[]`, «اطلاعات پرداخت»)

Optional for types 1 and 2 (ignored in P7, P11), but each field's rule says it is **mandatory for
type 3** (S1 §7-52…§7-60).

| field | فارسی | meaning | type | source |
|---|---|---|---|---|
| iinn | شماره سوییچ پرداخت | Payment switch number | digits 9 | S1 §7-52 |
| acn | شماره پذیرنده فروشگاهی | Merchant (acceptor) number | digits 14 | S1 §7-53 |
| trmn | شماره پایانه | Terminal number | digits 8 | S1 §7-54 |
| pmt | روش پرداخت | 1 cheque, 2 set-off (تهاتر), 3 cash, 4 POS, 5 internet gateway, 6 card-to-card, 7 account transfer, 8 other | int ≤2 | S1 §7-55 |
| trn | شماره پیگیری/شماره مرجع | Tracking / reference number | digits ≤14 | S1 §7-56 |
| pcn | شماره کارت پرداخت کننده | Payer card number | digits 16 | S1 §7-57 |
| pid | شماره/شناسه ملی/کد فراگیر پرداخت کننده | Payer id | digits ≤12 | S1 §7-58 |
| pdt | تاریخ و زمان پرداخت | Payment time, Unix ms at day precision | int 13 | S1 §7-59 |
| pv | مبلغ پرداختی | Amount paid for the cash part (cash amount + its VAT); 0 when setm = 2; ≤ tbill | dec(18,0) | S1 §7-60 |

## 4. Where moadian-full 0.0.2 disagrees with S1 (verified by running it)

| library behaviour (L) | official rule | effect |
|---|---|---|
| `TYPE_SALE=1, TYPE_SALE_CASH=2, TYPE_EXPORT=3, TYPE_CONTRACT=4` for inty | inty is 1/2/3 = type 1/2/3; export is inp 7, contracting inp 4; inty 4 does not exist (S1 §7-4, §7-7) | wrong labels; never use these constants |
| `PATTERN_SALE=1, PATTERN_RETURN=2, PATTERN_CANCEL=3` for inp | inp 2 = currency sale, 3 = gold; return/cancel are ins 4/3 (S1 §7-7, §7-8) | a "return" would be sent as a currency sale |
| `BUYER_LEGAL=1, BUYER_REAL=2` | tob 1 = natural person, 2 = legal entity (S1 §7-9 rule 3) | buyer type swapped if the constants are used |
| `dis = dis × am` | dis is the line total (S1 §7-39) | wrong adis, vam, totals |
| `insp = tadis`, `cap = tbill` on every invoice | cap/insp exclude VAT and are for setm 3 only (S1 §7-23, §7-24) | cash invoice declares a credit amount |
| `vop = vam`, `tvop = tvam` | vop = vam × cap / tadis (S1 §7-49) | only right for fully-cash payments |
| `ins` hard-coded to 1, `indati2m = indatim` | ins from the caller; indati2m only for Arts. 9/12 (S1 §7-3, §7-8) | corrections/cancels impossible; extra field |
| taxid check digit over base36 of the hex string | Verhoeff over ASCII codes + decimal day + decimal serial (S3 §3-1-4) | `DEF5GH0481F000000000C7` instead of `…C2` |
| `import moadian_full` | package folder is `moadian-full` | documented import fails; use `scripts/_moadian.py` |

`scripts/build_invoice.py` corrects all of these and lists each correction in its report.
