# Units of measure (`mu`)

Use this file to pick a `mu` code or to answer "what unit is code X". Do not use a code that is
not in the table: the system rejects a `mu` outside its list with **0103502** («مقدار وارد شده در
فیلد واحد اندازه‌گیری جز مقادیر مجاز نیست», `errors.md`). `scripts/validate_invoice.py` reads the
table below and warns on any other code (a warning, not an error, because INTA may add codes
after V1.18).

## Source

| id | document | kind |
|---|---|---|
| S4 | **RC_UMGS.ST_V1.18** «واحدهای اندازه‌گیری کالا/خدمت», مرکز تنظیم مقررات، نظام پایانه‌های فروشگاهی و سامانه مؤدیان, اردیبهشت ۱۴۰۴, 4 pp. Copy read from github.com/ali-hallaji/digi-tax-ops `docs/moadian/RC_UMGS_ST_V1_18.pdf` (Word export of 2025-04-23; sha256 `f02700c754cc9a315ad5254645dd19a9eacd81b01345db6d61723e89f23b8665`) because intamedia.ir was unreachable. A recompressed copy in github.com/mojtabahakimian/Taxation `Prg_Grpsend/InfoDocuments/` (sha256 `54707380…7c9`) has the same text | official |

How it was read: text layer extracted with pypdf, then every row checked against the rendered
pages (pdftoppm). Ten names whose word order or spaces the text layer lost (rows 19, 21, 26, 49,
58, 89, 90, 91, 97, 102) are written as printed. Arabic «ك» and «ي» in the text layer are written
as Persian «ک» and «ی». The English column is our gloss, not part of S4; «—» means we have no
confident gloss.

Notes on the list (S4):
- Codes are 3 to 5 digits and are **not** all 4 digits: کیلوگرم is `164`, متر `165`, تن `169`.
  Send `mu` as a JSON string of digits (S1 §7-30).
- `16106`, `16107`, `16109`, `16123` and `16124` are not in V1.18.
- V1.18 adds row 102, نفر-ماه, to V1.16 (S4 p. 2).
- moadian-full 0.0.2 fills `mu = "164"` (کیلوگرم) when no unit is given; `build_invoice.py`
  leaves `mu` out instead (`fields.md` §4).

## Table (S4 pp. 3–4, in the document's row order)

| code | واحد سنجش | English (gloss) | row |
|---|---|---|---|
| 1611 | لنگه | — | 1 |
| 1612 | عدل | bale | 2 |
| 1613 | جعبه | box | 3 |
| 1618 | توپ | bolt (of fabric) | 4 |
| 1619 | ست | set | 5 |
| 1620 | دست | set (of clothes, dishes) | 6 |
| 1624 | کارتن | carton | 7 |
| 1627 | عدد | piece (count) | 8 |
| 1628 | بسته | pack | 9 |
| 1629 | پاکت | packet, envelope | 10 |
| 1631 | دستگاه | device, machine | 11 |
| 1640 | تخته | board, sheet | 12 |
| 1641 | رول | roll | 13 |
| 1642 | طاقه | bolt (of cloth) | 14 |
| 1643 | جفت | pair | 15 |
| 1645 | متر مربع | square metre | 16 |
| 1649 | پالت | pallet | 17 |
| 1661 | دوجین | dozen | 18 |
| 1668 | حلقه (رینگ) | ring | 19 |
| 1673 | قراص | — | 20 |
| 1694 | قراصه (bundle) | bundle | 21 |
| 1637 | لیتر | litre | 22 |
| 1650 | ساشه | sachet | 23 |
| 1683 | کپسول | capsule | 24 |
| 1656 | بندیل | bundle | 25 |
| 1630 | حلقه (رول) | roll, coil | 26 |
| 163 | قالب | bar, block (e.g. soap) | 27 |
| 1660 | شانه | tray (e.g. eggs) | 28 |
| 1647 | متر مکعب | cubic metre | 29 |
| 1689 | ثوب | — | 30 |
| 1690 | نیم دوجین | half dozen | 31 |
| 1635 | قرقره | spool, reel | 32 |
| 164 | کیلوگرم | kilogram | 33 |
| 1638 | بطری | bottle | 34 |
| 161 | برگ | leaf, sheet | 35 |
| 1625 | سطل | bucket | 36 |
| 1654 | ورق | sheet | 37 |
| 1646 | شاخه | stick, length | 38 |
| 1644 | قوطی | can, tin | 39 |
| 1617 | جلد | volume (book) | 40 |
| 162 | تیوب | tube | 41 |
| 165 | متر | metre | 42 |
| 1610 | کلاف | skein, coil | 43 |
| 1615 | کیسه | bag, sack | 44 |
| 1680 | طغرا | — | 45 |
| 1639 | بشکه | barrel | 46 |
| 1614 | گالن | gallon (container) | 47 |
| 1687 | فاقد بسته بندی | unpackaged | 48 |
| 1693 | کارتن (master case) | master case | 49 |
| 166 | صفحه | page, plate | 50 |
| 1666 | مخزن | tank | 51 |
| 1626 | تانکر | tanker | 52 |
| 1648 | دبه | jerrycan | 53 |
| 1684 | سبد | basket | 54 |
| 169 | تن | tonne | 55 |
| 1651 | بانکه | jar | 56 |
| 1633 | سیلندر | cylinder | 57 |
| 1679 | فوت مربع | square foot | 58 |
| 168 | حلب | tin (container) | 59 |
| 1665 | شیت | sheet | 60 |
| 1659 | چلیک | keg, drum | 61 |
| 1636 | جام | — | 62 |
| 1622 | گرم | gram | 63 |
| 1616 | نخ | single (thread, cigarette) | 64 |
| 1652 | شعله | — | 65 |
| 1678 | قیراط | carat | 66 |
| 16100 | میلی لیتر | millilitre | 67 |
| 16101 | میلی متر | millimetre | 68 |
| 16102 | میلی گرم | milligram | 69 |
| 16103 | ساعت | hour | 70 |
| 16104 | روز | day | 71 |
| 16105 | تن کیلومتر | tonne-kilometre | 72 |
| 1669 | کیلووات ساعت | kilowatt-hour | 73 |
| 1676 | نفر | person | 74 |
| 16110 | ثانیه | second | 75 |
| 16111 | دقیقه | minute | 76 |
| 16112 | ماه | month | 77 |
| 16113 | سال | year | 78 |
| 16114 | قطعه | piece, part | 79 |
| 16115 | سانتی متر | centimetre | 80 |
| 16116 | سانتی متر مربع | square centimetre | 81 |
| 1632 | فروند | unit (ships, aircraft) | 82 |
| 1653 | واحد | unit | 83 |
| 16108 | لیوان | glass, cup | 84 |
| 16117 | نوبت | turn, session | 85 |
| 16118 | مگا وات ساعت | megawatt-hour | 86 |
| 16119 | گیگا بایت بر ثانیه | gigabyte per second | 87 |
| 1681 | ویال | vial | 88 |
| 1667 | حلقه (دیسک) | disc | 89 |
| 16120 | نسخه (جلد) | copy (volume) | 90 |
| 16121 | نفر-ساعت | person-hour | 91 |
| 16122 | کیلومتر | kilometre | 92 |
| 16125 | آمپر | ampere | 93 |
| 16126 | میلی آمپر | milliampere | 94 |
| 16127 | مثقال | mesghal (≈4.6 g) | 95 |
| 16128 | سیر | sir (≈75 g) | 96 |
| 16129 | دفعه (time) | time (occurrence) | 97 |
| 16130 | مگا یونیت | mega unit | 98 |
| 16131 | کادر | — | 99 |
| 16132 | پرس | portion (food) | 100 |
| 16133 | بلوک | block | 101 |
| 16134 | نفر-ماه | person-month | 102 |
