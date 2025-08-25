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

# Initialize sample data
@api_router.post("/init-data")
async def initialize_sample_data():
    # Check if data already exists
    category_count = await db.categories.count_documents({})
    if category_count > 0:
        return {"message": "Sample data already exists"}
    
    # Create categories
    categories_data = [
        {"name": "Pizza", "description": "Our delicious handcrafted pizzas", "sort_order": 1, "image_url": "https://images.unsplash.com/photo-1593504049359-74330189a345"},
        {"name": "Pasta", "description": "Authentic Italian pasta dishes", "sort_order": 2, "image_url": "https://images.unsplash.com/photo-1563245738-9169ff58eccf"},
        {"name": "Calzone", "description": "Stuffed pizza pockets", "sort_order": 3},
        {"name": "Wings", "description": "Crispy chicken wings", "sort_order": 4},
        {"name": "Salads", "description": "Fresh garden salads", "sort_order": 5},
        {"name": "Desserts", "description": "Sweet treats", "sort_order": 6}
    ]
    
    categories = []
    for cat_data in categories_data:
        category = Category(**cat_data)
        categories.append(prepare_for_mongo(category.dict()))
    
    await db.categories.insert_many(categories)
    
    # Get pizza category ID
    pizza_category = await db.categories.find_one({"name": "Pizza"})
    pasta_category = await db.categories.find_one({"name": "Pasta"})
    
    # Create sample products
    products_data = [
        {
            "name": "Buffalo Chicken Pizza",
            "description": "Spicy buffalo chicken with red onions and mozzarella cheese",
            "category_id": pizza_category['id'],
            "price": 18.95,
            "image_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38",
            "ingredients": ["Buffalo chicken", "Red onions", "Mozzarella cheese", "Buffalo sauce"],
            "sizes": [
                {"name": "Small 10\"", "price": 14.95},
                {"name": "Medium 12\"", "price": 16.95},
                {"name": "Large 14\"", "price": 18.95},
                {"name": "X-Large 16\"", "price": 20.95}
            ],
            "is_featured": True
        },
        {
            "name": "NY Cheese Pizza",
            "description": "Classic New York style cheese pizza with our signature sauce",
            "category_id": pizza_category['id'],
            "price": 12.95,
            "image_url": "https://images.unsplash.com/photo-1600628421066-f6bda6a7b976",
            "ingredients": ["Mozzarella cheese", "Tomato sauce", "Fresh basil"],
            "sizes": [
                {"name": "Small 10\"", "price": 9.95},
                {"name": "Medium 12\"", "price": 11.95},
                {"name": "Large 14\"", "price": 12.95},
                {"name": "X-Large 16\"", "price": 15.95}
            ],
            "is_featured": True
        },
        {
            "name": "Meat Lovers Pizza",
            "description": "Loaded with pepperoni, sausage, ham, and bacon",
            "category_id": pizza_category['id'],
            "price": 21.95,
            "ingredients": ["Pepperoni", "Italian sausage", "Ham", "Bacon", "Mozzarella cheese"],
            "sizes": [
                {"name": "Small 10\"", "price": 17.95},
                {"name": "Medium 12\"", "price": 19.95},
                {"name": "Large 14\"", "price": 21.95},
                {"name": "X-Large 16\"", "price": 23.95}
            ]
        },
        {
            "name": "Homemade Meat Lasagna",
            "description": "Layers of pasta, meat sauce, and three cheeses",
            "category_id": pasta_category['id'],
            "price": 14.95,
            "ingredients": ["Ground beef", "Pasta sheets", "Ricotta", "Mozzarella", "Parmesan"]
        },
        {
            "name": "Chicken Marsala",
            "description": "Tender chicken breast in marsala wine sauce",
            "category_id": pasta_category['id'],
            "price": 18.95,
            "ingredients": ["Chicken breast", "Marsala wine", "Mushrooms", "Cream sauce"]
        }
    ]
    
    products = []
    for prod_data in products_data:
        product = Product(**prod_data)
        products.append(prepare_for_mongo(product.dict()))
    
    await db.products.insert_many(products)
    
    return {"message": "Sample data initialized successfully"}

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