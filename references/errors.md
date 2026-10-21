# Moadian error and warning codes

Read this when a user pastes an error code or a FAILED inquiry result. Prefer running
`python scripts/explain_error.py <code>` — it reads the tables below and, for codes not in them,
decodes the 7-digit structure (section 2) without inventing a meaning.

**Reliability.** The official lists are «کد خطاهای سامانه مودیان» RC_TXPS.EC_V02 (اسفند ۱۴۰۲) and
«خطاهای پرتکرار در سامانه مودیان» RC_TXPS.RE_V01 (دی ۱۴۰۲) on intamedia.ir. They could not be fetched
while this file was written (Iranian hosts unreachable), so **every row is from secondary sources**
(developer digests of those documents, vendor help pages that quote the system's own messages, and
sandbox/production logs). Rows marked `[UNVERIFIED]` were derived (e.g. a full 7-digit form worked
out from the numbering scheme) rather than seen. Confirm against EC_V02 when it is available.

## 1. Sources

| id | source | kind |
|---|---|---|
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

## 2. How to read a 7-digit code (E1, E2, both citing EC_V02)

`K T FFF DD`

- **K** — `0` error (invoice rejected, status FAILED) · `1` warning (invoice still accepted).
- **T** — check type: `0` field empty · `1` JSON structure · `2` calculation/logic rule ·
  `3` mismatch with system data · `4` field sent "out of pattern" (not expected for this pattern) ·
  `5` duplicate.
- **FFF** — field number (table in section 5); `000` whole JSON; `500/600/700/800` header/body/payment/extension.
- **DD** — detail. For T=1: `01` disallowed property · `02` not an allowed value (enum) · `03` wrong type ·
  `04` regex/length · `05` exclusive min/max · `06` min/max · `09` too many decimal places · `10` (with 000) invalid JSON.

EC_V02 prints T=0/2/4 codes with 5 digits (`02002`, `14007`); the live system sends T=2 with detail `01`
(`0200201`) while T=0 and T=4 still arrive as 5 digits (`00012`, `14007`) (E2). Vendors also print short
forms such as `0301` for `0300101` (E6). One inquiry returns at most 50 messages; `00000` marks overflow (E1, E2).

Message templates (E2's reading of EC_V02; T=2/3/4 match real replies in E6, E9, E13):
T=0 «فیلد «X» خالی است.» · T=1/04 «در مقدار وارد شده در فیلد «X» الگو (regex) رعایت نشده است.» ·
T=1/02 «مقدار وارد شده در فیلد «X» جز مقادیر مجاز نیست.» · T=1/03 «نوع مقدار وارد شده در فیلد «X» صحیح نیست.» ·
T=2 «مقدار فیلد «X» از لحاظ قواعد محاسباتی و منطقی معتبر نیست.» · T=3 «مقدار فیلد «X» با اطلاعات سامانه منطبق نیست.» ·
T=4 «فیلد «X» در الگوی صورتحساب ارسالی خارج از الگو است.» · T=5 «فیلد «X» در صورتحساب ارسالی تکرار شده است.»

## 3. Invoice content codes (inquiry `data.error` / `data.warning`)

| code | message_fa | meaning_en | fields | fix | source |
|---|---|---|---|---|---|
| 0300101 | مقدار فیلد «شماره مالیاتی صورتحساب» با اطلاعات سامانه منطبق نیست | taxid does not match system data (error) | taxid | Causes listed in RE_V01 per E1: taxid already used; memory id in taxid is not this taxpayer's; 5-char date part ≠ day of `indatim`; wrong Verhoeff check digit. Run `scripts/taxid.py validate <taxid> --indatim <ms>`. Check کارپوشه first — the invoice may already be registered; never resend the same taxid (it is rejected, not overwritten). Note: moadian-full 0.0.2 generates wrong check digits. | E1 E2 E4 E5 E6 |
| 0200201 | مقدار فیلد «تاریخ و زمان صدور صورتحساب(میلادی)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | indatim fails a rule (error); EC_V02 prints it as 02002, vendors as 0202 | indatim | Causes per E1: more than 30 000 ms ahead of server time; past the submission deadline; for ins 2/3/4, earlier than the reference invoice's indatim. Real data: type-1 invoices accepted up to ~13 days late, rejected from 14 (E4). | E1 E2 E4 E6 E13 |
| 02002 | مقدار فیلد «تاریخ و زمان صدور صورتحساب(میلادی)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | Document form of 0200201 (see that row) | indatim | See 0200201 | E1 E2 E6 |
| 00107 | فیلد «قاعده ارسال صورتحساب» خالی است (paraphrase) | Submission-rule field empty; seen only together with 0200201 on late invoices | insr | Fix the date / deadline problem first; it disappears once the main error is fixed (E7). | E2 E4 E7 |
| 0304401 | مقدار فیلد «نرخ مالیات بر ارزش‌افزوده(J)» با اطلاعات سامانه منطبق نیست. | VAT rate differs from the rate registered for this sstid (error) | vra, sstid | Use the rate registered for the 13-digit sstid on stuffid.tax.gov.ir; export lines need a non-zero rate (E1). Also fires when a corrective changes a line's sstid (E12). | E1 E6 E7 E12 E13 |
| 0204501 | مقدار فیلد «مبلغ مالیات بر ارزش افزوده(KS)» از لحاظ قواعد محاسباتی و منطقی معتبر نیست. | vam fails the calculation rule (error); short form 0245 | vam | Per E1 (from RE_V01): `vam = vra × adis / 100` (export: `vra × ssrv / 100`; gold: see arithmetic-rules.md). Sandbox shows the system truncates; half-up rounding was rejected (E10). Run validate_invoice.py. | E1 E10 E13 |
| 0204101 | مقدار فیلد «مبلغ قبل از تخفیف» از لحاظ قواعد محاسباتی و منطقی معتبر نیست (template) | prdis fails the rule (error) | prdis, am, fee | `prdis = am × fee`, truncated to an integer, not rounded (E10; E2 citing FAQ 9-4). | E2 E10 |
| 0204301 | مقدار فیلد «مبلغ بعد از تخفیف» از لحاظ قواعد محاسباتی و منطقی معتبر نیست (template) | adis fails the rule (error) | adis, prdis, dis | `adis = prdis − dis` (gold pattern has its own formula). | E2 E10 |
| 0303301 | مقدار فیلد شناسه کالا/خدمت با اطلاعات سامانه منطبق نیست | sstid not in the goods/services registry, or inconsistent (error) | sstid, vra | Use a valid 13-digit id from stuffid.tax.gov.ir. Also returned when vra ≠ the id's registered rate (e.g. 0 to claim exemption) (E10). A corrective may not change a line's sstid (E12). | E1 E6 E10 E12 |
| 0300601 | شمارهٔ مالیاتی صورتحساب مرجع با اطلاعات سامانه منطبق نیست | Reference taxid (irtaxid) not acceptable (error) | irtaxid | Causes (E1): reference not in کارپوشه, cancelled, or itself a pending/rejected corrective. Point to the newest registered version of the invoice (E8). | E1 E2 E8 E9 |
| 0300901 | مقدار فیلد «شماره اقتصادی فروشنده» با اطلاعات سامانه منطبق نیست | Seller economic code mismatch (error) | tins | Use the code shown in کارپوشه (E6); legal entities use their 11-digit national id (E16). If validate_invoice.py warns `id-check-digit` on tins, the number itself is mistyped (check digit fails). | E6 E16 |
| 0300902 | فروشنده صورتحساب با فروشنده صورتحساب مرجع منطبق نیست. | Seller differs from the reference invoice's seller (error) [UNVERIFIED full code] | tins | Keep tins identical to the reference invoice. | E1 E2 |
| 0300903 | فروشنده صورتحساب مجاز به ارسال الگوی صورتحساب ارسالی نمی‌باشد. | Seller not allowed to send this invoice pattern (error) [UNVERIFIED full code] | tins, inp | Check that inp is allowed for this taxpayer. | E1 E2 |
| 0301201 | شماره اقتصادی خریدار با اطلاعات سامانه منطبق نیست (paraphrase) | Buyer economic code not found / mismatch (error) | tinb | Correct the buyer's economic code. If validate_invoice.py warns `id-check-digit` on tinb, the number itself is mistyped (check digit fails). | E1 E16 |
| 00012 | فیلد «شماره اقتصادی خریدار» خالی است | Buyer economic code empty (error) | tinb, inty | Type 1 needs tinb for legal/partnership buyers; a natural-person buyer without tinb needs bid + bpc (E1), or issue type 2 (E7). | E1 E4 E7 |
| 0101204 | در مقدار وارد شده در فیلد شماره اقتصادی خریدار الگو (regex) رعایت نشده است | Buyer economic code format (error); short form 011204 | tinb | Digits only: 14 for natural persons / foreign nationals, 11 for legal entities / civil partnerships. | E1 E4 E6 |
| 0101104 | در مقدار وارد شده در فیلد شماره ملی/شناسه مشارکت مدنی/کد فراگیر خریدار الگو (regex) رعایت نشده است | Buyer national id format (error); short form 011104 | bid | Digits only: 10 natural person, 11 legal entity / partnership, 12 foreign national. | E1 E6 |
| 0101304 | در مقدار وارد شده در فیلد کد شعبه فروشنده الگو (regex) رعایت نشده است | Seller branch code format (error); short form 011304 | sbc | Exactly 4 digits. | E1 E6 |
| 0101504 | در مقدار وارد شده در فیلد کد شعبه خریدار الگو (regex) رعایت نشده است (template) | Buyer branch code format (error) | bbc | Exactly 4 digits. | E2 |
| 0100504 | در مقدار وارد شده در فیلد «سریال صورتحساب» الگو (regex) رعایت نشده است (template) | inno format; must match ^[a-fA-F0-9]{10}$ (error) | inno | Send the 10-char hex serial, i.e. taxid characters 12–21. | E11 |
| 1300501 | مقدار فیلد «سریال صورتحساب» با اطلاعات سامانه منطبق نیست. | inno differs from the serial inside taxid (warning — invoice accepted) | inno, taxid | Send inno = taxid[11:21] (10 hex chars). | E1 E2 E8 E11 |
| 0102004 | در مقدار وارد شده در فیلد «شناسه یکتا ثبت قرارداد فروشنده» الگو(^\d{12}$) رعایت نشده است. | Contract registration id format (error) | crn | Exactly 12 digits. | E8 |
| 0302001 | مقدار فیلد «شناسه یکتا ثبت قرارداد فروشنده» با اطلاعات سامانه منطبق نیست. | Contract id not registered/confirmed (error) [UNVERIFIED full code; vendor prints 032001] | crn | Register the contract in کارپوشه and have the counter-party confirm it first. | E6 |
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
| 00000 | تعداد پیام‌های خطا/هشدار بیشتر از ۵۰ مورد است و امکان نمایش بیشتر از این تعداد وجود ندارد | More than 50 messages; list truncated | — | Fix the listed errors and resend. | E1 E2 |
| 1301101 | شناسه ملی خریدار با اطلاعات سامانه منطبق نیست (paraphrase) | Buyer national id mismatch (warning) | bid | Verify the buyer's id. If validate_invoice.py warns `id-check-digit` on bid, the number itself is mistyped (check digit fails). | E7 |
| 1301001 | نوع شخص خریدار با اطلاعات سامانه منطبق نیست (paraphrase) | Buyer type inconsistent with system data (warning) | tob | Check tob against the buyer's registration. | E2 E7 |
| 1301401 | کد پستی خریدار با اطلاعات سامانه منطبق نیست (template) | Buyer postal code mismatch (warning) | bpc | | E2 |
| 04111 | قرارداد شناسه یکتا و شرکت معتمد یافت نشد | Memory id inactive, or no contract with a trusted company (error) | fiscalId | Reactivate the memory id; check the trusted-company contract. | E1 E6 |
| 04130 | — | JWS invalid after decryption (packet error) | packet | Fix packet signing. | E1 |
| 04131 | — | Invoice JWS signature or certificate invalid | packet | Fix signature/certificate. | E1 |
| 04132 | — | Signer's certificate may not send for this fiscalId | fiscalId | Use the right key or delegation. | E1 |
| 04148 | — | Issuer memory id format invalid | fiscalId | 6 upper-case letters/digits. | E1 |
| 04150 | — | JWE not 5-part / cannot decrypt | packet | | E1 |
| 04152 | — | JWE enc ≠ A256GCM or alg ≠ RSA-OAEP-256 | packet | | E1 |
| 04153 | — | JWE IV length is not 96 bits | packet | | E1 |

## 4. API-level codes (HTTP errors; response `errors: [{code, message}]`)

Codes starting with 4 are the caller's fault; 5 are server side — retry later (E1). Inquiry status values:
SUCCESS, FAILED, IN_PROGRESS, NOT_FOUND (TIMEOUT for range inquiry; TIMEOUT means the invoice was **not**
registered) (E1).

| code | message_fa | meaning_en | fields | fix | source |
|---|---|---|---|---|---|
| 4101 | — | HTTP 401: wrong method, or token payload is not {nonce, clientId} | token | | E1 |
| 4102 | — | HTTP 401: nonce invalid, used or expired (one snippet says "JWT structure invalid") | token | Get a fresh nonce for every token. | E1 E16 |
| 4103 | — | HTTP 401: certificate national id (SERIALNUMBER) is not the owner of clientId | certificate | Use the certificate issued to the memory id's owner. | E1 E7 |
| 4110 | — | HTTP 401: clientId (memory id) not found or inactive | fiscalId | Reactivate in کارپوشه › عضویت › شناسه‌های یکتای حافظه مالیاتی. | E1 E16 |
| 4120 | — | HTTP 401: trusted-company id not found or inactive | fiscalId | | E1 |
| 4130 | — | HTTP 401: token is not 3-part Base64Url | token | | E1 |
| 4131 | — | HTTP 401: incomplete header, bad signature, certificate not from an intermediate CA, or expired/revoked | certificate | | E1 |
| 4132 | — | HTTP 401: no public key registered for this memory id | fiscalId | Register the public key in کارپوشه. | E1 |
| 4133 | — | HTTP 401: invoice signature invalid | signature | | E1 |
| 4134 | — | HTTP 401: signed packet is not UTF-8 | packet | | E1 |
| 4135 | — | HTTP 401: x5c header empty | certificate | | E1 |
| 4136 | — | HTTP 401: certificate in x5c malformed | certificate | | E1 |
| 4137 | — | HTTP 401: certificate uploaded to کارپوشه is invalid | certificate | Replace it in کارپوشه. | E1 |
| 4140 | — | HTTP 400: inquiry start time after end time | inquiry | | E1 |
| 4141 | — | HTTP 400: more than 100 ids in one inquiry | inquiry | | E1 |
| 4142 | — | HTTP 400: invalid status filter | inquiry | | E1 |
| 4143 | — | HTTP 400: more than 1000 invoices in one request | packet | | E1 |
| 4144 | — | HTTP 400: empty or invalid JSON body | packet | | E1 |
| 4145 | — | HTTP 400: item missing payload, fiscalId or requestTraceId | packet | | E1 |
| 4146 | — | HTTP 400: timeToLive outside 10–200 s | packet | | E1 |
| 4147 | — | HTTP 400: input format wrong | packet | | E1 |
| 4148 | — | HTTP 400: memory id format invalid | fiscalId | | E1 |
| 4160 | — | HTTP 403: no access to this memory id's data | fiscalId | | E1 |
| 4162 | — | HTTP 400: requestTraceId is not a UUID | packet | | E1 |
| 4163 | — | HTTP 400: requestTraceId duplicated in one request | packet | | E1 |
| 4164 | — | HTTP 400: inquiry range longer than one week | inquiry | | E1 |
| 4170 | — | HTTP 404: economic code not found (taxpayer lookup) | tins/tinb | | E1 |
| 4171 | — | HTTP 404: economic code has wrong length | tins/tinb | | E1 |
| 5199 | خطای غیر منتظره‌ای در انجام درخواست رخ داد. | HTTP 500: unexpected server error | — | Retry later. | E1 E15 |
| 5119 | — | HTTP 500: server error (file lookup) | — | Retry later. | E1 |
| 5129 | — | HTTP 500: server error (trusted company) | — | Retry later. | E1 |
| 5139 | — | HTTP 500: server error (signature check) | — | Retry later. | E1 |
| 5051 | پردازه مدیریت کلید در دسترس نمی باشد، مدتی بعد تلاش کنید | Key-management service unavailable | — | Retry later. | E15 |
| 4011 | امضای بسته صحیح نمی باشد | Old API v1: packet signature invalid (seen when the memory id did not belong to the signing key) | signature | Check the key pair matches the memory id. | E11 E14 |
| 4212 | — | Old API v1: 400 BAD_REQUEST, traced to JSON normalisation before signing [cause UNVERIFIED] | packet | | E2 E13 |
| 5202 | — | Old API v1 inquiry FAILED; reporter fixed the symmetricKey encryption [cause UNVERIFIED] | packet | | E13 |

## 5. Field numbers used in codes (E1, EC_V02 table; `insr`=107 per E2)

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
- **«اعتبار درخواست داده شده منقضی شده است»** — request validity expired; reported once from the official
  .NET SDK and resolved itself; likely clock/nonce related [UNVERIFIED] (E14 #6).
- **Duplicate taxid** — resending an existing taxid is rejected with 0300101 and does not overwrite the
  stored invoice (E1, E4).
