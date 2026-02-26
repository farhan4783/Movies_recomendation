"""
Complete DB migration - adds all missing columns to review table.
Run: python migrate_db.py
"""
import sqlite3, os, glob

possible_paths = ['instance/movies.db', 'instance/database.db', 'model/movies.db', 'movies.db', 'database.db']
db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    found = glob.glob('**/*.db', recursive=True)
    if found:
        db_path = found[0]

if not db_path:
    print("No SQLite database found! Run the app first to create it.")
    exit(1)

print(f"Found database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# All columns to ensure exist in review table
review_columns = [
    ("updated_at",    "DATETIME"),
    ("likes_count",   "INTEGER DEFAULT 0"),
    ("is_flagged",    "BOOLEAN DEFAULT 0"),
    ("is_hidden",     "BOOLEAN DEFAULT 0"),
    ("helpful_count", "INTEGER DEFAULT 0"),
]

cursor.execute("PRAGMA table_info(review)")
existing_cols = {row[1] for row in cursor.fetchall()}
print(f"Existing review columns: {sorted(existing_cols)}")

for col, col_type in review_columns:
    if col not in existing_cols:
        try:
            cursor.execute(f"ALTER TABLE review ADD COLUMN {col} {col_type}")
            conn.commit()
            print(f"  ✓ Added '{col}' ({col_type}) to review")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ Could not add '{col}': {e}")
    else:
        print(f"  • '{col}' already exists")

conn.close()
print("\nMigration complete!")
