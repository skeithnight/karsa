from .value_objects import EvaluationGrade

class ThesisEvaluationService:
    @staticmethod
    def evaluate(expected_outcome: float, actual_outcome: float, resolution_date: str) -> EvaluationGrade:
        # Simplified evaluation logic
        diff = abs(expected_outcome - actual_outcome)
        pred_score = max(0.0, 1.0 - diff)
        return EvaluationGrade(prediction_score=pred_score, investment_score=0.0, timing_score=1.0)
