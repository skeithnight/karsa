export interface SearchResultVM {
  type: string;
  id: string;
  label: string;
  route: string;
}

export interface SearchVM {
  results: SearchResultVM[];
}
