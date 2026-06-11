# Cost Attribution Audit

## Sample `pricing.json` (Auto-generated fallback)
```json
{
  "gemini-2.5-flash": {
    "base_input_rate": 0.075,
    "base_output_rate": 0.3
  },
  "gemini-2.5-pro": {
    "base_input_rate": 1.25,
    "base_output_rate": 5.0
  }
}
```

## Sample `PricingRegistryEntry` (In-memory dataclass)
```python
PricingRegistryEntry(
    model_id='gemini-2.5-flash', 
    base_input_rate=0.075, 
    base_output_rate=0.3, 
    reasoning_output_rate=0.0, 
    cached_input_rate=0.0, 
    tool_call_rate=0.0
)
```

## Exact Formula Used by `CostCalculator`
```python
input_cost = (input_tokens / 1_000_000) * entry.base_input_rate
output_cost = (output_tokens / 1_000_000) * entry.base_output_rate
return input_cost + output_cost
```

## Worked Example
Given the test execution:
- `model`: `gemini-2.5-flash`
- `input_tokens`: 22
- `output_tokens`: 5

**Math:**
1. `input_cost` = `(22 / 1,000,000) * 0.075` = `0.00000165`
2. `output_cost` = `(5 / 1,000,000) * 0.3` = `0.0000015`
3. `total_cost` = `0.00000165 + 0.0000015` = `0.00000315` USD

This matches the `cost_usd` output logged in the evidence exact to 8 decimal places.
