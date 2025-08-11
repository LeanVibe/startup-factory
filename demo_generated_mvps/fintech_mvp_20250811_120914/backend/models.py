from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# Business-specific models based on features: ['Invoice parsing', 'Data extraction', 'Client management', 'Reporting']
class BusinessEntity(Base):
    __tablename__ = "business_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
