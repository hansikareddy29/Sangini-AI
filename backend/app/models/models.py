from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from ..database.connection import Base

class SHG(Base):
    __tablename__ = "shgs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    village = Column(String(255))
    district = Column(String(255))
    state = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("Member", back_populates="shg", cascade="all, delete-orphan")

class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shg_id = Column(UUID(as_uuid=True), ForeignKey("shgs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True)
    preferred_language = Column(String(50), default="en")
    availability = Column(Boolean, default=True)
    daily_capacity = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shg = relationship("SHG", back_populates="members")
    member_products = relationship("MemberProduct", back_populates="member", cascade="all, delete-orphan")
    allocations = relationship("Allocation", back_populates="member", cascade="all, delete-orphan")

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
    status = Column(String(50), default="pending")
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
    status = Column(String(50), default="assigned")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_item = relationship("OrderItem", back_populates="allocations")
    member = relationship("Member", back_populates="allocations")
