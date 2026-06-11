from karsa.llm.client import LLMClient
from karsa.artifacts.manager import ArtifactManager

class ProductEngineerAgent:
    def __init__(self, llm_client: LLMClient, artifact_manager: ArtifactManager):
        self.llm = llm_client
        self.artifacts = artifact_manager

    def draft_design(self, idea: str):
        # 1. Vision
        vision_sys = (
            "You are a pragmatic CTO. Draft a precise markdown VISION document based on the idea.\n"
            "You MUST include the following sections exactly:\n"
            "- A specific problem statement\n"
            "- Target users\n"
            "- Goals\n"
            "- Non-goals\n"
            "- Success criteria\n"
            "Think deeply about the business value and avoid superficial statements. Output only markdown."
        )
        vision = self.llm.generate_with_obs(agent_name="ProductEngineerAgent", prompt=idea, system_prompt=vision_sys)
        self.artifacts.write_artifact("docs/vision/VISION.md", vision)

        # 2. Architecture
        arch_sys = (
            "You are an Enterprise Architect. Draft a simple, pragmatic markdown ARCHITECTURE document.\n"
            "You MUST include the following sections exactly:\n"
            "- Concrete architecture choices\n"
            "- Rationale\n"
            "- Tradeoffs\n"
            "- Components\n"
            "- Data flow\n"
            "Justify your decisions carefully. Output only markdown."
        )
        architecture = self.llm.generate_with_obs(agent_name="ProductEngineerAgent", prompt=f"Idea: {idea}\n\nVision:\n{vision}", system_prompt=arch_sys)
        self.artifacts.write_artifact("docs/architecture/ARCHITECTURE.md", architecture)

        # 3. Implementation Plan
        impl_sys = (
            "You are a Tech Lead. Draft a step-by-step IMPLEMENTATION_PLAN.\n"
            "You MUST include the following sections exactly:\n"
            "- Delivery phases\n"
            "- Real milestones\n"
            "- Actionable tasks\n"
            "Ensure the plan is realistic for a small team. Output only markdown."
        )
        implementation = self.llm.generate_with_obs(
            agent_name="ProductEngineerAgent",
            prompt=f"Idea: {idea}\n\nVision:\n{vision}\n\nArchitecture:\n{architecture}",
            system_prompt=impl_sys
        )
        self.artifacts.write_artifact("docs/implementation/IMPLEMENTATION_PLAN.md", implementation)

    def revise_design(self, unresolved_issues: str, cycle: int):
        idea = self.artifacts.read_artifact(".karsa/state.json")
        vision = self.artifacts.read_artifact("docs/vision/VISION.md")
        architecture = self.artifacts.read_artifact("docs/architecture/ARCHITECTURE.md")
        implementation = self.artifacts.read_artifact("docs/implementation/IMPLEMENTATION_PLAN.md")

        system_prompt = (
            "You are a Pragmatic CTO and Tech Lead. "
            "You have received a list of unresolved issues from the ReviewAgent. "
            "Your task is to revise the VISION, ARCHITECTURE, and IMPLEMENTATION_PLAN specifically targeting these issues. "
            "CRITICAL: Preserve existing content! Minimize unnecessary edits. Produce targeted changes only for the reported issues. "
            "Do NOT summarize. You MUST provide the FULL revised content for each document. "
            "Output MUST be in Markdown and contain three distinct sections separated by '---':\n"
            "Section 1: The updated VISION (must retain A specific problem statement, Target users, Goals, Non-goals, Success criteria).\n"
            "Section 2: The updated ARCHITECTURE (must retain Concrete architecture choices, Rationale, Tradeoffs, Components, Data flow).\n"
            "Section 3: The updated IMPLEMENTATION_PLAN (must retain Delivery phases, Real milestones, Actionable tasks)."
        )
        
        prompt = (
            f"Here are the unresolved issues to fix:\n\n{unresolved_issues}\n\n"
            "Here are the current artifacts:\n\n"
            f"=== VISION ===\n{vision}\n\n"
            f"=== ARCHITECTURE ===\n{architecture}\n\n"
            f"=== IMPLEMENTATION PLAN ===\n{implementation}"
        )

        revised_content = self.llm.generate_with_obs(agent_name="ProductEngineerAgent", prompt=prompt, system_prompt=system_prompt)
        
        # Save the revision log
        self.artifacts.write_artifact(f"docs/revisions/REVISION_{cycle:03d}.md", revised_content)
        
        # Split and update the original artifacts. In a real system, we'd parse properly.
        # For MVP, we can ask for a specific delimiter or just assume the LLM splits it by '---'
        parts = revised_content.split('---')
        if len(parts) >= 3:
            self.artifacts.write_artifact("docs/vision/VISION.md", parts[0].strip())
            self.artifacts.write_artifact("docs/architecture/ARCHITECTURE.md", parts[1].strip())
            self.artifacts.write_artifact("docs/implementation/IMPLEMENTATION_PLAN.md", parts[2].strip())
        else:
            # Fallback if the LLM doesn't follow the exact '---' splitting format
            self.artifacts.write_artifact("docs/vision/VISION.md", revised_content)
