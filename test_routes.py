# test_routes.py
from app import create_app

app = create_app()

print("All registered routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint:40} {rule.rule}")

print("\nEmployee routes:")
for rule in app.url_map.iter_rules():
    if 'employee' in rule.endpoint:
        print(f"{rule.endpoint:40} {rule.rule}")