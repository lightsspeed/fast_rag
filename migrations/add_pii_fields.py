"""
Database migration script for PII fields in ImageMetadata
Run this to update existing database schema
"""
from sqlalchemy import create_engine, text
import os

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fastrag")

engine = create_engine(DATABASE_URL)

# Migration SQL
MIGRATION_SQL = """
-- Add PII tracking fields to image_metadata table
ALTER TABLE image_metadata 
ADD COLUMN IF NOT EXISTS has_pii INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pii_types JSON DEFAULT '[]',
ADD COLUMN IF NOT EXISTS pii_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS needs_review INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS redacted_content TEXT;

-- Add index for PII queries
CREATE INDEX IF NOT EXISTS idx_image_metadata_pii ON image_metadata(has_pii, needs_review);

-- Update confidence column name if needed (from ocr_confidence to confidence)
DO $$ 
BEGIN
    IF EXISTS(SELECT 1 FROM information_schema.columns 
              WHERE table_name='image_metadata' AND column_name='ocr_confidence') THEN
        ALTER TABLE image_metadata RENAME COLUMN ocr_confidence TO confidence;
    END IF;
END $$;

-- Create query log table if not exists (for monitoring)
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    query_text TEXT,
    retrieved_chunks INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feedback_score INTEGER
);

CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at);

PRINT 'Migration completed successfully!';
"""

def run_migration():
    """Execute migration"""
    try:
        with engine.connect() as conn:
            conn.execute(text(MIGRATION_SQL))
            conn.commit()
        print("✅ Database migration completed successfully!")
        print("   - Added PII tracking fields")
        print("   - Created indexes")
        print("   - Updated schema")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("Running database migration...")
    run_migration()
