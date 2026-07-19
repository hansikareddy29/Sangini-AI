from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.order_agent import extract_order, process_order_node
from app.agents.inventory_agent import check_inventory_node
from app.agents.community_agent import check_community_capacity
from app.agents.allocation_agent import allocate_order
from app.database.connection import get_db
from app.models.models import Inventory, Product, Order, OrderItem, OrderStatus
from app.schemas.schemas import InventoryResponse
from app.schemas.state_schema import SharedState
from app.services.lifecycle_service import transition_order_state
from fastapi.middleware.cors import CORSMiddleware
from app.workflows.main_workflow import graph as workflow_graph
from app.api.whatsapp import router as whatsapp_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.visualizer import router as visualizer_router

app = FastAPI(title="Sangini API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's a hackathon demo, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(visualizer_router)

@app.get("/")
def home():
    return {"message": "Welcome to Sangini-AI"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/about")
def about():
    return {"project": "Sangini", "version": "0.1.0"}


class OrderRequest(BaseModel):
    customer_phone: str
    message: str

class ResumeRequest(BaseModel):
    thread_id: str
    customer_phone: str
    message: str


from langchain_core.messages import HumanMessage
import uuid

@app.post("/order")
async def create_order(request: OrderRequest, db: AsyncSession = Depends(get_db)):
    try:
        thread_id = str(uuid.uuid4())
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
                "customer_phone": request.customer_phone
            }
        }
        
        # We start the conversation with the human message
        initial_state = {"messages": [HumanMessage(content=request.message)]}
        
        # Invoke LangGraph Workflow
        final_state = await workflow_graph.ainvoke(initial_state, config)
        
        return {
            "status": "success",
            "thread_id": thread_id,
            "is_paused": False,
            "next_nodes": [],
            "state": "Processed dynamically"
        }
        
    except Exception as e:
        await db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/resume")
async def resume_order(request: ResumeRequest, db: AsyncSession = Depends(get_db)):
    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id,
                "db": db,
                "customer_phone": request.customer_phone
            }
        }
        
        # Append the new message to the existing thread state
        # Because we use `add_messages` reducer, it appends automatically!
        update = {"messages": [HumanMessage(content=request.message)]}
        
        # Just ainvoke with the new message and config. LangGraph loads history, appends, and runs.
        final_state = await workflow_graph.ainvoke(update, config)
        
        return {
            "status": "success",
            "thread_id": request.thread_id,
            "is_paused": False,
            "next_nodes": [],
            "state": "Processed dynamically"
        }
        
    except Exception as e:
        await db.rollback()
        return {"status": "error", "message": str(e)}


@app.get("/inventory", response_model=list[InventoryResponse])
async def get_inventory(db: AsyncSession = Depends(get_db)):
    """
    Fetch all inventory items from the database.
    We use selectinload to eagerly load the associated product data.
    """
    result = await db.execute(select(Inventory).options(selectinload(Inventory.product)))
    inventory_items = result.scalars().all()
    return inventory_items
