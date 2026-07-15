import asyncio
import json
from app.database.connection import async_session
from app.agents.community_agent import check_community_capacity

async def test_community():
    print("Testing Community Agent")

    # Simulated Shared State Input
    # Case 1: We need to produce 80 Papads
    shared_state = {
        "order": {
            "product": "Papad",
            "quantity": 100
        },
        "inventory": {
            "available": 20,
            "reserved": 20,
            "need_to_produce": 80
        }
    }

    print("Incoming Shared State:")
    print(json.dumps(shared_state, indent=2))
    print("\nProcessing...\n")

    # Open a database session
    async with async_session() as db:
        try:
            # Call the agent
            result = await check_community_capacity(shared_state, db)
            
            print("=== Community Agent Output ===")
            print(json.dumps(result, indent=2))
            print("================================")
            
            print("\n----------------------------------------\n")
            print("Testing Edge Case 3: Need to produce 0")
            shared_state["inventory"]["need_to_produce"] = 0
            
            result_zero = await check_community_capacity(shared_state, db)
            print("=== Community Agent Output (Zero Need) ===")
            print(json.dumps(result_zero, indent=2))
            print("================================")
            
            print("\n----------------------------------------\n")
            print("Testing Edge Case 1 & 2: Product no one can make (Candle)")
            shared_state["order"]["product"] = "Candle"
            shared_state["inventory"]["need_to_produce"] = 50
            
            result_candle = await check_community_capacity(shared_state, db)
            print("=== Community Agent Output (Candle) ===")
            print(json.dumps(result_candle, indent=2))
            print("================================")

        except Exception as e:
            print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_community())
