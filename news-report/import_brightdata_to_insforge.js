#!/usr/bin/env node
/**
 * Import Bright Data scraped news JSON into InsForge database
 * Usage: node import_brightdata_to_insforge.js <json_file_path> <source_name>
 * Example: node import_brightdata_to_insforge.js data/bbc_news.json BBC
 */

const fs = require('fs');
const { createClient } = require('@insforge/sdk');

// InsForge configuration
const INSFORGE_BASE_URL = "https://sv7kpi43.us-east.insforge.app";
const INSFORGE_API_KEY = process.env.INSFORGE_API_KEY || "ik_194453edb70ffcd51d76e2718b3f9eed";

// News source ID mapping (from your InsForge database)
const SOURCE_IDS = {
  "BBC": "969e05ab-1549-4c61-a7ad-accff1f0eb5f",
  "Reuters": "6cf6e9c0-a4b4-41be-8071-c74b722101e8",
  "Straight Arrow News": "8bfc9d71-b0ec-43be-a899-818bad04a684"
};

// Create InsForge client
const client = createClient({
  baseUrl: INSFORGE_BASE_URL,
  apiKey: INSFORGE_API_KEY
});

/**
 * Parse a Bright Data article object to InsForge schema
 */
function parseBrightDataArticle(article, sourceId) {
  const crypto = require('crypto');

  // Extract URL
  let url = article.input?.url || "";

  // Generate a pseudo-URL if not available (for uniqueness constraint)
  if (!url || url === "https://www.bbc.com/") {
    const headlineHash = crypto.createHash('md5').update(article.headline).digest('hex').substring(0, 12);
    url = `https://www.bbc.com/news/articles/${headlineHash}`;
  }

  const description = article.description || "";

  return {
    source_id: sourceId,
    title: (article.headline || "").trim(),
    url: url,
    content: description.trim(),
    summary: description.length > 200
      ? description.substring(0, 200).trim() + "..."
      : description.trim(),
    author: null,  // Not provided by Bright Data
    published_at: new Date().toISOString(),  // Not provided, use current time
    category: (article.section_name || "general").trim(),
    image_url: article.article_image?.trim() || null
  };
}

/**
 * Insert articles into InsForge database
 */
async function insertArticlesToInsforge(articles) {
  let inserted = 0;
  let skipped = 0;
  const errors = [];

  for (const article of articles) {
    try {
      const { data, error } = await client.database
        .from('news_articles')
        .insert([article])
        .select();

      if (error) {
        // Check if it's a duplicate (unique constraint violation)
        if (error.code === '23505' || error.message?.includes('duplicate')) {
          skipped++;
          console.log(`⊘ Skipped (duplicate): ${article.title.substring(0, 60)}...`);
        } else {
          errors.push(`Error inserting '${article.title.substring(0, 40)}': ${error.message || error}`);
          console.log(`✗ Error: ${article.title.substring(0, 60)}... - ${error.message || error}`);
        }
      } else {
        inserted++;
        console.log(`✓ Inserted: ${article.title.substring(0, 60)}...`);
      }
    } catch (e) {
      errors.push(`Exception for '${article.title.substring(0, 40)}': ${e.message}`);
      console.log(`✗ Exception: ${article.title.substring(0, 60)}... - ${e.message}`);
    }
  }

  return { inserted, skipped, errors };
}

/**
 * Update the last_scraped_at timestamp for a news source
 */
async function updateSourceLastScraped(sourceId) {
  try {
    const { error } = await client.database
      .from('news_sources')
      .update({ last_scraped_at: new Date().toISOString() })
      .eq('id', sourceId);

    if (error) {
      console.log(`⚠ Failed to update last_scraped_at: ${error.message}`);
    } else {
      console.log(`✓ Updated last_scraped_at for source`);
    }
  } catch (e) {
    console.log(`⚠ Exception updating last_scraped_at: ${e.message}`);
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.log("Usage: node import_brightdata_to_insforge.js <json_file_path> <source_name>");
    console.log("Example: node import_brightdata_to_insforge.js data/bbc_news.json BBC");
    console.log(`\nAvailable sources: ${Object.keys(SOURCE_IDS).join(', ')}`);
    process.exit(1);
  }

  const jsonFile = args[0];
  const sourceName = args[1];

  // Validate source
  if (!(sourceName in SOURCE_IDS)) {
    console.log(`Error: Unknown source '${sourceName}'`);
    console.log(`Available sources: ${Object.keys(SOURCE_IDS).join(', ')}`);
    process.exit(1);
  }

  const sourceId = SOURCE_IDS[sourceName];

  // Load JSON file
  let brightdataArticles;
  try {
    const fileContent = fs.readFileSync(jsonFile, 'utf-8');
    brightdataArticles = JSON.parse(fileContent);
  } catch (e) {
    if (e.code === 'ENOENT') {
      console.log(`Error: File '${jsonFile}' not found`);
    } else if (e instanceof SyntaxError) {
      console.log(`Error: Invalid JSON in file '${jsonFile}': ${e.message}`);
    } else {
      console.log(`Error: ${e.message}`);
    }
    process.exit(1);
  }

  console.log(`\n📰 Importing ${brightdataArticles.length} articles from ${sourceName}...`);
  console.log(`Source ID: ${sourceId}\n`);

  // Parse articles
  const parsedArticles = [];
  for (const article of brightdataArticles) {
    if (article.content_type === "article" && article.headline) {
      const parsed = parseBrightDataArticle(article, sourceId);
      parsedArticles.push(parsed);
    }
  }

  console.log(`Parsed ${parsedArticles.length} valid articles\n`);

  // Insert into InsForge
  const { inserted, skipped, errors } = await insertArticlesToInsforge(parsedArticles);

  // Update source timestamp
  if (inserted > 0) {
    await updateSourceLastScraped(sourceId);
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log(`✓ Inserted: ${inserted}`);
  console.log(`⊘ Skipped (duplicates): ${skipped}`);
  console.log(`✗ Errors: ${errors.length}`);
  console.log("=".repeat(60));

  if (errors.length > 0) {
    console.log("\nErrors:");
    errors.slice(0, 10).forEach(error => console.log(`  - ${error}`));
    if (errors.length > 10) {
      console.log(`  ... and ${errors.length - 10} more errors`);
    }
  }
}

main().catch(err => {
  console.error("Fatal error:", err);
  process.exit(1);
});
