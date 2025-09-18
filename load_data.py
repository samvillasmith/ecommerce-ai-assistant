import pandas as pd
import asyncio
from prisma import Prisma

async def load_csv_to_db():
    # Connect to database
    db = Prisma()
    await db.connect()
    
    # Read CSV
    df = pd.read_csv('shop-product-catalog.csv')
    
    # Load each row into database
    for _, row in df.iterrows():
        await db.product.create({
            'name': str(row['ProductName']),
            'brand': str(row['ProductBrand']) if pd.notna(row['ProductBrand']) else None,
            'gender': str(row['Gender']) if pd.notna(row['Gender']) else None,
            'price': str(row['Price']) if pd.notna(row['Price']) else None,
            'description': str(row['Description']) if pd.notna(row['Description']) else None,
            'primaryColor': str(row['PrimaryColor']) if pd.notna(row['PrimaryColor']) else None
        })
    
    print(f"Loaded {len(df)} products into database")
    await db.disconnect()

# Run it
asyncio.run(load_csv_to_db())