# Approvals and acceptance
## Internal business approval
The approver is the tenant business's manager or sales employee with approval permission, not the purchasing customer.

1. Freeze a quotation version with prices, quantities, currency, tax/discount rules, delivery assumptions, expiry and source timestamps.
2. Create approval task plus notification intent in a transaction.
3. Notify the assigned manager by email initially; messaging notifications use the same notification adapter later.
4. Manager opens the portal, signs in, and sees the exact quotation plus exceptions.
5. Approve, reject, or request revision using an authenticated state-changing request.
6. Validate tenant, role, assignment/policy, pending status, expiry and quotation version.
7. Record the decision and durable resume job atomically; resume the mapped workflow.
8. Before sending, confirm version approval and validity still hold.

A link opens a page; GET requests never approve. Email scanners must not trigger decisions.
Use CSRF protection for cookie-authenticated forms. Notification links are not sufficient authorization.
Revisions create a new version and invalidate authorization to send the superseded one.
Approval deadlines escalate to an authorized backup or exception queue; no automatic approval on timeout.
Concurrent/replayed decisions return the existing outcome or a conflict, never silently overwrite decisions.

## Customer acceptance
After internal approval, the customer receives the quotation and a supported acceptance route.
Acceptance uses an authenticated customer session or a scoped, expiring token bound to that customer and quotation version; exact identity requirements are a pre-M6 decision.
Email/chat "yes" is an intent signal until correlated and verified under the chosen policy.
Recheck quote expiry, commercial terms, stock and order constraints before creation. Material changes require a revised quote and fresh relevant approvals/acceptance.
A purchasing customer cannot perform an internal manager approval through an acceptance link.

## Planned portal views
Tenant inbox, enquiry detail, quote/version comparison, pending approvals, order status, exception queue, connection settings and audit history.
Notifications include minimal sensitive data and link to authorized detail.
