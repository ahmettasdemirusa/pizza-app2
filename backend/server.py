from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import secrets
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import re
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import hashlib
import hmac

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Security Configuration
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,crust-corner.preview.emergentagent.com').split(',')
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET or len(JWT_SECRET) < 32:
    JWT_SECRET = secrets.token_urlsafe(32)
    logging.warning("Generated new JWT secret. Set JWT_SECRET in environment for production.")

JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# MongoDB connection with security
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(
    title="I Love NY Pizza API",
    description="Secure Pizza Ordering System",
    version="1.0.0",
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Security Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SlowAPIMiddleware)

# Rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    })
    return response

# Security utilities
def hash_password(password: str) -> str:
    """Securely hash password with salt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    """Create JWT token with expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not isinstance(input_str, str):
        return str(input_str)
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>&"\']', '', input_str)
    return sanitized.strip()

def validate_password_strength(password: str) -> bool:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

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

# Security models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, regex=r'^\+?1?\d{9,15}$')
    address: Optional[str] = Field(None, max_length=500)

    @validator('full_name', 'address')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_admin: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, and number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=1000)
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('name', 'description')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=1000)
    sort_order: int = 0

    @validator('name', 'description')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: str
    price: float = Field(..., gt=0, le=1000)
    image_url: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[List[str]] = []
    sizes: Optional[List[Dict[str, Any]]] = []
    is_available: bool = True
    is_featured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('name', 'description')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

    @validator('ingredients')
    def sanitize_ingredients(cls, v):
        if v:
            return [sanitize_input(ingredient) for ingredient in v]
        return v

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: str
    price: float = Field(..., gt=0, le=1000)
    image_url: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[List[str]] = []
    sizes: Optional[List[Dict[str, Any]]] = []
    is_featured: bool = False

    @validator('name', 'description')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, le=50)
    size: Optional[str] = Field(None, max_length=50)
    price: float = Field(..., gt=0)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem]
    total_amount: float = Field(..., gt=0)
    status: str = Field(default="pending")
    delivery_address: Optional[str] = Field(None, max_length=500)
    phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    notes: Optional[str] = Field(None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('delivery_address', 'notes')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

class OrderCreate(BaseModel):
    items: List[CartItem]
    delivery_address: Optional[str] = Field(None, max_length=500)
    phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    notes: Optional[str] = Field(None, max_length=500)

    @validator('delivery_address', 'notes')
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_input(v)
        return v

# Security: Bearer token authentication
security = HTTPBearer()

# Auth helper with enhanced security
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = await db.users.find_one({'id': user_id})
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if account is locked
        if user_data.get('locked_until'):
            if datetime.fromisoformat(user_data['locked_until']) > datetime.now(timezone.utc):
                raise HTTPException(status_code=423, detail="Account temporarily locked")
        
        return User(**user_data)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        logging.warning(f"Unauthorized admin access attempt by user {current_user.email}")
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Rate limited auth endpoints
@api_router.post("/auth/register", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate):
    try:
        # Check if user exists
        existing_user = await db.users.find_one({'email': user_data.email.lower()})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user with hashed password
        user = User(
            email=user_data.email.lower(),
            full_name=user_data.full_name,
            phone=user_data.phone,
            address=user_data.address
        )
        
        user_dict = prepare_for_mongo(user.dict())
        user_dict['password'] = hash_password(user_data.password)
        
        await db.users.insert_one(user_dict)
        
        # Create JWT token
        token = create_access_token({'user_id': user.id})
        
        # Remove sensitive data
        user_response = user.dict()
        user_response.pop('failed_login_attempts', None)
        user_response.pop('locked_until', None)
        
        logging.info(f"New user registered: {user.email}")
        return {"token": token, "user": user_response}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.post("/auth/login", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def login(request: Request, login_data: UserLogin):
    try:
        user_data = await db.users.find_one({'email': login_data.email.lower()})
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if account is locked
        failed_attempts = user_data.get('failed_login_attempts', 0)
        locked_until = user_data.get('locked_until')
        
        if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail="Account temporarily locked due to failed login attempts")
        
        # Verify password
        if not verify_password(login_data.password, user_data['password']):
            # Increment failed attempts
            failed_attempts += 1
            update_data = {'failed_login_attempts': failed_attempts}
            
            if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                lockout_time = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
                update_data['locked_until'] = lockout_time.isoformat()
                logging.warning(f"Account locked for user {login_data.email} due to {failed_attempts} failed attempts")
            
            await db.users.update_one({'id': user_data['id']}, {'$set': update_data})
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Reset failed attempts on successful login
        await db.users.update_one(
            {'id': user_data['id']}, 
            {
                '$set': {
                    'failed_login_attempts': 0,
                    'last_login': datetime.now(timezone.utc).isoformat()
                },
                '$unset': {'locked_until': ''}
            }
        )
        
        user = User(**parse_from_mongo(user_data))
        token = create_access_token({'user_id': user.id})
        
        # Remove sensitive data
        user_response = user.dict()
        user_response.pop('failed_login_attempts', None)
        user_response.pop('locked_until', None)
        
        logging.info(f"User logged in: {user.email}")
        return {"token": token, "user": user_response}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# Categories endpoints with security
@api_router.get("/categories", response_model=List[Category])
@limiter.limit("100/minute")
async def get_categories(request: Request):
    try:
        categories = await db.categories.find({'is_active': True}).sort('sort_order', 1).to_list(length=100)
        return [Category(**parse_from_mongo(cat)) for cat in categories]
    except Exception as e:
        logging.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")

@api_router.post("/categories", response_model=Category)
@limiter.limit("10/minute")
async def create_category(request: Request, category_data: CategoryCreate, current_user: User = Depends(get_admin_user)):
    try:
        category = Category(**category_data.dict())
        category_dict = prepare_for_mongo(category.dict())
        await db.categories.insert_one(category_dict)
        logging.info(f"Category created by admin {current_user.email}: {category.name}")
        return category
    except Exception as e:
        logging.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")

# Products endpoints with security
@api_router.get("/products", response_model=List[Product])
@limiter.limit("100/minute")
async def get_products(request: Request, category_id: Optional[str] = None, featured: Optional[bool] = None):
    try:
        query = {'is_available': True}
        if category_id:
            query['category_id'] = category_id
        if featured is not None:
            query['is_featured'] = featured
        
        products = await db.products.find(query).limit(200).to_list(length=None)
        return [Product(**parse_from_mongo(product)) for product in products]
    except Exception as e:
        logging.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")

@api_router.get("/products/{product_id}", response_model=Product)
@limiter.limit("100/minute")
async def get_product(request: Request, product_id: str):
    try:
        # Validate product_id format
        if not re.match(r'^[a-f0-9\-]{36}$', product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
            
        product_data = await db.products.find_one({'id': product_id, 'is_available': True})
        if not product_data:
            raise HTTPException(status_code=404, detail="Product not found")
        return Product(**parse_from_mongo(product_data))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch product")

@api_router.post("/products", response_model=Product)
@limiter.limit("5/minute")
async def create_product(request: Request, product_data: ProductCreate, current_user: User = Depends(get_admin_user)):
    try:
        # Validate category exists
        category = await db.categories.find_one({'id': product_data.category_id})
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category ID")
            
        product = Product(**product_data.dict())
        product_dict = prepare_for_mongo(product.dict())
        await db.products.insert_one(product_dict)
        logging.info(f"Product created by admin {current_user.email}: {product.name}")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail="Failed to create product")

@api_router.put("/products/{product_id}", response_model=Product)
@limiter.limit("5/minute")
async def update_product(request: Request, product_id: str, product_data: ProductCreate, current_user: User = Depends(get_admin_user)):
    try:
        # Validate product_id format
        if not re.match(r'^[a-f0-9\-]{36}$', product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
            
        existing_product = await db.products.find_one({'id': product_id})
        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Validate category exists
        category = await db.categories.find_one({'id': product_data.category_id})
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        updated_product = Product(**{**existing_product, **product_data.dict(), 'id': product_id})
        product_dict = prepare_for_mongo(updated_product.dict())
        await db.products.replace_one({'id': product_id}, product_dict)
        logging.info(f"Product updated by admin {current_user.email}: {product_id}")
        return updated_product
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating product: {e}")
        raise HTTPException(status_code=500, detail="Failed to update product")

@api_router.delete("/products/{product_id}")
@limiter.limit("5/minute")
async def delete_product(request: Request, product_id: str, current_user: User = Depends(get_admin_user)):
    try:
        # Validate product_id format
        if not re.match(r'^[a-f0-9\-]{36}$', product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
            
        result = await db.products.delete_one({'id': product_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        logging.info(f"Product deleted by admin {current_user.email}: {product_id}")
        return {"message": "Product deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting product: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete product")

@api_router.put("/products/{product_id}/availability")
@limiter.limit("10/minute")
async def toggle_product_availability(request: Request, product_id: str, is_available: bool, current_user: User = Depends(get_admin_user)):
    try:
        # Validate product_id format
        if not re.match(r'^[a-f0-9\-]{36}$', product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
            
        result = await db.products.update_one(
            {'id': product_id}, 
            {'$set': {'is_available': is_available}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        status = "available" if is_available else "suspended"
        logging.info(f"Product {status} by admin {current_user.email}: {product_id}")
        return {"message": f"Product {status} successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating product availability: {e}")
        raise HTTPException(status_code=500, detail="Failed to update product status")

# Orders endpoints with enhanced security
@api_router.post("/orders", response_model=Order)
@limiter.limit("10/minute")
async def create_order(request: Request, order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    try:
        # Validate order items
        if not order_data.items or len(order_data.items) > 50:
            raise HTTPException(status_code=400, detail="Invalid number of items")
        
        total_amount = 0
        validated_items = []
        
        for item in order_data.items:
            # Validate product exists and is available
            product = await db.products.find_one({'id': item.product_id, 'is_available': True})
            if not product:
                raise HTTPException(status_code=400, detail=f"Product {item.product_id} not available")
            
            # Validate price matches
            expected_price = item.price
            if item.size:
                size_found = False
                for size in product.get('sizes', []):
                    if size['name'] == item.size:
                        expected_price = size['price']
                        size_found = True
                        break
                if not size_found:
                    raise HTTPException(status_code=400, detail=f"Invalid size for product {item.product_id}")
            else:
                expected_price = product['price']
            
            if abs(item.price - expected_price) > 0.01:
                raise HTTPException(status_code=400, detail=f"Price mismatch for product {item.product_id}")
            
            validated_items.append(item)
            total_amount += item.price * item.quantity
        
        order = Order(
            user_id=current_user.id,
            items=validated_items,
            total_amount=round(total_amount, 2),
            delivery_address=order_data.delivery_address,
            phone=order_data.phone,
            notes=order_data.notes
        )
        
        order_dict = prepare_for_mongo(order.dict())
        await db.orders.insert_one(order_dict)
        
        logging.info(f"Order created by user {current_user.email}: ${total_amount}")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")

@api_router.get("/orders", response_model=List[Order])
@limiter.limit("30/minute")
async def get_orders(request: Request, current_user: User = Depends(get_current_user)):
    try:
        if current_user.is_admin:
            orders = await db.orders.find().sort('created_at', -1).limit(200).to_list(length=None)
        else:
            orders = await db.orders.find({'user_id': current_user.id}).sort('created_at', -1).limit(50).to_list(length=None)
        
        return [Order(**parse_from_mongo(order)) for order in orders]
    except Exception as e:
        logging.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")

@api_router.put("/orders/{order_id}/status")
@limiter.limit("20/minute")
async def update_order_status(request: Request, order_id: str, status: str, current_user: User = Depends(get_admin_user)):
    try:
        # Validate order_id format
        if not re.match(r'^[a-f0-9\-]{36}$', order_id):
            raise HTTPException(status_code=400, detail="Invalid order ID format")
            
        valid_statuses = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        result = await db.orders.update_one(
            {'id': order_id}, 
            {'$set': {'status': status, 'updated_at': datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Order not found")
        
        logging.info(f"Order status updated by admin {current_user.email}: {order_id} -> {status}")
        return {"message": "Order status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating order status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update order status")

# Categories CRUD for admin
@api_router.put("/categories/{category_id}", response_model=Category)
@limiter.limit("5/minute")
async def update_category(request: Request, category_id: str, category_data: CategoryCreate, current_user: User = Depends(get_admin_user)):
    try:
        # Validate category_id format
        if not re.match(r'^[a-f0-9\-]{36}$', category_id):
            raise HTTPException(status_code=400, detail="Invalid category ID format")
            
        existing_category = await db.categories.find_one({'id': category_id})
        if not existing_category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        updated_category = Category(**{**existing_category, **category_data.dict(), 'id': category_id})
        category_dict = prepare_for_mongo(updated_category.dict())
        await db.categories.replace_one({'id': category_id}, category_dict)
        logging.info(f"Category updated by admin {current_user.email}: {category_id}")
        return updated_category
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating category: {e}")
        raise HTTPException(status_code=500, detail="Failed to update category")

@api_router.delete("/categories/{category_id}")
@limiter.limit("5/minute")
async def delete_category(request: Request, category_id: str, current_user: User = Depends(get_admin_user)):
    try:
        # Validate category_id format
        if not re.match(r'^[a-f0-9\-]{36}$', category_id):
            raise HTTPException(status_code=400, detail="Invalid category ID format")
            
        # Check if category has products
        product_count = await db.products.count_documents({'category_id': category_id})
        if product_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete category with existing products")
        
        result = await db.categories.delete_one({'id': category_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        logging.info(f"Category deleted by admin {current_user.email}: {category_id}")
        return {"message": "Category deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")

# Secure initialization endpoint
@api_router.post("/init-data")
@limiter.limit("1/minute")
async def initialize_sample_data(request: Request):
    try:
        # Check if data already exists
        category_count = await db.categories.count_documents({})
        if category_count > 0:
            return {"message": "Sample data already exists"}
        
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
        
        # Create complete product data - SECURE MENU DATA
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
            # Additional menu items...
            {
                "name": "Homemade Meat Lasagna",
                "description": "Layers of pasta, meat sauce, and three cheeses",
                "category_id": pasta_cat['id'],
                "price": 15.95,
                "image_url": "https://images.unsplash.com/photo-1571997478779-2adcbbe9ab2f",
                "ingredients": ["Ground beef", "Pasta sheets", "Ricotta", "Mozzarella", "Parmesan"]
            },
            {
                "name": "Mozzarella Sticks",
                "description": "Golden fried mozzarella sticks served with marinara sauce",
                "category_id": appetizers_cat['id'],
                "price": 9.95,
                "image_url": "https://images.unsplash.com/photo-1541014741259-de529411b96a",
                "ingredients": ["Mozzarella cheese", "Breadcrumbs", "Marinara sauce"]
            }
        ]
        
        products = []
        for prod_data in products_data:
            product = Product(**prod_data)
            products.append(prepare_for_mongo(product.dict()))
        
        await db.products.insert_many(products)
        
        # Create secure admin user
        admin_password = hash_password('NYPizza@Admin2025!')
        admin_user = User(
            email='admin@pizzashop.com',
            full_name='System Administrator',
            phone='(470) 545-0095',
            is_admin=True
        )
        
        admin_dict = prepare_for_mongo(admin_user.dict())
        admin_dict['password'] = admin_password
        
        # Check if admin already exists
        existing_admin = await db.users.find_one({'email': admin_user.email})
        if not existing_admin:
            await db.users.insert_one(admin_dict)
        
        logging.info("Sample data initialized successfully")
        return {"message": "Complete menu data initialized successfully. Admin login: admin@pizzashop.com / NYPizza@Admin2025!"}
        
    except Exception as e:
        logging.error(f"Error initializing data: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize data")

# Include the router in the main app
app.include_router(api_router)

# CORS with security
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://crust-corner.preview.emergentagent.com", "http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pizza_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Pizza ordering system started with enhanced security")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Database connection closed")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}