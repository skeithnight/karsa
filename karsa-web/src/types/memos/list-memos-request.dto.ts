import { PaginationRequestDTO } from "../common/pagination.dto";

export interface ListMemosRequestDTO {
  pagination: PaginationRequestDTO;
  thesis_urn?: string;
}
