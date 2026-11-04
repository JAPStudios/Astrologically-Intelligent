<p align="center">
  <img src="static/icons/icon-512.png" alt="Astrologically Intelligent" width="112">
</p>

# Astrologically Intelligent

A non-human virtual intelligence platform for research, work, coding, documents, and agent workflows.

## Quick start

Create a Python 3.11+ environment, install the application requirements, then start the local service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

The local service binds to `127.0.0.1` by default. Keep `AUTH_ENABLED=true` for any network-accessible deployment. Keep `LOCALHOST_BYPASS=false` outside local development.

Use `--host 0.0.0.0` only when intentionally exposing the service to a trusted LAN or reverse proxy. Do not expose the application port directly to the public internet.

## Setup and operations

See [the setup guide](website/setup.md) for Docker deployment, native installation, configuration, security controls, model providers, and troubleshooting. The [runtime specification](specs/runtime.md) documents the application architecture.

## Development

Run the test suite with `python -m pytest`. The CI workflows additionally validate Python and JavaScript syntax, dependency security, container images, secret exposure, and the agent runtime.

## Android client

The native Android client is maintained in the repository root `app/` directory. It currently connects to the separate root agent API (`/v1/chat`) on port `8765`; emulator builds use `http://10.0.2.2:8765` to reach the host service. It does not yet expose every feature in this full web application, which runs separately on port `7000`.

## Upstream source provenance

This repository contains pinned upstream source references. A Git submodule is a source reference, not an assertion that its project has been merged into the application. See [UPSTREAM_IMPORT.md](../UPSTREAM_IMPORT.md), [THIRD_PARTY_PROVENANCE.json](THIRD_PARTY_PROVENANCE.json), and [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for import and attribution records.
