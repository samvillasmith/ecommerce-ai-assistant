from fastapi import FastAPI

app = FastAPI(title="Ecommerce AI Assistant")

@app.get("/")
async def root():
    return {"message": "Welcome to Ecommerce AI Assistant"}

def main():
    print("Hey there")

if __name__ == "__main__":
    main()