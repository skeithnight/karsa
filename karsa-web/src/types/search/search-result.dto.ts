export interface SearchResultDTO {
  type: "THESIS" | "RESEARCH" | "ANALYST" | "TICKER";
  id: string;
  label: string;
  route: string;
}
