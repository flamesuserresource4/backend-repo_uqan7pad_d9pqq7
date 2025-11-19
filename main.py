import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

# Database helpers
from database import db, create_document, get_documents

# Pydantic Schemas
from schemas import Category, DroneProduct, Order

app = FastAPI(title="FPV 24/7 API", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FPV 24/7 backend running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Seed demo data if empty so the storefront has content
@app.post("/seed")
def seed_demo():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = list(db["droneproduct"].find({}).limit(1))
    if existing:
        return {"status": "ok", "message": "Products already seeded"}

    categories = [
        Category(slug="custom-drones", name="Custom Drones", description="Fully built quads tuned for performance", icon="drone"),
        Category(slug="frames", name="Frames", description="Lightweight and durable", icon="box"),
        Category(slug="motors", name="Motors", description="High KV, smooth bearings", icon="cpu"),
        Category(slug="batteries", name="Batteries", description="High C LiPos", icon="battery"),
        Category(slug="goggles", name="Goggles", description="Digital & analog", icon="eye"),
    ]

    for c in categories:
        db["category"].update_one({"slug": c.slug}, {"$set": c.model_dump()}, upsert=True)

    products: List[DroneProduct] = [
        DroneProduct(
            title="FPV 24/7 Raven 5" ,
            description="5-inch freestyle beast with F7 FC, 2207 1950KV motors, tune by pros.",
            price=499.0,
            category="custom-drones",
            images=[
                "https://images.unsplash.com/photo-1512820790803-83ca734da794?q=80&w=1200&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1484704849700-f032a568e944?q=80&w=1200&auto=format&fit=crop"
            ],
            in_stock=True,
            stock_qty=12,
            rating=4.9,
            featured=True,
            tags=["freestyle","5-inch","raven"],
            specs={"Weight":"410g","Flight Time":"6-8 min","Props":"5\""}
        ),
        DroneProduct(
            title="CineWhoop Mini",
            description="Ducted 3-inch cinematic rig. Ultra stable for indoors.",
            price=389.0,
            category="custom-drones",
            images=[
                "https://images.unsplash.com/photo-1548438294-1ad5d5f4f063?q=80&w=1200&auto=format&fit=crop"
            ],
            in_stock=True,
            stock_qty=9,
            rating=4.7,
            featured=True,
            tags=["cinewhoop","3-inch","ducted"],
            specs={"Weight":"290g","Flight Time":"5-7 min","Props":"3\""}
        ),
        DroneProduct(
            title="2207 1950KV Pro Motor",
            description="Smooth and powerful. Durable bell, N52H magnets.",
            price=23.9,
            category="motors",
            images=[
                "https://images.unsplash.com/photo-1601203227133-14f42f67d03a?q=80&w=1200&auto=format&fit=crop"
            ],
            in_stock=True,
            stock_qty=120,
            rating=4.8,
            featured=False,
            tags=["motor","2207","1950KV"],
            specs={"Shaft":"5mm","Stator":"2207","KV":"1950"}
        ),
    ]

    for p in products:
        create_document("droneproduct", p)

    return {"status": "ok", "inserted": len(products)}


# Public product endpoints
class DroneProductOut(DroneProduct):
    id: str

@app.get("/products", response_model=List[DroneProductOut])
def list_products(category: Optional[str] = None, featured: Optional[bool] = None, limit: int = 50):
    query = {}
    if category:
        query["category"] = category
    if featured is not None:
        query["featured"] = featured

    docs = get_documents("droneproduct", query, limit)
    out: List[DroneProductOut] = []
    for d in docs:
        d_copy = d.copy()
        _id = d_copy.pop("_id", None)
        try:
            id_str = str(_id) if _id else ""
        except Exception:
            id_str = ""
        out.append(DroneProductOut(id=id_str, **d_copy))
    return out


class CartItem(BaseModel):
    product_id: str
    qty: int = 1

class CreateOrderRequest(BaseModel):
    email: str
    items: List[CartItem]

@app.post("/orders")
def create_order(payload: CreateOrderRequest):
    # compute total from DB prices to prevent tampering
    total = 0.0
    for item in payload.items:
        try:
            doc = db["droneproduct"].find_one({"_id": ObjectId(item.product_id)})
        except Exception:
            doc = None
        if not doc:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        total += float(doc.get("price", 0)) * max(1, item.qty)

    order = Order(email=payload.email, items=[{"product_id": i.product_id, "qty": i.qty} for i in payload.items], total=round(total, 2))
    order_id = create_document("order", order)
    return {"status": "ok", "order_id": order_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
