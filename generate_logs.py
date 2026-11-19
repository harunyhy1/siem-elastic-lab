import json
import sys
import time
from datetime import datetime, timezone

ip = "192.0.2.10"
jumlah = int(sys.argv[1]) if len(sys.argv) > 1 else 8

with open("logs/auth.log", "a", encoding="utf-8") as f:
    for i in range(jumlah):
        event = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "event": {
                "category": ["authentication"],
                "outcome": "failure",
                "kind": "event"
            },
            "source": {"ip": ip},
            "process": {"name": "sshd"},
            "message": f"Failed password for testuser from {ip} port {22000+i} ssh2"
        }
        f.write(json.dumps(event) + "\n")
        f.flush()
        print(f"Event {i+1}/{jumlah} dibuat")
        time.sleep(2)
