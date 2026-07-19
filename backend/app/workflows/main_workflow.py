from typing import Any, Dict, Literal
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
from sqlalchemy import select

from app.schemas.state_schema import SharedState
from app.agents.intent_agent import intent_node
from app.agents.order_agent import process_order_node
from app.agents.inventory_agent import check_inventory_node
from app.agents.community_agent import check_community_capacity
from app.agents.allocation_agent import allocate_order
from app.agents.response_agent import generate_response_node
from app.services.lifecycle_service import transition_order_state
from app.models.models import OrderStatus, Order, OrderItem, Product, InventoryReservation, Inventory
import uuid

# --- Wrappers for nodes that need DB ---

async def duplicate_check_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"duplicate_check": {"is_duplicate": False}}

async def return_existing_order_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "returned"}}

async def ask_customer_to_clarify_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "waiting_for_customer"}}

async def ask_customer_to_select_product_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "waiting_for_customer"}}

async def check_products_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": state.get("order", {})}

async def save_order_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    db = config["configurable"]["db"]
    customer_phone = config["configurable"]["customer_phone"]
    
    extracted = state.get("order", {}).get("extracted_items", {})
    if not extracted.get("orders"):
        return state
        
    deadlines = [item["deadline"] for item in extracted["orders"] if item.get("deadline")]
    order_deadline = datetime.strptime(deadlines[0], "%Y-%m-%d").date() if deadlines else None
    
    db_order = Order(
        customer_phone=customer_phone,
        status=OrderStatus.pending,
        deadline=order_deadline
    )
    db.add(db_order)
    await db.flush()
    
    for ai_item in extracted["orders"]:
        stmt = select(Product).where(Product.name.ilike(f"%{ai_item['item']}%"))
        result = await db.execute(stmt)
        product = result.scalars().first()
        if product:
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=product.id,
                quantity=ai_item['quantity']
            )
            db.add(db_item)
    await db.commit()
    
    order_data = state.get("order", {})
    order_data["order_id"] = str(db_order.id)
    
    # Order update broadcast moved to response_agent to ensure proper ordering
        
    return {"order": order_data}

async def inventory_node_wrapper(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    db = config["configurable"]["db"]
    res = await check_inventory_node(state, db)
    
    order_id = state.get("order", {}).get("order_id")
    if order_id:
        try:
            # Create InventoryReservation records for reserved items
            status_list = res.get("inventory", {}).get("inventory_status", [])
            for item_status in status_list:
                reserved_qty = item_status.get("reserved_quantity", 0)
                if reserved_qty > 0:
                    product_name = item_status.get("product_name")
                    # Find OrderItem and Inventory
                    stmt = select(OrderItem.id, Inventory.id).join(Product, OrderItem.product_id == Product.id).join(Inventory, Product.id == Inventory.product_id).where(OrderItem.order_id == uuid.UUID(order_id), Product.name == product_name)
                    item_res = await db.execute(stmt)
                    row = item_res.first()
                    if row:
                        order_item_id, inventory_id = row
                        reservation = InventoryReservation(
                            inventory_id=inventory_id,
                            order_item_id=order_item_id,
                            reserved_quantity=reserved_qty
                        )
                        db.add(reservation)
            await db.commit()
            
            await transition_order_state(order_id, OrderStatus.inventory_reserved, db)
        except Exception as e:
            await db.rollback()
            print(f"Failed to transition order {order_id} to inventory_reserved: {e}")
            
    return res

async def community_node_wrapper(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    db = config["configurable"]["db"]
    return await check_community_capacity(state, db)

async def allocation_node_wrapper(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    db = config["configurable"]["db"]
    return await allocate_order(state, db)

async def propose_revised_deadline_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "waiting_for_customer"}}

async def check_delivery_feasibility_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"feasibility": {"feasible": True, "high_risk": False}}

async def notify_shg_leader_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"approval": {"status": "waiting"}}

async def replan_inventory_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"inventory": {"replanned": True}}

async def replan_capacity_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"community": {"replanned": True}}

async def replan_allocation_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"allocation": {"replanned": True}}

async def reject_order_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "rejected"}}

async def finalize_order_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    return {"order": {"status": "released"}}

# --- Routing Functions (Diamonds) ---

def duplicate_router(state: SharedState) -> Literal["return_existing_order_node", "intent_node"]:
    if state.get("duplicate_check", {}).get("is_duplicate"):
        return "return_existing_order_node"
    return "intent_node"

def order_parsed_router(state: SharedState) -> Literal["ask_customer_to_clarify_node", "check_products_node"]:
    order = state.get("order", {})
    if order.get("error"):
        return "ask_customer_to_clarify_node"
    return "check_products_node"

def products_identified_router(state: SharedState) -> Literal["ask_customer_to_select_product_node", "save_order_node"]:
    extracted = state.get("order", {}).get("extracted_items", {})
    if not extracted.get("orders") or len(extracted.get("orders")) == 0:
        return "ask_customer_to_select_product_node"
    return "save_order_node"

def stock_router(state: SharedState) -> Literal["check_community_capacity", "check_delivery_feasibility_node"]:
    inventory = state.get("inventory", {})
    any_need_production = any(item.get("need_to_produce", 0) > 0 for item in inventory.get("inventory_status", []))
    if any_need_production:
        return "check_community_capacity"
    return "check_delivery_feasibility_node"

def capacity_router(state: SharedState) -> Literal["allocate_order", "propose_revised_deadline_node"]:
    community = state.get("community", {})
    products_data = community.get("products", {})
    any_capacity = any(p.get("total_capacity", 0) > 0 for p in products_data.values())
    if any_capacity:
        return "allocate_order"
    return "propose_revised_deadline_node"

def fully_assigned_router(state: SharedState) -> Literal["check_delivery_feasibility_node", "propose_revised_deadline_node"]:
    allocation = state.get("allocation", {})
    if allocation.get("allocation_successful"):
        return "check_delivery_feasibility_node"
    return "propose_revised_deadline_node"

def deadline_decision_router(state: SharedState) -> Literal["generate_response_node", "notify_shg_leader_node", "reject_order_node"]:
    approval = state.get("approval", {})
    status = approval.get("status", "waiting")
    if status == "waiting":
        return "generate_response_node"
    elif status == "approved":
        return "notify_shg_leader_node"
    return "reject_order_node"

def high_risk_router(state: SharedState) -> Literal["notify_shg_leader_node", "finalize_order_node"]:
    feasibility = state.get("feasibility", {})
    if feasibility.get("high_risk"):
        return "notify_shg_leader_node"
    return "finalize_order_node"

def leader_decision_router(state: SharedState) -> Literal["generate_response_node", "replan_inventory_node", "reject_order_node"]:
    approval = state.get("approval", {})
    status = approval.get("status", "waiting")
    if status == "waiting":
        return "generate_response_node"
    elif status == "approved":
        return "replan_inventory_node"
    return "reject_order_node"


# --- Build the Graph ---

builder = StateGraph(SharedState)

builder.add_node("duplicate_check_node", duplicate_check_node)
builder.add_node("return_existing_order_node", return_existing_order_node)
builder.add_node("intent_node", intent_node)
builder.add_node("process_order_node", process_order_node)
builder.add_node("ask_customer_to_clarify_node", ask_customer_to_clarify_node)
builder.add_node("check_products_node", check_products_node)
builder.add_node("ask_customer_to_select_product_node", ask_customer_to_select_product_node)
builder.add_node("save_order_node", save_order_node)
builder.add_node("check_inventory_node", inventory_node_wrapper)
builder.add_node("check_community_capacity", community_node_wrapper)
builder.add_node("allocate_order", allocation_node_wrapper)
builder.add_node("propose_revised_deadline_node", propose_revised_deadline_node)
builder.add_node("check_delivery_feasibility_node", check_delivery_feasibility_node)
builder.add_node("notify_shg_leader_node", notify_shg_leader_node)
builder.add_node("replan_inventory_node", replan_inventory_node)
builder.add_node("replan_capacity_node", replan_capacity_node)
builder.add_node("replan_allocation_node", replan_allocation_node)
builder.add_node("reject_order_node", reject_order_node)
builder.add_node("finalize_order_node", finalize_order_node)
builder.add_node("generate_response_node", generate_response_node)

builder.add_edge(START, "duplicate_check_node")
builder.add_conditional_edges("duplicate_check_node", duplicate_router)
builder.add_edge("return_existing_order_node", END)

builder.add_edge("intent_node", "process_order_node")
builder.add_conditional_edges("process_order_node", order_parsed_router)

builder.add_edge("ask_customer_to_clarify_node", "generate_response_node")

builder.add_conditional_edges("check_products_node", products_identified_router)

builder.add_edge("ask_customer_to_select_product_node", "generate_response_node")

builder.add_edge("save_order_node", "check_inventory_node")
builder.add_conditional_edges("check_inventory_node", stock_router)
builder.add_conditional_edges("check_community_capacity", capacity_router)
builder.add_conditional_edges("allocate_order", fully_assigned_router)

builder.add_conditional_edges("propose_revised_deadline_node", deadline_decision_router)

builder.add_conditional_edges("check_delivery_feasibility_node", high_risk_router)

builder.add_conditional_edges("notify_shg_leader_node", leader_decision_router)
builder.add_edge("replan_inventory_node", "replan_capacity_node")
builder.add_edge("replan_capacity_node", "replan_allocation_node")
builder.add_edge("replan_allocation_node", "check_delivery_feasibility_node")

builder.add_edge("reject_order_node", END)
builder.add_edge("finalize_order_node", "generate_response_node")
builder.add_edge("generate_response_node", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
