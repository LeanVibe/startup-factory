from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter()

@router.get("/users")
async def get_users():
    return {"users": [{"id": 1, "name": "Test User", "email": "test@example.com"}]}

@router.post("/users")
async def create_user(user_data: dict):
    return {"id": 1, "message": "User created successfully", "data": user_data}

@router.get("/dashboard")
async def get_dashboard():
    return {
        "metrics": {
            "total_users": 150,
            "monthly_revenue": 5000,
            "growth_rate": 15.2
        },
        "recent_activity": [
            {"action": "User signup", "timestamp": "2025-01-01T10:00:00Z"},
            {"action": "Payment received", "timestamp": "2025-01-01T09:30:00Z"}
        ]
    }
