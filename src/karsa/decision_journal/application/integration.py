class InitiateDecisionExecutionService:
    def __init__(self, execution_client):
        self.execution_client = execution_client
        
    def handle_journal_appended(self, event):
        # Connect Decision Journal to Execution Engine
        self.execution_client.execute_intent(event.journal_urn, event.thesis_urn)
