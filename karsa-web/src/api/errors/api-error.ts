import { ErrorResponseDTO } from "../../types/common/error.dto";

export class ApiError extends Error {
  constructor(public statusCode: number, public payload: ErrorResponseDTO | null) {
    super(payload?.message || `API Error: ${statusCode}`);
    this.name = "ApiError";
  }
}
