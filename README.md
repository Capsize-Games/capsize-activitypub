# Capsize ActivityPub

Capsize ActivityPub is a small standalone ActivityPub client bridge extracted
from the ActivityPub work originally implemented in UwUChat. It is intended to
give Capsize applications a shared way to discover and read public ActivityPub
accounts without coupling them to UwUChat's Django models.

Current surface:

- WebFinger account discovery (`@user@example.com`)
- Actor document retrieval
- Public actor outbox/collection reads
- Local SQLite storage for discovered actors
- SSRF-aware outbound URL validation
- HTTP-signature creation and verification primitives for future signed actions
- A local HTTP bridge for dashboard extensions
- A public Capsize identity status endpoint for a hosted actor configured by
  `capsize.online`

The bridge is deliberately read-oriented in this first extraction. The local
dashboard is not automatically a publicly reachable ActivityPub actor. When a
Capsize account service supplies `CAPSIZE_ACTIVITYPUB_ACTOR_URL`, the bridge
reports that hosted identity to local clients; the hosted service remains the
owner of account authentication, actor documents, inbox delivery, and private
keys. UwUChat is optional and is not an identity dependency.

## Run the bridge

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
capsize-activitypub
```

The default bridge is `http://127.0.0.1:8790`.

```text
GET /health
GET /api/activitypub/discover?acct=@user@example.com
GET /api/activitypub/timeline?actor=https://example.com/users/user
GET /api/activitypub/connections
GET /api/activitypub/identity
```

For a hosted Capsize identity, configure the bridge with the actor service's
public endpoints. The private key is never returned by the bridge:

```bash
export CAPSIZE_ACTIVITYPUB_ACTOR_URL=https://capsize.online/ap/users/your-name
export CAPSIZE_ACTIVITYPUB_INBOX_URL=https://capsize.online/ap/users/your-name/inbox
export CAPSIZE_ACTIVITYPUB_KEY_ID=https://capsize.online/ap/users/your-name#main-key
export CAPSIZE_ACTIVITYPUB_PRIVATE_KEY_FILE=/path/to/private-key.pem
```

`/api/activitypub/identity` reports the public actor URL and whether local
signed delivery is configured. It does not create or authenticate a Capsize
account; that remains a `capsize.online` account-service responsibility.

Set `CAPSIZE_ACTIVITYPUB_RESOLVE_DNS=1` when deploying a bridge that fetches
arbitrary remote accounts. The default rejects local and private IP literals;
DNS resolution adds protection against hostnames that resolve to local space.

## Source extraction

The extraction is based on the ActivityPub adapter in `uwuchat_old`, especially
its `activitypub/as2.py`, `http_signatures.py`, `security.py`, `api_views.py`,
and the ActivityPub roadmap in `docs/DECENTRALIZED_PROTOCOLS_ROADMAP.md`.
UwUChat's Django models, accounts, social posts, Celery tasks, and product
views remain in UwUChat and are not copied into this repository.
