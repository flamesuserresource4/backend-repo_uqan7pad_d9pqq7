"""
Database Schemas for FPV 24/7

Pydantic models that map to MongoDB collections. Class names are lowercased
for their collection names.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, HttpUrl

class Category(BaseModel):
    """
    Drone categories (e.g., "FPV", "Cinewhoop", "Racing", "Parts")
    Collection: "category"
    """
    slug: str = Field(..., description="URL-friendly identifier")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Short description")
    icon: Optional[str] = Field(None, description="Lucide icon name for UI")

class DroneProduct(BaseModel):
    """
    Products sold in FPV 24/7
    Collection: "droneproduct" (class name lowercased)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: str = Field(..., description="Category slug")
    images: List[HttpUrl] = Field(default_factory=list, description="Image URLs")
    in_stock: bool = Field(True, description="Stock availability")
    stock_qty: int = Field(10, ge=0, description="How many units available")
    rating: float = Field(4.8, ge=0, le=5, description="Average rating 0-5")
    featured: bool = Field(False, description="Show on homepage hero grid")
    tags: List[str] = Field(default_factory=list, description="Search tags")
    specs: Dict[str, str] = Field(default_factory=dict, description="Key specs")

class Order(BaseModel):
    """Simple order model (for future expansion) Collection: "order"""
    email: str
    items: List[Dict[str, int]] = Field(..., description="List of {product_id, qty}")
    total: float = Field(..., ge=0)
    status: str = Field("pending", description="Order status")
