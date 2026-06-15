class ThesisError(Exception):
    pass

class LineageCycleError(ThesisError):
    pass

class InvalidLifecycleTransitionError(ThesisError):
    pass
