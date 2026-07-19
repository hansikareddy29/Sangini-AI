from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.order_agent import extract_order, process_order_node
from app.agents.inventory_agent import check_inventory_node
from app.agents.community_agent import check_community_capacity
from app.agents.allocation_agent import allocate_order
from app.database.connection import get_db
from app.models.models import Inventory, Product, Order, OrderItem, OrderStatus, Message, User
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
    allow_origins=["*"], 
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
        # Save customer message to DB
        stmt = select(User).where(User.phone_number == request.customer_phone)
        result = await db.execute(stmt)
        user = result.scalars().first()
        from langchain_core.messages import HumanMessage, AIMessage
        langchain_messages = []
        
        if user:
            db_message = Message(
                id=uuid.uuid4(),
                sender_id=user.id,
                message=request.message,
                message_type="text"
            )
            db.add(db_message)
            await db.commit()
            
            history_stmt = select(Message).where(
                ((Message.sender_id == user.id) & (Message.receiver_id == None)) |
                ((Message.receiver_id == user.id) & (Message.group_id == None))
            ).order_by(Message.timestamp.asc())
            history_res = await db.execute(history_stmt)
            history_msgs = history_res.scalars().all()
            
            for hm in history_msgs:
                if hm.sender_id:
                    langchain_messages.append(HumanMessage(content=hm.message))
                else:
                    langchain_messages.append(AIMessage(content=hm.message))
        else:
            langchain_messages.append(HumanMessage(content=request.message))
            
        thread_id = str(uuid.uuid4())
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
                "customer_phone": request.customer_phone
            }
        }
        
        # We start the conversation with the full history
        initial_state = {"messages": langchain_messages}
        
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
        # Save customer message to DB
        stmt = select(User).where(User.phone_number == request.customer_phone)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            db_message = Message(
                id=uuid.uuid4(),
                sender_id=user.id,
                message=request.message,
                message_type="text"
            )
            db.add(db_message)
            await db.commit()

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
