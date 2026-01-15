# check_routes.py
from app import create_app

app = create_app()

print("Checking for duplicate routes...")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint}: {rule.rule}")

print("\nChecking for duplicate endpoint names...")
endpoints = {}
for rule in app.url_map.iter_rules():
    if rule.endpoint in endpoints:
        print(f"DUPLICATE FOUND: {rule.endpoint}")
        print(f"  Existing: {endpoints[rule.endpoint]}")
        print(f"  New: {rule.rule}")
    else:
        endpoints[rule.endpoint] = rule.rule