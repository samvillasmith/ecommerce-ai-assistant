# backend/routes/products.py
from fastapi import APIRouter, HTTPException
from prisma import Prisma
from prisma.engine.errors import AlreadyConnectedError

router = APIRouter()
prisma = Prisma()

@router.on_event("startup")
async def _connect_db() -> None:
    try:
        if not prisma.is_connected():          # <-- guard
            await prisma.connect()
    except AlreadyConnectedError:
        pass

@router.on_event("shutdown")
async def _disconnect_db() -> None:
    if prisma.is_connected():
        await prisma.disconnect()

@router.get("/products")
async def get_products():
    try:
        rows = await prisma.product.find_many()
        return [r.model_dump() for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
