# Tokenization Audit

## Implementation (`src/karsa/observability/collector.py`)

```python
class TokenUsageCollector:
    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Simple heuristic: ~4 chars per token
        # In a real implementation, this would use tiktoken or similar
        return max(1, len(text) // 4)
```

## Exact Token Counting Approach
The implemented approach is a **pure heuristic**. It divides the total string length (characters) by 4 and enforces a minimum of 1 token. 

## Heuristic vs Provider Based
- **Is it heuristic?** Yes.
- **Is it provider tokenizer based?** No.

## Limitations
1. **Mathematical Inaccuracy**: Different providers (OpenAI `tiktoken`, Anthropic, Gemini) tokenize whitespace, special characters, and non-English text entirely differently. Dividing characters by 4 is wildly inaccurate for code (which is dense in symbols) and non-Latin scripts.
2. **Pre-flight Governance Failure**: Since `TokenUsageCollector` doesn't use the exact tokenizer of the target model, the Governance Engine's pessimistic estimates will frequently drift from the actual billed amount, causing soft budgets to be breached silently.
