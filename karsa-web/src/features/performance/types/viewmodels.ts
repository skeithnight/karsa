export interface AttributionVM {
  dateRaw: string;
  dateDisplay: string;
  selectionReturnRaw: number;
  selectionReturnDisplay: string;
  allocationReturnRaw: number;
  allocationReturnDisplay: string;
  betaReturnRaw: number;
  betaReturnDisplay: string;
}

export interface PerformanceAttributionVM {
  data: AttributionVM[];
}
