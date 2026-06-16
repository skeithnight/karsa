import { PostMortemDTO } from "./post-mortem.dto";

export interface ListPostMortemsResponseDTO {
  data: PostMortemDTO[];
  next_cursor?: string;
}
