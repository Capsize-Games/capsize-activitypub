# Extraction boundary

The original implementation lived under the `activitypub` package in the
`uwuchat_old` repository:

```text
backend/activitypub
```

It provided both protocol mechanics and UwUChat product integration. The
standalone repository keeps the protocol mechanics that can be shared:

| Original surface | Standalone surface |
| --- | --- |
| WebFinger and remote actor fetches | `ActivityPubClient.discover()` and `.actor()` |
| Remote collection reads | `ActivityPubClient.collection()` and `.public_timeline()` |
| SSRF checks | `security.validate_remote_url()` |
| HTTP Signatures | `signatures.sign_request()` and `.verify_request()` |
| Remote actor persistence | `store.ConnectionStore` |

The following remain adapter responsibilities and are intentionally not
published as generic protocol behavior:

- UwUChat users and local actor URLs
- Django migrations and admin models
- social post rendering and post signal hooks
- Celery delivery jobs and dead-letter tables
- account authentication and moderation policy

The hosted Capsize account service is also intentionally outside this
repository. Configure its public actor and inbox URLs through environment
variables when a local bridge needs to report the user's public identity.

That boundary prevents the Capsize extension from modifying or vendoring the
AIRunner/UwUChat application while leaving the original federation server
available to that product.
