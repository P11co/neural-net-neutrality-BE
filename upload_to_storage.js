// Node.js script to upload audio to InsForge Storage
const { createClient } = require('@insforge/sdk');
const fs = require('fs');
require('dotenv').config();

const client = createClient({ 
  baseUrl: process.env.INSFORGE_BASE_URL || 'https://sv7kpi43.us-east.insforge.app',
  anonKey: process.env.INSFORGE_API_KEY
});

async function uploadAudio(filePath, storageFilename) {
  console.log(`📤 Uploading ${filePath} to InsForge Storage...`);
  
  // Read file
  const fileBuffer = fs.readFileSync(filePath);
  const blob = new Blob([fileBuffer], { type: 'audio/mpeg' });
  
  // Upload to storage
  const { data, error } = await client.storage
    .from('podcast-episodes')
    .upload(storageFilename, blob);
  
  if (error) {
    console.error('❌ Upload failed:', error);
    return null;
  }
  
  console.log('✅ Upload successful!');
  console.log('URL:', data.url);
  console.log('Key:', data.key);
  
  return data.url;
}

// Test upload
const audioPath = process.argv[2] || '../Neural-Net-Neutrality/audio/podcast_20251026_062045.mp3';
const filename = process.argv[3] || 'podcast_20251026_062045.mp3';

uploadAudio(audioPath, filename).then((url) => {
  if (url) {
    console.log(`\n🎧 Audio URL: ${url}`);
  }
  process.exit(url ? 0 : 1);
});
