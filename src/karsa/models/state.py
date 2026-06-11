from enum import Enum

class WorkflowState(str, Enum):
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    ARCHITECTURE = "ARCHITECTURE"
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"
    IMPLEMENTATION = "IMPLEMENTATION"
    RELEASE = "RELEASE"
    DONE = "DONE"
