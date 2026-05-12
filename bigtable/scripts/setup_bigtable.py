#!/usr/bin/env python3
"""
setup_bigtable.py — Create Bigtable tables and column families in the local emulator.

Table definitions are pre-populated from DataTable.java and driven by the
TABLES list below.  The emulator host/port and project/instance IDs can be
overridden via environment variables or CLI arguments (see --help).

Usage:
    # Default (reads from docker-compose defaults)
    python setup_bigtable.py

    # Override host/project/instance
    python setup_bigtable.py --host localhost:9986 --project my-project --instance my-instance

Requirements:
    pip install google-cloud-bigtable
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# ✏️  EDIT THIS SECTION to define your tables and column families.
#
# Structure:
#   TableConfig(
#       name="my-table",
#       column_families=["cf1", "cf2"],
#       # Optional TTL in seconds applied to every column family in the table.
#       # None means no GC rule (retain forever).
#       ttl_seconds=86400,
#   )
# ---------------------------------------------------------------------------

@dataclass
class TableConfig:
    name: str
    column_families: list[str]
    # TTL in seconds for all column families. None = no GC rule.
    ttl_seconds: Optional[int] = None


# Tables sourced from DataTable.java
TABLES: list[TableConfig] = [
    TableConfig("symphony-message-ef-violation",            ["m"]),
    TableConfig("symphony-external-msg",                    ["bt", "m", "t"]),
    TableConfig("symphony-last-read",                       ["b", "u"]),
    TableConfig("symphony-message",                         ["m", "a", "p", "t", "e", "r"]),
    TableConfig("symphony-user-receipts",                   ["m"]),
    TableConfig("symphony-message-receipts",                ["m"]),
    TableConfig("symphony-messageimport",                   ["r"]),
    TableConfig("symphony-delivery-record",                 ["c"]),
    TableConfig("usrmsg",                                   ["um", "umb"]),
    TableConfig("symphony-notification",                    ["r"]),
    TableConfig("last-activity-date",                       ["l"]),
    TableConfig("lc-threadindex-v3",                        ["a", "l"]),
    TableConfig("lc-threadindex-v3-chrono",                 ["a", "l"]),
    TableConfig("symphony-attachments",                     ["m"]),
    TableConfig("symphony-attachments-chrono",              ["m"]),           # DEPRECATED
    TableConfig("symphony-userthreadindex",                 ["m"]),
    TableConfig("symphony-userthreadindex-chrono",          ["m"]),           # DEPRECATED
    TableConfig("usr-th-lm",                                ["m", "r"]),
    TableConfig("hashtag-typeahead-suggestions",            ["t"]),
    TableConfig("symphony-presence",                        ["r"]),
    TableConfig("symphony-metadata-message",                ["m"]),
    TableConfig("user-bookmark",                            ["b", "n"]),
    TableConfig("bookmark-content",                         ["c"]),
    TableConfig("user-mentions-rev",                        ["f"]),
    TableConfig("symphony-relations",                       ["r"],            ttl_seconds=15552000),
    TableConfig("symphony-stat",                            ["s"]),
    TableConfig("symphony-retention",                       ["m"]),
    TableConfig("symphony-retention-streams",               ["r"]),
    TableConfig("symphony-cem",                             ["m", "v"]),
    TableConfig("symphony-cev",                             ["m", "v"]),
    TableConfig("symphony-keystore-certs-info",             ["r", "c", "v"]),
    TableConfig("symphony-keystore-clientcerts",            ["c"]),
    TableConfig("symphony-keystore-cached-entities",        ["e"]),
    TableConfig("symphony-keystore-accountkeys-info",       ["a"]),
    TableConfig("symphony-keystore-contentkeys-info",       ["c"]),
    TableConfig("symphony-keystore-rsawrappedcontentkeys",  ["r"]),
    TableConfig("symphony-keystore-wrappedaccountkeys",     ["a"]),
    TableConfig("symphony-keystore-wrappedcontentkeys",     ["k"]),
    TableConfig("user-activethread-rotationid-index",       ["t"]),
    TableConfig("session",                                  ["df", "kf"],     ttl_seconds=1209600),
    TableConfig("session-user-index",                       ["df", "kf"],     ttl_seconds=1209600),
    TableConfig("xpod_queue",                               ["m", "s"]),
    TableConfig("xpod-retry",                               ["r"],            ttl_seconds=86400),
    TableConfig("xpod-key-request-retry",                   ["r"]),
]

# ---------------------------------------------------------------------------
# Defaults matching docker-compose.yaml
# ---------------------------------------------------------------------------
DEFAULT_PROJECT  = "sym-gke-emul-data-01"
DEFAULT_INSTANCE = "sbe-instance"
DEFAULT_EMULATOR_HOST = "localhost:9986"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Bigtable tables and column families in the local emulator."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BIGTABLE_EMULATOR_HOST", DEFAULT_EMULATOR_HOST),
        help=f"Emulator host:port (default: {DEFAULT_EMULATOR_HOST}, "
             "or $BIGTABLE_EMULATOR_HOST)",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("BIGTABLE_PROJECT_ID", DEFAULT_PROJECT),
        help=f"GCP project ID (default: {DEFAULT_PROJECT}, "
             "or $BIGTABLE_PROJECT_ID)",
    )
    parser.add_argument(
        "--instance",
        default=os.environ.get("BIGTABLE_INSTANCE_ID", DEFAULT_INSTANCE),
        help=f"Bigtable instance ID (default: {DEFAULT_INSTANCE}, "
             "or $BIGTABLE_INSTANCE_ID)",
    )
    return parser.parse_args()


def ensure_table(admin_client, instance, table_cfg: TableConfig) -> None:
    """Create a table and its column families if they do not already exist."""
    from google.cloud.bigtable import column_family as cf_module
    from google.api_core.exceptions import AlreadyExists

    table = instance.table(table_cfg.name)

    # Build GC rule if a TTL is specified
    gc_rule = None
    if table_cfg.ttl_seconds is not None:
        import datetime
        gc_rule = cf_module.MaxAgeGCRule(
            datetime.timedelta(seconds=table_cfg.ttl_seconds)
        )

    column_families = {cf: gc_rule for cf in table_cfg.column_families}

    try:
        table.create(column_families=column_families)
        print(f"  ✓ Created table: {table_cfg.name}")
        for cf in table_cfg.column_families:
            print(f"    ✓ Column family: {cf}")
    except AlreadyExists:
        print(f"  ~ Table already exists: {table_cfg.name}")
        # Ensure all column families exist even if the table was pre-existing
        for cf_name in table_cfg.column_families:
            cf = table.column_family(cf_name, gc_rule=gc_rule)
            try:
                cf.create()
                print(f"    ✓ Created column family: {cf_name}")
            except AlreadyExists:
                print(f"    ~ Column family already exists: {cf_name}")
    except Exception as e:
        print(f"  ✗ Failed to create table {table_cfg.name}: {e}", file=sys.stderr)
        raise


def main() -> None:
    args = parse_args()

    os.environ["BIGTABLE_EMULATOR_HOST"] = args.host

    print(f"Bigtable emulator : {args.host}")
    print(f"Project           : {args.project}")
    print(f"Instance          : {args.instance}")
    print()

    try:
        from google.cloud import bigtable
    except ImportError:
        print(
            "✗ google-cloud-bigtable is not installed.\n"
            "  Run: pip install google-cloud-bigtable",
            file=sys.stderr,
        )
        sys.exit(1)

    admin_client = bigtable.Client(project=args.project, admin=True)
    instance = admin_client.instance(args.instance)

    for table_cfg in TABLES:
        ensure_table(admin_client, instance, table_cfg)

    print()
    print(f"Done. {len(TABLES)} tables processed.")


if __name__ == "__main__":
    main()
