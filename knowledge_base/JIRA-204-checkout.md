# JIRA-204: Checkout Flow

**Status:** In Progress
**Sprint:** Sprint 3
**Acceptance Criteria:**
- Step 1 (/checkout-step-one.html): Collect first name, last name, zip code
- Validation: all three fields required — error if any missing
- Step 2 (/checkout-step-two.html): Order summary with item total, tax (8%), total
- Finish button completes the order
- Complete page (/checkout-complete.html): Shows "Thank you for your order!"
- Back Home button returns to /inventory.html

**Tax calculation:** 8% of item total (e.g. $29.99 → tax $2.40 → total $32.39)

**MISSING:** No end-to-end test from login through checkout complete
**MISSING:** No validation test for empty checkout fields
**MISSING:** No test verifying correct total calculation with tax
