from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class User(BaseModel):
    id: int  # Telegram ID
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    org_name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    role: str = "client"
    created_at: datetime = Field(default_factory=datetime.now)

class Order(BaseModel):
    id: Optional[int] = None
    user_id: int
    category: str
    params: Dict[str, Any]  # Храним как JSON
    description: Optional[str] = None
    files: List[str] = []   # Список file_id
    status: str = "pending_calculation"
    offered_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Promotion(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    is_active: bool = True
