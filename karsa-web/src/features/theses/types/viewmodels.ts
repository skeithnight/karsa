import { StatusBadge } from "../../../lib/formatters/status";

export interface ThesisVM {
  thesisUrn: string;
  ticker: string;
  direction: string;
  stateRaw: string;
  stateBadge: StatusBadge;
  convictionScoreRaw: number;
  convictionScoreDisplay: string;
  expectedHorizonDaysRaw: number;
  expectedHorizonDaysDisplay: string;
}

export interface ListThesesVM {
  data: ThesisVM[];
  totalPages: number;
  totalElements: number;
}

export interface ThesisDetailVM {
  thesisUrn: string;
  ticker: string;
  invalidationCriteria: string[];
}

export interface ThesisLineageVM {
  sourceResearchIds: string[];
  decisionUrns: string[];
  governanceReviewIds: string[];
}
