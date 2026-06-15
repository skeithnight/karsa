import os

# Fix src/karsa/llm/client.py
client_path = "src/karsa/llm/client.py"
if os.path.exists(client_path):
    with open(client_path, "r") as f:
        content = f.read()
    content = content.replace("ObservabilityManager = None", "None = None")
    with open(client_path, "w") as f:
        f.write(content)

# Fix src/karsa/regime/domain/events.py
events_path = "src/karsa/regime/domain/events.py"
if os.path.exists(events_path):
    with open(events_path, "r") as f:
        lines = f.readlines()
    with open(events_path, "w") as f:
        for line in lines:
            if "snapshot_urn: str" in line and "=" not in line:
                line = line.replace("snapshot_urn: str", "snapshot_urn: str = ''")
            if "occurred_at: datetime = " in line:
                pass # keep as is
            f.write(line)

# Fix tests/test_state_tracking.py
state_path = "tests/test_state_tracking.py"
if os.path.exists(state_path):
    with open(state_path, "r") as f:
        content = f.read()
    content = content.replace("from karsa.workflow.engine import RevisionEngine", "# removed karsa.workflow.engine")
    with open(state_path, "w") as f:
        f.write(content)

# Fix Dockerfile
with open("Dockerfile", "a") as f:
    f.write("RUN pip install cryptography testcontainers psycopg_pool\n")
