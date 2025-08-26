from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import bcrypt
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT Secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'pizza-app-secret-key-2025')

# Security
security = HTTPBearer()

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data.get('created_at'), datetime):
        data['created_at'] = data['created_at'].isoformat()
    if isinstance(data.get('updated_at'), datetime):
        data['updated_at'] = data['updated_at'].isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    if isinstance(item.get('updated_at'), str):
        item['updated_at'] = datetime.fromisoformat(item['updated_at'])
    return item

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    category_id: str
    price: float
    image_url: Optional[str] = None
    ingredients: Optional[List[str]] = []
    sizes: Optional[List[Dict[str, Any]]] = []
    is_available: bool = True
    is_featured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: str
    price: float
    image_url: Optional[str] = None
    ingredients: Optional[List[str]] = []
    sizes: Optional[List[Dict[str, Any]]] = []
    is_featured: bool = False

class CartItem(BaseModel):
    product_id: str
    quantity: int
    size: Optional[str] = None
    price: float

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem]
    total_amount: float
    status: str = "pending"  # pending, confirmed, preparing, ready, delivered, cancelled
    delivery_address: Optional[str] = None
    phone: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    items: List[CartItem]
    delivery_address: Optional[str] = None
    phone: str
    notes: Optional[str] = None

# Auth helper
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = await db.users.find_one({'id': user_id})
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_data)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth endpoints
@api_router.post("/auth/register", response_model=Dict[str, Any])
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({'email': user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone=user_data.phone,
        address=user_data.address
    )
    
    user_dict = prepare_for_mongo(user.dict())
    user_dict['password'] = hashed_password.decode('utf-8')
    
    await db.users.insert_one(user_dict)
    
    # Create JWT token
    token = jwt.encode({'user_id': user.id}, JWT_SECRET, algorithm='HS256')
    
    return {"token": token, "user": user}

@api_router.post("/auth/login", response_model=Dict[str, Any])
async def login(login_data: UserLogin):
    user_data = await db.users.find_one({'email': login_data.email})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check password
    if not bcrypt.checkpw(login_data.password.encode('utf-8'), user_data['password'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = User(**parse_from_mongo(user_data))
    token = jwt.encode({'user_id': user.id}, JWT_SECRET, algorithm='HS256')
    
    return {"token": token, "user": user}

# Categories endpoints
@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find({'is_active': True}).sort('sort_order', 1).to_list(length=None)
    return [Category(**parse_from_mongo(cat)) for cat in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    category = Category(**category_data.dict())
    category_dict = prepare_for_mongo(category.dict())
    await db.categories.insert_one(category_dict)
    return category

# Products endpoints
@api_router.get("/products", response_model=List[Product])
async def get_products(category_id: Optional[str] = None, featured: Optional[bool] = None):
    query = {'is_available': True}
    if category_id:
        query['category_id'] = category_id
    if featured is not None:
        query['is_featured'] = featured
    
    products = await db.products.find(query).to_list(length=None)
    return [Product(**parse_from_mongo(product)) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product_data = await db.products.find_one({'id': product_id})
    if not product_data:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**parse_from_mongo(product_data))

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    product = Product(**product_data.dict())
    product_dict = prepare_for_mongo(product.dict())
    await db.products.insert_one(product_dict)
    return product

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing_product = await db.products.find_one({'id': product_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = Product(**{**existing_product, **product_data.dict(), 'id': product_id})
    product_dict = prepare_for_mongo(updated_product.dict())
    await db.products.replace_one({'id': product_id}, product_dict)
    return updated_product

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.products.delete_one({'id': product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted successfully"}

@api_router.put("/products/{product_id}/availability")
async def toggle_product_availability(product_id: str, is_available: bool, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.products.update_one(
        {'id': product_id}, 
        {'$set': {'is_available': is_available}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    status = "available" if is_available else "suspended"
    return {"message": f"Product {status} successfully"}

# Categories CRUD
@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, category_data: CategoryCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing_category = await db.categories.find_one({'id': category_id})
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    updated_category = Category(**{**existing_category, **category_data.dict(), 'id': category_id})
    category_dict = prepare_for_mongo(updated_category.dict())
    await db.categories.replace_one({'id': category_id}, category_dict)
    return updated_category

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if category has products
    product_count = await db.products.count_documents({'category_id': category_id})
    if product_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category with existing products")
    
    result = await db.categories.delete_one({'id': category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {"message": "Category deleted successfully"}

# Orders endpoints
@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    order = Order(
        user_id=current_user.id,
        items=order_data.items,
        total_amount=sum(item.price * item.quantity for item in order_data.items),
        delivery_address=order_data.delivery_address,
        phone=order_data.phone,
        notes=order_data.notes
    )
    
    order_dict = prepare_for_mongo(order.dict())
    await db.orders.insert_one(order_dict)
    return order

@api_router.get("/orders", response_model=List[Order])
async def get_orders(current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        orders = await db.orders.find().sort('created_at', -1).to_list(length=None)
    else:
        orders = await db.orders.find({'user_id': current_user.id}).sort('created_at', -1).to_list(length=None)
    
    return [Order(**parse_from_mongo(order)) for order in orders]

@api_router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_statuses = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.orders.update_one(
        {'id': order_id}, 
        {'$set': {'status': status, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order status updated successfully"}

# Initialize complete menu data
@api_router.post("/init-data")
async def initialize_sample_data():
    # Clear existing data
    await db.categories.delete_many({})
    await db.products.delete_many({})
    
    # Create all categories
    categories_data = [
        {"name": "Pizza", "description": "Our delicious handcrafted pizzas", "sort_order": 1, "image_url": "https://images.unsplash.com/photo-1593504049359-74330189a345"},
        {"name": "Pasta", "description": "Authentic Italian pasta dishes", "sort_order": 2, "image_url": "https://images.unsplash.com/photo-1563245738-9169ff58eccf"},
        {"name": "Appetizers", "description": "Start your meal right", "sort_order": 3, "image_url": "https://images.unsplash.com/photo-1541014741259-de529411b96a"},
        {"name": "Wings", "description": "Crispy chicken wings with your favorite sauce", "sort_order": 4, "image_url": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7"},
        {"name": "Salads", "description": "Fresh garden salads", "sort_order": 5, "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd"},
        {"name": "Burgers", "description": "Juicy grilled burgers", "sort_order": 6, "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd"},
        {"name": "Hot Subs", "description": "Hot submarine sandwiches", "sort_order": 7, "image_url": "https://images.unsplash.com/photo-1539252554453-80ab65ce3586"},
        {"name": "Cold Subs", "description": "Fresh cold submarine sandwiches", "sort_order": 8, "image_url": "https://images.unsplash.com/photo-1555072956-7758afb20e8f"},
        {"name": "Calzone", "description": "Stuffed pizza pockets", "sort_order": 9, "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b"},
        {"name": "Stromboli", "description": "Rolled and baked pizza", "sort_order": 10, "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b"},
        {"name": "Gyros", "description": "Mediterranean style gyros", "sort_order": 11, "image_url": "https://images.unsplash.com/photo-1621996346565-e3dbc691d8e9"},
        {"name": "Sides", "description": "Perfect sides for your meal", "sort_order": 12, "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877"},
        {"name": "Desserts", "description": "Sweet treats to finish your meal", "sort_order": 13, "image_url": "https://images.unsplash.com/photo-1551024601-bec78aea704b"}
    ]
    
    categories = []
    for cat_data in categories_data:
        category = Category(**cat_data)
        categories.append(prepare_for_mongo(category.dict()))
    
    await db.categories.insert_many(categories)
    
    # Get category IDs
    pizza_cat = await db.categories.find_one({"name": "Pizza"})
    pasta_cat = await db.categories.find_one({"name": "Pasta"})
    appetizers_cat = await db.categories.find_one({"name": "Appetizers"})
    wings_cat = await db.categories.find_one({"name": "Wings"})
    salads_cat = await db.categories.find_one({"name": "Salads"})
    burgers_cat = await db.categories.find_one({"name": "Burgers"})
    hot_subs_cat = await db.categories.find_one({"name": "Hot Subs"})
    cold_subs_cat = await db.categories.find_one({"name": "Cold Subs"})
    calzone_cat = await db.categories.find_one({"name": "Calzone"})
    stromboli_cat = await db.categories.find_one({"name": "Stromboli"})
    gyros_cat = await db.categories.find_one({"name": "Gyros"})
    sides_cat = await db.categories.find_one({"name": "Sides"})
    desserts_cat = await db.categories.find_one({"name": "Desserts"})
    
    # Create complete product data
    products_data = [
        # PIZZAS - CORRECT PRICES AND INGREDIENTS
        {
            "name": "NY Cheese Pizza",
            "description": "Classic cheese pizza",
            "category_id": pizza_cat['id'],
            "price": 18.95,
            "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591",
            "ingredients": ["Mozzarella cheese", "Tomato sauce"],
            "sizes": [
                {"name": "Medium 12\"", "price": 16.95},
                {"name": "Large 14\"", "price": 18.95},
                {"name": "Extra Large 18\"", "price": 20.95}
            ],
            "is_featured": True
        },
        {
            "name": "Deluxe Pizza",
            "description": "Pepperoni, sausage, ham, bacon, mushrooms, onions, green peppers, black olives",
            "category_id": pizza_cat['id'],
            "price": 23.95,
            "image_url": "https://images.unsplash.com/photo-1595708684082-a173bb3a06c5",
            "ingredients": ["Pepperoni", "Sausage", "Ham", "Bacon", "Mushrooms", "Onions", "Green peppers", "Black olives"],
            "sizes": [
                {"name": "Medium 12\"", "price": 20.95},
                {"name": "Large 14\"", "price": 23.95},
                {"name": "Extra Large 18\"", "price": 26.95}
            ],
            "is_featured": True
        },
        {
            "name": "Meat Lover's Pizza",
            "description": "Pepperoni, ham, bacon",
            "category_id": pizza_cat['id'],
            "price": 22.95,
            "image_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e",
            "ingredients": ["Pepperoni", "Ham", "Bacon"],
            "sizes": [
                {"name": "Medium 12\"", "price": 19.95},
                {"name": "Large 14\"", "price": 22.95},
                {"name": "Extra Large 18\"", "price": 24.95}
            ],
            "is_featured": True
        },
        {
            "name": "NY White Pizza",
            "description": "Ricotta, mozzarella, fresh garlic; no red sauce",
            "category_id": pizza_cat['id'],
            "price": 20.95,
            "image_url": "https://images.unsplash.com/photo-1571066811602-716837d681de",
            "ingredients": ["Ricotta cheese", "Mozzarella", "Fresh garlic"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 20.95},
                {"name": "Extra Large 18\"", "price": 22.95}
            ]
        },
        {
            "name": "Hawaiian Pizza",
            "description": "Ham and pineapple",
            "category_id": pizza_cat['id'],
            "price": 21.95,
            "image_url": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002",
            "ingredients": ["Ham", "Pineapple"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "Extra Large 18\"", "price": 23.95}
            ]
        },
        {
            "name": "Buffalo Chicken Pizza",
            "description": "Chicken, cheddar, buffalo sauce; no red sauce",
            "category_id": pizza_cat['id'],
            "price": 21.95,
            "image_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38",
            "ingredients": ["Chicken", "Cheddar cheese", "Buffalo sauce"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "Extra Large 18\"", "price": 23.95}
            ]
        },
        {
            "name": "BBQ Chicken Pizza",
            "description": "Chicken, BBQ sauce, cheddar; no red sauce",
            "category_id": pizza_cat['id'],
            "price": 21.95,
            "image_url": "https://images.unsplash.com/photo-1506354666786-959d6d497f1a",
            "ingredients": ["Chicken", "BBQ sauce", "Cheddar cheese"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "Extra Large 18\"", "price": 23.95}
            ]
        },
        {
            "name": "The Greek Pizza",
            "description": "Gyro meat, tomato, red onion, olives, feta; no tomato sauce",
            "category_id": pizza_cat['id'],
            "price": 21.95,
            "image_url": "https://images.unsplash.com/photo-1571997478779-2adcbbe9ab2f",
            "ingredients": ["Gyro meat", "Tomato", "Red onion", "Olives", "Feta cheese"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "Extra Large 18\"", "price": 23.95}
            ]
        },
        {
            "name": "Roma Spinach Pizza",
            "description": "Spinach, mozzarella, feta, and tomato",
            "category_id": pizza_cat['id'],
            "price": 22.95,
            "ingredients": ["Spinach", "Mozzarella", "Feta cheese", "Tomato"],
            "sizes": [
                {"name": "Medium 12\"", "price": 19.95},
                {"name": "Large 14\"", "price": 22.95},
                {"name": "Extra Large 18\"", "price": 24.95}
            ]
        },
        {
            "name": "Primavera Pizza",
            "description": "Broccoli, spinach, tomato, onion, mushroom, and green pepper",
            "category_id": pizza_cat['id'],
            "price": 22.95,
            "ingredients": ["Broccoli", "Spinach", "Tomato", "Onion", "Mushroom", "Green pepper"],
            "sizes": [
                {"name": "Medium 12\"", "price": 19.95},
                {"name": "Large 14\"", "price": 22.95},
                {"name": "Extra Large 18\"", "price": 24.95}
            ]
        },
        {
            "name": "Lasagna Pizza",
            "description": "Ricotta, meatballs, mozzarella, and red sauce",
            "category_id": pizza_cat['id'],
            "price": 21.95,
            "ingredients": ["Ricotta cheese", "Meatballs", "Mozzarella", "Red sauce"],
            "sizes": [
                {"name": "Medium 12\"", "price": 18.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "Extra Large 18\"", "price": 23.95}
            ]
        },
        {
            "name": "Stuffed Meat Pizza",
            "description": "Pepperoni, sausage, ham, and meatball",
            "category_id": pizza_cat['id'],
            "price": 25.95,
            "ingredients": ["Pepperoni", "Sausage", "Ham", "Meatball"],
            "sizes": [
                {"name": "Medium 12\"", "price": 22.95},
                {"name": "Large 14\"", "price": 25.95},
                {"name": "Extra Large 18\"", "price": 27.95}
            ]
        },
        {
            "name": "Stuffed Veggie Pizza",
            "description": "Broccoli, spinach, and mushroom",
            "category_id": pizza_cat['id'],
            "price": 25.95,
            "ingredients": ["Broccoli", "Spinach", "Mushroom"],
            "sizes": [
                {"name": "Medium 12\"", "price": 22.95},
                {"name": "Large 14\"", "price": 25.95},
                {"name": "Extra Large 18\"", "price": 27.95}
            ]
        },
        {
            "name": "Stuffed Chicken Pizza",
            "description": "Chicken, tomato, bacon, cheddar, and ranch",
            "category_id": pizza_cat['id'],
            "price": 25.95,
            "ingredients": ["Chicken", "Tomato", "Bacon", "Cheddar cheese", "Ranch"],
            "sizes": [
                {"name": "Medium 12\"", "price": 22.95},
                {"name": "Large 14\"", "price": 25.95},
                {"name": "Extra Large 18\"", "price": 27.95}
            ]
        },
        
        # PASTA
        {
            "name": "Homemade Meat Lasagna",
            "description": "Layers of pasta, meat sauce, and three cheeses",
            "category_id": pasta_cat['id'],
            "price": 14.95,
            "image_url": "https://images.unsplash.com/photo-1621996346565-e3dbc691d8e9",
            "ingredients": ["Ground beef", "Pasta sheets", "Ricotta", "Mozzarella", "Parmesan"],
            "is_featured": True
        },
        {
            "name": "Homemade Veggie Lasagna",
            "description": "Layers of pasta with fresh vegetables and cheese",
            "category_id": pasta_cat['id'],
            "price": 13.95,
            "ingredients": ["Fresh vegetables", "Pasta sheets", "Ricotta", "Mozzarella", "Spinach"]
        },
        {
            "name": "Chicken Marsala",
            "description": "Tender chicken breast in marsala wine sauce",
            "category_id": pasta_cat['id'],
            "price": 18.95,
            "ingredients": ["Chicken breast", "Marsala wine", "Mushrooms", "Cream sauce"]
        },
        {
            "name": "Chicken Francese",
            "description": "Lightly battered chicken in lemon butter sauce",
            "category_id": pasta_cat['id'],
            "price": 17.95,
            "ingredients": ["Chicken breast", "Lemon", "Butter", "White wine", "Capers"]
        },
        {
            "name": "Fettuccine Alfredo",
            "description": "Classic creamy alfredo pasta",
            "category_id": pasta_cat['id'],
            "price": 14.95,
            "ingredients": ["Fettuccine pasta", "Cream sauce", "Parmesan cheese", "Butter"]
        },
        {
            "name": "Fettuccine Alfredo w/Chicken",
            "description": "Creamy alfredo pasta with grilled chicken",
            "category_id": pasta_cat['id'],
            "price": 18.95,
            "ingredients": ["Fettuccine pasta", "Grilled chicken", "Cream sauce", "Parmesan"]
        },
        {
            "name": "Chicken Parmigiana Pasta",
            "description": "Breaded chicken with marinara and mozzarella over pasta",
            "category_id": pasta_cat['id'],
            "price": 15.95,
            "ingredients": ["Breaded chicken", "Marinara sauce", "Mozzarella", "Pasta"]
        },
        {
            "name": "Shrimp Scampi",
            "description": "Shrimp sautéed in garlic, white wine, and butter",
            "category_id": pasta_cat['id'],
            "price": 19.95,
            "ingredients": ["Shrimp", "Garlic", "White wine", "Butter", "Pasta"]
        },
        
        # APPETIZERS
        {
            "name": "Mozzarella Sticks",
            "description": "Golden fried mozzarella sticks (6 pieces)",
            "category_id": appetizers_cat['id'],
            "price": 9.95,
            "image_url": "https://images.unsplash.com/photo-1541014741259-de529411b96a",
            "ingredients": ["Mozzarella cheese", "Breadcrumbs", "Marinara sauce"]
        },
        {
            "name": "Fried Ravioli",
            "description": "Crispy fried cheese ravioli with marinara",
            "category_id": appetizers_cat['id'],
            "price": 7.50,
            "ingredients": ["Cheese ravioli", "Breadcrumbs", "Marinara sauce"]
        },
        {
            "name": "Garlic Bread",
            "description": "Fresh bread with garlic and herbs",
            "category_id": appetizers_cat['id'],
            "price": 5.95,
            "ingredients": ["Italian bread", "Garlic", "Herbs", "Butter"]
        },
        {
            "name": "Garlic Knots with Sauce",
            "description": "Homemade garlic knots with marinara",
            "category_id": appetizers_cat['id'],
            "price": 3.99,
            "ingredients": ["Pizza dough", "Garlic", "Herbs", "Marinara sauce"]
        },
        
        # WINGS
        {
            "name": "Jumbo Wings (6 pieces)",
            "description": "Large crispy wings with your choice of sauce",
            "category_id": wings_cat['id'],
            "price": 10.95,
            "image_url": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7",
            "ingredients": ["Chicken wings", "Choice of sauce"]
        },
        {
            "name": "Jumbo Wings (12 pieces)",
            "description": "Large crispy wings with your choice of sauce",
            "category_id": wings_cat['id'],
            "price": 18.95,
            "ingredients": ["Chicken wings", "Choice of sauce"]
        },
        {
            "name": "Jumbo Wings (20 pieces)",
            "description": "Large crispy wings with your choice of sauce",
            "category_id": wings_cat['id'],
            "price": 30.95,
            "ingredients": ["Chicken wings", "Choice of sauce"]
        },
        
        # SALADS
        {
            "name": "Garden Salad",
            "description": "Fresh mixed greens with vegetables",
            "category_id": salads_cat['id'],
            "price": 13.95,
            "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd",
            "ingredients": ["Mixed greens", "Tomatoes", "Cucumbers", "Onions", "Peppers"]
        },
        {
            "name": "Caesar Salad",
            "description": "Romaine lettuce with caesar dressing and croutons",
            "category_id": salads_cat['id'],
            "price": 13.95,
            "ingredients": ["Romaine lettuce", "Caesar dressing", "Croutons", "Parmesan"]
        },
        {
            "name": "Greek Salad",
            "description": "Traditional Greek salad with feta cheese and olives",
            "category_id": salads_cat['id'],
            "price": 13.95,
            "ingredients": ["Mixed greens", "Feta cheese", "Olives", "Tomatoes", "Onions"]
        },
        {
            "name": "Grilled Chicken Salad",
            "description": "Garden salad topped with grilled chicken",
            "category_id": salads_cat['id'],
            "price": 15.95,
            "ingredients": ["Mixed greens", "Grilled chicken", "Vegetables", "Dressing"]
        },
        
        # BURGERS
        {
            "name": "Hamburger",
            "description": "Classic beef burger with lettuce and tomato",
            "category_id": burgers_cat['id'],
            "price": 13.95,
            "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd",
            "ingredients": ["Beef patty", "Lettuce", "Tomato", "Onion", "Pickle"]
        },
        {
            "name": "Cheeseburger",
            "description": "Classic beef burger with cheese",
            "category_id": burgers_cat['id'],
            "price": 14.95,
            "ingredients": ["Beef patty", "Cheese", "Lettuce", "Tomato", "Onion"]
        },
        {
            "name": "Double Burger",
            "description": "Two beef patties with cheese and fixings",
            "category_id": burgers_cat['id'],
            "price": 17.95,
            "ingredients": ["Two beef patties", "Cheese", "Lettuce", "Tomato", "Onion"]
        },
        
        # HOT SUBS
        {
            "name": "Meatball Parmigiana Sub",
            "description": "Homemade meatballs with marinara and mozzarella",
            "category_id": hot_subs_cat['id'],
            "price": 13.95,
            "ingredients": ["Meatballs", "Marinara sauce", "Mozzarella cheese", "Sub roll"]
        },
        {
            "name": "Chicken Parmigiana Sub",
            "description": "Breaded chicken with marinara and mozzarella",
            "category_id": hot_subs_cat['id'],
            "price": 13.95,
            "ingredients": ["Breaded chicken", "Marinara sauce", "Mozzarella cheese"]
        },
        {
            "name": "Steak & Cheese Sub",
            "description": "Philly steak with onions, peppers, and cheese",
            "category_id": hot_subs_cat['id'],
            "price": 13.95,
            "ingredients": ["Philly steak", "Onions", "Green peppers", "Cheese"]
        },
        
        # COLD SUBS
        {
            "name": "Ham Sub",
            "description": "Sliced ham with lettuce, tomato, and mayo",
            "category_id": cold_subs_cat['id'],
            "price": 12.95,
            "ingredients": ["Ham", "Lettuce", "Tomato", "Mayo", "Sub roll"]
        },
        {
            "name": "Italian Sub",
            "description": "Ham, salami, and pepperoni with Italian dressing",
            "category_id": cold_subs_cat['id'],
            "price": 13.95,
            "ingredients": ["Ham", "Salami", "Pepperoni", "Italian dressing", "Vegetables"]
        },
        
        # CALZONES
        {
            "name": "Cheese Calzone",
            "description": "Mozzarella and ricotta cheese in pizza dough",
            "category_id": calzone_cat['id'],
            "price": 11.75,
            "ingredients": ["Mozzarella", "Ricotta cheese", "Pizza dough"]
        },
        {
            "name": "Pepperoni Calzone",
            "description": "Pepperoni with mozzarella and ricotta",
            "category_id": calzone_cat['id'],
            "price": 12.75,
            "ingredients": ["Pepperoni", "Mozzarella", "Ricotta cheese"]
        },
        
        # GYROS
        {
            "name": "Lamb Gyro with Fries",
            "description": "Traditional lamb gyro with tzatziki and fries",
            "category_id": gyros_cat['id'],
            "price": 13.95,
            "ingredients": ["Lamb", "Tzatziki sauce", "Onions", "Tomatoes", "French fries"]
        },
        
        # SIDES
        {
            "name": "French Fries",
            "description": "Golden crispy french fries",
            "category_id": sides_cat['id'],
            "price": 3.50,
            "ingredients": ["Potatoes", "Salt"]
        },
        {
            "name": "Onion Rings",
            "description": "Beer battered onion rings",
            "category_id": sides_cat['id'],
            "price": 6.95,
            "ingredients": ["Onions", "Beer batter"]
        },
        
        # DESSERTS
        {
            "name": "Cannoli",
            "description": "Traditional Italian pastry with sweet ricotta filling",
            "category_id": desserts_cat['id'],
            "price": 5.95,
            "image_url": "https://images.unsplash.com/photo-1551024601-bec78aea704b",
            "ingredients": ["Pastry shell", "Sweet ricotta", "Chocolate chips"]
        },
        {
            "name": "New York Cheesecake",
            "description": "Classic creamy New York style cheesecake",
            "category_id": desserts_cat['id'],
            "price": 5.95,
            "ingredients": ["Cream cheese", "Graham cracker crust", "Vanilla"]
        },
        {
            "name": "Tiramisu",
            "description": "Classic Italian coffee-flavored dessert",
            "category_id": desserts_cat['id'],
            "price": 6.95,
            "ingredients": ["Ladyfingers", "Mascarpone", "Coffee", "Cocoa powder"]
        }
    ]
    
    products = []
    for prod_data in products_data:
        product = Product(**prod_data)
        products.append(prepare_for_mongo(product.dict()))
    
    await db.products.insert_many(products)
    
    # Create admin user
    admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
    admin_user = User(
        email='admin@pizzashop.com',
        full_name='Admin User',
        phone='(470) 545-0095',
        is_admin=True
    )
    
    admin_dict = prepare_for_mongo(admin_user.dict())
    admin_dict['password'] = admin_password.decode('utf-8')
    
    await db.users.insert_one(admin_dict)
    
    return {"message": "Complete menu data initialized successfully. Admin login: admin@pizzashop.com / admin123"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()