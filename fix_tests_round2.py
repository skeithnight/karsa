import os

# Fix src/karsa/regime/domain/events.py
events_path = "src/karsa/regime/domain/events.py"
if os.path.exists(events_path):
    with open(events_path, "r") as f:
        lines = f.readlines()
    with open(events_path, "w") as f:
        for line in lines:
            if "segment_urn: str" in line and "=" not in line:
                line = line.replace("segment_urn: str", "segment_urn: str = ''")
            if "allocation_urn: str" in line and "=" not in line:
                line = line.replace("allocation_urn: str", "allocation_urn: str = ''")
            f.write(line)

# Fix src/karsa/llm/provider.py
provider_path = "src/karsa/llm/provider.py"
if os.path.exists(provider_path):
    with open(provider_path, "r") as f:
        content = f.read()
    content = content.replace("from karsa.observability.manager import ObservabilityManager", "")
    content = content.replace("obs_manager: ObservabilityManager = None", "None = None")
    with open(provider_path, "w") as f:
        f.write(content)

# Fix tests/test_state_tracking.py
state_path = "tests/test_state_tracking.py"
if os.path.exists(state_path):
    with open(state_path, "r") as f:
        content = f.read()
    content = content.replace("from karsa.observability.trace import TraceLogger", "")
    with open(state_path, "w") as f:
        f.write(content)

