import { SearchResultDTO } from "../../../types/search/search-result.dto";
import { SearchResponseDTO } from "../../../types/search/search-response.dto";
import { SearchResultVM, SearchVM } from "../types/viewmodels";

export function mapSearchResult(dto: SearchResultDTO): SearchResultVM {
  return {
    type: dto.type, // Could map 'WORKER' to 'ANALYST' here if needed. The DTO currently uses 'ANALYST'.
    id: dto.id,
    label: dto.label,
    route: dto.route,
  };
}

export function mapSearchResponse(dto: SearchResponseDTO): SearchVM {
  return {
    results: (dto.results ?? []).map(mapSearchResult),
  };
}
