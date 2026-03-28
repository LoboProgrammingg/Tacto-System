#!/usr/bin/env python3
"""
Link a restaurant to a Join WhatsApp instance.

Updates the canal_master_id in the database directly (no API server needed).

Usage:
    python scripts/connect_restaurant.py --restaurant-id <UUID> --instance wp-empresa-7

Reads DB_* settings from .env automatically.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def connect_restaurant(restaurant_id: str, instance_key: str) -> None:
    from dotenv import load_dotenv

    load_dotenv()

    from tacto.domain.shared.value_objects import RestaurantId
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.persistence.restaurant_repository import (
        PostgresRestaurantRepository,
    )

    rid = RestaurantId(UUID(restaurant_id))

    print(f"🔗 Linking restaurant {restaurant_id} to instance '{instance_key}'")

    async with get_async_session() as session:
        repo = PostgresRestaurantRepository(session)

        # Verify the restaurant exists
        find_result = await repo.find_by_id(rid)
        if find_result.is_failure() or find_result.value is None:
            print(f"❌ Restaurant {restaurant_id} not found in database.")
            sys.exit(1)

        restaurant = find_result.value
        print(f"   Found: {restaurant.name}")
        print(f"   Current canal_master_id: '{restaurant.canal_master_id}'")

        # Update canal_master_id
        update_result = await repo.update_canal_master_id(
            restaurant_id=rid,
            canal_master_id=instance_key,
        )

        if update_result.is_failure():
            print(f"❌ Failed to update: {update_result.error}")
            sys.exit(1)

    print(f"\n✅ Success!")
    print(f"   Restaurant '{restaurant.name}' → instance '{instance_key}'")
    print(f"   Webhook routing: messages from '{instance_key}' → '{restaurant.name}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Link a restaurant to a Join WhatsApp instance")
    parser.add_argument("--restaurant-id", required=True, help="Restaurant UUID")
    parser.add_argument("--instance", required=True, help="Join instance key (e.g. wp-empresa-7)")
    args = parser.parse_args()

    asyncio.run(connect_restaurant(args.restaurant_id, args.instance))


if __name__ == "__main__":
    main()
