#!/usr/bin/env python3
"""
setup_pubsub.py — Create topics and subscriptions in the local PubSub emulator.

Configuration is driven by the TOPICS_AND_SUBSCRIPTIONS dict below.
The emulator host/port and project ID can be overridden via environment
variables or CLI arguments (see --help).

Usage:
    # Default (reads from docker-compose defaults)
    python setup_pubsub.py

    # Override host/project
    python setup_pubsub.py --host localhost:9985 --project my-project

Requirements:
    pip install google-cloud-pubsub
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# ✏️  EDIT THIS SECTION to define your topics and subscriptions.
#
# Structure:
#   TopicConfig(
#       name="your-topic-name",
#       subscriptions=[
#           SubscriptionConfig(name="your-sub-name"),
#           SubscriptionConfig(
#               name="your-sub-with-filter",
#               filter='attributes.type = "order"',
#               ack_deadline_seconds=60,
#           ),
#       ],
#   )
# ---------------------------------------------------------------------------

@dataclass
class SubscriptionConfig:
    name: str
    # Optional Pub/Sub filter expression (server-side filtering)
    filter: Optional[str] = None
    # How long the subscriber has to acknowledge a message (10–600 s)
    ack_deadline_seconds: int = 10


@dataclass
class TopicConfig:
    name: str
    subscriptions: list[SubscriptionConfig] = field(default_factory=list)


TOPICS_AND_SUBSCRIPTIONS: list[TopicConfig] = [
    TopicConfig(
        name="emul-use4-sbe-s002-maestroMsg",
        subscriptions=[
            SubscriptionConfig(name="emul-use4-sbe-s002-maestroMsg-sbe-users"),
        ],
    ),
        TopicConfig(
        name="emul-use4-sbe-s002-internalMsg",
        subscriptions=[
            SubscriptionConfig(name="emul-use4-sbe-s002-internalMsg-sbe-users"),
            SubscriptionConfig(name="emul-use4-sbe-s002-internalMsg-sbe-streams"),
        ],
    ),
        TopicConfig(
        name="emul-use4-sbe-s002-presenceV1ExchangeEnvelope",
        subscriptions=[],
    )

    # -----------------------------------------------------------------------
    # Add your topics/subscriptions here, for example:
    #
    # TopicConfig(
    #     name="my-topic",
    #     subscriptions=[
    #         SubscriptionConfig(name="my-topic-sub"),
    #     ],
    # ),
    # -----------------------------------------------------------------------
]

# ---------------------------------------------------------------------------
# Defaults matching docker-compose.yaml
# ---------------------------------------------------------------------------
DEFAULT_PROJECT = "sym-gke-emul-data-01"
DEFAULT_EMULATOR_HOST = "localhost:9985"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create PubSub topics and subscriptions in the local emulator."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("PUBSUB_EMULATOR_HOST", DEFAULT_EMULATOR_HOST),
        help=f"Emulator host:port (default: {DEFAULT_EMULATOR_HOST}, "
             "or $PUBSUB_EMULATOR_HOST)",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("PUBSUB_PROJECT_ID", DEFAULT_PROJECT),
        help=f"GCP project ID (default: {DEFAULT_PROJECT}, "
             "or $PUBSUB_PROJECT_ID)",
    )
    return parser.parse_args()


def ensure_topic(publisher, project_path: str, topic_name: str) -> str:
    """Create a topic if it does not already exist. Returns the full topic path."""
    topic_path = f"{project_path}/topics/{topic_name}"
    try:
        publisher.create_topic(name=topic_path)
        print(f"  ✓ Created topic: {topic_path}")
    except Exception as e:
        if "already exists" in str(e).lower() or "409" in str(e):
            print(f"  ~ Topic already exists: {topic_path}")
        else:
            print(f"  ✗ Failed to create topic {topic_path}: {e}", file=sys.stderr)
            raise
    return topic_path


def ensure_subscription(
    subscriber,
    project_path: str,
    topic_path: str,
    sub_config: SubscriptionConfig,
) -> None:
    """Create a subscription if it does not already exist."""
    sub_path = f"{project_path}/subscriptions/{sub_config.name}"

    kwargs: dict = dict(
        name=sub_path,
        topic=topic_path,
        ack_deadline_seconds=sub_config.ack_deadline_seconds,
    )
    if sub_config.filter:
        kwargs["filter"] = sub_config.filter

    try:
        subscriber.create_subscription(**kwargs)
        print(f"    ✓ Created subscription: {sub_path}")
    except Exception as e:
        if "already exists" in str(e).lower() or "409" in str(e):
            print(f"    ~ Subscription already exists: {sub_path}")
        else:
            print(f"    ✗ Failed to create subscription {sub_path}: {e}", file=sys.stderr)
            raise


def main() -> None:
    args = parse_args()

    # Point the client libraries at the emulator
    os.environ["PUBSUB_EMULATOR_HOST"] = args.host

    print(f"PubSub emulator : {args.host}")
    print(f"Project         : {args.project}")
    print()

    if not TOPICS_AND_SUBSCRIPTIONS:
        print("⚠️  No topics defined in TOPICS_AND_SUBSCRIPTIONS. "
              "Edit setup_pubsub.py to add them.")
        sys.exit(0)

    try:
        from google.cloud import pubsub_v1
    except ImportError:
        print(
            "✗ google-cloud-pubsub is not installed.\n"
            "  Run: pip install google-cloud-pubsub",
            file=sys.stderr,
        )
        sys.exit(1)

    project_path = f"projects/{args.project}"

    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    for topic_cfg in TOPICS_AND_SUBSCRIPTIONS:
        print(f"Topic: {topic_cfg.name}")
        topic_path = ensure_topic(publisher, project_path, topic_cfg.name)

        for sub_cfg in topic_cfg.subscriptions:
            ensure_subscription(subscriber, project_path, topic_path, sub_cfg)

        print()

    print("Done.")


if __name__ == "__main__":
    main()
