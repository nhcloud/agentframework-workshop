"""
Demo Router for MCP Server demonstration.

Contains sample REST endpoints that can be exposed via MCP.
Matches the .NET DemoController implementation.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["Demo"])


# ???????????????????????????????????????????????????????????????????????????
# DATA MODELS
# ???????????????????????????????????????????????????????????????????????????

class DemoProduct(BaseModel):
    id: int
    name: str
    category: str
    price: float
    stock: int
    description: str = ""


class DemoOrder(BaseModel):
    id: int
    customer_id: str
    product_id: int
    quantity: int
    status: str
    order_date: datetime
    total_amount: float
    notes: Optional[str] = None


class CreateOrderRequest(BaseModel):
    customer_id: str
    product_id: int
    quantity: int = 1
    notes: Optional[str] = None


class WeatherData(BaseModel):
    location: str
    temperature: int
    condition: str
    humidity: int
    wind_speed: int
    unit: str = "Celsius"


class DemoApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str = ""
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None


# ???????????????????????????????????????????????????????????????????????????
# SIMULATED DATA
# ???????????????????????????????????????????????????????????????????????????

PRODUCTS = [
    DemoProduct(id=1, name="Laptop Pro", category="Electronics", price=1299.99, stock=50, description="High-performance laptop for professionals"),
    DemoProduct(id=2, name="Wireless Mouse", category="Electronics", price=49.99, stock=200, description="Ergonomic wireless mouse with long battery life"),
    DemoProduct(id=3, name="Office Chair", category="Furniture", price=399.99, stock=30, description="Comfortable ergonomic office chair"),
    DemoProduct(id=4, name="Standing Desk", category="Furniture", price=599.99, stock=25, description="Adjustable height standing desk"),
    DemoProduct(id=5, name="Monitor 27\"", category="Electronics", price=349.99, stock=75, description="4K Ultra HD monitor with HDR support"),
]

ORDERS = [
    DemoOrder(id=1, customer_id="CUST001", product_id=1, quantity=1, status="Completed", order_date=datetime.utcnow(), total_amount=1299.99),
    DemoOrder(id=2, customer_id="CUST002", product_id=2, quantity=3, status="Shipped", order_date=datetime.utcnow(), total_amount=149.97),
    DemoOrder(id=3, customer_id="CUST001", product_id=5, quantity=2, status="Processing", order_date=datetime.utcnow(), total_amount=699.98),
]

WEATHER_DATA = {
    "Seattle": WeatherData(location="Seattle", temperature=15, condition="Cloudy", humidity=75, wind_speed=12),
    "New York": WeatherData(location="New York", temperature=22, condition="Sunny", humidity=55, wind_speed=8),
    "London": WeatherData(location="London", temperature=12, condition="Rainy", humidity=85, wind_speed=15),
    "Tokyo": WeatherData(location="Tokyo", temperature=28, condition="Partly Cloudy", humidity=65, wind_speed=6),
    "Paris": WeatherData(location="Paris", temperature=18, condition="Sunny", humidity=60, wind_speed=10),
    "Sydney": WeatherData(location="Sydney", temperature=25, condition="Clear", humidity=50, wind_speed=14),
    "Berlin": WeatherData(location="Berlin", temperature=14, condition="Overcast", humidity=70, wind_speed=18),
    "Mumbai": WeatherData(location="Mumbai", temperature=32, condition="Hot and Humid", humidity=80, wind_speed=5),
    "San Francisco": WeatherData(location="San Francisco", temperature=17, condition="Foggy", humidity=78, wind_speed=11),
    "Singapore": WeatherData(location="Singapore", temperature=30, condition="Tropical", humidity=85, wind_speed=7),
}


# ???????????????????????????????????????????????????????????????????????????
# WEATHER API
# ???????????????????????????????????????????????????????????????????????????

@router.get("/weather")
async def get_weather(location: str = Query(..., description="Location to get weather for")) -> Dict[str, Any]:
    """
    Get weather information for a location.
    
    This is the same functionality as the local WeatherTool but exposed via REST API.
    Demonstrates how the same tool can be available locally AND via MCP.
    """
    logger.info(f"GetWeather called for location: {location}")
    
    if not location or not location.strip():
        raise HTTPException(status_code=400, detail="Location parameter is required")
    
    # Try exact match first, then partial match
    weather = WEATHER_DATA.get(location)
    
    if not weather:
        # Try case-insensitive match
        for key, value in WEATHER_DATA.items():
            if key.lower() == location.lower() or location.lower() in key.lower():
                weather = value
                break
    
    if weather:
        return {
            "success": True,
            "data": weather.model_dump(),
            "message": f"Weather data for {weather.location}",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "source": "demo-api",
                "cached": True
            }
        }
    
    # Return simulated weather for unknown locations
    simulated = WeatherData(
        location=location,
        temperature=random.randint(10, 30),
        condition=random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
        humidity=random.randint(40, 80),
        wind_speed=random.randint(5, 20)
    )
    
    return {
        "success": True,
        "data": simulated.model_dump(),
        "message": f"Simulated weather data for {location} (location not in database)",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "source": "demo-api",
            "simulated": True,
            "note": f"Known locations: {', '.join(WEATHER_DATA.keys())}"
        }
    }


@router.get("/weather/locations")
async def get_weather_locations() -> Dict[str, Any]:
    """Get list of all locations with available weather data."""
    logger.info("GetWeatherLocations called")
    
    return {
        "success": True,
        "data": sorted(WEATHER_DATA.keys()),
        "message": f"Found {len(WEATHER_DATA)} locations with weather data",
        "timestamp": datetime.utcnow().isoformat()
    }


# ???????????????????????????????????????????????????????????????????????????
# PRODUCTS API
# ???????????????????????????????????????????????????????????????????????????

@router.get("/products")
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, alias="minPrice", description="Minimum price"),
    max_price: Optional[float] = Query(None, alias="maxPrice", description="Maximum price")
) -> Dict[str, Any]:
    """Get all products or filter by category and price range."""
    logger.info(f"GetProducts called with category={category}, minPrice={min_price}, maxPrice={max_price}")
    
    products = PRODUCTS.copy()
    
    if category:
        products = [p for p in products if p.category.lower() == category.lower()]
    
    if min_price is not None:
        products = [p for p in products if p.price >= min_price]
    
    if max_price is not None:
        products = [p for p in products if p.price <= max_price]
    
    return {
        "success": True,
        "data": [p.model_dump() for p in products],
        "message": f"Found {len(products)} products",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "totalCount": len(products),
            "filters": {"category": category, "minPrice": min_price, "maxPrice": max_price}
        }
    }


@router.get("/products/{product_id}")
async def get_product(product_id: int) -> Dict[str, Any]:
    """Get a specific product by ID."""
    logger.info(f"GetProduct called with id={product_id}")
    
    product = next((p for p in PRODUCTS if p.id == product_id), None)
    
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    return {
        "success": True,
        "data": product.model_dump(),
        "message": "Product found",
        "timestamp": datetime.utcnow().isoformat()
    }


# ???????????????????????????????????????????????????????????????????????????
# ORDERS API
# ???????????????????????????????????????????????????????????????????????????

@router.post("/orders")
async def create_order(request: CreateOrderRequest) -> Dict[str, Any]:
    """Create a new order."""
    logger.info(f"CreateOrder called with customerId={request.customer_id}, productId={request.product_id}")
    
    # Find product
    product = next((p for p in PRODUCTS if p.id == request.product_id), None)
    if not product:
        raise HTTPException(status_code=400, detail=f"Product with ID {request.product_id} not found")
    
    # Check stock
    if product.stock < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {product.stock}, Requested: {request.quantity}"
        )
    
    # Create order
    new_order = DemoOrder(
        id=len(ORDERS) + 1,
        customer_id=request.customer_id,
        product_id=request.product_id,
        quantity=request.quantity,
        status="Processing",
        order_date=datetime.utcnow(),
        total_amount=product.price * request.quantity,
        notes=request.notes
    )
    
    ORDERS.append(new_order)
    product.stock -= request.quantity
    
    logger.info(f"Order {new_order.id} created for customer {new_order.customer_id}")
    
    return {
        "success": True,
        "data": new_order.model_dump(),
        "message": "Order created successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "productName": product.name,
            "remainingStock": product.stock
        }
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: int) -> Dict[str, Any]:
    """Get order by ID."""
    logger.info(f"GetOrder called with id={order_id}")
    
    order = next((o for o in ORDERS if o.id == order_id), None)
    
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    product = next((p for p in PRODUCTS if p.id == order.product_id), None)
    
    return {
        "success": True,
        "data": order.model_dump(),
        "message": "Order found",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "productName": product.name if product else "Unknown"
        }
    }


@router.get("/orders/customer/{customer_id}")
async def get_customer_orders(customer_id: str) -> Dict[str, Any]:
    """Get orders for a specific customer."""
    logger.info(f"GetCustomerOrders called with customerId={customer_id}")
    
    orders = [o for o in ORDERS if o.customer_id.lower() == customer_id.lower()]
    
    return {
        "success": True,
        "data": [o.model_dump() for o in orders],
        "message": f"Found {len(orders)} orders for customer {customer_id}",
        "timestamp": datetime.utcnow().isoformat()
    }


# ???????????????????????????????????????????????????????????????????????????
# HEALTH CHECK
# ???????????????????????????????????????????????????????????????????????????

@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """Health check endpoint for Demo API."""
    return {
        "status": "healthy",
        "service": "DemoController",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "endpoints": [
            {"method": "GET", "path": "/api/demo/weather", "description": "Get weather for a location"},
            {"method": "GET", "path": "/api/demo/weather/locations", "description": "List available weather locations"},
            {"method": "GET", "path": "/api/demo/products", "description": "List products with optional filters"},
            {"method": "GET", "path": "/api/demo/products/{id}", "description": "Get product by ID"},
            {"method": "POST", "path": "/api/demo/orders", "description": "Create a new order"},
            {"method": "GET", "path": "/api/demo/orders/{id}", "description": "Get order by ID"},
            {"method": "GET", "path": "/api/demo/orders/customer/{customerId}", "description": "Get customer orders"},
        ]
    }
