const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { createProxyMiddleware } = require('http-proxy-middleware');

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/', (req, res) => {
  res.json({ status: 'ok', message: 'Neural Net Neutrality Backend API' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Import and mount API routes
const generateNewsScript = require('./api/generate-news-script');
app.get('/api/generate-news-script', generateNewsScript);

// Proxy to Python FastAPI server for /api/battle
// Python server should be running on port 8080
// Start it with: uvicorn generate:app --port 8080 --reload
app.use('/api/battle', createProxyMiddleware({
  target: 'http://localhost:8080',
  changeOrigin: true,
  pathRewrite: {
    '^/api/battle': '/battle'
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(503).json({
      error: 'Python FastAPI server not available',
      message: 'Please start the Python server: uvicorn generate:app --port 8080',
      details: err.message
    });
  }
}));

// Proxy to Python FastAPI server for /api/generate-podcast
// Python server should be running on port 8081
// Start it with: uvicorn generate_podcast:app --port 8081 --reload
app.use('/api/generate-podcast', createProxyMiddleware({
  target: 'http://localhost:8081',
  changeOrigin: true,
  pathRewrite: {
    '^/api/generate-podcast': '/generate-podcast'
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(503).json({
      error: 'Python FastAPI server not available',
      message: 'Please start the Python server: uvicorn generate_podcast:app --port 8081 --reload',
      details: err.message
    });
  }
}));

// Proxy to Python FastAPI server for /api/podcasts (GET episodes list)
app.use('/api/podcasts', createProxyMiddleware({
  target: 'http://localhost:8081',
  changeOrigin: true,
  pathRewrite: {
    '^/api/podcasts': '/podcasts'
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(503).json({
      error: 'Python FastAPI server not available',
      message: 'Please start the Python server: uvicorn generate_podcast:app --port 8081 --reload',
      details: err.message
    });
  }
}));

// FastAPI endpoints (will run separately on Python)
// POST /api/take_test - FastAPI endpoint (see api.py)
//   Start with: uvicorn api:app --port 8000

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    message: `Route ${req.method} ${req.path} not found`
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📍 Health check: http://localhost:${PORT}/health`);
  console.log(`📰 News API: http://localhost:${PORT}/api/generate-news-script`);
});
