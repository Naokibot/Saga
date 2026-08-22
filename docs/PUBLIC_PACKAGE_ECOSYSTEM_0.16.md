# Saga 0.16 public package ecosystem profile

Saga 0.16 includes a signed package format, Ed25519 publisher keys, SHA-256 package identity, explicit publisher trust, immutable name/version publication, safe extraction, dependency lock records, search/fetch APIs, TLS server mode, health endpoint, request time/body/header limits, and a local abuse-rate guard. Two starter projects live under `ecosystem/starter-packages/`.

A public Internet ecosystem is an operational service, not a source-code feature. A production operator must still provide a real HTTPS domain, certificate automation, secret/token rotation, persistent storage, off-site backups and restore drills, monitoring, abuse reporting, publisher governance and availability commitments. The project must not describe this as a live public registry until an externally reachable endpoint is deployed and verified.

The supplied `deploy/registry/` directory is a deployment kit. The release validation runs publish -> search -> trusted add -> verify against a localhost registry and records that separately from Internet deployment status.

## Static publication profile
`tools/export_static_registry.py` exports a verified append-only registry tree into deterministic `index.json`, `index.sha256`, package and signature paths suitable for an HTTPS static host/CDN. The exporter refuses a stored package whose SHA-256 differs from its signature metadata. This reduces the trusted online service surface for read-only package discovery. A real public endpoint still requires an operator-owned domain/TLS/CDN/storage and is not claimed by source-code generation alone.
