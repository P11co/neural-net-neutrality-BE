# Neural Net Neutrality - Backend

Backend server for Neural Net Neutrality project. Runs on Render.

## Structure

- `server.js` - Express.js server for Node.js endpoints
- `api.py` - FastAPI server for Python endpoints
- `api/` - Node.js API endpoints
- `news-report/` - News reporting scripts and utilities
- Python modules for AI testing functionality

## Setup

### Node.js Server

```bash
npm install
npm start
```

### Python FastAPI Server

```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

- `INSFORGE_BASE_URL` - InsForge database URL
- `INSFORGE_API_KEY` - InsForge API key
- `OPENAI_API_KEY` - OpenAI API key
- `PORT` - Node.js server port (default: 3001)

## Deployment
### Prompt responses:
- uvicorn generate:app                    

### Render Configuration

1. **Node.js Service**:
   - Build Command: `npm install`
   - Start Command: `npm start`
   - Port: Uses `PORT` environment variable

2. **Python Service** (if needed separately):
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

## API Endpoints

### Node.js Endpoints

- `GET /health` - Health check
- `GET /api/generate-news-script` - Generate news anchor script from top articles

### Python/FastAPI Endpoints

- `POST /api/take_test` - Run AI political compass test
