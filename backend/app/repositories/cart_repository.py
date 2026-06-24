from sqlalchemy import create_engine, Column, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, relationship
from database import Base

class CartItem(Base):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    price = Column(Float)
    user_id = Column(Integer)
    
    product = relationship("Product", foreign_keys=[product_id])

class Cart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    items = relationship("CartItem", backref="cart", lazy=True)
    total = Column(Float)

    def calculate_total(self):
        self.total = sum(item.price * item.quantity for item in self.items)
        return self.total