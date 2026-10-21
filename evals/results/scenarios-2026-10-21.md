# moadian-invoice: grading summary

| Iter | Eval | with_skill | without_skill | Notes |
|---|---|---|---|---|
| 1 | 1 build-type1 | 6/7 | 3/7 | The skill run never said a real send needs the user's explicit OK. The baseline hand-wrote the JSON with cap=tbill/insp=0, so the validator fails it; its reply is in English. |
| 1 | 2 debug-arith | 4/4 | 0/4 | The baseline missed the prdis truncation and recommended cap=tbill, insp=0 and tbill 2090001, all wrong. |
| 1 | 5 key+send | 5/5 | 4/5 | The baseline only eyeballed the totals and missed the stale indatim. |
| 2 | 1 build-type1 | 7/7 | 4/7 | Same baseline invoice problems as iteration 1, but the reply is now in Persian with Persian digits. |
| 2 | 2 debug-arith | 4/4 | 4/4 **CONTAMINATED** | The baseline found /home/user/moadian-invoice and ran the skill's validate_invoice.py. Excluded; use iteration 1's 0/4 baseline. |
| 2 | 5 key+send | 5/5 | 4/5 | Same pattern as iteration 1. |

**Clean totals.** Iteration 2 with_skill: 16/16. Without_skill: iteration 1 = 7/16; iteration 2, excluding eval 2, = 8/12.

**Repo exposure in other baselines.** Three baselines only listed the skill repo and never read skill files or ran scripts, so I kept them as valid baselines and noted it in each grading.json:
- iteration 1 eval 2: `ls /home/user/moadian-invoice …/examples`
- iteration 1 and iteration 2 eval 5: `ls -la /home/user/moadian-invoice`

**Assertions that pass in every run (they don't discriminate):**
- Eval 1: body line, header totals, inty/inp/ins/tob.
- Eval 5: key not written, key not echoed, rotation and external-path advice, no send and asked for confirmation.
- In eval 5, only "Validated invoice.json" separates the configurations.

**Other observations:**
- **Eval 1 validation assertion.** The skill runs passed "Ran validate_invoice.py" because build_invoice.py runs the validator internally (`"validation": {"ok": true}`). They never ran it as a separate command. Consider rewording the assertion.
- **Seller ID check digit.** Seller ID 10101234567 fails the legal-entity check-digit algorithm (I recomputed it). The iteration-1 baseline flagged this; neither skill run did, and the validator doesn't check it.
- **Stale invoice date.** In eval 5, both skill runs caught that indatim is about six months old, so the invoice would likely be rejected (0200201). No baseline caught it, and no assertion rewards it. It would make a strong discriminating assertion.
- **What improved in iteration 2.** The iteration-1 with_skill eval-1 failure on explicit send confirmation is fixed. For eval 2, the current validator reports all 8 propagated errors with tbill=2090000.
