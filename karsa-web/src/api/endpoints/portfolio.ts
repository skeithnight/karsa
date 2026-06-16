import { ApiClient } from "../client";
import { PortfolioSummaryResponseDTO } from "../../types/portfolio/portfolio-summary-response.dto";
import { PortfolioExposureResponseDTO } from "../../types/portfolio/portfolio-exposure-response.dto";

export const PortfolioApi = {
  getSummary: (): Promise<PortfolioSummaryResponseDTO> => {
    return ApiClient.fetch<PortfolioSummaryResponseDTO>("/portfolio/summary");
  },
  getExposure: (): Promise<PortfolioExposureResponseDTO> => {
    return ApiClient.fetch<PortfolioExposureResponseDTO>("/portfolio/exposure");
  }
};
