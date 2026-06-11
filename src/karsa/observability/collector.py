from typing import Tuple, Dict

class TokenizerPlugin:
    def estimate_tokens(self, text: str) -> Tuple[int, str]:
        raise NotImplementedError

class HeuristicTokenizer(TokenizerPlugin):
    def estimate_tokens(self, text: str) -> Tuple[int, str]:
        # Simple heuristic fallback
        return max(1, len(text) // 4), "LOW"

class TiktokenFallbackTokenizer(TokenizerPlugin):
    def __init__(self):
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding("cl100k_base")
            self.available = True
        except ImportError:
            self.available = False

    def estimate_tokens(self, text: str) -> Tuple[int, str]:
        if not self.available:
            return HeuristicTokenizer().estimate_tokens(text)
        return len(self.encoder.encode(text)), "HIGH"

class TokenizerFactory:
    _plugins: Dict[str, TokenizerPlugin] = {
        "gemini-2.5-flash": TiktokenFallbackTokenizer(), # Ideally uses Gemini API, falling back to tiktoken for now
        "gemini-2.5-pro": TiktokenFallbackTokenizer(),
        "default": TiktokenFallbackTokenizer()
    }
    
    @classmethod
    def get_tokenizer(cls, model_id: str) -> TokenizerPlugin:
        plugin = cls._plugins.get(model_id, cls._plugins["default"])
        if hasattr(plugin, "available") and not plugin.available:
            return HeuristicTokenizer()
        return plugin

class TokenUsageCollector:
    @staticmethod
    def estimate_tokens(model_id: str, text: str) -> Tuple[int, str]:
        tokenizer = TokenizerFactory.get_tokenizer(model_id)
        return tokenizer.estimate_tokens(text)
