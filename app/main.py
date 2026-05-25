from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse
import sqlite3
import uvicorn

app = FastAPI(title="SwiggyOps Delivery Service")

request_counter = Counter("delivery_requests_total", "Total requests", ["method", "endpoint"])

def get_db():
    conn = sqlite3.connect("delivery.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'assigned',
            pickup_location TEXT NOT NULL,
            delivery_location TEXT NOT NULL,
            estimated_time INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            is_available INTEGER DEFAULT 1,
            current_location TEXT
        )
    """)
    conn.execute("INSERT OR IGNORE INTO drivers (id, name, phone, is_available, current_location) VALUES (1, 'Ravi Kumar', '9876543210', 1, 'Banjara Hills')")
    conn.execute("INSERT OR IGNORE INTO deliveries (id, order_id, driver_id, status, pickup_location, delivery_location) VALUES (1, 1, 1, 'delivered', 'Biryani House', 'Banjara Hills')")
    conn.commit()
    conn.close()

init_db()

class Delivery(BaseModel):
    order_id: int
    driver_id: int
    pickup_location: str
    delivery_location: str
    estimated_time: Optional[int] = 30

class DeliveryStatus(BaseModel):
    status: str

@app.get("/deliveries")
def get_deliveries():
    request_counter.labels(method="GET", endpoint="/deliveries").inc()
    conn = get_db()
    deliveries = conn.execute("SELECT * FROM deliveries").fetchall()
    conn.close()
    return [dict(d) for d in deliveries]

@app.post("/deliveries")
def create_delivery(delivery: Delivery):
    request_counter.labels(method="POST", endpoint="/deliveries").inc()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO deliveries (order_id, driver_id, pickup_location, delivery_location, estimated_time) VALUES (?, ?, ?, ?, ?)",
        (delivery.order_id, delivery.driver_id, delivery.pickup_location, delivery.delivery_location, delivery.estimated_time)
    )
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Delivery created!"}

@app.get("/drivers")
def get_drivers():
    request_counter.labels(method="GET", endpoint="/drivers").inc()
    conn = get_db()
    drivers = conn.execute("SELECT * FROM drivers").fetchall()
    conn.close()
    return [dict(d) for d in drivers]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "delivery-service"}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
