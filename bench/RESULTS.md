# Validator benchmark

moadian-invoice 0.3.0 · Python 3.13.16 · Linux · 0.022 s

**PASS** — valid traps clean: 13/13 · seeded defects caught at the root: 37/37

## Traps (valid invoices that must stay clean)

| trap | result |
|---|---|
| sale-legal-cash | clean |
| sale-natural-person-bid-bpc | clean |
| type2-no-buyer | clean |
| setm3-mixed | clean |
| gold-pattern | clean |
| export-pattern | clean |
| cancellation-header-only | clean |
| decimal-quantity-and-price | clean |
| other-taxes-odam | clean |
| correction-ins2 | clean |
| sales-return-ins4 | clean |
| credit-sale-zero-payment | clean |
| multi-line-discounts | clean |

## Seeded defects

| defect | expected | result | likely code |
|---|---|---|---|
| prdis rounded instead of truncated | error at body[0].prdis | caught | 0204101 |
| adis ≠ prdis − dis | error at body[0].adis | caught | 0204301 |
| vam rounded half-up | error at body[0].vam | caught | 0204501 |
| dis greater than prdis | error at body[0].dis | caught | 0204201 |
| odam ≠ adis × odr | error at body[0].odam | caught |  |
| tsstam ≠ adis + vam + odam | error at body[0].tsstam | caught |  |
| tvam ≠ Σ vam | error at header.tvam | caught | 0202501 |
| tbill ≠ Σ tsstam | error at header.tbill | caught | 0202701 |
| tdis ≠ Σ dis | error at header.tdis | caught | 0202301 |
| cap = tbill on a cash invoice | error at header.cap | caught |  |
| setm 3 with cap + insp ≠ net | error at header.cap | caught |  |
| setm 3 without insp | error at header.insp | caught | 00030 |
| gold tcpbs ≠ consfee + spro + bros | error at body[0].tcpbs | caught |  |
| tax17 above tvam | error at header.tax17 | caught |  |
| pv on a credit invoice | error at payments[0].pv | caught |  |
| legal buyer without tinb | error at header.tinb | caught | 00012 |
| natural person without tinb or bpc | error at header.tinb | caught | 00012 |
| inty 4 (does not exist) | error at header.inty | caught | 0100402 |
| contracting pattern on type 2 | error at header.inp | caught |  |
| correction without irtaxid | error at header.irtaxid | caught | 00006 |
| return on an export invoice | error at header.ins | caught |  |
| wrong taxid check digit | error at header.taxid | caught | 0300101 |
| taxid day ≠ indatim day | error at header.taxid | caught | 0300101 |
| inno not 10 hex characters | error at header.inno | caught | 0100504 |
| sstid with 12 digits | error at body[0].sstid | caught | 0103304 |
| tins sent as a number | error at header.tins | caught | 0100903 |
| vam with decimals | error at body[0].vam | caught | 0104509 |
| body field in the header | error at header.vam | caught |  |
| VAT on a chain-sale pattern (inp 14) | error at body[0].vra | caught |  |
| required fee missing | error at body[0].fee | caught | 00037 |
| type 3 without payment data | error at payments | caught |  |
| indatim in the future | error at header.indatim | caught | 0200201 |
| seller legal id check digit | warning at header.tins | caught | 0300901 |
| buyer national code check digit | warning at header.bid | caught | 1301101 |
| field ignored for the pattern | warning at header.billid | caught | 14021 |
| unknown field | warning at header.foo | caught |  |
| items sent on a cancellation | warning at body | caught |  |
