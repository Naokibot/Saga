# Saga Registry Protocol v1 review

## Canonical protocol

There is one public v1 surface:

- `PUT /v1/packages/{name}/{version}` — immutable signed publication
- `GET /v1/packages/{name}/{version}` — raw `.sagapkg` plus signature metadata
- `GET /v1/search?q=...` — package discovery

The former `/v1/publish`, `/v1/index`, and `/v1/package/...` endpoints return HTTP 410 and are not an alternate protocol.

## Local interoperability check

```sh
python tools/registry_interop_validation.py
```

This must prove both directions: Go publisher -> Python server/client and Python publisher -> Go server/client, including publisher fingerprint verification.

## Public HTTPS GA evidence

Deploy `deploy/registry/` behind a public, CA-validated HTTPS hostname. Keep the Registry bearer token secret and use a dedicated test publisher key. Then run from an independent client network:

```sh
export SAGA_REGISTRY_LIVE=1
export SAGA_REGISTRY_URL=https://registry.example.invalid
export SAGA_REGISTRY_TOKEN=...
export SAGA_REGISTRY_SIGNING_KEY=/secure/path/reviewer-publisher.pem
export SAGA_REGISTRY_QUALIFICATION_PACKAGE=your-unique-probe-prefix
python tools/registry_live_qualification.py
```

The live tool rejects non-HTTPS/local/private-only resolution, verifies TLS, tests explicit publisher trust, rejects same-version mutation, and exercises Python<->Go publish/search/install interoperability.

Do not publish secrets or production packages as qualification probes. Use a disposable namespace and revoke/rotate the test token after review.
