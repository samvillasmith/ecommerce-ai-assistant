from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import products, chat

app = FastAPI(title="Ecommerce AI Assistant") 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(chat.router)
app.include_router(products.router)