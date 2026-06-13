from typing import List, Dict, Any
from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot, AttributedValue

class AttributionService:
    @staticmethod
    def calculate_allocations(gross_pnl: float, currency: str, contributors: List[Dict[str, Any]], policy: PolicyInputSnapshot) -> List[AttributedValue]:
        allocations = []
        # Normalization and weighting logic based on role_weights
        targets = sorted(contributors, key=lambda x: x['target_id']) # LEXICOGRAPHICAL_TARGET_ID
        
        total_weight = 0.0
        weights = []
        for c in targets:
            role = c.get('role', 'AUTHOR')
            w = policy.role_weights.get(role, 0.0)
            total_weight += w
            weights.append(w)
            
        remaining_pnl = gross_pnl
        for i, c in enumerate(targets):
            frac = weights[i] / total_weight if total_weight > 0 else 0.0
            
            if i == len(targets) - 1:
                # Give remainder to the last person lexicographically, or first?
                # Actually, LEXICOGRAPHICAL_TARGET_ID means remainder handled deterministically.
                val = remaining_pnl
            else:
                val = round(gross_pnl * frac, policy.currency_precision)
                remaining_pnl -= val
                
            allocations.append(AttributedValue(
                target_identity=c['target_id'],
                gross_pnl=gross_pnl,
                attributed_pnl=val,
                attribution_percentage=frac,
                currency=currency
            ))
        return allocations
