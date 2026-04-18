import sqlite3, json, asyncio

async def init():
    from src.database.core import init_db
    await init_db()

asyncio.run(init())

conn = sqlite3.connect('shop.db')
data = json.load(open('backup_data.json'))

for table, rows in data.items():
    if not rows:
        continue
    cols = list(rows[0].keys())
    placeholders = ','.join(['?' for _ in cols])
    col_names = ','.join(cols)
    count = 0
    for row in rows:
        try:
            conn.execute(
                f'INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})',
                [row[c] for c in cols]
            )
            count += 1
        except Exception as e:
            pass
    print(f"✅ 恢复 {table}: {count} 条")

conn.commit()
conn.close()
print("✅ 数据恢复完成")
