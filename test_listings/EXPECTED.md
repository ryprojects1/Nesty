# Expected results (B2)

Enter price + city in the app alongside the pasted text. Adjust price values if A1's rent_averages.py differs.

| File | Price | City | Expected level | Why |
|------|-------|------|----------------|-----|
| obvious_scam.txt | 300 | Guildford | RED (score 100) | Hits nearly every rule: pay_before_viewing, landlord_abroad, odd_payment, off_platform, urgency, no_contract, price_too_low. Override rule applies |
| subtle_scam.txt | 520 | Guildford | AMBER or RED | Few exact keywords. Rules may catch only weak signs ("reservation", "can't hold it for long"). AI should catch the pressure tactic, deferred viewing, inconsistent story (Victoria line isn't in Guildford; "room" vs "3 bed flat on the 4th floor with a garden"), generic "trustworthy" text, personal details request. |
| legit.txt | 680 | Guildford | GREEN | Viewings first, written contract, protected deposit, named agency |
| edge_legit_holding_deposit.txt | 640 | Guildford | GREEN (AMBER acceptable, RED = bug) | Legit but contains "holding deposit", "lots of people interested". Tests false positives. Holding deposit comes AFTER viewing |
| edge_short_cheap.txt | 250 | Guildford | AMBER | No keywords. Only price_too_low should fire. Tests that short text doesn't crash and price check works alone |

## Extra tests (no file needed)
- Empty text -> friendly message, no crash
- Whitespace only -> same
- Wi-Fi/API off -> rules-only result, ai_available = false
- No price / no city entered -> price_too_low simply skipped, no crash
- Unknown city (e.g. "Aberystwyth") -> no crash
- Very long text (paste obvious_scam 10 times) -> still works
