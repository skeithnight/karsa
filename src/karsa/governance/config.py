import hashlib
import json
from pathlib import Path
from karsa.domain.models import GovernancePolicy, GovernancePolicySnapshot

class ConfigurationLoader:
    def __init__(self, config_path: Path = Path("karsa.toml")):
        self.config_path = config_path
        
    def _parse_toml(self, text: str) -> dict:
        # A minimal TOML parser just for our governance limits to avoid external dependencies
        # if `tomllib` is not available (only in 3.11+). 
        # Using basic parsing for flat dict.
        res = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                try:
                    res[k] = float(v) if "." in v else int(v)
                except ValueError:
                    res[k] = v
        return res

    def load_policy(self) -> GovernancePolicy:
        if not self.config_path.exists():
            return GovernancePolicy() # Default empty limits (0 means no limit for this implementation, or infinite)
            
        with open(self.config_path, "r") as f:
            content = f.read()
            data = self._parse_toml(content)
            
        return GovernancePolicy(
            max_workflow_cost=data.get("max_workflow_cost", 0.0),
            max_workflow_tokens=data.get("max_workflow_tokens", 0),
            max_review_cycles=data.get("max_review_cycles", 0),
            max_cycle_cost=data.get("max_cycle_cost", 0.0)
        )
        
    def create_snapshot(self, version: str = "1.0") -> GovernancePolicySnapshot:
        policy = self.load_policy()
        
        # Calculate Hash
        policy_dict = {
            "max_workflow_cost": policy.max_workflow_cost,
            "max_workflow_tokens": policy.max_workflow_tokens,
            "max_review_cycles": policy.max_review_cycles,
            "max_cycle_cost": policy.max_cycle_cost
        }
        policy_str = json.dumps(policy_dict, sort_keys=True)
        policy_hash = hashlib.sha256(policy_str.encode("utf-8")).hexdigest()
        
        return GovernancePolicySnapshot(
            policy_version=version,
            policy_hash=policy_hash,
            max_workflow_cost=policy.max_workflow_cost,
            max_workflow_tokens=policy.max_workflow_tokens,
            max_review_cycles=policy.max_review_cycles,
            max_cycle_cost=policy.max_cycle_cost
        )
