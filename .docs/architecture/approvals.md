# Approvals and acceptance
## Internal business approval
The approver is the tenant business's manager or sales employee with approval permission, not the purchasing customer.

1. Freeze a quotation version with prices, quantities, currency, tax/discount rules, delivery assumptions, expiry and source timestamps.
2. Create approval task plus notification intent in a transaction.
3. Send a review packet through the tenant's configured manager approval channel(s), independently of the customer's enquiry channel.
4. Manager reviews the exact quotation and exceptions in the mobile-friendly portal or directly within a supported messaging channel. Provide the draft PDF or complete accessible commercial detail, not just an unexplained total.
5. Approve, reject, or request revision through a verified interaction. All entry points submit the same approval command to the application service.
6. Validate tenant, role, assignment/policy, pending status, expiry and quotation version.
7. Record the decision and durable resume job atomically; resume the mapped workflow.
8. Before sending, confirm version approval and validity still hold.

A link opens a page; GET requests never approve. Email scanners must not trigger decisions.
Use CSRF protection for cookie-authenticated forms. Notification links are not sufficient authorization.
Channel decisions require verified provider events, an enrolled internal manager identity and task-specific action correlation. Provider authentication alone proves neither the manager's role nor their authority for this quotation.
Revisions create a new version and invalidate authorization to send the superseded one.
Approval deadlines escalate to an authorized backup or exception queue; no automatic approval on timeout.
Concurrent/replayed decisions return the existing outcome or a conflict, never silently overwrite decisions.

## Manager experience and configuration
Example: the customer enquires by email; the business's manager reviews on Telegram; the approved PDF goes back to the customer by email. These routes are separate tenant settings.
An in-channel review packet identifies the business, customer, quote number/version, line items, currency, totals, discounts, taxes, delivery assumptions, expiry and exceptions. Any draft PDF is marked as pending approval and distinct from the customer-facing approved document.
Actions are Approve, Reject and Request revision. Capture a reason where tenant policy requires it. Unsupported/ambiguous text prompts clarification rather than silently changing state.
Do not require portal login for every action when an enrolled channel identity satisfies the configured authorization policy. Enrollment/recovery, unusual risk or insufficient review capability may require additional verification.
Email review/decision mode is confirmed: managers can approve or reject by replying directly to the review email, without opening the portal for each decision. Verify the enrolled sender using trusted inbound-provider evidence and correlate the reply to the exact pending task/version. Do not implement bare sender-address matching as approval authentication.
Only the manager's new reply text is a candidate decision; quoted history, signatures, forwarded approvals and automatic replies must not authorize actions. Ambiguous, conditional or mixed instructions remain pending for clarification. For example, "approved if you reduce the price" requests a revision, not approval of unseen changed terms. Send a confirmation identifying the recorded decision and quotation version. Define and test provider-specific verification before enabling direct email decisions.

## Identity and command contract
Enroll a channel identity through an authenticated administrator/manager flow and proof of control. Bind tenant, membership, provider connection, stable external user ID and allowed context. Display names, phone-number text in a message, and customer contact records do not confer authority.
Revalidate current role, binding status and task assignment on every decision. Revocation invalidates outstanding actions. Tenant policy must define allowed private/shared contexts before enabling a connector.
Canonical decision fields: command ID, tenant resolved by the server, approval task ID, quotation ID/version/hash, internal actor ID, action, optional reason, transport, verified evidence reference and received timestamp.
Use opaque expiring action references bound server-side to task, version, intended actor and connection. Verify actor independently so forwarded buttons/links cannot authorize another person. Keep credentials/tokens out of audit text and model input.
The service atomically records one valid decision, consumes its action reference, writes audit and creates a resume job. Replay returns the recorded result; conflicting actions report conflict. Failure to deliver a confirmation does not undo a completed approval.
When multiple channels notify the same manager, they reference one task. Completing it makes all other actions stale; best-effort message updates are cosmetic, not the authority check.

## Extension boundary
See [module boundaries](module-boundaries.md) and [integration contracts](integrations.md). New provider approval support adds transport mapping, identity verification, rendering, registration/configuration and adapter tests. It must not introduce provider branches into pricing, quotation versioning, order creation or LangGraph's approval-resume logic.

## Customer acceptance
After internal approval, the customer receives the quotation and a supported acceptance route.
Acceptance uses an authenticated customer session or a scoped, expiring token bound to that customer and quotation version; exact identity requirements are a pre-M6 decision.
Email/chat "yes" is an intent signal until correlated and verified under the chosen policy.
Recheck quote expiry, commercial terms, stock and order constraints before creation. Material changes require a revised quote and fresh relevant approvals/acceptance.
A purchasing customer cannot perform an internal manager approval through an acceptance link.
Price objections and counteroffers are not acceptance. See the [deferred negotiation plan](../plan/negotiation.md).

## Planned portal views
Tenant inbox, enquiry detail, quote/version comparison, pending approvals, order status, exception queue, connection settings and audit history.
Review messages provide the authorized manager enough detail to decide in-channel, with tenant-controlled disclosure. The portal remains an optional review surface.
