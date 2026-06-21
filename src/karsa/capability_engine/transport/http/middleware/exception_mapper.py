"""Exception mapper -- Sprint-12. Wave-1.

Centralized exception-to-HTTP-status mapping.
Registers global exception handlers on the FastAPI app.

Maps:
- DomainValidationError -> 400
- ProjectionStalenessError -> 409
- OptimisticConcurrencyError -> 409
- ValueError -> 400
- Unhandled Exception -> 500
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from karsa.capability_engine.domain.exceptions import (
    EvaluationOrderingError,
    InvalidContextSnapshotError,
    InvalidEvolutionDeltaError,
    InvalidEvolutionError,
    InvalidEvolutionEvidenceError,
    InvalidHealthScoreError,
    InvalidScoreComponentError,
    ProjectionStalenessError,
)
from karsa.capability_engine.transport.http.responses.error_response import (
    ErrorResponse,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""

    # --- Domain validation errors -> 400 ---

    @app.exception_handler(InvalidEvolutionError)
    async def handle_invalid_evolution(
        request: Request, exc: InvalidEvolutionError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_EVOLUTION", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(InvalidHealthScoreError)
    async def handle_invalid_health_score(
        request: Request, exc: InvalidHealthScoreError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_HEALTH_SCORE", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(InvalidEvolutionDeltaError)
    async def handle_invalid_delta(
        request: Request, exc: InvalidEvolutionDeltaError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_EVOLUTION_DELTA", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(InvalidEvolutionEvidenceError)
    async def handle_invalid_evidence(
        request: Request, exc: InvalidEvolutionEvidenceError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_EVOLUTION_EVIDENCE", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(InvalidContextSnapshotError)
    async def handle_invalid_snapshot(
        request: Request, exc: InvalidContextSnapshotError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_CONTEXT_SNAPSHOT", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(InvalidScoreComponentError)
    async def handle_invalid_score_component(
        request: Request, exc: InvalidScoreComponentError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INVALID_SCORE_COMPONENT", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    @app.exception_handler(EvaluationOrderingError)
    async def handle_evaluation_ordering(
        request: Request, exc: EvaluationOrderingError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="EVALUATION_ORDERING_VIOLATION", message=str(exc)
        )
        return JSONResponse(status_code=400, content=body.model_dump())

    # --- Projection staleness -> 409 ---

    @app.exception_handler(ProjectionStalenessError)
    async def handle_projection_staleness(
        request: Request, exc: ProjectionStalenessError
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="PROJECTION_STALENESS", message=str(exc)
        )
        return JSONResponse(status_code=409, content=body.model_dump())

    # --- ValueError -> 400 ---

    @app.exception_handler(ValueError)
    async def handle_value_error(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        body = ErrorResponse(error_code="VALIDATION_ERROR", message=str(exc))
        return JSONResponse(status_code=400, content=body.model_dump())

    # --- Catch-all -> 500 ---

    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred",
        )
        return JSONResponse(status_code=500, content=body.model_dump())
