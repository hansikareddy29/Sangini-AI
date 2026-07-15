import asyncio
import json
from app.database.connection import async_session
from app.agents.allocation_agent import allocate_order

async def test_allocation():
    print("Testing Allocation Agent (Scoring & Greedy Algo)")

    # Simulated Shared State Input from the User Prompt
    shared_state = {
        "order": {
            "order_id": "123e4567-e89b-12d3-a456-426614174000", # Fake UUID
            "product": "Papad",
            "quantity": 100
        },
        "inventory": {
            "available": 20,
            "reserved": 20,
            "need_to_produce": 80
        },
        "community": {
            "eligible_members": [
                {
                    "member_id": "22222222-2222-2222-2222-222222222221",
                    "name": "Lakshmi",
                    "remaining_capacity": 30,
                    "current_workload": 10,
                    "experience_level": "High",
                    "priority": 1
                },
                {
                    "member_id": "22222222-2222-2222-2222-222222222222",
                    "name": "Radha",
                    "remaining_capacity": 25,
                    "current_workload": 5,
                    "experience_level": "Medium",
                    "priority": 2
                },
                {
                    "member_id": "22222222-2222-2222-2222-222222222223",
                    "name": "Anita",
                    "remaining_capacity": 40,
                    "current_workload": 0,
                    "experience_level": "High",
                    "priority": 3
                }
            ],
            "total_capacity": 95,
            "can_fulfill": True
        }
    }

    print("Incoming Shared State (From Community Agent):")
    print(json.dumps(shared_state, indent=2))
    print("\nProcessing Allocations...\n")

    # Open a database session
    async with async_session() as db:
        try:
            # Call the agent
            result = await allocate_order(shared_state, db)
            
            print("=== Allocation Agent Output ===")
            print(json.dumps(result, indent=2))
            print("=================================\n")
            
            # Test Edge Case: Partial Fulfillment (Need 100, but only 95 capacity available)
            print("Testing Edge Case: Need to produce 100 (Capacity is only 95)")
            shared_state["inventory"]["need_to_produce"] = 100
            
            result_partial = await allocate_order(shared_state, db)
            print("=== Allocation Agent Output (Partial Fulfillment) ===")
            print(json.dumps(result_partial, indent=2))
            print("=================================\n")

        except Exception as e:
            print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_allocation())
