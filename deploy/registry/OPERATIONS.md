# Saga Registry Protocol v1 — public deployment operations

The public profile uses the same raw signed-package HTTP protocol in the Python reference client/server and Go Native client/server:

- `PUT /v1/packages/{name}/{version}` — authenticated, signed immutable publish;
- `GET /v1/packages/{name}/{version}` — raw package plus signature/digest headers;
- `GET /v1/search?q=...` — metadata search;
- `GET /healthz` — service health.

## Minimum production controls

Use a dedicated DNS name and HTTPS, set a strong `SAGA_REGISTRY_TOKEN`, keep publisher private keys outside the registry host, persist `/var/lib/saga-registry`, back it up, monitor `/healthz`, and put Internet-facing rate/abuse controls at the ingress. Package versions are immutable: publishing different bytes for the same `name@version` must return conflict, while an identical retry is idempotent.

The reference Go server rejects unsigned publication on Protocol v1, validates the package's internal name/version before persistence, verifies Ed25519 publisher evidence before writing, limits package sizes, and stores a version through staging/rename. Clients verify SHA-256 and Ed25519 signatures and require an explicit publisher fingerprint trust decision.

## Reviewer acceptance

A source tree or successful local container is **not** live-registry GA evidence. Run `tools/registry_live_qualification.py` against the externally reachable HTTPS endpoint. It refuses loopback/private-only endpoints and records the verified TLS session, Python-client roundtrip, Go Native client roundtrip, publisher fingerprints, immutable-version rejection, and installed execution output.

Record DNS/endpoint ownership, certificate automation, backup/restore test, incident/abuse contact, retention policy, monitoring URL, and operator identity separately. Do not include publisher tokens or private keys in review artifacts.
