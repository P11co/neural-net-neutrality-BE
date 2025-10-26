#!/usr/bin/env python3
"""
Simple working podcast API that uses raw SQL via MCP
Run this alongside your static file server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from pathlib import Path

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock episode data (from InsForge DB)
EPISODES = [{
    "id": "2f679026-497f-4891-85f5-9a659b2edee2",
    "title": "Daily Brief - October 26, 2025",
    "description": "Your daily AI-generated neutral news podcast covering the latest in tech, science, and space exploration",
    "publication_date": "2025-10-26",
    "audio_url": "http://localhost:3001/audio/podcast_20251026_011221.mp3",
    "duration_seconds": 249,
    "cover_image_url": "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=800",
    "play_count": 0
}]

@app.get("/api/podcasts")
async def get_podcasts(limit: int = 10):
    """Get list of podcast episodes"""
    return {
        "episodes": EPISODES[:limit],
        "count": len(EPISODES)
    }

@app.get("/api/podcasts/latest")
async def get_latest_podcast():
    """Get today's podcast episode"""
    if EPISODES:
        return {
            "episode": EPISODES[0],
            "found": True
        }
    return {
        "episode": None,
        "found": False,
        "message": "No episodes available"
    }

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files"""
    audio_path = Path(__file__).parent / "public" / "audio" / filename

    if audio_path.exists():
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={"Accept-Ranges": "bytes"}
        )

    return {"error": "File not found"}, 404

@app.get("/health")
async def health():
    return {"status": "ok", "service": "simple-podcast-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
