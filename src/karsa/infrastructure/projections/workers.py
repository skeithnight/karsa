class ResearchFeedbackProjectionWorker:
    def __init__(self, repo):
        self.repo = repo
        
    def handle_research_feedback(self, event):
        # Consume ResearchFeedbackCandidateCreated event and persist to query model
        self.repo.save_feedback(event.attrib_urn, event.thesis_urn)
