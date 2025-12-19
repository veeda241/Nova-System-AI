
import json
import random
import os

# INTENTS = {0: "LOCK_SYSTEM", 1: "VOLUME_UP", 2: "VOLUME_DOWN", 3: "SYSTEM_STATUS", 4: "UNKNOWN"}

DATASET_CONFIG = {
    0: [
        "lock systems", "lock computer", "secure laptop", "lock it", "screen lock",
        "lock workstation", "lock now", "please lock", "lock the machine", "protect screen"
    ],
    1: [
        "volume up", "increase volume", "louder", "make it louder", "sound up",
        "more volume", "volume increase", "turn it up", "sound plus", "volume high"
    ],
    2: [
        "volume down", "decrease volume", "quieter", "make it quiet", "sound down",
        "less volume", "volume decrease", "turn it down", "sound minus", "volume low"
    ],
    3: [
        "system status", "how are you", "show status", "system health", "check laptop",
        "battery status", "cpu usage", "resource stats", "how is the machine", "stats"
    ],
    4: [
        "what is the time", "hello", "who are you", "open chrome", "delete file",
        "lock everything now", "make it super quiet", "do that thing", "random test",
        "help me", "weather", "search for items", "play music", "go home"
    ]
}

def generate_noise(text):
    # Add minor noise to make it robust
    if random.random() > 0.7:
        text = text + "!" 
    return text

def create_dataset(output_path="engine_training/dataset.json"):
    dataset = []
    for intent_id, examples in DATASET_CONFIG.items():
        for ex in examples:
            # Add some variations
            dataset.append({"text": ex, "label": intent_id})
            dataset.append({"text": generate_noise(ex), "label": intent_id})
            dataset.append({"text": "can you " + ex, "label": intent_id})
            dataset.append({"text": "please " + ex, "label": intent_id})
            
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"✅ Generated {len(dataset)} synthetic samples.")

if __name__ == "__main__":
    create_dataset()
