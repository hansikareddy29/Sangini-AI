import asyncio
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

from app.models.models import Base, SHG, Member, Product, MemberProduct, Inventory, Order, OrderStatus, OrderItem, Allocation, AllocationStatus, User, UserRole, Message

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sangini_user:sangini_password@localhost:5432/sangini_db")

async def reset_and_seed():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    print("Seeding data...")
    async with async_session() as session:
        # Create Users
        customer_user = User(id=uuid.uuid4(), name="Ramesh", role=UserRole.customer, phone_number="+911234567890")
        anita_user = User(id=uuid.uuid4(), name="Anita", role=UserRole.shg_member, phone_number="+919999999991")
        lakshmi_user = User(id=uuid.uuid4(), name="Lakshmi", role=UserRole.shg_member, phone_number="+919999999992")
        rekha_user = User(id=uuid.uuid4(), name="Rekha", role=UserRole.shg_member, phone_number="+919999999993")
        admin_user = User(id=uuid.uuid4(), name="Admin", role=UserRole.admin, phone_number="+910000000000")
        system_user = User(id=uuid.uuid4(), name="Sangini AI", role=UserRole.system)
        
        session.add_all([customer_user, anita_user, lakshmi_user, rekha_user, admin_user, system_user])

        # Create SHG (Group)
        shg1 = SHG(id=uuid.uuid4(), name="Women's SHG", village="Village A", district="District X", state="State Y")
        session.add(shg1)
        
        # Create Members
        anita = Member(id=uuid.uuid4(), user_id=anita_user.id, shg_id=shg1.id, name="Anita", phone_number="+919999999991", availability=True, daily_capacity=50)
        lakshmi = Member(id=uuid.uuid4(), user_id=lakshmi_user.id, shg_id=shg1.id, name="Lakshmi", phone_number="+919999999992", availability=True, daily_capacity=30)
        rekha = Member(id=uuid.uuid4(), user_id=rekha_user.id, shg_id=shg1.id, name="Rekha", phone_number="+919999999993", availability=True, daily_capacity=20)
        session.add_all([anita, lakshmi, rekha])

        # Create Products
        mango_pickle = Product(id=uuid.uuid4(), name="Mango Pickles", unit="jars", description="Delicious mango pickles")
        papad = Product(id=uuid.uuid4(), name="Papads", unit="packs", description="Crunchy lentil papads")
        session.add_all([mango_pickle, papad])

        # Create MemberProducts (Capacities)
        mp1 = MemberProduct(id=uuid.uuid4(), member_id=anita.id, product_id=mango_pickle.id, daily_capacity=20)
        mp2 = MemberProduct(id=uuid.uuid4(), member_id=lakshmi.id, product_id=mango_pickle.id, daily_capacity=15)
        mp3 = MemberProduct(id=uuid.uuid4(), member_id=rekha.id, product_id=mango_pickle.id, daily_capacity=15)
        
        mp4 = MemberProduct(id=uuid.uuid4(), member_id=anita.id, product_id=papad.id, daily_capacity=50)
        mp5 = MemberProduct(id=uuid.uuid4(), member_id=lakshmi.id, product_id=papad.id, daily_capacity=50)
        session.add_all([mp1, mp2, mp3, mp4, mp5])

        # Create Global Inventory
        inv_pickle = Inventory(id=uuid.uuid4(), product_id=mango_pickle.id, available_quantity=100, reserved_quantity=0)
        inv_papad = Inventory(id=uuid.uuid4(), product_id=papad.id, available_quantity=200, reserved_quantity=0)
        session.add_all([inv_pickle, inv_papad])

        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(reset_and_seed())
