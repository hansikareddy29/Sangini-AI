from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.agents.order_agent import extract_order
from app.database.connection import get_db
from app.models.models import Inventory, Product, Order, OrderItem
from app.schemas.schemas import InventoryResponse

app = FastAPI(title="Sangini API")

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


@app.post("/order")
async def create_order(request: OrderRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. AI Extraction: Parse the unstructured WhatsApp message
        extracted_data = extract_order(request.message)
        
        # Determine the earliest deadline from the AI's extracted items
        deadlines = [item.deadline for item in extracted_data.orders if item.deadline]
        order_deadline = datetime.strptime(deadlines[0], "%Y-%m-%d").date() if deadlines else None
        
        # 2. Database Insertion: Create the Order
        db_order = Order(
            customer_phone=request.customer_phone,
            status="pending",
            deadline=order_deadline
        )
        db.add(db_order)
        await db.flush() # Flush to get the newly generated db_order.id
        
        # 3. Create the Order Items
        unmatched_items = []
        for ai_item in extracted_data.orders:
            # Find the corresponding product in our database (case-insensitive search)
            stmt = select(Product).where(Product.name.ilike(f"%{ai_item.item}%"))
            result = await db.execute(stmt)
            product = result.scalars().first()
            
            if product:
                db_item = OrderItem(
                    order_id=db_order.id,
                    product_id=product.id,
                    quantity=ai_item.quantity
                )
                db.add(db_item)
            else:
                unmatched_items.append(ai_item.item)
                
        await db.commit() # Save everything to PostgreSQL
        
        response = {
            "status": "success", 
            "order_id": str(db_order.id), 
            "extracted_data": extracted_data
        }
        
        if unmatched_items:
            response["warning"] = f"These items were not found in the product database: {unmatched_items}"
            
        return response
        
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
