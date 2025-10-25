const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

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

// FastAPI endpoints (will run separately on Python)
// These are documented here for reference:
// POST /api/take_test - FastAPI endpoint (see api.py)

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
