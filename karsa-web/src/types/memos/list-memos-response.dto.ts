import { PaginationResponseDTO } from "../common/pagination.dto";
import { DecisionMemoDTO } from "./memo.dto";

export interface ListMemosResponseDTO {
  data: DecisionMemoDTO[];
  pagination: PaginationResponseDTO;
}
