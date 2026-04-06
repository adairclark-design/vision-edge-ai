# Layer 1 Architecture: Payment Gating

This SOP documents the `Stripe` logic used in Layer 2 (Next.js Navigation) before a scan is allowed.

## 1. Goal

Ensure a user has sufficient credits or an active "Pro" subscription before invoking Layer 3 (`tools/analyze_chart.py`). LLM API calls cost money; we must block unauthorized execution.

## 2. Logic Flow

1. **Request Intercept:** User uploads image -> hits `/api/scan`.
2. **Auth Check:** Middleware checks Supabase session. If no user, return `401 Unauthorized`.
3. **Entitlement Check:**
   - Query `users` table in Supabase.
   - Check `subscription_status` == 'active' OR `credits` > 0.
   - If false, return `402 Payment Required` with a Stripe Checkout URL.
4. **Execution:** If true, proceed to Layer 3.
5. **Deduction:** If the scan is successful (Layer 3 returns `200 OK` and a valid `AnalysisPayload`), deduct 1 credit from the user's Supabase record (if not on 'active' sub).

## 3. Edge Cases

- **Stripe Webhook Failure:** If a user pays but the webhook fails to update Supabase, we log the Stripe `session_id` in a `failed_webhooks` table for a cron job to retry.
- **Scan Failure:** If `tools/analyze_chart.py` fails (e.g., 500 error, Gemini is down), DO NOT deduct a credit. The user only pays for successful clarity.
