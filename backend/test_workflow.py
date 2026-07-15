import asyncio
import json
import logging
from pprint import pprint

from app.database.connection import async_session
from app.agents.order_agent import extract_order
from app.agents.inventory_agent import check_inventory
from app.agents.community_agent import check_community_capacity
from app.agents.allocation_agent import allocate_order

logger = logging.getLogger(__name__)

def print_header(title):
    print("\n=============================")
    print(f"{title}")
    print("=============================\n")

async def run_workflow(message: str, customer_phone: str = "9876543210"):
    print_header("STARTING END-TO-END WORKFLOW TEST")
    print(f"Customer Message: '{message}'\n")

    shared_state = {}

    async with async_session() as db:
        # STEP 1: ORDER AGENT
        print_header("STEP 1 : ORDER AGENT")
        try:
            # Order agent is synchronous
            order_extraction = extract_order(message)
            order_dict = order_extraction.model_dump()
            
            # The inventory agent supports lists under 'orders' or 'items'.
            shared_state["order"] = order_dict
            
            print("Parsed Order")
            print(json.dumps(order_dict, indent=2))
        except Exception as e:
            print(f"Failed at Order Agent: {e}")
            return

        # STEP 2: INVENTORY AGENT
        print_header("STEP 2 : INVENTORY AGENT")
        try:
            inv_result = await check_inventory(shared_state["order"], db)
            
            # Extract first item's status to match single-item expected state for next agents
            inv_status_list = inv_result.get("inventory_status", [])
            if not inv_status_list:
                print("No products found in order to process inventory.")
                return
                
            first_item_status = inv_status_list[0]
            
            # Check for NOT_FOUND status before proceeding
            if first_item_status.get("status") == "NOT_FOUND":
                print(f"Product '{first_item_status.get('product_name')}' does not exist in the database.")
                print_header("FINAL SHARED STATE")
                shared_state["inventory"] = {"status": "NOT_FOUND"}
                print(json.dumps(shared_state, indent=2))
                return
            
            # Update shared state with inventory results for the first item
            shared_state["inventory"] = {
                "available": first_item_status.get("available_before", 0),
                "reserved": first_item_status.get("reserved_quantity", 0),
                "need_to_produce": first_item_status.get("need_to_produce", 0)
            }
            
            # Community and Allocation agents expect the order to be in a specific single-item format for this pipeline test
            shared_state["order"] = {
                "order_id": "temp-order-id-1234",
                "product": first_item_status.get("product_name"),
                "quantity": first_item_status.get("requested_quantity")
            }
            
            print("Inventory Updated")
            print(json.dumps(shared_state["inventory"], indent=2))
        except Exception as e:
            print(f"Failed at Inventory Agent: {e}")
            return

        # Check if we even need to run community/allocation
        if shared_state["inventory"]["need_to_produce"] == 0:
            print("\nNeed to produce is 0. Inventory is sufficient. Skipping allocation.")
            print_header("FINAL SHARED STATE")
            print(json.dumps(shared_state, indent=2))
            return

        # STEP 3: COMMUNITY AGENT
        print_header("STEP 3 : COMMUNITY AGENT")
        try:
            community_result = await check_community_capacity(shared_state, db)
            shared_state["community"] = community_result.get("community", {})
            
            print("Eligible Members")
            print(json.dumps(shared_state["community"], indent=2))
            
            if not shared_state["community"].get("eligible_members"):
                print("No eligible members found. Product might not exist or no capacity.")
                # We continue to Allocation agent so it handles the "No eligible members" gracefully
        except Exception as e:
            print(f"Failed at Community Agent: {e}")
            return

        # STEP 4: ALLOCATION AGENT
        print_header("STEP 4 : ALLOCATION AGENT")
        try:
            allocation_result = await allocate_order(shared_state, db)
            shared_state["allocation"] = allocation_result.get("allocation", {})
            
            print("Allocation Plan")
            print(json.dumps(shared_state["allocation"], indent=2))
        except Exception as e:
            print(f"Failed at Allocation Agent: {e}")
            return

        # FINAL VERIFICATION
        print_header("FINAL SHARED STATE")
        print(json.dumps(shared_state, indent=2))

async def run_all_tests():
    tests = [
        ("Test 1: Need 10 papads by Friday.", "10 papads (Should have enough inventory)"),
        ("Test 2: Need 100 papads by Friday.", "100 papads (Should require allocation)"),
        ("Test 3: Need 500 papads.", "500 papads (Should exhaust capacity)"),
        ("Test 4: Need 50 pickles tomorrow.", "50 pickles (Different product)"),
        ("Test 5: Need 20 laddus.", "20 laddus (Product not found)")
    ]
    
    for message, description in tests:
        print("\n\n********************************************************")
        print(f"RUNNING TEST: {description}")
        print("********************************************************")
        await run_workflow(message)
        print("\n")

if __name__ == "__main__":
    # Ensure database is clean or just run the tests
    asyncio.run(run_all_tests())
