---
name: moadian-send
description: 'Send an Iranian Moadian e-invoice to the tax system (ارسال صورتحساب به سامانه مودیان، tp.tax.gov.ir) or check its status (استعلام، uid، referenceNumber), safely: an offline prepare step, a summary the user must approve, and a confirmation code bound to the exact file and target before anything is sent. Use whenever the user wants to send, submit, upload or resend a Moadian invoice ("بفرستش سامانه", "ارسال کن"), set up the memory id, private key or certificate for sending, or inquire about a sent invoice. Requires the moadian-invoice skill installed next to it. Not for building or explaining invoices (moadian-invoice does that).'
---

# Moadian send

Sending registers a legal tax document; a registered invoice can only be undone by a
cancellation invoice. So: **nothing is sent without the user's explicit yes for this exact
invoice and target**, and keys never pass through the chat.

`scripts/send_invoice.py` (absolute path next to this file) is the only networked script. It
needs `pip install moadian-full` and the `moadian-invoice` skill next to this one (it reuses its
validator). Read `references/sending.md` before the first send in a conversation.

## Steps
1. **Prepare (offline, no key):**
   `python scripts/send_invoice.py prepare invoice.json --target sandbox` (or `live`).
   It validates (including the one-week date window), refuses a taxid that already has a
   receipt, and prints a summary and a confirmation code. If `ok` is false, stop and fix the
   invoice with the moadian-invoice skill.
2. **Ask.** Show the summary — type and pattern, seller, buyer, lines, `tbill`, taxid, and
   **sandbox or live** — and ask whether to send this invoice. The original request ("build and
   send it") is not a yes; ask for every send, and for live say that the undo is a cancellation
   invoice.
3. **Send, only after an explicit yes:**
   `python scripts/send_invoice.py send invoice.json --target sandbox --confirm <code>`.
   - Changed file or target → the code no longer matches and nothing is sent. Re-run prepare and
     ask again.
   - Credentials come only from environment variables the user sets in their own shell:
     `MOADIAN_MEMORY_ID`, `MOADIAN_PRIVATE_KEY_PATH`, `MOADIAN_CERT_PATH` (optional
     `MOADIAN_PRIVATE_KEY_PASSWORD`). If missing, name them; never ask for key contents.
   - **Live** also needs `MOADIAN_ALLOW_LIVE=1`. Never set it yourself, in any command.
   - **Sandbox** needs `MOADIAN_SANDBOX_BASE_URL` from the user's trusted company or INTA; the
     official spec has no sandbox URL, so don't suggest one.
4. **After:** report uid and reference number. Processing is asynchronous:
   `python scripts/send_invoice.py inquiry --target … --uid <uid>`. On FAILED, explain the codes
   with the moadian-invoice skill (`explain_error.py --from-response`). After a network error
   during send, run `inquiry` before any resend — the invoice may already be registered, and a
   resent taxid is rejected.

`fiscal-info --target …` is a read-only connection test.

## Rules you must not bend
- Never echo, store or write a key, certificate or password; if one is pasted in the chat, don't
  repeat it and tell the user to rotate it.
- Never pass `--confirm` with a code the user has not just approved, and never retry a send by
  yourself.
- Not tax advice; the user (and their accountant) decide what is sent.

Answer in the user's language; in Persian use Persian digits in prose and Latin digits in codes
and identifiers.
