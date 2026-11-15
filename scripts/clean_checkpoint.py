import json

checkpoint_path = "tests/data/eval_checkpoint_1000.json"
with open(checkpoint_path, "r", encoding="utf-8") as f:
    cp = json.load(f)

print(f"Total claims in checkpoint before cleaning: {len(cp)}")

clean_cp = {}
pruned = 0
for cid, data in cp.items():
    is_tainted = False
    for cfg_id, res in data.get("evaluations", {}).items():
        reasoning = res.get("reasoning", "")
        if "unavailable" in reasoning.lower() or "error code" in reasoning.lower() or "execution error" in reasoning.lower():
            is_tainted = True
            break
    if not is_tainted and len(data.get("evaluations", {})) == 3:
        clean_cp[cid] = data
    else:
        pruned += 1

print(f"Pruned tainted claims: {pruned}")
print(f"Clean valid claims remaining: {len(clean_cp)}")

with open(checkpoint_path, "w", encoding="utf-8") as f:
    json.dump(clean_cp, f, indent=2)

print("Checkpoint successfully cleaned!")
