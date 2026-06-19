import sqlite3

# Connect to database
conn = sqlite3.connect('punjab_rozgar.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Database Tables:")
for table in tables:
    print(f"- {table[0]}")

# Check if users table exists and get schema
if any(table[0] == 'users' for table in tables):
    print("\nUsers table schema:")
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Count users
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\nTotal users: {count}")

conn.close()