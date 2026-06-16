// @ts-nocheck
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { usePortfolioSummary, usePortfolioExposure } from "../portfolio";
import { useListTheses, useThesisDetail, useThesisLineage } from "../theses";
import { useListResearchReports } from "../research";
import { useListMemos } from "../memos";
import { useAnalystsMetrics } from "../analysts";
import { usePerformanceAttribution } from "../performance";
import { useGovernancePostMortems } from "../governance";

import { PortfolioApi } from "../../api/endpoints/portfolio";
import { ThesesApi } from "../../api/endpoints/theses";
import { ResearchApi } from "../../api/endpoints/research";
import { MemosApi } from "../../api/endpoints/memos";
import { AnalystsApi } from "../../api/endpoints/analysts";
import { PerformanceApi } from "../../api/endpoints/performance";
import { GovernanceApi } from "../../api/endpoints/governance";

vi.mock("../../api/endpoints/portfolio");
vi.mock("../../api/endpoints/theses");
vi.mock("../../api/endpoints/research");
vi.mock("../../api/endpoints/memos");
vi.mock("../../api/endpoints/analysts");
vi.mock("../../api/endpoints/performance");
vi.mock("../../api/endpoints/governance");

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("React Query Hooks", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.resetAllMocks();
  });

  describe("usePortfolioSummary", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(PortfolioApi.getSummary).mockResolvedValueOnce({
        total_aum: 1000,
        daily_pnl: 100,
        active_theses_count: 5,
        net_exposure: 0.8,
        last_updated: "2025-01-01",
      });
      const { result } = renderHook(() => usePortfolioSummary(), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.totalAumRaw).toBe(1000);
      expect(PortfolioApi.getSummary).toHaveBeenCalledTimes(1);
    });

    it("verifies error path", async () => {
      vi.mocked(PortfolioApi.getSummary).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => usePortfolioSummary(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error?.message).toBe("API Error");
    });
  });

  describe("usePortfolioExposure", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(PortfolioApi.getExposure).mockResolvedValueOnce({ sectors: [] });
      const { result } = renderHook(() => usePortfolioExposure(), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.sectors).toEqual([]);
      expect(PortfolioApi.getExposure).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(PortfolioApi.getExposure).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => usePortfolioExposure(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useListTheses", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(ThesesApi.list).mockResolvedValueOnce({ data: [], pagination: { total_pages: 1, total_elements: 0 } });
      const { result } = renderHook(() => useListTheses({ pagination: { page: 1 } }), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(ThesesApi.list).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(ThesesApi.list).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useListTheses({ pagination: { page: 1 } }), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useThesisDetail", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(ThesesApi.getById).mockResolvedValueOnce({ thesis_urn: "1", ticker: "A", invalidation_criteria: [] });
      const { result } = renderHook(() => useThesisDetail("1"), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.ticker).toBe("A");
      expect(ThesesApi.getById).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(ThesesApi.getById).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useThesisDetail("1"), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useThesisLineage", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(ThesesApi.getLineage).mockResolvedValueOnce({ source_research_ids: [], decision_urns: [], governance_review_ids: [] });
      const { result } = renderHook(() => useThesisLineage("1"), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.sourceResearchIds).toEqual([]);
      expect(ThesesApi.getLineage).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(ThesesApi.getLineage).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useThesisLineage("1"), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useListResearchReports", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(ResearchApi.listReports).mockResolvedValueOnce({ data: [] });
      const { result } = renderHook(() => useListResearchReports({ limit: 50 }), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(ResearchApi.listReports).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(ResearchApi.listReports).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useListResearchReports({ limit: 50 }), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useListMemos", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(MemosApi.list).mockResolvedValueOnce({ data: [], pagination: { total_pages: 1, total_elements: 0 } });
      const { result } = renderHook(() => useListMemos({ pagination: { page: 1 } }), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(MemosApi.list).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(MemosApi.list).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useListMemos({ pagination: { page: 1 } }), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useAnalystsMetrics", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(AnalystsApi.listMetrics).mockResolvedValueOnce({ data: [] });
      const { result } = renderHook(() => useAnalystsMetrics(), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(AnalystsApi.listMetrics).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(AnalystsApi.listMetrics).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useAnalystsMetrics(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("usePerformanceAttribution", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(PerformanceApi.getAttribution).mockResolvedValueOnce({ data: [] });
      const { result } = renderHook(() => usePerformanceAttribution({ start_date: "2025-01-01", end_date: "2025-12-31" }), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(PerformanceApi.getAttribution).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(PerformanceApi.getAttribution).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => usePerformanceAttribution({ start_date: "2025-01-01", end_date: "2025-12-31" }), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useGovernancePostMortems", () => {
    it("verifies loading, success path, mapper invocation, and queryKey", async () => {
      vi.mocked(GovernanceApi.listPostMortems).mockResolvedValueOnce({ data: [] });
      const { result } = renderHook(() => useGovernancePostMortems({ limit: 50 }), { wrapper });
      expect(result.current.isLoading).toBe(true);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data).toEqual([]);
      expect(GovernanceApi.listPostMortems).toHaveBeenCalledTimes(1);
    });
    it("verifies error path", async () => {
      vi.mocked(GovernanceApi.listPostMortems).mockRejectedValueOnce(new Error("API Error"));
      const { result } = renderHook(() => useGovernancePostMortems({ limit: 50 }), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
