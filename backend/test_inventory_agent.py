import asyncio
import json
from app.database.connection import async_session
from app.agents.inventory_agent import check_inventory

async def test_inventory():
    print("========================================")
    print("Testing Inventory Agent Edge Cases")
    print("========================================")

    dummy_order = {
        "customer_name": "Test User",
        "phone_number": "1234567890",
        "items": [
            {
                "product_name": "Papad", 
                "quantity": 5
            },
            {
                "product_name": "Papad", 
                "quantity": 10
            },
            {
                "product_name": "Candle", 
                "quantity": 1
            }
        ],
        "deadline": "2026-07-25"
    }

    print("Incoming Order Request:")
    print(json.dumps(dummy_order, indent=2))
    print("\nProcessing...\n")

    # Open a database session
    async with async_session() as db:
        try:
            # Calling the agent
            result = await check_inventory(dummy_order, db)
            
            print("=== Inventory Agent Output ===")
            print(json.dumps(result, indent=2))
            print("================================")
            
        except Exception as e:
            print(f" Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_inventory())
