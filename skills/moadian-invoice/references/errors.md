# Moadian error and warning codes

Read this when a user pastes an error code or a FAILED inquiry result. Prefer running
`python scripts/explain_error.py <code>` — it reads the tables below and, for codes not in them,
decodes the 7-digit structure (section 2) without inventing a meaning.

**Reliability.** The official lists are «کد خطاهای سامانه مودیان» RC_TXPS.EC_V02 (اسفند ۱۴۰۲, O1) and
«خطاهای پرتکرار در سامانه مودیان» RC_TXPS.RE_V01 (دی ۱۴۰۲, O2). Both were read in full from a byte copy
(intamedia.ir itself is unreachable from the build environment) and every row below was checked against
them. A row whose source column has **O1/O2** is confirmed by the official text; the code scheme
(section 2), the API/transport tables (section 4) and the field numbers (section 5) are official too.
Rows with only E-sources were seen in real replies or vendor pages but are not printed in O1/O2;
rows marked `(template)` are built from the official scheme. `[UNVERIFIED]` marks what no source shows.
Where O1/O2 disagree with the newer invoice guideline RC_IITP.IS_V7.8 (fields.md S1), V7.8 wins.

## 1. Sources

| id | source | kind |
|---|---|---|
| O1 | **RC_TXPS.EC_V02** «کد خطاهای سامانه مودیان», اسفند ۱۴۰۲, 33 pp. Copy: github.com/mojtabahakimian/Taxation @ `f005a6f` `Prg_Grpsend/InfoDocuments/کد خطاهای سامانه مودیان اسفندماه 1402-compressed.pdf` (sha256 `5de176d2…b92c4e`). Tables 1–6 API/transport, Table 7 code scheme, Table 8 field numbers, Table 9 frequent errors | official |
| O2 | **RC_TXPS.RE_V01** «خطاهای پرتکرار در سامانه مودیان», دی ۱۴۰۲, 8 pp. Same copy, `…/سند خطاهای پرتکرار در سامانه مودیان RC_TXPS.RE_V01-compressed.pdf` (sha256 `c11d7896…872b06`). Causes for ten frequent codes; its body font does not extract, so it was read from rendered pages | official |
| E1 | github.com/Mr0Hadi/OurERP — `Backend-Net/docs/Moadian/راهنمای اتصال سیستم حسابداری به سامانه مودیان.md` (digest of EC_V02, RE_V01, RC_TICS.IS v1.6) | secondary, best single source |
| E2 | github.com/mojtabahakimian/Taxation — `TestTools/LocalMoadian/moadian_mock_full.py` (built from EC_V02, corrected with ~15.9k production rows) | secondary, code |
| E4 | same repo — `CLAUDE.md` (production failure statistics) | secondary, empirical |
| E5 | same repo — `Prg_Moadian/Service/TaxService.cs` comments | secondary |
| E6 | github.com/Mohsensoft/faktor-doc — `source/mtax.rst` «رفع خطا» (quotes system messages verbatim) | secondary, vendor help |
| E7 | github.com/baapar1101/arc — `hesabixAPI/app/integrations/moadian/error_playbook.py` | secondary, vendor code |
| E8–E12 | github.com/ali-hallaji/digi-tax-ops — `docs/invoice_flow_matrix.md`, `docs/moadian/corrective_inp_inty_experiment_2026-07.md`, `docs/moadian/gold_pattern3_sandbox_2026-07-28.md`, `docs/progress.md`, `docs/moadian/pdf_remine_2026-07.md` | secondary, sandbox logs with verbatim replies |
| E13 | github.com/Jooyeshgar/moadian issues #21 #22 #31–#33 #38 #41 | secondary, user reports |
| E14 | github.com/Torabi-srh/Moadian issues #5 #6 #10 | secondary, user reports |
| E15 | github.com/thisiskarimi/moadian issues #7 #8 | secondary, user reports |
| E16 | search-engine snippets of vendor pages (keysuntsp.com, malitor.ir, movadian.com …) | secondary, lowest — corroboration only |

## 2. How to read a 7-digit code (O1 §3 and Table 7)

`K T FFF DD`

- **K** — `0` error (invoice rejected, status FAILED) · `1` warning (invoice still accepted).
- **T** — check type: `0` field empty · `1` JSON structure · `2` calculation/logic rule ·
  `3` mismatch with system data · `4` field sent "out of pattern" or not defined for this pattern ·
  `5` duplicate.
- **FFF** — field number (table in section 5); `000` whole JSON; `500/600/700/800` header/body/payment/extension.
- **DD** — detail. For T=1: `01` disallowed property (additionalProperties) · `02` not an allowed value (enum) ·
  `03` wrong type · `04` regex, including fixed length · `05` exclusive max/min · `06` max/min ·
  `09` too many decimal places (multipleOf) · `10` with 000: invalid JSON. For T=3: `01`, and for field 009
  also `02` (seller ≠ reference seller) and `03` (seller may not send this pattern). T=0/2/4/5 have no detail.

So O1 prints T=0/2/4 codes with 5 digits (`02002`, `14007`, `00012`). The live system has been seen sending
T=2 with detail `01` (`0200201`) (E2). O2 and vendors print short forms such as `0301` for `0300101`
(section 7). One inquiry returns at most 50 messages, errors first; beyond that a `00000` message is added (O1 §3).

Inquiry status (O1 §3): SUCCESS registered (may carry warnings) · FAILED rejected · IN_PROGRESS still queued ·
TIMEOUT processing took too long and the invoice was **not** put in کارپوشه · NOT_FOUND unknown id in the range.

Message templates (O1 Table 7; T=2/3/4 also match real replies in E6, E9, E13):
T=0 «فیلد ... خالی است.» · T=1/01 «در صورتحساب ارسالی فیلد ... غیرمجاز است.» ·
T=1/02 «مقدار وارد شده در فیلد ... جز مقادیر مجاز نیست.» · T=1/03 «در مقدار وارد شده در فیلد ... نوع فیلد صحیح نیست.» ·
T=1/04 «در مقدار وارد شده در فیلد ... الگو (regex) رعایت نشده است.» ·
T=1/05 «در مقدار وارد شده‌ی فیلد ... حداکثر (حداقل) مقدار مطلق رعایت نشده است.» ·
T=1/06 «در مقدار وارد شده‌ی فیلد ... حداکثر (حداقل) مقدار رعایت نشده است.» ·
T=1/09 «حداکثر تعداد رقم اعشار وارد شده در فیلد ... صحیح نیست.» · 000/10 «در صورتحساب ارسالی ساختار جیسون رعایت نشده است.» ·
T=2 «مقدار فیلد ... از لحاظ قواعد محاسباتی و منطقی معتبر نیست.» · T=3 «مقدار فیلد ... با اطلاعات سامانه منطبق نیست.» ·
T=4 «فیلد ... در الگوی صورتحساب ارسالی خارج از الگو است.» · T=5 «در صورتحساب ارسالی ... تکرار شده است.» ·
600 empty body «صورتحساب باید حداقل یک قلم کالا داشته باشد».
O1 Table 7: T=2 and T=3 on a mandatory field are errors and on an optional field warnings (`1300501`);
every T=4 (out of pattern / not defined) is a warning, so the invoice is still accepted.

## 3. Invoice content codes (inquiry `data.error` / `data.warning`)

| code | message_fa | meaning_en | fields | fix | source |
|---|---|---|---|---|---|
| 0300101 | مقدار فیلد «شماره مالیاتی صورتحساب» با اطلاعات سامانه منطبق نیست | taxid does not match system data (error); O2 prints 0301 | taxid | Causes in O2: taxid already used; memory id in taxid is not this taxpayer's; 5-char date part ≠ the date in `indatim`; wrong Verhoeff check digit. O1 Table 9 adds: usually the date part vs `indatim`, or a repeated internal serial. Run `scripts/taxid.py validate <taxid> --indatim <ms>`. Check کارپوشه first — the invoice may already be registered; never resend the same taxid (it is rejected, not overwritten). Note: moadian-full 0.0.2 generates wrong check digits. | O1 O2 E1 E2 E4 E5 E6 |
| 0200201 | مقدار فیلد «تاریخ و زمان صدور صورتحساب(میلادی)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | indatim fails a rule (error); O1 prints it as 02002, O2 as 0202 | indatim | Causes in O2 (and O1 Table 9): more than 30 000 ms ahead of the current time; received outside the sending window of the invoice guideline; for ins 2/3/4, earlier than the reference invoice's indatim. Real data: type-1 invoices accepted up to ~13 days late, rejected from 14 (E4). | O1 O2 E1 E2 E4 E6 E13 |
| 02002 | مقدار فیلد «تاریخ و زمان صدور صورتحساب(میلادی)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | Document form of 0200201 (O1 Table 9 and its inquiry example) | indatim | See 0200201 | O1 O2 E1 E2 E6 |
| 00107 | فیلد «قاعده ارسال صورتحساب» خالی است (paraphrase) | Submission-rule field empty; seen only together with 0200201 on late invoices | insr | Fix the date / deadline problem first; it disappears once the main error is fixed (E7). | E2 E4 E7 |
| 0304401 | مقدار فیلد «نرخ مالیات بر ارزش‌افزوده(J)» با اطلاعات سامانه منطبق نیست. | VAT rate differs from what the system expects (error); O2 prints 0344 | vra, sstid | Non-export patterns: use the rate registered for the 13-digit sstid on stuffid.tax.gov.ir (O2). Export (inp 7): vra must be 0 per O1 Table 9 and the newer guideline V7.8 §7-41 (fields.md S1); the older O2 said non-zero — follow V7.8. A seller not subject to VAT (غیرمشمول) must send vra 0 on every pattern (O1). Also fires when a corrective changes a line's sstid (E12). | O1 O2 E6 E7 E12 E13 |
| 0204501 | مقدار فیلد «مبلغ مالیات بر ارزش افزوده(KS)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | vam fails the calculation rule (error); O2 prints 0245 | vam | O2: `vam = vra × adis / 100`; export `vra × ssrv / 100`; gold `rate × tcpbs` (O2's 1402 examples use 9 %; the current rule is in arithmetic-rules.md R7). Sandbox shows the system truncates; half-up rounding was rejected (E10). Run validate_invoice.py. | O2 E1 E10 E13 |
| 0204101 | مقدار فیلد «مبلغ قبل از تخفیف» از لحاظ قواعد محاسباتی و منطقی معتبر نیست (template) | prdis fails the rule (error) | prdis, am, fee | `prdis = am × fee`, truncated to an integer, not rounded (E10; E2 citing FAQ 9-4). | E2 E10 |
| 0204301 | مقدار فیلد «مبلغ بعد از تخفیف» از لحاظ قواعد محاسباتی و منطقی معتبر نیست (template) | adis fails the rule (error) | adis, prdis, dis | `adis = prdis − dis` (gold pattern has its own formula). | E2 E10 |
| 0303301 | مقدار فیلد «شناسه کالا/خدمت» با اطلاعات سامانه منطبق نیست | sstid not found in the goods/services registry (error); O2 prints 0333 | sstid, vra | O2: the id is not in the goods-id database — use a valid 13-digit id from stuffid.tax.gov.ir. Also returned when vra ≠ the id's registered rate (e.g. 0 to claim exemption) (E10). A corrective may not change a line's sstid (E12). | O2 E1 E6 E10 E12 |
| 0300601 | مقدار فیلد «شماره مالیاتی صورتحساب مرجع» با اطلاعات سامانه منطبق نیست. | Reference taxid (irtaxid) not acceptable (error) | irtaxid | O1 Table 9, for corrective, return and cancellation invoices: irtaxid matches no taxid in کارپوشه, the reference was cancelled, or the reference is itself a corrective that is pending or rejected. Point to the newest registered version of the invoice (E8). | O1 E1 E2 E8 E9 |
| 0300901 | مقدار فیلد «شماره اقتصادی فروشنده» با اطلاعات سامانه منطبق نیست | Seller economic code mismatch (error) | tins | Use the code shown in کارپوشه (E6); legal entities use their 11-digit national id (E16). If validate_invoice.py warns `id-check-digit` on tins, the number itself is mistyped (check digit fails). | E6 E16 |
| 0300902 | فروشنده صورتحساب با فروشنده صورتحساب مرجع منطبق نیست. | Seller differs from the reference invoice's seller (error) | tins | Keep tins identical to the reference invoice. | O1 E1 E2 |
| 0300903 | فروشنده صورتحساب مجاز به ارسال الگوی صورتحساب ارسالی نمی‌باشد. | Seller not allowed to send this invoice pattern (error) | tins, inp | Check that inp is allowed for this taxpayer. | O1 E1 E2 |
| 0301201 | مقدار فیلد «شماره اقتصادی خریدار» با اطلاعات سامانه منطبق نیست. | Buyer economic code wrong (error) | tinb | O1 Table 9: the buyer's economic code was entered wrongly. If validate_invoice.py warns `id-check-digit` on tinb, the number itself is mistyped (check digit fails). | O1 E1 E16 |
| 00012 | فیلد «شماره اقتصادی خریدار» خالی است | Buyer economic code empty (error); O2 prints 0012 | tinb, inty | O2 flowchart, original type-1 invoices: legal entity / civil partnership buyer (tob 2–3) on sale, gold or contracting → tinb needed; natural person / foreign national (tob 1, 4) → error only if bid and bpc are also missing; currency sale, utility bills, airline tickets and export → no tinb needed. Type 2 and correction/return/cancellation do not need tinb. Or issue type 2 (E7). | O2 E1 E4 E7 |
| 0101204 | در مقدار وارد شده در فیلد شماره اقتصادی خریدار الگو (regex) رعایت نشده است | Buyer economic code format (error); O2 prints 011204 | tinb | O2: digits 0–9 only; 14 digits for natural persons / foreign nationals, 11 for legal entities / civil partnerships. | O2 E1 E4 E6 |
| 0101104 | در مقدار وارد شده در فیلد شماره ملی/شناسه مشارکت مدنی/کد فراگیر خریدار الگو (regex) رعایت نشده است | Buyer national id format (error); O2 prints 011104 | bid | O2: digits 0–9 only; 10 natural person, 11 legal entity / civil partnership, 12 foreign national. | O2 E1 E6 |
| 0101304 | در مقدار وارد شده در فیلد کد شعبه فروشنده الگو (regex) رعایت نشده است | Seller branch code format (error); O2 prints 011304 | sbc | O2: digits 0–9 only, exactly 4 digits. | O2 E1 E6 |
| 0101504 | در مقدار وارد شده در فیلد کد شعبه خریدار الگو (regex) رعایت نشده است (template) | Buyer branch code format (error) | bbc | Exactly 4 digits. | E2 |
| 0100504 | در مقدار وارد شده در فیلد «سریال صورتحساب» الگو (regex) رعایت نشده است (template) | inno format; must match ^[a-fA-F0-9]{10}$ (error) | inno | Send the 10-char hex serial, i.e. taxid characters 12–21. | E11 |
| 1300501 | مقدار فیلد «سریال صورتحساب» با اطلاعات سامانه منطبق نیست. | inno differs from the serial inside taxid (warning — invoice accepted) | inno, taxid | Send inno = taxid[11:21] (10 hex chars). The code and message are O1's own inquiry example; the cause is from E1/E8. | O1 E1 E2 E8 E11 |
| 0102004 | در مقدار وارد شده در فیلد «شناسه یکتا ثبت قرارداد فروشنده» الگو(^\d{12}$) رعایت نشده است. | Contract registration id format (error) | crn | Exactly 12 digits. | E8 |
| 0302001 | مقدار فیلد «شناسه یکتا ثبت قرارداد فروشنده» با اطلاعات سامانه منطبق نیست. | Contract id not registered/confirmed (error); full code built from the O1 scheme (template), vendor prints 032001 | crn | Register the contract in کارپوشه and have the counter-party confirm it first. | E6 |
| 0103502 | مقدار وارد شده در فیلد «واحد اندازه‌گیری» جز مقادیر مجاز نیست (template) | Measurement unit not an allowed code (error) | mu | Use a numeric unit code from the official unit list (RC_UMGS). | E7 |
| 0103504 | در مقدار وارد شده در فیلد «واحد اندازه‌گیری» الگو (regex) رعایت نشده است (template) | Measurement unit format (error) | mu | Digits only. | E7 |
| 0103605 | (exclusiveMinimum) | am must be > 0 (error) | am | Quantity greater than zero. | E2 |
| 0103705 | (exclusiveMinimum) | fee must be > 0 (error) | fee | Unit price greater than zero. | E2 |
| 0104105 | (exclusiveMinimum) | prdis must be > 0 (error) | prdis | | E2 |
| 0102205 | (exclusiveMinimum) | tprdis must be > 0 (error) | tprdis | | E2 |
| 0107305 | (exclusiveMinimum) | ssrv must be > 0 when sent (error) | ssrv | Do not send 0; omit unless there is a real value. | E7 |
| 00052 | فیلد «اجرت ساخت» خالی است (paraphrase) | Gold pattern: consfee empty (error) | consfee | Gold pattern (inp=3) needs consfee, spro, bros, tcpbs on every line. | E10 |
| 00053 | فیلد «سود فروشنده» خالی است (paraphrase) | Gold pattern: spro empty (error) | spro | As 00052. | E10 |
| 00054 | فیلد «حق‌العمل» خالی است (paraphrase) | Gold pattern: bros empty (error) | bros | As 00052. | E10 |
| 00055 | فیلد «جمع کل اجرت، حق‌العمل و سود» خالی است (paraphrase) | Gold pattern: tcpbs empty (error) | tcpbs | As 00052. | E10 |
| 14007 | فیلد «الگوی صورتحساب» در الگوی صورتحساب ارسالی خارج از الگو است. | inp sent out of pattern (warning) | inp, ins | On ins 2/3/4, omit inp (taken from the reference). | E8 E9 |
| 14004 | فیلد «نوع صورتحساب» در الگوی صورتحساب ارسالی خارج از الگو است. | inty sent out of pattern (warning) | inty, ins | On ins 2/3/4, omit inty. | E8 E9 |
| 14029 | فیلد «مبلغ پرداختی نقدی» در الگوی صورتحساب ارسالی خارج از الگو است. (template) | cap sent when not expected (warning) | cap, setm | Send cap only when setm calls for it; seen even when 0 is sent. | E2 |
| 14030 | فیلد «مبلغ نسیه» در الگوی صورتحساب ارسالی خارج از الگو است. (template) | insp sent when not expected (warning) | insp, setm | Send insp only when setm calls for it. | E2 |
| 14003 | فیلد «تاریخ و زمان ایجاد صورتحساب» در الگوی صورتحساب ارسالی خارج از الگو است. (template) | indati2m sent out of pattern (warning) | indati2m | | E2 |
| 14800 | (out-of-pattern template) | extension section sent out of pattern (warning) | extension | Do not send `extension: [{}]`. | E2 |
| 00000 | تعداد پیام‌های خطا/هشدار بیش‌تر از ۵۰ مورد است و امکان نمایش بیش‌تر از این تعداد وجود ندارد. | More than 50 messages; list truncated (shown next to the first 50) | — | Fix the listed errors and resend. | O1 E1 E2 |
| 1301101 | شناسه ملی خریدار با اطلاعات سامانه منطبق نیست (paraphrase) | Buyer national id mismatch (warning) | bid | Verify the buyer's id. If validate_invoice.py warns `id-check-digit` on bid, the number itself is mistyped (check digit fails). | E7 |
| 1301001 | نوع شخص خریدار با اطلاعات سامانه منطبق نیست (paraphrase) | Buyer type inconsistent with system data (warning) | tob | Check tob against the buyer's registration. | E2 E7 |
| 1301401 | کد پستی خریدار با اطلاعات سامانه منطبق نیست (template) | Buyer postal code mismatch (warning) | bpc | | E2 |
| 04111 | قرارداد شناسه یکتا و شرکت معتمد یافت نشد. | Memory id inactive, or no contract between memory id and trusted company (packet error at inquiry) | fiscalId | Reactivate the memory id; check the trusted-company contract. | O1 O2 E1 E6 |
| 04130 | ساختار بسته‌ی صورتحساب (encrypted payload) امضا شده صحیح نیست. | JWS invalid after decryption (packet error) | packet | Fix packet signing. | O1 E1 |
| 04131 | امضای صورتحساب ارسالی یا گواهی امضایی که صورتحساب با آن امضا شده معتبر نمی‌باشد. | Invoice JWS signature or certificate invalid (like API 4131) | packet | Fix signature/certificate. | O1 E1 |
| 04132 | گواهی امضایی که صورتحساب با آن امضا شده، دسترسی صدور و امضای صورتحساب برای این شناسه یکتا را ندارد. | Signer's certificate may not send for this fiscalId, e.g. the memory id is delegated to a trusted company | fiscalId | Use the right key or delegation. | O1 E1 |
| 04148 | شناسه یکتای ارسالی نامعتبر است. | Issuer memory id format invalid | fiscalId | 6 upper-case letters/digits (O1 Table 1). | O1 E1 |
| 04150 | بسته‌ی JWE صورتحساب ارسالی از نظر ساختاری معتبر نمی‌باشد و امکان رمزگشایی آن وجود ندارد. | JWE not 5-part / cannot decrypt | packet | | O1 E1 |
| 04152 | الگوریتم مورد استفاده برای رمزنگاری معتبر نمی‌باشد. | JWE enc ≠ A256GCM or alg ≠ RSA-OAEP-256 | packet | | O1 E1 |
| 04153 | طول فیلد IV باید 96 بیت باشد. | JWE IV length is not 96 bits | packet | | O1 E1 |
| 04133 | شناسه حافظه امضا کننده‌ی صورتحساب یافت نشد/غیر فعال می‌باشد. | Signing memory id not found or inactive when the queue checks the invoice | fiscalId | Reactivate the memory id in کارپوشه. | O1 |
| 04134 | شناسه شرکت معتمد امضا کننده‌ی صورتحساب یافت نشد/غیرفعال می‌باشد. | Signing trusted-company id not found or inactive | fiscalId | | O1 |
| 05139 | خطای غیرمنتظره‌ای در فرآیند بررسی امضای صورتحساب رخ داد. | Server-side error while checking the invoice signature (not caused by the packet) | — | Retry later. | O1 |
| 05151 | خطایی غیر منتظره در رمزگشایی صورتحساب ارسالی رخ داد. | Server-side error while decrypting the invoice (not caused by the packet) | — | Retry later. | O1 |
| 05159 | خطای غیرمنتظره‌ای در فرآیند بررسی دسترسی امضاکننده صورتحساب رخ داد. | Server-side error while checking the signer's access | — | Retry later. | O1 |

## 4. API-level codes (HTTP errors; response `errors: [{code, message}]`) — O1 §2, Tables 1–6

A code starting with 4 is the caller's fault (wrong request or parameters); 5 is a server problem, or a caller
problem the server could not classify — check the request and retry later (O1 §2.1). A 401 with no code means
no Bearer token was sent (O1 Table 1). Status values for inquiries are in section 2.

| code | message_fa | meaning_en | fields | fix | source |
|---|---|---|---|---|---|
| 4101 | متد درخواست ارسالی پشتیبانی نمی‌شود. / ساختار payload در توکن JWT فرستاده شده مطابق با ساختار {"nonce","clientId"} نمی‌باشد. | HTTP 401: wrong HTTP method, or token payload is not {nonce, clientId} (O1 uses one code for both) | token | | O1 E1 |
| 4102 | چالش تصادفی امضا شده در توکن JWT معتبر نمی‌باشد (قبلاً استفاده شده یا زمان استفاده آن گذشته است). | HTTP 401: nonce invalid, already used or expired | token | Get a fresh nonce for every token. | O1 E1 |
| 4103 | کد ملی گواهی امضایی که توکن JWT با آن امضا شده با کد ملی مربوط به شناسه کلاینت قرار داده شده در توکن مطابقت ندارد. | HTTP 401: certificate national id (SUBJECT SERIALNUMBER) is not the owner of clientId | certificate | Use the certificate issued to the memory id's owner. | O1 E1 E7 |
| 4110 | شناسه کلاینت (شناسه حافظه) وارد شده در توکن JWT یافت نشد. | HTTP 401: clientId (memory id) not found or inactive | fiscalId | Reactivate in کارپوشه › عضویت › شناسه‌های یکتای حافظه مالیاتی. | O1 E1 E16 |
| 4120 | شناسه کلاینت (شناسه شرکت معتمد) وارد شده در توکن JWT یافت نشد. | HTTP 401: trusted-company id not found or inactive | fiscalId | | O1 E1 |
| 4130 | ساختار توکن JWT فرستاده شده صحیح نیست. | HTTP 401: token is not 3-part Base64Url | token | | O1 E1 |
| 4131 | امضای توکن JWT یا گواهی امضای فرستاده شده معتبر نمی‌باشد. | HTTP 401: incomplete header, signature does not verify, certificate not from a trusted intermediate CA, or expired/revoked (OCSP/CRL) | certificate | | O1 E1 |
| 4132 | کلید عمومی معتبر یافت نشد. | HTTP 401: no public key registered for this memory id | fiscalId | Register the public key in کارپوشه. | O1 E1 |
| 4133 | امضاء نامعتبر است. | HTTP 401: invoice signature check failed | signature | | O1 E1 |
| 4134 | Encoding برابر با UTF-8 نیست. | HTTP 401: signed packet is not UTF-8 | packet | | O1 E1 |
| 4135 | گواهی امضایی در فیلد x5c یافت نشد. | HTTP 401: x5c header empty | certificate | | O1 E1 |
| 4136 | فرمت گواهی امضای ارسالی در فیلد x5c معتبر نمی‌باشد. | HTTP 401: certificate in x5c malformed | certificate | | O1 E1 |
| 4137 | کلید عمومی مربوط به شناسه یکتا معتبر نمی‌باشد. لطفا از طریق کارپوشه مجددا کلید عمومی خود را آپلود نمایید. | HTTP 401: certificate uploaded to کارپوشه is invalid | certificate | Replace it in کارپوشه. | O1 E1 |
| 4140 | زمان شروع بازه‌ی استعلام باید قبل از زمان پایان آن باشد. | HTTP 400: inquiry start time after end time | inquiry | | O1 E1 |
| 4141 | نمی‌توانید در یک درخواست وضعیت بیش از 100 صورتحساب را استعلام بگیرید. | HTTP 400: more than 100 uid/referenceId in one inquiry | inquiry | | O1 E1 |
| 4142 | مقدار status وارد شده نامعتبر است. مقادیر مجاز: [SUCCESS, FAILED, IN_PROGRESS, TIMEOUT] | HTTP 400: invalid status filter | inquiry | | O1 E1 |
| 4143 | در یک درخواست نمی‌توانید بیشتر از 1000 صورتحساب ارسال نمایید. | HTTP 400: more than 1000 invoices in one request | packet | | O1 E1 |
| 4144 | بدنه‌ی درخواست ارسالی خالی است یا از نظر ساختار JSON معتبر نیست. | HTTP 400: empty or invalid JSON body | packet | | O1 E1 |
| 4145 | در بدنه‌ی درخواست ارسالی، بعضی از فیلدهای ضروری خالی است (برای هر صورتحساب باید payload، fiscalId و requestTraceId موجود باشد). | HTTP 400: item missing payload, fiscalId or requestTraceId | packet | | O1 E1 |
| 4146 | زمان اعتبار چالش تصادفی باید بین 10 تا 200 ثانیه باشد. | HTTP 400 (nonce API): timeToLive outside 10–200 s | token | | O1 E1 |
| 4147 | فرمت ورودی‌های درخواست نادرست می‌باشد. | HTTP 400: input format wrong | packet | | O1 E1 |
| 4148 | شناسه یکتای ارسالی نامعتبر است. | HTTP 400: memory id format invalid (6 upper-case letters or digits) | fiscalId | | O1 E1 |
| 4160 | دسترسی مشاهده اطلاعات شناسه یکتای درخواست شده ممکن نیست. | HTTP 403: no access to this memory id's data | fiscalId | | O1 E1 |
| 4162 | شناسه درخواست (requestTraceId) داخل درخواست معتبر نمی‌باشد. | HTTP 400: requestTraceId is not a UUID | packet | | O1 E1 |
| 4163 | در درخواست ارسالی شناسه درخواست تکراری وجود دارد. | HTTP 400: requestTraceId duplicated in one request | packet | | O1 E1 |
| 4164 | بازه زمانی استعلام حداکثر یک هفته است. | HTTP 400: inquiry range longer than one week | inquiry | | O1 E1 |
| 4170 | شماره اقتصادی وارد شده یافت نشد. | HTTP 404: economic code not found (taxpayer lookup) | tins/tinb | | O1 E1 |
| 4171 | شماره اقتصادی وارد شده از نظر طول معتبر نیست. | HTTP 404: economic code has wrong length | tins/tinb | | O1 E1 |
| 5199 | خطای غیر منتظره‌ای در انجام درخواست رخ داد. | HTTP 500: unexpected server error | — | Retry later. | O1 E1 E15 |
| 5119 | مشکل غیرمنتظره در دریافت اطلاعات پرونده مالیاتی رخ داد. | HTTP 500: server error fetching the tax file (certificate check) | — | Retry later. | O1 E1 |
| 5129 | مشکل غیرمنتظره در دریافت اطلاعات شرکت معتمد رخ داد. | HTTP 500: server error fetching the trusted company | — | Retry later. | O1 E1 |
| 5139 | خطای غیرمنتظره‌ای در بررسی صحت امضای توکن JWT رخ داد. | HTTP 500: server error checking the token signature | — | Retry later. | O1 E1 |

Old (v1) collection API, still active "until further notice" (O1 §2.7, Table 6). Message only, as in O1:

| code | message_fa | meaning_en | fields | fix | source |
|---|---|---|---|---|---|
| 4001 | ساختار JSON درخواست داده شده اشتباه است. | Old API: request JSON malformed | packet | | O1 |
| 4002 | نوع بسته با محتوای بسته یکسان نیست. | Old API: packet type does not match its content | packet | | O1 |
| 4003 | بسته ارسالی پشتیبانی نمی شود. | Old API: packet not supported | packet | | O1 |
| 4004 | برای این نوع بسته، ارسال هدر Authorization الزامی می باشد. | Old API: Authorization header required | token | | O1 |
| 4005 | ارسال این نوع بسته به صورت همگام مجاز نمی باشد. | Old API: this packet may not be sent synchronously | packet | | O1 |
| 4006 | ارسال این بسته به صورت غیرهمگام مجاز نمی باشد. | Old API: this packet may not be sent asynchronously | packet | | O1 |
| 4007 | برای این نوع بسته، ارسال امضا الزامی می باشد. | Old API: signature required | signature | | O1 |
| 4008 | شناسه کلید رمزنگاری اشتباه است. | Old API: wrong encryption key id | packet | | O1 |
| 4009 | شناسه حافظه در بسته الزامی است. | Old API: memory id required in the packet | fiscalId | | O1 |
| 4010 | ساختار JSON بسته داده شده اشتباه است. | Old API: packet JSON malformed | packet | | O1 |
| 4011 | امضای بسته صحیح نمی باشد. (در APIهای جمع‌آوری) | Old API: packet signature invalid (seen when the memory id did not belong to the signing key) | signature | Check the key pair matches the memory id. | O1 E11 E14 |
| 4012 | تعداد بسته ها داخل درخواست بیش از حد مجاز است. | Old API: too many packets in one request | packet | | O1 |
| 4015 | ساختار تاریخ ارسال شده صحیح نمی باشد. | Old API: date format wrong | packet | | O1 |
| 4016 | ساختار توکن دسترسی صحیح نمی باشد. | Old API: access token malformed | token | | O1 |
| 4017 | اعتبار توکن دسترسی به پایان رسیده است. | Old API: access token expired | token | Get a new token. | O1 |
| 4018 | اعتبار درخواست داده شده منقضی شده است. | Old API: request validity expired | packet | Check the clock; resend with a fresh timestamp. | O1 E14 |
| 4019 | درخواست تکراری است. | Old API: duplicate request | packet | | O1 |
| 4020 | توکن دسترسی معتبری یافت نشد. | Old API: no valid access token | token | | O1 |
| 4021 | ارسال فیلد packet الزامی است | Old API: packet field required | packet | | O1 |
| 4022 | امضای توکن دسترسی صحیح نمی باشد | Old API: access token signature invalid | token | | O1 |
| 4024 | شما مجاز به استفاده از این سرویس نیستید | Old API: not allowed to use this service | — | | O1 |
| 4200 | شما مجاز به ارسال بسته برای این شناسه یکتای حافظه مالیاتی نیستید. | Old API: not allowed to send for this memory id | fiscalId | | O1 |
| 4202 | فیلد packet الزامی است. | Old API: packet field required | packet | | O1 |
| 4204 | رمزنگاری بسته الزامی است. | Old API: packet must be encrypted | packet | | O1 |
| 4205 | ارسال کلید متقارن الزامی است. | Old API: symmetric key required | packet | | O1 |
| 4206 | داده های ورودی برای رمزگشایی معتبر نمی‌باشد. | Old API: input cannot be decrypted | packet | | O1 |
| 4207 | ساختار کلید متقارن صحیح نمی باشد. | Old API: symmetric key malformed | packet | | O1 |
| 4208 | داده ها با کلید متقارن رمزگشایی نشد. | Old API: data did not decrypt with the symmetric key | packet | | O1 |
| 4209 | وارد کردن کد اقتصادی الزامی است. (در متد دریافت اطلاعات کد اقتصادی) | Old API: economic code required (taxpayer lookup) | tins/tinb | | O1 |
| 4210 | نوع بسته استعلام کد اقتصادی معتبر نمی باشد. | Old API: invalid economic-code inquiry packet | packet | | O1 |
| 4212 | امضا بسته صحیح نمی باشد. (هنگام استعلام وضعیت صورتحساب) | Old API: packet signature invalid on status inquiry (E2/E13 traced one case to JSON normalisation before signing) | signature | Check how the packet is normalised and signed. | O1 E2 E13 |
| 5051 | پردازه مدیریت کلید در دسترس نمی باشد، مدتی بعد تلاش کنید | Old API: key-management process unavailable | — | Retry later. | O1 E15 |
| 5052 | امکان پردازش این نوع بسته وجود ندارد | Old API: this packet type cannot be processed | packet | | O1 |
| 5056 | خطا در ارتباط با صف | Old API: queue connection error | — | Retry later. | O1 |
| 5057 | خطا در ارتباط با سرویس توزیع، مدتی بعد تلاش کنید | Old API: distribution service error | — | Retry later. | O1 |
| 5200 | خطای ناشناخته ای در هنگام پردازش درخواست شما رخ داده است. | Old API: unknown processing error | — | Retry later. | O1 |
| 5201 | سرویس احراز هویت در دسترس نمی باشد، مدتی بعد تلاش کنید. | Old API: authentication service unavailable | — | Retry later. | O1 |
| 5202 | سرویس مدیریت کلید سازمان در دسترس نمی باشد، مدتی بعد تلاش کنید. | Old API: INTA key-management service unavailable (one reporter saw it go away after fixing symmetricKey encryption, E13) | — | Retry later; check the symmetric-key encryption. | O1 E13 |
| 5203 | خطا در رمزگشایی بسته. | Old API: packet decryption failed | packet | | O1 |
| 5205 | خطا در نرمال کردن بسته. | Old API: packet normalisation failed | packet | | O1 |
| 5206 | سرویس مدیریت کلید در دسترس نمی باشد، مدتی بعد تلاش کنید. | Old API: key-management service unavailable | — | Retry later. | O1 |
| 5207 | سرویس اطلاعات پرونده مالیاتی در دسترس نمی باشد، مدتی بعد تلاش کنید. | Old API: tax-file service unavailable | — | Retry later. | O1 |

## 5. Field numbers used in codes (O1 Table 8; `107 insr` only from E2 — fields after O1 are not numbered there)

001 taxid · 002 indatim · 003 indati2m · 004 inty · 005 inno · 006 irtaxid · 007 inp · 008 ins · 009 tins ·
010 tob · 011 bid · 012 tinb · 013 sbc · 014 bpc · 015 bbc · 016 ft · 017 bpn · 018 scln · 019 scc · 020 crn ·
021 billid · 022 tprdis · 023 tdis · 024 tadis · 025 tvam · 026 todam · 027 tbill · 028 setm · 029 cap ·
030 insp · 031 tvop · 032 tax17 · 033 sstid · 034 sstt · 035 mu · 036 am · 037 fee · 038 cfee · 039 cut ·
040 exr · 041 prdis · 042 dis · 043 adis · 044 vra · 045 vam · 046 odt · 047 odr · 048 odam · 049 olt ·
050 olr · 051 olam · 052 consfee · 053 spro · 054 bros · 055 tcpbs · 056 cop · 057 vop · 058 bsrn ·
059 tsstam · 060 iinn · 061 acn · 062 trmn · 063 trn · 064 pcn · 065 pid · 066 pdt · 067 cdcn · 068 cdcd ·
069 tonw · 070 torv · 071 tocv · 072 nw · 073 ssrv · 074 sscv · 075 pmt · 076 pv · 077 pspd · 078 cui ·
079 tinc · 080 hs · 107 insr

## 6. Other failures without a numeric code

- **HTTP 401 on server-information / token** — usually the wrong private key, or a CSR passed instead of the
  certificate (`-----BEGIN CERTIFICATE-----`) (E13 #38 #41); the private key must match the public key
  registered for the memory id (E6).
- **HTTP 500 that looks like a network error** — a wrong memory id can surface this way (E6).
- **«اعتبار درخواست داده شده منقضی شده است»** — this is old-API code 4018 (O1 Table 6); reported once from the
  official .NET SDK and it resolved itself; the clock or nonce is a likely cause [UNVERIFIED] (E14 #6).
- **Duplicate taxid** — resending an existing taxid is rejected with 0300101 and does not overwrite the
  stored invoice (O2 cause 1, E1, E4).
- **401 with no code** — no Bearer token in the request header (O1 Table 1).

## 7. Short forms (O2 headings and vendor pages)

O2 and vendor pages drop the zero padding and the detail digits. `explain_error.py` maps these to the full code.

| short | full |
|---|---|
| 0301 | 0300101 |
| 0202 | 0200201 |
| 0344 | 0304401 |
| 0245 | 0204501 |
| 0333 | 0303301 |
| 0411 | 04111 |
| 0012 | 00012 |
| 011304 | 0101304 |
| 011204 | 0101204 |
| 011104 | 0101104 |
| 032001 | 0302001 |
