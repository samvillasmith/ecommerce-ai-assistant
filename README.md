# E-commerce AI Shopping Assistant

AI-powered conversational shopping assistant built with Google Gemini, Pinecone vector search, and FastAPI. Customers can ask natural language questions like "show me Nike shoes under $100" and get intelligent product recommendations.

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **MySQL database**
- **Google Cloud account** (for Vertex AI) **OR** **Google AI Studio API key**
- **Pinecone account**

### 1. Clone & Install

```bash
git clone <repository-url>
cd ecommerce-ai-assistant

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
prisma generate

# Frontend
cd shop-frontend
npm install
```

### 2. Environment Variables - **CRITICAL SETUP**

Create **`.env`** in the **project root**:

```env
# ============================================================================
# DATABASE (REQUIRED)
# ============================================================================
DATABASE_URL="mysql://username:password@localhost:3306/ecommerce_db"

# ============================================================================
# GOOGLE AI - CHOOSE ONE OPTION
# ============================================================================
# Option 1: Vertex AI (Production - Recommended)
EMBEDDINGS_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Option 2: Google AI Studio (Development/Testing)
# EMBEDDINGS_PROVIDER=genai
# GOOGLE_API_KEY=your-google-ai-studio-api-key

# ============================================================================
# PINECONE (REQUIRED)
# ============================================================================
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=ecommerce-ai-assistant
PINECONE_NAMESPACE=
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# ============================================================================
# OPTIONAL SETTINGS
# ============================================================================
EMBED_BATCH_SIZE=32
```

Create **`shop-frontend/.env.local`**:

```env
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

### 3. Setup Database & Vectors

```bash
# Create database schema
prisma migrate dev

# Load product catalog (from CSV)
python load_data.py

# Generate embeddings and sync to Pinecone (THIS CREATES THE INDEX)
python -m embedding.sync_pinecone
```

### 4. Run Application

**Terminal 1 - Backend:**
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd shop-frontend
npm run dev
```

Open **http://localhost:3000**

---

## 🔑 Environment Variables Explained

### Database Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ Yes | MySQL connection string | `mysql://user:pass@localhost:3306/dbname` |

### Embeddings Provider (Choose ONE)

#### Option A: Vertex AI (Production)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `EMBEDDINGS_PROVIDER` | ✅ Yes | Set to `vertex` | `vertex` |
| `GOOGLE_CLOUD_PROJECT` | ✅ Yes | Your GCP project ID | `my-project-123456` |
| `GOOGLE_CLOUD_LOCATION` | ⚠️ Optional | GCP region | `us-central1` (default) |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ Yes | Path to service account JSON | `/path/to/key.json` |

**Getting Vertex AI credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Vertex AI API
3. Create service account with "Vertex AI User" role
4. Download JSON key file
5. Set `GOOGLE_APPLICATION_CREDENTIALS` to the file path

#### Option B: Google AI Studio (Development)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `EMBEDDINGS_PROVIDER` | ✅ Yes | Set to `genai` | `genai` |
| `GOOGLE_API_KEY` | ✅ Yes | API key from AI Studio | `AIzaSy...` |

**Getting AI Studio key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key to `GOOGLE_API_KEY`

### Pinecone Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `PINECONE_API_KEY` | ✅ Yes | Pinecone API key | `pcsk_...` |
| `PINECONE_INDEX_NAME` | ⚠️ Optional | Index name | `ecommerce-ai-assistant` (default) |
| `PINECONE_NAMESPACE` | ❌ No | Namespace for multi-tenancy | `` (empty default) |
| `PINECONE_CLOUD` | ⚠️ Optional | Cloud provider | `aws` (default) |
| `PINECONE_REGION` | ⚠️ Optional | Region | `us-east-1` (default) |

**Getting Pinecone credentials:**
1. Sign up at [Pinecone](https://www.pinecone.io)
2. Create a free account
3. Copy API key from dashboard

### Frontend Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE` | ✅ Yes | Backend API URL | `http://127.0.0.1:8000` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBED_BATCH_SIZE` | `32` | Batch size for embedding generation |

---

## 🏗️ Architecture

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
1. User query → Next.js frontend
2. Frontend → FastAPI `/chat` endpoint
3. Backend retrieves conversation history
4. **Pinecone vector search** finds similar products
5. **Gemini generates** natural language response with RAG context
6. Response → Frontend

---

## 📁 Project Structure

```
.
├── .env                          # ⚠️ ENVIRONMENT VARIABLES (CREATE THIS)
├── backend/
│   ├── db/                       # Database connection
│   ├── routes/
│   │   ├── chat.py              # Chat endpoint
│   │   └── products.py          # Products API
│   ├── services/
│   │   ├── gemini_chain.py      # Gemini + RAG logic
│   │   ├── vector_store.py      # Pinecone setup
│   │   └── price.py             # Price formatting
│   └── main.py                  # FastAPI app
├── embedding/
│   └── sync_pinecone.py         # ⚠️ RUN THIS TO POPULATE VECTORS
├── providers/
│   └── embeddings.py            # Embedding provider abstraction
├── shop-frontend/
│   ├── .env.local               # ⚠️ FRONTEND ENV (CREATE THIS)
│   ├── app/
│   │   └── page.tsx             # Chat UI
│   └── __tests__/               # Frontend tests
├── tests/                        # Backend tests
├── prisma/schema.prisma         # Database schema
├── shop-product-catalog.csv     # Product data
├── load_data.py                 # ⚠️ RUN THIS FIRST
└── requirements.txt
```

---

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test
pytest tests/test_chat.py -v
```

### Frontend Tests

```bash
cd shop-frontend
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

---

## 🔧 API Endpoints

### `POST /chat`

Send chat message, get AI response.

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
  "response": "Here are Nike shoes under $100:\n- Nike Air Max 270 ($109.99)\n- Nike Presto Fly ($89.99)",
  "history": [
    "User: show me Nike shoes under $100",
    "Assistant: Here are Nike shoes under $100:..."
  ]
}
```

### `GET /products`

Retrieve all products.

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

---

## ⚠️ Troubleshooting

### "GOOGLE_CLOUD_PROJECT not set"

**Solution:** If using Vertex AI, set all three variables:
```env
EMBEDDINGS_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### "GOOGLE_API_KEY is not set"

**Solution:** If using AI Studio, set:
```env
EMBEDDINGS_PROVIDER=genai
GOOGLE_API_KEY=your-api-key
```

### "No relevant context found"

**Cause:** Pinecone index is empty.

**Solution:**
```bash
python -m embedding.sync_pinecone
```

### Frontend can't connect to backend

**Check:**
1. Backend is running: `http://127.0.0.1:8000/docs`
2. Frontend `.env.local` has correct URL:
   ```env
   NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
   ```

### Price formatting issues

Prices in database are stored as integers (cents). The system automatically converts:
- `10999` → `$109.99`
- `5499` → `$54.99`

---

## 🎯 Features

- ✅ **Natural Language Search** - "show me black Vans under $50"
- ✅ **RAG-Powered** - Semantic search with Pinecone vectors
- ✅ **Multi-Product Listings** - "list all Nike shoes"
- ✅ **Brand Detection** - Automatically filters by mentioned brands
- ✅ **Price Normalization** - Consistent `$XX.XX` formatting
- ✅ **Session Memory** - Conversation history per browser tab
- ✅ **Full Test Coverage** - Pytest + Jest

---

## 📝 License

MIT

---

## 🚨 CRITICAL REMINDERS

1. **ALWAYS run `python -m embedding.sync_pinecone` after loading products**
2. **Set EMBEDDINGS_PROVIDER to either `vertex` or `genai`** - don't mix them
3. **Don't commit `.env` or `.env.local` to version control**
4. **MySQL database must be created before running migrations**
5. **Pinecone free tier works fine for development**

---

**Need help?** Check `/docs` endpoint when backend is running: `http://127.0.0.1:8000/docs`
