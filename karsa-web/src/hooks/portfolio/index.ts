import { ApiError } from "../../api/errors/api-error";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../query-keys";
import { PortfolioApi } from "../../api/endpoints/portfolio";
import { mapPortfolioSummary, mapPortfolioExposure } from "../../features/portfolio/utils/mappers";
import { PortfolioSummaryVM, PortfolioExposureVM } from "../../features/portfolio/types/viewmodels";

export function usePortfolioSummary() {
  return useQuery<PortfolioSummaryVM, ApiError>({
    queryKey: queryKeys.portfolio.summary(),
    queryFn: () => PortfolioApi.getSummary().then(mapPortfolioSummary),
    staleTime: 60 * 1000,
  });
}

export function usePortfolioExposure() {
  return useQuery<PortfolioExposureVM, ApiError>({
    queryKey: queryKeys.portfolio.exposure(),
    queryFn: () => PortfolioApi.getExposure().then(mapPortfolioExposure),
    staleTime: 5 * 60 * 1000,
  });
}
