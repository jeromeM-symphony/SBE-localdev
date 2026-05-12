# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

**SBE-localdev** is a local development environment for Symphony Backend Ecosystem (SBE) services. It uses Docker Compose to run local emulators and databases that SBE services depend on.

## Commands

### Start / Stop

```bash
docker compose up          # Start all services
docker compose up redis    # Start a single service (redis, mongodb, bigtable, pubsub)
docker compose down -v     # Stop and remove volumes
```

### Initialize Data Stores (run once after `docker compose up`)

```bash
./init_datastores.sh
```

This script: creates a Python venv, installs dependencies, sets up MongoDB (schema + seed data), Bigtable tables, and Pub/Sub topics/subscriptions.

### Individual Setup Scripts

```bash
# Bigtable
python bigtable/scripts/setup_bigtable.py
python bigtable/scripts/setup_bigtable.py --instance your-instance-id --dry-run

# Pub/Sub
python pubsub/scripts/setup_pubsub.py
python pubsub/scripts/setup_pubsub.py --host localhost:9985 --project my-other-project --dry-run
```

Both scripts support `--dry-run` to preview changes without modifying the emulator.

## Architecture

Four services defined in `docker-compose.yaml`:

| Service   | Port  | Image                        | Notes |
|-----------|-------|------------------------------|-------|
| MongoDB   | 27017 | `mongo:8`                    | Credentials: `root`/`example`; app user: `dbadmin`/`password`; DB: `mtc` |
| Bigtable  | 9986  | `google/cloud-sdk:emulators` | GCP project `sym-gke-emul-data-01`, instance `sbe-instance` |
| Pub/Sub   | 9985  | `google/cloud-sdk:emulators` | GCP project `sym-gke-emul-data-01` |
| Redis     | 6379  | `redis:latest`               | No auth |

### Initialization Flow

`init_datastores.sh` orchestrates everything:
1. Runs a `mongo:8` container connected to the compose network to execute `mongodb/scripts/createMtcDB.js` (creates `dbadmin` user) and `mongorestore` (loads seed data from `mongodb/data/`).
2. Creates `.venv/` and installs `google-cloud-bigtable` + `google-cloud-pubsub`.
3. Runs `bigtable/scripts/setup_bigtable.py` — creates 45+ tables with column families and TTL rules.
4. Runs `pubsub/scripts/setup_pubsub.py` — creates topics (`maestroMsg`, `internalMsg`, `presenceV1ExchangeEnvelope`) and subscriptions.

### MongoDB Schema Updates

When the MongoDB schema changes, use the **SBE-Mongo** repository (not this one) and run its localdev migration tooling.

### Seed Data Location

MongoDB seed data lives in `mongodb/data/` as gzip-compressed BSON (mongodump format). Bigtable and Pub/Sub configuration is fully defined in their respective setup scripts — no external data files.
