# Invoice type (inty), pattern (inp) and subject (ins)

Read this to decide which type/pattern/subject to use, or to explain the difference. Every
statement cites S1 = RC_IITP.IS_V7.8 (official; see fields.md for source details). These three
fields are the ones most often confused — moadian-full 0.0.2 itself mislabels them (fields.md §4).

## 1. inty — invoice type «نوع صورتحساب» (S1 §7-4, definitions §3)

> «نوع صورتحساب شامل: صورتحساب الکترونیکی نوع اول ۱، صورتحساب الکترونیکی نوع دوم ۲، صورتحساب الکترونیکی نوع سوم ۳ است.»

| inty | name | what it is | buyer data |
|---|---|---|---|
| 1 | نوع اول | Full seller **and buyer** information. After acceptance it goes to the buyer's کارپوشه by economic code; once the buyer confirms, the VAT counts as the buyer's tax credit. | Required: tob; for legal entity / partnership (tob 2/3) `tinb`; for natural person / foreign national (tob 1/4) `tinb` **or** `bid` + `bpc` (S1 §7-9 rules 4–5) |
| 2 | نوع دوم | Full seller and item information, buyer information optional; no tax credit for the buyer. «در صورتی که صورتحساب از نوع دوم باشد، ثبت اطلاعات مربوط به خریدار، الزامی نیست و کل مبلغ صورتحساب نقدی تلقی می‌شود.» | Optional |
| 3 | نوع سوم | The card-reader / payment-gateway receipt: amount, acceptor data (switch, acceptor, terminal), tracking number, payment time and minimal seller data. Still has a taxid. | None |

There is **no inty 4**. Export, contracting etc. are patterns (inp), not types.

**Choosing between 1 and 2** (facts from S1, the choice itself is the taxpayer's): the buyer can
only claim the VAT as a credit from a type-1 invoice. A type-2 invoice is allowed only with
patterns 1, 3, 9, 13 and its whole amount is treated as cash. If you lack the buyer's economic
code, a type-1 invoice for a natural person is still possible with national id + postal code.
This skill is not tax advice — the user should confirm the choice with their accountant.

Type 3 has **no column in S1 Table 1**; which header fields and patterns apply to it is
[UNVERIFIED]. The payment fields are mandatory for it (S1 §7-52…§7-60).

## 2. inp — invoice pattern «الگوی صورتحساب» (S1 §7-7)

| inp | pattern | inty 1 | inty 2 | notes (S1) |
|---|---|---|---|---|
| 1 | فروش (sale) | ✔ | ✔ | general pattern for all sellers |
| 2 | فروش ارز (currency sale) | ✔ | ✘ | exchange offices and banks; cfee, cut, exr, cpr, sovat mandatory |
| 3 | طلا، جواهر و پلاتین (gold, jewellery, platinum) | ✔ | ✔ | consfee, spro, bros, tcpbs mandatory |
| 4 | قرارداد پیمانکاری (contracting) | ✔ | ✘ | crn mandatory |
| 5 | قبوض خدماتی (utility bills) | ✔ | ✘ | billid mandatory; settlement cash |
| 6 | بلیط هواپیما (airline ticket) | ✔ | ✘ | ft mandatory; am = 1 |
| 7 | صادرات (export) | ✔ | ✘ | ssrv, sscv, torv, tocv mandatory; vra = 0 |
| 8 | بارنامه (waybill) | ✔ | ✘ | lno, ocu, dco, tid, lt, cno, sg mandatory |
| 9 | فروش فرآورده‌های نفتی (petroleum products) | ✔ | ✔ | only the two national petroleum companies |
| 11 | بورس اوراق بهادار مبتنی بر کالا (commodity exchange) | ✔ | ✘ | asn, asd mandatory; vra = 0; one line |
| 13 | فروش خدمات بیمه‌ای (insurance) | ✔ | ✔ | `in` mandatory |
| 14 | فروش زنجیره (chain sale, Art. 17 note 5) | ✔ | ✘ | tinb mandatory; vra = 0; one line |

Values 10 and 12 are not defined in V7.8.

## 3. ins — invoice subject «موضوع صورتحساب» (S1 §7-8, §5)

| ins | subject | when (S1 §5) | rules |
|---|---|---|---|
| 1 | اصلی (original) | first invoice for a transaction | — |
| 2 | اصلاحی (correction) | change amounts/quantities of a registered invoice | irtaxid required; same inty, inp; buyer, sstid, inty, inp, vra cannot change (cancel and reissue instead) |
| 3 | ابطالی (cancellation) | buyer data change, all items returned, transaction did not happen, wrong date | irtaxid required; inty/inp ignored; buyer and items come from the reference invoice |
| 4 | برگشت از فروش (sales return) | partial return; send the sold items **minus** the returned ones | irtaxid required; not allowed for P7, P8, P11 |

For ins 2/3/4 all buyer fields are «خارج از الگو» (S1 §7-8 rule 3), and indatim must be later
than the reference invoice (S1 §7-2). Secondary sandbox logs (errors.md E8, E9) report 14004/14007
warnings when inty/inp are sent on a referring invoice and that a cancellation is accepted as
header-only (`body: []`); `build_invoice.py` follows that for ins 3.

## 4. Other enumerations

- **tob** «نوع شخص خریدار»: 1 حقیقی (natural), 2 حقوقی (legal), 3 مشارکت مدنی (civil partnership), 4 اتباع غیر ایرانی (S1 §7-9 rule 3).
- **setm** «روش تسویه»: 1 نقدی (cash), 2 نسیه (credit), 3 نقدی/نسیه (mixed); types 2 and 3 are cash; P5, P11 cash (S1 §7-22).
- **pmt** «روش پرداخت»: 1 چک, 2 تهاتر, 3 وجه نقد, 4 pos, 5 درگاه اینترنتی, 6 کارت به کارت, 7 انتقال به حساب, 8 سایر (S1 §7-55).
- **ft**: 1 domestic, 2 international (S1 §7-9). **lt**: 1 road, 2 rail, 3 air, 4 sea (S1 §7-73).

## 5. Field requirements per type and pattern (S1 Table 1, p.13)

M mandatory · O optional · C mandatory under conditions (see fields.md) · – ignored («خارج از الگو»:
the system does not store it; sending it may produce a 14xxx warning). Columns are inty·inp.
This table is machine-checked against `scripts/_spec.py` by the tests.

| field | فارسی | T1·P1 | T1·P2 | T1·P3 | T1·P4 | T1·P5 | T1·P6 | T1·P7 | T1·P8 | T1·P9 | T1·P11 | T1·P13 | T1·P14 | T2·P1 | T2·P3 | T2·P9 | T2·P13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| taxid | شماره منحصر به فرد مالیاتی | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| indatim | تاریخ و زمان صدور صورتحساب (میلادی) | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| indati2m | تاریخ و زمان ایجاد صورتحساب (میلادی) | C | C | C | C | C | C | C | C | C | C | C | C | C | C | C | C |
| inty | نوع صورتحساب | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| inno | سریال صورتحساب داخلی حافظه مالیاتی | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O |
| irtaxid | شماره منحصر به فرد مالیاتی صورتحساب مرجع | C | C | C | C | C | C | C | C | C | C | C | C | C | C | C | C |
| inp | الگوی صورتحساب | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| ins | موضوع صورتحساب | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| tins | شماره اقتصادی فروشنده | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| tob | نوع شخص خریدار | M | M | M | M | M | M | O | M | M | – | M | M | O | O | O | O |
| bid | شماره/شناسه ملی/شناسه مشارکت مدنی/کد فراگیر خریدار | O | C | O | O | O | C | O | O | O | – | O | O | O | O | O | O |
| tinb | شماره اقتصادی خریدار | C | C | C | C | O | O | O | C | C | – | C | M | O | O | O | O |
| sbc | کد شعبه فروشنده | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O |
| bpc | کد پستی خریدار | O | O | O | O | O | O | O | O | O | – | O | O | O | O | O | O |
| bbc | کد شعبه خریدار | O | O | O | O | O | O | O | O | O | – | O | O | O | O | O | O |
| ft | نوع پرواز | – | – | – | – | – | M | – | – | – | – | – | – | – | – | – | – |
| bpn | شماره گذرنامه خریدار | – | C | – | – | – | C | O | – | – | – | – | – | – | – | – | – |
| scln | شماره پروانه گمرکی | O | O | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| scc | کد گمرک محل اظهار فروشنده | O | O | – | – | – | – | O | – | – | – | – | – | – | – | – | – |
| cdcn | شماره کوتاژ اظهارنامه گمرکی | – | – | – | – | – | – | O | – | – | – | – | – | – | – | – | – |
| cdcd | تاریخ کوتاژ اظهارنامه گمرکی | – | – | – | – | – | – | O | – | – | – | – | – | – | – | – | – |
| crn | شماره قرارداد پیمانکاری | O | O | O | M | – | – | – | – | – | – | – | – | – | – | – | – |
| billid | شماره اشتراک/شناسه قبض بهره‌بردار | – | – | – | – | M | – | – | – | – | – | – | – | – | – | – | – |
| tprdis | مجموع مبلغ قبل از کسر تخفیف | M | M | M | M | M | M | – | M | M | – | M | M | M | M | M | M |
| tdis | مجموع تخفیفات | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| tadis | مجموع مبلغ پس از کسر تخفیف | M | M | M | M | M | M | – | M | M | M | M | M | M | M | M | M |
| tvam | مجموع مالیات بر ارزش افزوده | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| todam | مجموع سایر مالیات، عوارض و وجوه قانونی | M | M | M | M | M | M | M | M | M | – | M | M | M | M | M | M |
| tbill | مجموع صورتحساب | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| tonw | مجموع وزن خالص | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – | – |
| torv | مجموع ارزش ریالی | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – | – |
| tocv | مجموع ارزش ارزی | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – | – |
| setm | روش تسویه | M | M | M | M | – | M | M | M | M | – | M | M | – | – | – | – |
| cap | مبلغ پرداختی نقدی | C | C | C | C | – | C | C | C | C | – | C | C | – | – | – | – |
| insp | مبلغ نسیه | C | C | C | C | – | C | C | C | C | – | C | C | – | – | – | – |
| tvop | مجموع سهم مالیات بر ارزش افزوده از پرداخت | O | O | O | O | – | O | O | O | O | – | O | O | – | – | – | – |
| tax17 | مالیات موضوع ماده ۱۷ | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| sstid | شناسه کالا/خدمت | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| sstt | شرح کالا/خدمت | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O | O |
| am | تعداد/مقدار | M | – | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| mu | واحد اندازه‌گیری | O | – | O | O | O | O | O | – | O | M | O | O | O | O | O | O |
| nw | وزن خالص | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – | – |
| fee | مبلغ واحد | M | – | M | M | M | M | O | M | M | – | M | M | M | M | M | M |
| cfee | میزان ارز | O | M | O | O | – | O | – | O | O | – | O | O | O | O | O | O |
| cut | نوع ارز | O | M | O | O | – | O | M | O | O | – | O | O | O | O | O | O |
| exr | نرخ برابری ارز با ریال | O | M | O | O | – | O | M | O | O | – | O | O | O | O | O | O |
| ssrv | ارزش ریالی کالا | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – | – |
| sscv | ارزش ارزی کالا | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – | – |
| prdis | مبلغ قبل از تخفیف | M | M | M | M | M | M | – | M | M | – | M | M | M | M | M | M |
| dis | مبلغ تخفیف | M | M | M | M | M | M | – | M | M | – | M | M | M | M | M | M |
| adis | مبلغ بعد از تخفیف | M | M | M | M | M | M | – | M | M | M | M | M | M | M | M | M |
| vra | نرخ مالیات بر ارزش افزوده | M | M | M | M | M | M | M | M | C | M | M | M | M | M | C | M |
| vam | مبلغ مالیات بر ارزش افزوده | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| odt | موضوع سایر مالیات و عوارض | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| odr | نرخ سایر مالیات و عوارض | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| odam | مبلغ سایر مالیات و عوارض | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| olt | موضوع سایر وجوه قانونی | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| olr | نرخ سایر وجوه قانونی | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| olam | مبلغ سایر وجوه قانونی | C | C | C | C | C | C | C | C | C | – | C | C | C | C | C | C |
| consfee | اجرت ساخت | – | – | M | – | – | – | – | – | – | – | – | – | – | M | – | – |
| spro | سود فروشنده | – | – | M | – | – | – | – | – | – | – | – | – | – | M | – | – |
| bros | حق‌العمل | – | – | M | – | – | – | – | – | – | – | – | – | – | M | – | – |
| tcpbs | جمع کل اجرت، حق‌العمل و سود | – | – | M | – | – | – | – | – | – | – | – | – | – | M | – | – |
| cop | سهم نقدی از پرداخت | O | O | O | O | – | O | O | O | O | – | O | O | – | – | – | – |
| vop | سهم مالیات بر ارزش افزوده از پرداخت | O | O | O | O | – | O | O | O | O | – | O | O | – | – | – | – |
| bsrn | شماره قرارداد حق‌العملکاری | O | O | O | O | O | O | O | O | O | – | O | O | O | O | O | O |
| tsstam | مبلغ کل کالا/خدمت | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| iinn | شماره سوئیچ پرداخت | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| acn | شماره پذیرنده فروشگاهی | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| trmn | شماره پایانه | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| pmt | روش پرداخت | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| trn | شماره پیگیری/شماره مرجع | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| pcn | شماره کارت پرداخت کننده | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| pid | شماره/شناسه ملی پرداخت کننده | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| pdt | تاریخ و زمان پرداخت | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| pv | مبلغ پرداختی | O | O | O | O | O | O | – | O | O | – | O | O | O | O | O | O |
| cui | عیار | – | – | O | – | – | – | – | – | – | O | – | – | – | O | – | – |
| tinc | شماره اقتصادی آژانس | – | – | – | – | – | O | – | – | – | – | – | – | – | – | – | – |
| lno | شماره بارنامه | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| lrno | شماره بارنامه مرجع | – | – | – | – | – | – | – | O | – | – | – | – | – | – | – | – |
| ocu | کشور مبدا | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| oci | شهر مبدا | – | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – |
| dco | کشور مقصد | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| dci | شهر مقصد | – | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – |
| tid | شناسه/شماره ملی فرستنده | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| rid | شناسه/شماره ملی گیرنده | – | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – |
| lt | نوع بارنامه/نوع حمل | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| cno | شماره ناوگان | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| did | شماره ملی/کد فراگیر راننده | – | – | – | – | – | – | – | C | – | – | – | – | – | – | – | – |
| sg | کالاهای حمل شده | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| sgid | شناسه کالای حمل شده | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| sgt | شرح کالای حمل شده | – | – | – | – | – | – | – | M | – | – | – | – | – | – | – | – |
| cpr | نرخ خرید ارز | – | M | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| sovat | ماخذ مالیات بر ارزش افزوده در الگوی فروش ارز | – | M | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| asn | شماره اعلامیه فروش بورس | – | – | – | – | – | – | – | – | – | M | – | – | – | – | – | – |
| asd | تاریخ اعلامیه فروش بورس | – | – | – | – | – | – | – | – | – | M | – | – | – | – | – | – |
| in | شناسه یکتای بیمه‌نامه | – | – | – | – | – | – | – | – | – | – | M | – | – | – | – | M |
| an | شناسه یکتای الحاقیه | – | – | – | – | – | – | – | – | – | – | O | – | – | – | – | O |
| vba | مبلغ پایه مالیات بر ارزش افزوده | – | – | – | – | – | – | – | – | C | – | – | – | – | – | C | – |
