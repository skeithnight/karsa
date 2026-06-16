import { PaginationResponseDTO } from "../common/pagination.dto";
import { ThesisDTO } from "./thesis.dto";

export interface ListThesesResponseDTO {
  data: ThesisDTO[];
  pagination: PaginationResponseDTO;
}
