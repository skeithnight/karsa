import { StatusBadge } from "../../../lib/formatters/status";

export interface ThesisVM {
  urn: string;
  title: string;
  status: string;
  confidence: number;
  version: number;
  author_urn: string;
  regime_urn: string;
}

export interface ListThesesVM {
  data: ThesisVM[];
  totalPages: number;
  totalElements: number;
}

export interface AssumptionVM {
  urn: string;
  statement: string;
  is_valid?: boolean;
}

export interface ThesisDetailVM {
  urn: string;
  current_snapshot_urn: string;
  title: string;
  summary: string;
  rationale: string;
  confidence: number;
  author_urn: string;
  regime_urn: string;
  status: string;
  version: number;
  assumptions: AssumptionVM[];
}

export interface ThesisLineageVM {
  sourceResearchIds: string[];
  decisionUrns: string[];
  governanceReviewIds: string[];
}
