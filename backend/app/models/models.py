from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, func, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from ..database.connection import Base

class OrderStatus(str, enum.Enum):
    pending = "pending"
    inventory_reserved = "inventory_reserved"
    allocated = "allocated"
    partially_allocated = "partially_allocated"
    replan_required = "replan_required"
    in_production = "in_production"
    ready_for_delivery = "ready_for_delivery"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"

class AllocationStatus(str, enum.Enum):
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    declined = "declined"
    cancelled = "cancelled"

class UserRole(str, enum.Enum):
    customer = "customer"
    shg_member = "shg_member"
    admin = "admin"
    system = "system"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # We can fetch messages sent or received by this user
    messages_sent = relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="[Message.receiver_id]", back_populates="receiver")


class SHG(Base):
    __tablename__ = "shgs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    village = Column(String(255))
    district = Column(String(255))
    state = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("Member", back_populates="shg", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")

class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shg_id = Column(UUID(as_uuid=True), ForeignKey("shgs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True)
    preferred_language = Column(String(50), default="en")
    availability = Column(Boolean, default=True)
    daily_capacity = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shg = relationship("SHG", back_populates="members")
    member_products = relationship("MemberProduct", back_populates="member", cascade="all, delete-orphan")
    allocations = relationship("Allocation", back_populates="member", cascade="all, delete-orphan")
    
class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("shgs.id", ondelete="CASCADE"), nullable=True)
    message = Column(Text, nullable=False)
    message_type = Column(String(50), default="text") # 'text', 'system', 'allocation'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")
    group = relationship("SHG", back_populates="messages")

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    member_products = relationship("MemberProduct", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")

class MemberProduct(Base):
    __tablename__ = "member_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    daily_capacity = Column(Integer, default=0)

    member = relationship("Member", back_populates="member_products")
    product = relationship("Product", back_populates="member_products")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    available_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_phone = Column(String(20), nullable=False)
    status = Column(Enum(OrderStatus, name="order_status"), default=OrderStatus.pending)
    deadline = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
 
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    allocations = relationship("Allocation", back_populates="order_item", cascade="all, delete-orphan")

class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    allocated_quantity = Column(Integer, nullable=False)
    status = Column(Enum(AllocationStatus, name="allocation_status"), default=AllocationStatus.assigned)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("OrderItem", back_populates="allocations")
    member = relationship("Member", back_populates="allocations")

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    reserved_quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inventory = relationship("Inventory")
    order_item = relationship("OrderItem")
