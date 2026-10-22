# Technical references
Reviewed 2026-10-22. Recheck current provider requirements and exact library versions when implementing.

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpointers preserve workflow state; they are not the business database or outbound scheduler.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): supports pause/resume; resumed execution requires replay-safe actions.
- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html): policy enforcement is part of the isolation design; privileged/owner roles require care.
- [Telegram Bot API](https://core.telegram.org/bots/api): verify webhook and outbound capabilities against the implemented API version.
- [n8n hosting](https://docs.n8n.io/hosting/): optional deployment choices; evaluate commercial licensing separately.
- [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/overview): reference URL; fetch returned HTTP 429 during planning, so detailed requirements remain unverified.
- [Instagram messaging API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api): reference URL; fetch returned HTTP 429 during planning. Validate current permissions, supported account types and messaging restrictions before adapter implementation.

Architectural decisions are project choices. These sources establish relevant platform capabilities, not proof that this application already implements them.
