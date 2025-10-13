# E-commerce AI Shopping Assistant

AI-powered conversational shopping assistant that helps customers find products through natural language queries. Built with Google Gemini, Pinecone vector search, and FastAPI.

## Overview

This system enables customers to ask questions like "show me Nike shoes under $100" or "do you have black Vans?" and receive intelligent, context-aware product recommendations powered by retrieval-augmented generation (RAG).

## Features

- **Natural Language Search**: Query products conversationally instead of traditional filters
- **RAG-Powered Responses**: Pinecone vector similarity search for semantic product matching
- **Multi-Product Enumeration**: Handles "list all X" queries by returning multiple relevant products
- **Brand Extraction**: Automatically detects brand names in queries for focused results
- **Price Normalization**: Consistent currency formatting across responses
- **Real-time Chat Interface**: Responsive Next.js frontend with session-based conversation memory
- **Comprehensive Testing**: Full test coverage with pytest and Jest

## Architecture

```
┌─────────────────┐          ┌──────────────────┐
│  Next.js        │  HTTP    │  FastAPI         │
│  Frontend       ├─────────>│  Backend         │
│  (Port 3000)    │          │  (Port 8000)     │
└─────────────────┘          └────────┬─────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────────┐  ┌──────────┐   ┌─────────────┐
            │ Google Gemini │  │ Pinecone │   │   MySQL     │
            │ (LLM)         │  │ (Vectors)│   │  (Products) │
            └───────────────┘  └──────────┘   └─────────────┘
```

**Flow:**
1. User sends query → Next.js frontend
2. Frontend calls FastAPI `/chat` endpoint
3. Backend retrieves conversation history (if any)
4. Performs vector similarity search in Pinecone for relevant products
5. Constructs prompt with search results + context
6. Gemini generates natural language response
7. Response returned to frontend and displayed

## Tech Stack

**Backend:**
- FastAPI - Web framework
- Google Gemini 1.5 Flash - LLM for response generation
- Pinecone - Vector database for semantic search
- Google Vertex AI / GenAI - Embeddings (text-embedding-004 / embedding-001)
- Prisma - Database ORM
- MySQL - Product catalog storage
- LangChain - RAG orchestration
- Python 3.10+

**Frontend:**
- Next.js 15 - React framework
- TypeScript - Type safety
- Tailwind CSS 4 - Styling
- Jest + React Testing Library - Testing

## Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL database
- Google Cloud project (for Vertex AI) OR Google AI Studio API key
- Pinecone account and API key

## Setup Instructions

### 1. Clone Repository

```bash
git clone <repository-url>
cd ecommerce-ai-assistant
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate Prisma client
prisma generate
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL="mysql://user:password@localhost:3306/ecommerce_db"

# Google AI (choose ONE option)
# Option 1: Vertex AI (recommended for production)
EMBEDDINGS_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Option 2: Google AI Studio (for development)
EMBEDDINGS_PROVIDER=genai
GOOGLE_API_KEY=your-google-api-key

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=ecommerce-ai-assistant
PINECONE_NAMESPACE=  # Optional
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Embedding batch size (optional)
EMBED_BATCH_SIZE=32
```

### 4. Database Setup

```bash
# Run Prisma migrations
prisma migrate dev

# Load product catalog
python load_data.py
```

This loads products from `shop-product-catalog.csv` into MySQL.

### 5. Vector Database Setup

Sync products to Pinecone with embeddings:

```bash
python -m embedding.sync_pinecone
```

This will:
- Create Pinecone index if it doesn't exist (768 dimensions, cosine similarity)
- Generate embeddings for all products
- Upsert vectors with metadata (name, brand, price, description, etc.)

### 6. Frontend Setup

```bash
cd shop-frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000" > .env.local
```

## Running the Application

### Start Backend (FastAPI)

```bash
# From project root
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

API will be available at `http://127.0.0.1:8000`

### Start Frontend (Next.js)

```bash
cd shop-frontend
npm run dev
```

Frontend will be available at `http://localhost:3000`

## API Endpoints

### POST /chat

Send a chat message and receive AI response.

**Request:**
```json
{
  "query": "show me Nike shoes under $100",
  "history": []
}
```

**Response:**
```json
{
  "response": "Here are some Nike shoes under $100:\n- Nike Air Max 270 ($109.99)\n- Nike Presto Fly ($89.99)",
  "history": [
    "User: show me Nike shoes under $100",
    "Assistant: Here are some Nike shoes under $100:..."
  ]
}
```

### GET /products

Retrieve all products from the database.

**Response:**
```json
[
  {
    "id": 1000,
    "name": "Presto Fly 3",
    "brand": "Nike",
    "gender": "Women",
    "price": "10999",
    "price_display": "$109.99",
    "description": "Lightweight running shoes",
    "primaryColor": "Pink"
  }
]
```

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_chat.py -v
```

Test coverage includes:
- Chat endpoint functionality
- Database connection handling
- Price formatting
- Vector store initialization
- Pinecone sync logic
- Provider embeddings

### Frontend Tests

```bash
cd shop-frontend
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

## Project Structure

```
.
├── backend/
│   ├── db/              # Database connection
│   ├── routes/          # API endpoints
│   │   ├── chat.py      # Chat endpoint
│   │   └── products.py  # Products endpoint
│   ├── services/        # Business logic
│   │   ├── gemini_chain.py    # Gemini + RAG integration
│   │   ├── vector_store.py    # Pinecone setup
│   │   └── price.py           # Price formatting
│   └── main.py          # FastAPI app
├── embedding/
│   └── sync_pinecone.py # Product embedding & sync
├── providers/
│   └── embeddings.py    # Embedding provider abstraction
├── shop-frontend/       # Next.js application
│   ├── app/
│   │   └── page.tsx     # Main chat interface
│   └── __tests__/       # Frontend tests
├── tests/               # Backend tests
├── prisma/
│   └── schema.prisma    # Database schema
├── shop-product-catalog.csv  # Product data
├── load_data.py         # CSV → MySQL loader
└── requirements.txt     # Python dependencies
```

## Key Components

### Gemini Chain (`backend/services/gemini_chain.py`)

- Constructs prompts with system instructions + conversation history + RAG context
- Performs vector similarity search via Pinecone
- Handles multi-product enumeration for "list all X" queries
- Extracts brand hints from natural language
- Formats prices consistently ($XX.XX)

### Vector Store (`backend/services/vector_store.py`)

- Abstracts Pinecone initialization
- Supports both Vertex AI and Google GenAI embeddings
- Uses `text-embedding-004` (768 dimensions) by default

### Sync Script (`embedding/sync_pinecone.py`)

- Batched embedding generation for performance
- Stores metadata: name, brand, price, description, gender, color
- Includes formatted price_display field for consistent rendering
- Handles empty/None values safely

## Configuration

### Embedding Providers

**Vertex AI (Production):**
```env
EMBEDDINGS_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

**Google AI Studio (Development):**
```env
EMBEDDINGS_PROVIDER=genai
GOOGLE_API_KEY=your-api-key
```

### Pinecone Index Settings

- **Dimensions**: 768 (matches text-embedding-004)
- **Metric**: Cosine similarity
- **Cloud**: AWS
- **Region**: us-east-1 (configurable)

## Troubleshooting

### "No relevant context found"

**Cause**: Pinecone index is empty or not synced.

**Solution**:
```bash
python -m embedding.sync_pinecone
```

### "GOOGLE_CLOUD_PROJECT not set"

**Cause**: Using Vertex AI without proper configuration.

**Solution**: Set environment variables or switch to GenAI provider.

### Price formatting issues

**Cause**: Database stores prices as integers (cents).

**Solution**: The system automatically converts cents to dollars. Ensure `price.py` logic matches your data format.

### Frontend can't connect to backend

**Cause**: CORS or incorrect API URL.

**Solution**: 
1. Check `NEXT_PUBLIC_API_BASE` in frontend `.env.local`
2. Verify FastAPI CORS middleware allows frontend origin

## Performance Considerations

- **Embedding Batch Size**: Default 32, adjust via `EMBED_BATCH_SIZE`
- **Pinecone Query**: Returns top 10 results, filters by brand when detected
- **Response Time**: ~500ms for query → embedding → Pinecone → Gemini → response
- **Rate Limiting**: Consider implementing for production use

## Future Enhancements

- [ ] Add user authentication
- [ ] Implement conversation memory persistence
- [ ] Add product images to responses
- [ ] Support multi-language queries
- [ ] Add filtering by price range, gender, color
- [ ] Implement clickable product cards in responses
- [ ] Add analytics and query logging
- [ ] Support voice input/output

## License

MIT

## Contributing

Pull requests welcome! Please ensure tests pass before submitting.

```bash
# Run all checks
pytest && cd shop-frontend && npm test
```
