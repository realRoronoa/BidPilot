# Billing (Sandbox)

Billing is demonstrated in sandbox mode — no real charges are ever made.

- Plans: Starter / Professional / Business (demo pricing in USD).
- `GET /api/billing` returns subscription, usage meters, plans, invoices.
- `POST /api/billing/upgrade` switches the plan and updates usage limits, always returning `sandbox: true`.
- Payment method is a demo card. Invoices are seeded history.

## Integration points for a real provider
- Replace `POST /api/billing/upgrade` with a provider checkout session (e.g. Stripe).
- Verify charges server-side via webhooks before marking a subscription active.
- Never trust frontend payment status. Never display success without provider confirmation.
