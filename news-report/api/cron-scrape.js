/**
 * Vercel Serverless Function for Daily News Scraping
 *
 * This can be triggered by Vercel Cron or manually via HTTP request
 * URL: https://your-app.vercel.app/api/cron-scrape
 */

const { spawn } = require('child_process');
const path = require('path');

export default async function handler(req, res) {
  // Security: Add a secret token to prevent unauthorized triggers
  const CRON_SECRET = process.env.CRON_SECRET || 'your-secret-here';
  const authHeader = req.headers['authorization'];

  if (authHeader !== `Bearer ${CRON_SECRET}` && req.method !== 'GET') {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  console.log('🚀 Starting daily news scrape...');

  try {
    // Run the scraping script
    const scriptPath = path.join(process.cwd(), 'backend', 'news-report', 'scrape_and_import.sh');

    const scrapeProcess = spawn('bash', [scriptPath], {
      env: {
        ...process.env,
        BRIGHTDATA_API_TOKEN: process.env.BRIGHTDATA_API_TOKEN,
        INSFORGE_API_KEY: process.env.INSFORGE_API_KEY
      }
    });

    let output = '';
    let errorOutput = '';

    scrapeProcess.stdout.on('data', (data) => {
      const message = data.toString();
      console.log(message);
      output += message;
    });

    scrapeProcess.stderr.on('data', (data) => {
      const message = data.toString();
      console.error(message);
      errorOutput += message;
    });

    // Wait for the process to complete
    await new Promise((resolve, reject) => {
      scrapeProcess.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`Process exited with code ${code}`));
        }
      });
    });

    console.log('✅ Scraping completed successfully');

    return res.status(200).json({
      success: true,
      message: 'Daily news scrape completed successfully',
      timestamp: new Date().toISOString(),
      output: output.substring(output.length - 500) // Last 500 chars
    });

  } catch (error) {
    console.error('❌ Scraping failed:', error);

    return res.status(500).json({
      success: false,
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
}

// Configure for Vercel Cron
export const config = {
  // Run daily at 9 AM PST (5 PM UTC)
  // Note: Vercel Cron uses UTC time
  api: {
    bodyParser: false,
    externalResolver: true
  }
};
