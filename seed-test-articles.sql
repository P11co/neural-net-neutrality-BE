-- Seed test articles for podcast generation
-- Run this in InsForge SQL console to populate news_articles table

-- First, ensure the tables exist
CREATE TABLE IF NOT EXISTS news_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    url TEXT,
    content TEXT,
    summary TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    source_id UUID REFERENCES news_sources(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert news sources
INSERT INTO news_sources (name, url)
VALUES
    ('BBC', 'https://www.bbc.com'),
    ('Reuters', 'https://www.reuters.com'),
    ('Straight Arrow News', 'https://www.straightarrownews.com')
ON CONFLICT (name) DO NOTHING;

-- Insert test articles (adjust date to today)
INSERT INTO news_articles (title, content, url, published_at, source_id)
VALUES
    (
        'AI Regulation Bill Passes Senate Committee',
        'The Senate Commerce Committee approved landmark legislation today that would establish federal oversight of artificial intelligence systems. The bipartisan bill, supported by both Democrats and Republicans, aims to create safety standards for AI models while promoting innovation. Proponents argue it provides necessary guardrails, while critics worry it may stifle technological progress. The bill now moves to the full Senate for consideration.',
        'https://www.bbc.com/news/technology-ai-regulation-2025',
        NOW() - INTERVAL ''2 hours'',
        (SELECT id FROM news_sources WHERE name = ''BBC'')
    ),
    (
        'Federal Reserve Holds Interest Rates Steady',
        'The Federal Reserve announced it will maintain current interest rates following its policy meeting, citing stable inflation and steady economic growth. Fed Chair Jerome Powell stated the central bank remains data-dependent and will adjust policy as needed. Markets responded positively to the decision, with major indices gaining ground. Economists predict rates will remain unchanged through the end of the year.',
        'https://www.reuters.com/markets/fed-rates-2025',
        NOW() - INTERVAL ''3 hours'',
        (SELECT id FROM news_sources WHERE name = ''Reuters'')
    ),
    (
        'Bipartisan Infrastructure Projects Break Ground Nationwide',
        'Construction began today on dozens of infrastructure projects across the country, funded by the 2021 bipartisan infrastructure law. Projects include bridge repairs, highway expansions, and broadband deployment in rural areas. Transportation Secretary Pete Buttigieg toured sites in three states, highlighting the economic benefits and job creation. Both parties claimed credit for the achievements during separate press conferences.',
        'https://www.straightarrownews.com/politics/infrastructure-projects-2025',
        NOW() - INTERVAL ''4 hours'',
        (SELECT id FROM news_sources WHERE name = ''Straight Arrow News'')
    ),
    (
        'Tech Companies Announce Voluntary AI Safety Commitments',
        'Major technology companies including Google, Microsoft, and OpenAI pledged new voluntary safety commitments for AI development. The agreements include increased transparency, third-party audits, and investment in AI safety research. The White House praised the commitments as a positive step, though some advocates argue binding regulations are still necessary. The announcements come amid growing calls for AI governance.',
        'https://www.bbc.com/news/technology-ai-safety-2025',
        NOW() - INTERVAL ''5 hours'',
        (SELECT id FROM news_sources WHERE name = ''BBC'')
    ),
    (
        'Supreme Court Agrees to Hear Social Media Regulation Case',
        'The U.S. Supreme Court will hear arguments on the constitutionality of state laws regulating social media platforms. The cases from Texas and Florida involve restrictions on content moderation practices. Tech industry groups argue the laws violate free speech rights, while state officials contend platforms have too much power. Legal experts call it one of the most significant First Amendment cases in decades.',
        'https://www.reuters.com/legal/supreme-court-social-media-2025',
        NOW() - INTERVAL ''6 hours'',
        (SELECT id FROM news_sources WHERE name = ''Reuters'')
    );

-- Verify the data
SELECT
    na.title,
    ns.name as source,
    na.published_at
FROM news_articles na
JOIN news_sources ns ON na.source_id = ns.id
ORDER BY na.published_at DESC
LIMIT 5;
