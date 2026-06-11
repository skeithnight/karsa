import json
from pathlib import Path
from typing import Dict, Optional
from karsa.domain.models import PricingRegistryEntry

class PricingRegistry:
    def __init__(self, global_pricing_file: Path):
        self.pricing_file = global_pricing_file
        self.entries: Dict[str, PricingRegistryEntry] = {}
        self._load()

    def _load(self):
        if not self.pricing_file.exists():
            default_data = {
                "gemini-2.5-flash": {
                    "base_input_rate": 0.075,
                    "base_output_rate": 0.30,
                },
                "gemini-2.5-pro": {
                    "base_input_rate": 1.25,
                    "base_output_rate": 5.00,
                }
            }
            self.pricing_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pricing_file, "w") as f:
                json.dump(default_data, f, indent=2)
                
        with open(self.pricing_file, "r") as f:
            data = json.load(f)
            for model_id, rates in data.items():
                self.entries[model_id] = PricingRegistryEntry(
                    model_id=model_id,
                    base_input_rate=rates.get("base_input_rate", 0.0),
                    base_output_rate=rates.get("base_output_rate", 0.0),
                    reasoning_output_rate=rates.get("reasoning_output_rate", 0.0),
                    cached_input_rate=rates.get("cached_input_rate", 0.0),
                    tool_call_rate=rates.get("tool_call_rate", 0.0)
                )

    def get_entry(self, model_id: str) -> Optional[PricingRegistryEntry]:
        if model_id in self.entries:
            return self.entries[model_id]
        for key in self.entries.keys():
            if key in model_id:
                return self.entries[key]
        return None

class CostCalculator:
    def __init__(self, registry: PricingRegistry):
        self.registry = registry

    def calculate_usd(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        entry = self.registry.get_entry(model_id)
        if not entry:
            return 0.0
            
        input_cost = (input_tokens / 1_000_000) * entry.base_input_rate
        output_cost = (output_tokens / 1_000_000) * entry.base_output_rate
        return input_cost + output_cost
