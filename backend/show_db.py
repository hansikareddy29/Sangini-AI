import asyncio
from sqlalchemy import select, text
from app.database.connection import get_db
from app.models.models import User, SHG, Member, Product, Inventory, Order, OrderItem, Allocation, Message

async def show_db():
    async for db in get_db():
        print("=== DATABASE STATUS ===")
        
        users = (await db.execute(select(User))).scalars().all()
        print(f"\nUSERS ({len(users)}):")
        for u in users:
            print(f" - {u.name} ({u.role}) - {u.phone_number}")
            
        shgs = (await db.execute(select(SHG))).scalars().all()
        print(f"\nSHGs ({len(shgs)}):")
        for s in shgs:
            print(f" - {s.name} ({s.village}, {s.district})")
            
        members = (await db.execute(select(Member))).scalars().all()
        print(f"\nMEMBERS ({len(members)}):")
        for m in members:
            print(f" - {m.name} (SHG ID: {m.shg_id}) - Capacity: {m.daily_capacity}")
            
        products = (await db.execute(select(Product))).scalars().all()
        print(f"\nPRODUCTS ({len(products)}):")
        for p in products:
            print(f" - {p.name}")
            
        inventory = (await db.execute(select(Inventory))).scalars().all()
        print(f"\nINVENTORY ({len(inventory)}):")
        for i in inventory:
            print(f" - Product ID {i.product_id}: Available {i.available_quantity}, Reserved {i.reserved_quantity}")
            
        orders = (await db.execute(select(Order))).scalars().all()
        print(f"\nORDERS ({len(orders)}):")
        for o in orders:
            print(f" - Order {o.id} | Status: {o.status} | Customer: {o.customer_phone}")
            items = (await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))).scalars().all()
            for it in items:
                print(f"    -> Product ID {it.product_id} | Qty: {it.quantity}")
                
        allocations = (await db.execute(select(Allocation))).scalars().all()
        print(f"\nALLOCATIONS ({len(allocations)}):")
        for a in allocations:
            print(f" - Alloc {a.id} | OrderItem {a.order_item_id} | Member {a.member_id} | Qty {a.allocated_quantity}")
            
        messages = (await db.execute(select(Message))).scalars().all()
        print(f"\nMESSAGES ({len(messages)}):")
        for m in messages[-5:]: # show last 5
            print(f" - From {m.sender_id} to {m.receiver_id}: {m.message[:50]}...")
        break

if __name__ == "__main__":
    asyncio.run(show_db())
