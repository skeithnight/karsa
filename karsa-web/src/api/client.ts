import { ApiError } from "./errors/api-error";
import { ErrorResponseDTO } from "../types/common/error.dto";

export class ApiClient {
  private static baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  static async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = (await response.json().catch(() => null)) as ErrorResponseDTO | null;
      throw new ApiError(response.status, errorData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json() as Promise<T>;
  }
}
