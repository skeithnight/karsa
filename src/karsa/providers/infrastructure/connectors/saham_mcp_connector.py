"""Saham-MCP Connector — IDX Stock Data via MCP Server.

Provides access to Indonesian Stock Exchange (IDX) data through the
saham-mcp MCP server. Supports 9 tools for market data, stock info,
historical data, sector performance, and technical analysis.

Data sources (priority-based fallback):
1. GitHub Dataset (wildangunawan/Dataset-Saham-IDX) - 2019-2025
2. Yahoo Finance - real-time quotes
3. Web Scraping - fallback

Usage:
    connector = SahamMCPConnector()
    market = await connector.get_market_overview()
    stock_info = await connector.get_stock_info("BBCA")
"""
import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from karsa.providers.application.connector_factory import BaseConnector, register_connector

logger = logging.getLogger(__name__)


class SahamMCPError(Exception):
    """Base exception for Saham-MCP connector errors."""
    pass


class SahamMCPServerError(SahamMCPError):
    """MCP server returned an error response."""
    pass


class SahamMCPTimeoutError(SahamMCPError):
    """MCP server request timed out."""
    pass


@register_connector("saham-mcp")
class SahamMCPConnector(BaseConnector):
    """Connector for Indonesian Stock Exchange data via saham-mcp MCP server.

    Communicates with the MCP server using JSON-RPC over subprocess.
    Provides clean Python interface for Karsa's AI agents.

    Supports 9 tools:
    - get_market_overview: IHSG index, market status, top gainers/losers
    - get_stock_info: Detailed stock information
    - get_historical_data: Historical OHLCV data (2019-present)
    - get_sector_performance: IDX sector performance
    - search_stocks: Search 958 IDX stocks
    - get_stock_analysis: Technical analysis with indicators
    - compare_stocks: Compare 2-5 stocks
    - get_available_stocks: List all 958 IDX stocks
    - get_dataset_info: Dataset metadata and statistics
    """

    # Tool name constants
    TOOL_GET_MARKET_OVERVIEW = "get_market_overview"
    TOOL_GET_STOCK_INFO = "get_stock_info"
    TOOL_GET_HISTORICAL_DATA = "get_historical_data"
    TOOL_GET_SECTOR_PERFORMANCE = "get_sector_performance"
    TOOL_SEARCH_STOCKS = "search_stocks"
    TOOL_GET_STOCK_ANALYSIS = "get_stock_analysis"
    TOOL_COMPARE_STOCKS = "compare_stocks"
    TOOL_GET_AVAILABLE_STOCKS = "get_available_stocks"
    TOOL_GET_DATASET_INFO = "get_dataset_info"

    def __init__(
        self,
        provider_id: str = "saham-mcp",
        config: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        """Initialize Saham-MCP connector.

        Args:
            provider_id: Unique identifier for this provider instance.
            config: Configuration dictionary (optional).
            credentials: Credentials dictionary (optional, not used for saham-mcp).
        """
        super().__init__(
            provider_id=provider_id,
            config=config or {},
            credentials=credentials or {},
        )
        self._server_command = self.config.get("server_command", "npx")
        self._server_args = self.config.get("server_args", ["@baguskto/saham@latest"])
        self._timeout = self.config.get("timeout", 30)  # seconds
        self._max_retries = self.config.get("max_retries", 3)
        self._retry_delay = self.config.get("retry_delay", 1.0)  # seconds
        self._request_id = 0
        self._process: Optional[subprocess.Popen] = None

    async def start(self) -> None:
        """Start the MCP server connection."""
        self._running = True
        logger.info("Saham-MCP connector starting")

        # Verify server is accessible
        try:
            await self._verify_server()
            logger.info("Saham-MCP server verified successfully")
        except Exception as e:
            logger.error("Failed to verify Saham-MCP server: %s", e)
            raise

    async def stop(self) -> None:
        """Stop the MCP server connection."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception as e:
                logger.warning("Error stopping MCP server process: %s", e)
            finally:
                self._process = None
        logger.info("Saham-MCP connector stopped")

    async def health_check(self) -> bool:
        """Check if the MCP server is healthy.

        Returns:
            True if server responds to get_dataset_info request.
        """
        try:
            result = await self.get_dataset_info()
            return result is not None and "total_stocks" in result
        except Exception as e:
            logger.warning("Health check failed: %s", e)
            return False

    async def _verify_server(self) -> None:
        """Verify the MCP server is accessible."""
        try:
            result = await self._call_tool(self.TOOL_GET_DATASET_INFO)
            if not result or "total_stocks" not in result:
                raise SahamMCPServerError("Invalid response from MCP server")
        except Exception as e:
            raise SahamMCPServerError(f"Cannot connect to MCP server: {e}")

    def _get_next_request_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call an MCP tool via JSON-RPC.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool arguments (optional).

        Returns:
            Tool result as parsed JSON.

        Raises:
            SahamMCPServerError: If server returns an error.
            SahamMCPTimeoutError: If request times out.
        """
        request_id = self._get_next_request_id()

        # Construct JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        # Execute with retry logic
        last_error = None
        for attempt in range(self._max_retries):
            try:
                result = await self._execute_jsonrpc(request)
                return result
            except SahamMCPTimeoutError as e:
                last_error = e
                logger.warning(
                    "Timeout on attempt %d/%d for %s: %s",
                    attempt + 1,
                    self._max_retries,
                    tool_name,
                    e,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
            except SahamMCPServerError as e:
                last_error = e
                logger.error("Server error for %s: %s", tool_name, e)
                raise
            except Exception as e:
                last_error = e
                logger.error("Unexpected error for %s: %s", tool_name, e)
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise SahamMCPTimeoutError(
            f"Failed after {self._max_retries} attempts: {last_error}"
        )

    async def _execute_jsonrpc(self, request: Dict[str, Any]) -> Any:
        """Execute a JSON-RPC request via subprocess.

        Args:
            request: JSON-RPC request dictionary.

        Returns:
            Parsed result from the response.

        Raises:
            SahamMCPServerError: If server returns an error.
            SahamMCPTimeoutError: If request times out.
        """
        request_json = json.dumps(request)

        try:
            # Run MCP server command with request as input
            process = await asyncio.create_subprocess_exec(
                self._server_command,
                *self._server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send request and wait for response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=request_json.encode()),
                timeout=self._timeout,
            )

            # Parse response
            response_text = stdout.decode().strip()
            if not response_text:
                error_text = stderr.decode().strip()
                raise SahamMCPServerError(
                    f"Empty response from MCP server. stderr: {error_text}"
                )

            # Handle multiple JSON responses (MCP server may send multiple lines)
            # Take the last complete JSON object
            response_lines = response_text.split('\n')
            response = None
            for line in reversed(response_lines):
                line = line.strip()
                if line:
                    try:
                        response = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue

            if response is None:
                raise SahamMCPServerError(
                    f"No valid JSON response. Raw output: {response_text[:500]}"
                )

            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise SahamMCPServerError(
                    f"MCP error {error.get('code')}: {error.get('message')}"
                )

            # Extract result
            result = response.get("result")
            if result is None:
                raise SahamMCPServerError("No result in response")

            # MCP tools return content array with text
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Extract text from first content item
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        try:
                            return json.loads(first_content["text"])
                        except json.JSONDecodeError:
                            return first_content["text"]

            return result

        except asyncio.TimeoutError:
            raise SahamMCPTimeoutError(f"Request timed out after {self._timeout}s")
        except (SahamMCPServerError, SahamMCPTimeoutError):
            raise
        except Exception as e:
            raise SahamMCPServerError(f"Failed to execute JSON-RPC: {e}")

    # ========================================================================
    # Public API Methods
    # ========================================================================

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get IHSG index value, change, trading volume/value, market status.

        Returns:
            Dictionary containing:
            - index_value: IHSG index value
            - change: Point change
            - change_pct: Percentage change
            - volume: Trading volume
            - value: Trading value
            - market_status: Market open/close status
            - top_gainers: List of top gaining stocks
            - top_losers: List of top losing stocks
            - last_updated: Timestamp of last update

        Example:
            >>> overview = await connector.get_market_overview()
            >>> print(f"IHSG: {overview['index_value']} ({overview['change_pct']}%)")
        """
        return await self._call_tool(self.TOOL_GET_MARKET_OVERVIEW)

    async def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """Get detailed stock information including price, ratios, and market cap.

        Args:
            ticker: Stock ticker symbol (e.g., "BBCA", "BBRI").

        Returns:
            Dictionary containing stock information:
            - ticker: Stock ticker
            - name: Company name
            - price: Current price
            - change: Price change
            - change_pct: Percentage change
            - volume: Trading volume
            - market_cap: Market capitalization
            - pe_ratio: Price-to-earnings ratio
            - pb_ratio: Price-to-book ratio
            - dividend_yield: Dividend yield
            - sector: Sector classification

        Example:
            >>> info = await connector.get_stock_info("BBCA")
            >>> print(f"BBCA: Rp{info['price']} | P/E: {info['pe_ratio']}")
        """
        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker must be a non-empty string")

        return await self._call_tool(
            self.TOOL_GET_STOCK_INFO,
            {"ticker": ticker.upper()},
        )

    async def get_historical_data(
        self,
        ticker: str,
        period: str = "1y",
    ) -> Dict[str, Any]:
        """Get historical price data from July 2019 to present.

        Args:
            ticker: Stock ticker symbol.
            period: Time period (default: "1y").
                Options: "1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"

        Returns:
            Dictionary containing:
            - ticker: Stock ticker
            - period: Requested period
            - data: List of OHLCV data points
            - count: Number of data points

        Example:
            >>> hist = await connector.get_historical_data("BBCA", period="1y")
            >>> print(f"Retrieved {hist['count']} data points")
        """
        valid_periods = ["1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period '{period}'. Must be one of {valid_periods}")

        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker must be a non-empty string")

        return await self._call_tool(
            self.TOOL_GET_HISTORICAL_DATA,
            {"ticker": ticker.upper(), "period": period},
        )

    async def get_sector_performance(self) -> Dict[str, Any]:
        """Get performance data for all IDX sectors.

        Returns:
            Dictionary containing sector performance data:
            - sectors: List of sectors with performance metrics
            - last_updated: Timestamp

        Example:
            >>> sectors = await connector.get_sector_performance()
            >>> for sector in sectors['sectors']:
            ...     print(f"{sector['name']}: {sector['change_pct']}%")
        """
        return await self._call_tool(self.TOOL_GET_SECTOR_PERFORMANCE)

    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search stocks by company name or ticker from 958 available stocks.

        Args:
            query: Search query (company name or ticker).

        Returns:
            List of matching stocks with:
            - ticker: Stock ticker
            - name: Company name
            - sector: Sector classification

        Example:
            >>> results = await connector.search_stocks("bank")
            >>> print(f"Found {len(results)} bank stocks")
        """
        if not query or not isinstance(query, str):
            raise ValueError("query must be a non-empty string")

        return await self._call_tool(
            self.TOOL_SEARCH_STOCKS,
            {"query": query},
        )

    async def get_stock_analysis(
        self,
        ticker: str,
        period: str = "1y",
    ) -> Dict[str, Any]:
        """Get comprehensive technical analysis with indicators and recommendations.

        Args:
            ticker: Stock ticker symbol.
            period: Analysis period (default: "1y").
                Options: "1m", "3m", "6m", "1y", "2y", "5y"

        Returns:
            Dictionary containing:
            - ticker: Stock ticker
            - period: Analysis period
            - indicators: Technical indicators (RSI, MACD, etc.)
            - recommendation: Buy/Sell/Hold recommendation
            - support_levels: Support price levels
            - resistance_levels: Resistance price levels

        Example:
            >>> analysis = await connector.get_stock_analysis("BBCA", period="6m")
            >>> print(f"Recommendation: {analysis['recommendation']}")
        """
        valid_periods = ["1m", "3m", "6m", "1y", "2y", "5y"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period '{period}'. Must be one of {valid_periods}")

        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker must be a non-empty string")

        return await self._call_tool(
            self.TOOL_GET_STOCK_ANALYSIS,
            {"ticker": ticker.upper(), "period": period},
        )

    async def compare_stocks(
        self,
        tickers: List[str],
        period: str = "1y",
    ) -> Dict[str, Any]:
        """Compare performance across 2-5 stocks.

        Args:
            tickers: List of 2-5 stock ticker symbols.
            period: Comparison period (default: "1y").
                Options: "1m", "3m", "6m", "1y", "2y"

        Returns:
            Dictionary containing:
            - stocks: List of stock performance data
            - comparison_metrics: Comparative metrics
            - period: Comparison period

        Example:
            >>> comparison = await connector.compare_stocks(
            ...     tickers=["BBCA", "BBRI", "BMRI"],
            ...     period="1y"
            ... )
        """
        valid_periods = ["1m", "3m", "6m", "1y", "2y"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period '{period}'. Must be one of {valid_periods}")

        if not tickers or not isinstance(tickers, list):
            raise ValueError("tickers must be a non-empty list")

        if len(tickers) < 2 or len(tickers) > 5:
            raise ValueError("tickers must contain 2-5 items")

        # Normalize tickers to uppercase
        normalized_tickers = [t.upper() for t in tickers]

        return await self._call_tool(
            self.TOOL_COMPARE_STOCKS,
            {"tickers": normalized_tickers, "period": period},
        )

    async def get_available_stocks(self) -> List[Dict[str, Any]]:
        """Get complete list of 958 IDX stocks with LQ45 categorization.

        Returns:
            List of stocks with:
            - ticker: Stock ticker
            - name: Company name
            - sector: Sector classification
            - is_lq45: Whether stock is in LQ45 index
            - is_banking: Whether stock is in banking sector

        Example:
            >>> stocks = await connector.get_available_stocks()
            >>> lq45 = [s for s in stocks if s.get("is_lq45")]
            >>> print(f"Total: {len(stocks)} | LQ45: {len(lq45)}")
        """
        return await self._call_tool(self.TOOL_GET_AVAILABLE_STOCKS)

    async def get_dataset_info(self) -> Dict[str, Any]:
        """Get repository info, last update, total stocks, cache statistics.

        Returns:
            Dictionary containing:
            - repository: Source repository URL
            - last_update: Last data update timestamp
            - total_stocks: Total number of stocks (958)
            - cache_stats: Cache hit/miss statistics
            - data_coverage: Date range (2019-2025)

        Example:
            >>> info = await connector.get_dataset_info()
            >>> print(f"Total stocks: {info['total_stocks']}")
            >>> print(f"Coverage: {info['data_coverage']}")
        """
        return await self._call_tool(self.TOOL_GET_DATASET_INFO)

    # ========================================================================
    # Convenience Methods for Researcher Agent
    # ========================================================================

    async def get_current_price(self, ticker: str) -> float:
        """Get current price for a ticker.

        Convenience method for integration with ResearcherAgentService.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Current price as float.

        Example:
            >>> price = await connector.get_current_price("BBCA")
            >>> print(f"BBCA price: Rp{price:,.0f}")
        """
        info = await self.get_stock_info(ticker)
        price = info.get("price", 0.0)

        # Handle string price with currency formatting
        if isinstance(price, str):
            # Remove currency symbols and thousands separators
            price = price.replace("Rp", "").replace(",", "").strip()
            try:
                price = float(price)
            except ValueError:
                logger.warning("Could not parse price '%s' for %s", info.get("price"), ticker)
                price = 0.0

        return float(price)

    async def get_ticker_technical_summary(self, ticker: str) -> str:
        """Get a formatted technical summary for a ticker.

        Useful for including in LLM prompts for thesis generation.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Formatted string with key technical metrics.

        Example:
            >>> summary = await connector.get_ticker_technical_summary("BBCA")
            >>> print(summary)
            # Outputs formatted technical analysis summary
        """
        try:
            info = await self.get_stock_info(ticker)
            analysis = await self.get_stock_analysis(ticker, period="6m")

            summary_parts = [
                f"## {ticker} Technical Summary",
                f"- Price: Rp{info.get('price', 'N/A'):,}",
                f"- Change: {info.get('change_pct', 'N/A')}%",
                f"- P/E Ratio: {info.get('pe_ratio', 'N/A')}",
                f"- Market Cap: Rp{info.get('market_cap', 'N/A'):,}",
                f"- Recommendation: {analysis.get('recommendation', 'N/A')}",
            ]

            # Add key indicators if available
            indicators = analysis.get("indicators", {})
            if indicators:
                summary_parts.append("- Key Indicators:")
                for key, value in indicators.items():
                    if isinstance(value, (int, float)):
                        summary_parts.append(f"  - {key}: {value:.2f}")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.error("Failed to get technical summary for %s: %s", ticker, e)
            return f"## {ticker}\n- Data unavailable: {str(e)}"

    async def get_market_context(self) -> str:
        """Get formatted market context for LLM prompts.

        Returns:
            Formatted string with market overview and sector performance.

        Example:
            >>> context = await connector.get_market_context()
            >>> # Include in researcher agent prompt
        """
        try:
            overview = await self.get_market_overview()
            sectors = await self.get_sector_performance()

            context_parts = [
                "## IDX Market Context",
                f"- IHSG: {overview.get('index_value', 'N/A')} ({overview.get('change_pct', 'N/A')}%)",
                f"- Market Status: {overview.get('market_status', 'N/A')}",
                f"- Volume: {overview.get('volume', 'N/A'):,}",
                "",
                "### Top Gainers",
            ]

            # Add top gainers
            for stock in overview.get("top_gainers", [])[:3]:
                context_parts.append(
                    f"- {stock.get('ticker')}: +{stock.get('change_pct')}%"
                )

            context_parts.append("")
            context_parts.append("### Top Losers")
            for stock in overview.get("top_losers", [])[:3]:
                context_parts.append(
                    f"- {stock.get('ticker')}: {stock.get('change_pct')}%"
                )

            # Add sector highlights
            context_parts.append("")
            context_parts.append("### Sector Performance")
            for sector in sectors.get("sectors", [])[:5]:
                context_parts.append(
                    f"- {sector.get('name')}: {sector.get('change_pct')}%"
                )

            return "\n".join(context_parts)

        except Exception as e:
            logger.error("Failed to get market context: %s", e)
            return f"## IDX Market Context\n- Data unavailable: {str(e)}"
