import { PaginationRequestDTO } from "../common/pagination.dto";
import { ThesisFilterDTO } from "./thesis-filter.dto";
import { ThesisSortDTO } from "./thesis-sort.dto";

export interface ListThesesRequestDTO {
  pagination: PaginationRequestDTO;
  filter?: ThesisFilterDTO;
  sort?: ThesisSortDTO;
}
