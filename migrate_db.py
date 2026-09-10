"""
Complete DB migration - adds all missing columns to user, review, watchlist, and related tables.
Run: python migrate_db.py
"""
import sqlite3, os, glob

possible_paths = ['instance/database.db', 'instance/movies.db', 'model/movies.db', 'movies.db', 'database.db']
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

# Column specifications per table
table_columns = {
    "user": [
        ("email", "VARCHAR(120)"),
        ("bio", "VARCHAR(500)"),
        ("avatar_url", "VARCHAR(200) DEFAULT 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix'"),
        ("is_admin", "BOOLEAN DEFAULT 0"),
        ("is_moderator", "BOOLEAN DEFAULT 0"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("created_at", "DATETIME"),
        ("last_login", "DATETIME"),
    ],
    "review": [
        ("updated_at", "DATETIME"),
        ("likes_count", "INTEGER DEFAULT 0"),
        ("is_flagged", "BOOLEAN DEFAULT 0"),
        ("is_hidden", "BOOLEAN DEFAULT 0"),
        ("helpful_count", "INTEGER DEFAULT 0"),
    ],
    "watchlist": [
        ("poster_path", "VARCHAR(500)"),
        ("tmdb_id", "INTEGER"),
        ("added_at", "DATETIME"),
        ("watch_status", "VARCHAR(20) DEFAULT 'want_to_watch'"),
    ],
    "movie_list": [
        ("description", "VARCHAR(500)"),
        ("is_public", "BOOLEAN DEFAULT 1"),
        ("created_at", "DATETIME"),
        ("updated_at", "DATETIME"),
    ],
    "list_item": [
        ("poster_path", "VARCHAR(500)"),
        ("tmdb_id", "INTEGER"),
        ("added_at", "DATETIME"),
    ],
    "viewing_history": [
        ("tmdb_id", "INTEGER"),
        ("viewed_at", "DATETIME"),
    ],
    "notification": [
        ("link", "VARCHAR(200)"),
        ("is_read", "BOOLEAN DEFAULT 0"),
        ("created_at", "DATETIME"),
    ]
}

for table, cols in table_columns.items():
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if not cursor.fetchone():
        print(f"Table '{table}' does not exist yet; skipping column additions.")
        continue

    cursor.execute(f"PRAGMA table_info({table})")
    existing_cols = {row[1] for row in cursor.fetchall()}
    print(f"\nExisting {table} columns: {sorted(existing_cols)}")

    for col, col_type in cols:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                conn.commit()
                print(f"  [+] Added '{col}' ({col_type}) to {table}")
            except Exception as e:
                conn.rollback()
                print(f"  [-] Could not add '{col}' to {table}: {e}")
        else:
            print(f"  [.] '{col}' already exists")

conn.close()
print("\nMigration complete!")

