import abc
import os
import time
from karsa.observability.manager import ObservabilityManager

class LLMClient(abc.ABC):
    def __init__(self, obs_manager: ObservabilityManager = None):
        self.obs = obs_manager

    def generate_with_obs(self, agent_name: str, prompt: str, system_prompt: str = "") -> str:
        start_time = time.time()
        if self.obs:
            self.obs.log_trace(f"{agent_name}Started")
            self.obs.log_trace("LLMRequestStarted")
            self.obs.log_execution(agent_name, "START", "RUNNING", 0)
        
        try:
            response = self.generate(prompt, system_prompt)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if self.obs:
                self.obs.log_trace("LLMResponseReceived")
                self.obs.log_execution(agent_name, "COMPLETE", "SUCCESS", duration_ms)
                self.obs.record_execution(
                    agent=agent_name,
                    model=getattr(self, "model_name", "unknown"),
                    duration_ms=duration_ms,
                    status="SUCCESS",
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response=response
                )
                self.obs.track_timeline(agent_name, duration_ms)
                self.obs.log_trace(f"{agent_name}Completed")
            return response
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if self.obs:
                self.obs.log_execution(agent_name, "FAILED", "ERROR", duration_ms)
                self.obs.record_execution(
                    agent=agent_name,
                    model=getattr(self, "model_name", "unknown"),
                    duration_ms=duration_ms,
                    status="ERROR",
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response=str(e)
                )
            raise e

    @abc.abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass

class MockLLMClient(LLMClient):
    def __init__(self, obs_manager: ObservabilityManager = None):
        super().__init__(obs_manager)
        self.model_name = "mock-llm"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        sys_upper = system_prompt.upper()
        if "VISION" in sys_upper and "ARCHITECTURE" not in sys_upper:
            return f"# Vision\n\n## A specific problem statement\nMock problem.\n\n## Target users\nMock users.\n\n## Goals\nMock goals.\n\n## Non-goals\nMock non goals.\n\n## Success criteria\nMock criteria for: {prompt}"
        elif "ARCHITECTURE" in sys_upper and "VISION" in sys_upper and "TECH LEAD" not in sys_upper:
            return f"# Architecture\n\n## Concrete architecture choices\nMock choices.\n\n## Rationale\nMock rationale.\n\n## Tradeoffs\nMock tradeoffs.\n\n## Components\nMock components.\n\n## Data flow\nMock flow for: {prompt}"
        elif "REVISE" in sys_upper:
            return (
                "# Vision\n## A specific problem statement\nRevised problem.\n## Target users\nRevised users.\n## Goals\nRevised goals.\n## Non-goals\nRevised non-goals.\n## Success criteria\nRevised criteria.\n---\n"
                "# Architecture\n## Concrete architecture choices\nRevised choices.\n## Rationale\nRevised rationale.\n## Tradeoffs\nRevised tradeoffs.\n## Components\nRevised components.\n## Data flow\nRevised data flow.\n---\n"
                "# Implementation Plan\n## Delivery phases\nRevised phases.\n## Real milestones\nRevised milestones.\n## Actionable tasks\nRevised tasks."
            )
        elif "IMPLEMENTATION_PLAN" in sys_upper or "TECH LEAD" in sys_upper:
            return f"# Implementation Plan\n\n## Delivery phases\nMock phases.\n\n## Real milestones\nMock milestones.\n\n## Actionable tasks\nMock tasks for: {prompt}"
        elif "REVIEWER" in sys_upper or "SKEPTICAL" in sys_upper or "VERIFICATION" in sys_upper:
            if "unresolved" in prompt.lower() or "revised" in prompt.lower():
                return (
                    "# Review Result\n\nOutcome:\nAPPROVE\n\n"
                    "# Existing Issues\n"
                    "Issue: P001\nStatus: RESOLVED\n\n"
                    "# New Issues\n\n"
                    "# Summary\n\n"
                    "Open Blocking Issues: 0\n"
                    "Open Non Blocking Issues: 0\n\n"
                    "# Confidence\n0.95"
                )
            return (
                "# Review Result\n\nOutcome:\nREJECT\n\n"
                "# Existing Issues\n\n"
                "# New Issues\n\n"
                "Issue: A001\nSeverity: BLOCKING\n\nDescription:\nThe Problem definition lacks measurable goals.\n\nEvidence:\nNo numbers.\n\n"
                "# Summary\n\n"
                "Open Blocking Issues: 1\n"
                "Open Non Blocking Issues: 0\n\n"
                "# Confidence\n0.85"
            )
        return f"Mock response for: {prompt}"

class GeminiClient(LLMClient):
    def __init__(self, obs_manager: ObservabilityManager = None, pool=None):
        super().__init__(obs_manager)
        self.model_name = "gemini-2.5-flash"
        self.pool = pool
        self.current_key_fingerprint = None
        # Wire pool trace events to observability
        if self.pool and self.obs:
            self.pool.trace_fn = self.obs.log_trace

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.pool:
            raise Exception("No ProviderPool configured")
            
        provider_key = self.pool.get_next_key()
        if not provider_key:
            raise Exception("429 QUOTA_EXHAUSTED: All keys suspended")
            
        self.current_key_fingerprint = provider_key.fingerprint
        import google.genai
        client = google.genai.Client(api_key=provider_key.key)
        
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"system_instruction": system_prompt}
            )
            self.pool.mark_success(provider_key)
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            is_quota = "429" in error_msg or "quota" in error_msg
            self.pool.mark_failure(provider_key, is_quota=is_quota)
            raise e
