export interface PaginationRequestDTO {
  page: number;
  size: number;
}

export interface PaginationResponseDTO {
  total_elements: number;
  total_pages: number;
}
