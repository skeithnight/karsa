from karsa.llm.client import LLMClient
from karsa.artifacts.manager import ArtifactManager

class ReviewAgent:
    def __init__(self, llm_client: LLMClient, artifact_manager: ArtifactManager):
        self.llm = llm_client
        self.artifacts = artifact_manager

    def review_design(self, cycle: int = 1, active_issues_text: str = ""):
        vision = self.artifacts.read_artifact("docs/vision/VISION.md")
        architecture = self.artifacts.read_artifact("docs/architecture/ARCHITECTURE.md")
        implementation = self.artifacts.read_artifact("docs/implementation/IMPLEMENTATION_PLAN.md")

        if cycle == 1:
            mode_instructions = (
                "MODE: DISCOVERY REVIEW\n"
                "You are an independent, skeptical, and hostile Staff Engineer, Principal Architect, QA Lead, "
                "Product Reviewer, and Operations Reviewer. Your goal is to find flaws. Do NOT be a helpful assistant. "
                "Evaluate the provided artifacts from multiple perspectives:\n\n"
                "1. Product Review: Clear problem? Measurable goals? Non-goals? Realistic scope? Identify missing requirements, scope creep, ambiguity.\n"
                "2. Architecture Review: Too complex? Too simple? Scalability risks? Maintainability risks? Identify over/under-engineering, hidden assumptions.\n"
                "3. Feasibility Review: Can one engineer build this? Realistic timeline/dependencies? Identify unrealistic expectations.\n"
                "4. Cost Review: Infra/API/Operational costs? Identify hidden expenses and budget risks.\n"
                "5. Operations Review: Monitoring, Backup, Recovery, Deployment? Identify blind spots.\n"
                "6. Governance Review: Are major decisions documented? Assumptions explicit? Risks tracked? Identify gaps.\n\n"
            )
        else:
            mode_instructions = (
                "MODE: VERIFICATION & REGRESSION REVIEW (ISSUE FREEZE IN EFFECT)\n"
                "You are an independent Staff Engineer. The project is under strict ISSUE FREEZE.\n"
                "Your PRIMARY objective is to verify if the following active issues have been resolved by the author's recent changes:\n"
                f"{active_issues_text}\n\n"
                "CONSTRAINTS:\n"
                "1. You MUST NOT open new issues for flaws that existed in previous versions but were missed.\n"
                "2. You MAY ONLY open new issues if they are direct REGRESSIONS caused by the recent changes.\n"
                "3. Evaluate the active issues and update their status to RESOLVED, PARTIALLY_RESOLVED, OPEN, or REOPENED.\n\n"
            )

        system_prompt = (
            f"{mode_instructions}"
            "IMPORTANT: Your review MUST contain specific findings tied directly to the generated artifacts. Generic reviews are NOT acceptable. "
            "Quote or reference specific sections.\n\n"
            "Output MUST be in Markdown with the following exact structure:\n"
            "# Review Result\n\n"
            "Outcome:\n(APPROVE, APPROVE_WITH_CHANGES, or REJECT)\n\n"
            "# Existing Issues\n\n"
            "(For each previously reported issue that you are re-reviewing, output:\n"
            "Issue: [ID]\nStatus: [OPEN or PARTIALLY_RESOLVED or RESOLVED or REOPENED]\n)\n\n"
            "# New Issues\n\n"
            "(For each newly discovered issue (ONLY if cycle 1 or a regression), output:\n"
            "Issue: [Any ID]\n"
            "Severity: [BLOCKING or NON_BLOCKING]\n\n"
            "Description:\n[Clear description. If cycle > 1, state why this is a regression]\n\n"
            "Evidence:\n[Specific quotes or references]\n)\n\n"
            "# Summary\n\n"
            "Open Blocking Issues: [Count]\n"
            "Open Non Blocking Issues: [Count]\n\n"
            "# Confidence\n"
            "[Float between 0.0 and 1.0]"
        )

        prompt = (
            "Here are the artifacts to review:\n\n"
            f"=== VISION.md ===\n{vision}\n\n"
            f"=== ARCHITECTURE.md ===\n{architecture}\n\n"
            f"=== IMPLEMENTATION_PLAN.md ===\n{implementation}"
        )

        review = self.llm.generate_with_obs(agent_name="ReviewAgent", prompt=prompt, system_prompt=system_prompt)
        
        import re
        outcome = "REJECT"
        match = re.search(r'Outcome:\s*(APPROVE_WITH_CHANGES|APPROVE|REJECT)', review)
        if match:
            outcome = match.group(1)
            
        return outcome, review
