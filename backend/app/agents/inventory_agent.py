import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import Product, Inventory
from app.schemas.state_schema import SharedState
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

async def check_inventory(order_json: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Checks requested items against current inventory, reserves available stock,
    and calculates what needs to be produced by the community.
    """
    # Extract the items requested by the customer
    # Handle both the new JSON structure ('items') and the older one ('orders')
    requested_items = order_json.get("items") or order_json.get("orders", [])
    
    if not requested_items:
        return {"inventory_status": []}

    inventory_status_list = []
    
    try:
        for req_item in requested_items:
            # Handle variations in product key name ('product_name' or 'item')
            product_name = req_item.get("product_name") or req_item.get("item")
            requested_quantity = req_item.get("quantity", 0)
            
            if not product_name:
                continue

            # 1. Find the product in the Products table (case-insensitive)
            # Use ilike to handle slight mismatches
            product_stmt = select(Product).where(Product.name.ilike(f"%{product_name}%"))
            product_result = await db.execute(product_stmt)
            product = product_result.scalars().first()
            
            if not product:
                inventory_status_list.append({
                    "product_name": product_name,
                    "requested_quantity": requested_quantity,
                    "status": "NOT_FOUND"
                })
                continue
                
            # 2. Fetch current inventory for this product
            # Using with_for_update() locks the row for this transaction,
            # preventing race conditions from concurrent requests modifying the same inventory.
            inv_stmt = select(Inventory).where(Inventory.product_id == product.id).with_for_update()
            inv_result = await db.execute(inv_stmt)
            inventory_record = inv_result.scalars().first()
            
            if not inventory_record:
                # Product exists, but no inventory record found. Assume 0 available.
                inventory_status_list.append({
                    "product_name": product.name,
                    "requested_quantity": requested_quantity,
                    "available_before": 0,
                    "reserved_quantity": 0,
                    "available_after": 0,
                    "need_to_produce": requested_quantity,
                    "status": "OUT_OF_STOCK"
                })
                continue

            available_before = inventory_record.available_quantity
            
            # 3. Compare requested quantity with available quantity
            if available_before >= requested_quantity:
                reserved_quantity = requested_quantity
                need_to_produce = 0
                status = "RESERVED"
            elif available_before > 0:
                reserved_quantity = available_before
                need_to_produce = requested_quantity - available_before
                status = "PARTIALLY_RESERVED"
            else:
                reserved_quantity = 0
                need_to_produce = requested_quantity
                status = "OUT_OF_STOCK"
                
            available_after = available_before - reserved_quantity
            
            # 4. Reserve inventory by updating the database record
            inventory_record.available_quantity = available_after
            # Increment the total reserved amount
            if hasattr(inventory_record, 'reserved_quantity'):
                inventory_record.reserved_quantity = (inventory_record.reserved_quantity or 0) + reserved_quantity

            # Append the status for this specific product
            inventory_status_list.append({
                "product_name": product.name,
                "requested_quantity": requested_quantity,
                "available_before": available_before,
                "reserved_quantity": reserved_quantity,
                "available_after": available_after,
                "need_to_produce": need_to_produce,
                "status": status
            })

        # 5. Commit the transaction after successfully processing all items
        # If any step fails before this point, the transaction is rolled back in the except block
        await db.commit()
        
        return {
            "inventory_status": inventory_status_list
        }
        
    except SQLAlchemyError as e:
        # Rollback the transaction if any database error occurs to prevent partial updates
        await db.rollback()
        logger.error(f"Database error in check_inventory: {str(e)}")
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in check_inventory: {str(e)}")
        return {"status": "error", "message": f"Unexpected error occurred: {str(e)}"}

async def check_inventory_node(state: SharedState, db: AsyncSession) -> dict:
    """
    LangGraph node for checking inventory.
    Reads from SharedState.order and updates SharedState.inventory.
    """
    order_data = state.get("order", {})
    if not order_data or "extracted_items" not in order_data:
        return {"inventory": {"error": "No extracted items found in order state."}}
    
    # We pass the extracted items as "items" list to check_inventory
    extracted_items = order_data["extracted_items"].get("orders", [])
    
    # check_inventory expects {"items": [...]}
    result = await check_inventory({"items": extracted_items}, db)
    
    return {"inventory": result}
