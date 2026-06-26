import json
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='localhost',
    port=8123,
    username='default',
    password='dev123'
)

# Drop and recreate to avoid duplicate inserts on re-runs
client.command('DROP TABLE IF EXISTS restaurants')

client.command('''
    CREATE TABLE IF NOT EXISTS restaurants (
        name String,
        address String,
        item_name String,
        price Float32
    ) ENGINE = MergeTree()
    ORDER BY (address, name)
''')

with open('restaurants.json', 'r') as f:
    data = json.load(f)

rows = []

for restaurant in data:
    name = restaurant["name"]
    address = restaurant["address"]

    for item in restaurant["items"]:
        rows.append([
            name,
            address,
            item["name"],
            float(item["price"])
        ])

client.insert(
    table='restaurants',
    data=rows,
    column_names=['name', 'address', 'item_name', 'price']
)

print("data successfully inserted into clickhouse")

# find restaurants sharing the same address
result = client.query('''
    SELECT 
        address,
        groupArray(DISTINCT name) AS restaurants,
        count(DISTINCT name) AS restaurant_count
    FROM restaurants
    GROUP BY address
    HAVING restaurant_count > 1
''')

print(" Suspicious addresses found:")
for row in result.named_results():
    print(f"\nAddress: {row['address']}")
    print(f"Restaurants: {row['restaurants']}")
    print(f"Count: {row['restaurant_count']}")