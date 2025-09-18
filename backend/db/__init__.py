# backend/db/__init__.py
# backend/db/__init__.py
from prisma import Prisma

# Reuse a single Prisma client
db = Prisma()

# Ensure tests/fakes always start disconnected (no-op for real Prisma)
for attr in ("_connected", "connected"):
    if hasattr(db, attr):
        try:
            setattr(db, attr, False)
        except Exception:
            pass

async def connect_db():
    if not db.is_connected():
        await db.connect()

async def disconnect_db():
    if db.is_connected():
        await db.disconnect()
