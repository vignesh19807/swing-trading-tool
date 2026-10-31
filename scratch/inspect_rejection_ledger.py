import json

with open("docs/audit_artifacts/AUDIT_016_REJECTION_LEDGER.json", "r") as f:
    data = json.load(f)

print("Total in ledger:", len(data["ledger"]))
pit_buys = [item for item in data["ledger"] if "REVERTED" not in item.get("audit_016_pit_resolution", "")]
print("PIT Non-reverted buys count:", len(pit_buys))
for b in pit_buys:
    print(b)

