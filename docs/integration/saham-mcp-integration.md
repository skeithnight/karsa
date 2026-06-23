# Saham-MCP Integration Guide

## Overview

This document describes how to integrate the **saham-mcp** MCP server with Karsa's AI agents to access Indonesian Stock Exchange (IDX) data. The saham-mcp server provides 9 tools for accessing real-time and historical data for 958 IDX-listed stocks.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Karsa AI Agents                          │
│  (Researcher Agent, CIO Dashboard, Performance Analytics)   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              SahamMCPConnector (Python)                     │
│  - JSON-RPC communication                                   │
│  - Response parsing & caching                               │
│  - Error handling & retry logic                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ subprocess
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              saham-mcp MCP Server (TypeScript)              │
│  - 9 tools for IDX data                                     │
│  - Multi-source fallback (GitHub, Yahoo Finance, Web)       │
│  - 958 stocks with historical data from 2019                │
└─────────────────────────────────────────────────────────────┘
```

## Available Tools

### 1. get_market_overview
Get IHSG index value, change, trading volume/value, market status, top gainers/losers.

**Parameters:** None

**Use Cases:**
- Market sentiment analysis
- Daily market briefing for CIO dashboard
- Portfolio benchmarking

### 2. get_stock_info
Get detailed stock information including price, ratios, and market cap.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol (e.g., BBCA, BBRI)

**Use Cases:**
- Fundamental analysis
- Valuation metrics for thesis generation
- Position sizing calculations

### 3. get_historical_data
Get historical price data from July 2019 to present (~1,200+ data points per stock).

**Parameters:**
- `ticker` (string, required): Stock ticker symbol
- `period` (string, optional, default: "1y"): Time period
  - Options: `"1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"`

**Use Cases:**
- Technical analysis
- Backtesting trading strategies
- Volatility calculations
- Historical performance attribution

### 4. get_sector_performance
Get performance data for all IDX sectors.

**Parameters:** None

**Use Cases:**
- Sector rotation analysis
- Sector-relative performance comparison
- Portfolio diversification insights

### 5. search_stocks
Search stocks by company name or ticker from 958 available stocks.

**Parameters:**
- `query` (string, required): Search query (company name or ticker)

**Use Cases:**
- Stock discovery
- Building watchlists
- Natural language stock lookup

### 6. get_stock_analysis
Get comprehensive technical analysis with indicators and recommendations.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol
- `period` (string, optional, default: "1y"): Analysis period
  - Options: `"1m", "3m", "6m", "1y", "2y", "5y"`

**Use Cases:**
- Automated technical analysis for thesis generation
- Entry/exit signal generation
- Risk assessment

### 7. compare_stocks
Compare performance across 2-5 stocks.

**Parameters:**
- `tickers` (array, required): Array of 2-5 stock ticker symbols
- `period` (string, optional, default: "1y"): Comparison period
  - Options: `"1m", "3m", "6m", "1y", "2y"`

**Use Cases:**
- Relative strength analysis
- Peer comparison for investment decisions
- Portfolio optimization

### 8. get_available_stocks
Get complete list of 958 IDX stocks with LQ45 categorization and banking sector identification.

**Parameters:** None

**Use Cases:**
- Universe definition for systematic strategies
- LQ45 index tracking
- Sector-specific stock screening

### 9. get_dataset_info
Get repository info, last update, total stocks, cache statistics, data coverage range.

**Parameters:** None

**Use Cases:**
- Data freshness verification
- System health monitoring
- Coverage reporting

## Configuration

### MCP Server Configuration

The configuration file is located at:
```
config/saham-mcp-config.json
```

Key configuration options:
- **Cache TTL**: Controls how long data is cached (market overview: 60s, stock info: 300s, historical: 86400s)
- **Timeouts**: Yahoo Finance (10s), Web scraper (15s)
- **Debug mode**: Set `IDX_MCP_DEBUG=true` for verbose logging

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `IDX_MCP_SERVER_NAME` | Server display name | `"IDX MCP Server"` |
| `IDX_MCP_LOG_LEVEL` | Log level (set to `error` for clean MCP) | - |
| `IDX_MCP_DEBUG` | Debug mode toggle | `false` |
| `IDX_MCP_CACHE_TYPE` | Cache backend | `memory` |
| `IDX_MCP_YAHOO_TIMEOUT` | Yahoo Finance timeout (ms) | `10000` |
| `IDX_MCP_WEB_TIMEOUT` | Web scraper timeout (ms) | `15000` |

## Usage Examples

### Python Integration

```python
from karsa.providers.infrastructure.connectors.saham_mcp_connector import SahamMCPConnector

# Initialize connector
connector = SahamMCPConnector()

# Get market overview
market = await connector.get_market_overview()
print(f"IHSG: {market['index_value']} ({market['change_pct']}%)")

# Get stock info
stock_info = await connector.get_stock_info("BBCA")
print(f"BBCA: Rp{stock_info['price']} | P/E: {stock_info['pe_ratio']}")

# Get historical data for analysis
historical = await connector.get_historical_data("BBCA", period="1y")
print(f"Retrieved {len(historical['data'])} data points")

# Technical analysis
analysis = await connector.get_stock_analysis("BBCA", period="6m")
print(f"Recommendation: {analysis['recommendation']}")

# Compare multiple stocks
comparison = await connector.compare_stocks(
    tickers=["BBCA", "BBRI", "BMRI"],
    period="1y"
)

# Search for stocks
results = await connector.search_stocks("bank")
print(f"Found {len(results)} bank stocks")
```

### Integration with Researcher Agent

The `SahamMCPConnector` is designed to integrate seamlessly with Karsa's `ResearcherAgentService`:

```python
from karsa.thesis.ai.application.researcher_agent import ResearcherAgentService
from karsa.providers.infrastructure.connectors.saham_mcp_connector import SahamMCPConnector

# Initialize services
saham_connector = SahamMCPConnector()
researcher = ResearcherAgentService(
    call_llm=my_llm_function,
    retrieve_context=my_rag_function,
    get_current_price=saham_connector.get_current_price,  # Use saham-mcp for price data
)

# Researcher agent can now use IDX data for thesis generation
thesis = await researcher.on_market_bar(
    ticker="BBCA",
    close_price=9500,
    sector="Banking",
)
```

### CIO Dashboard Integration

```python
# Get market overview for dashboard
market_data = await connector.get_market_overview()

# Get sector performance for sector allocation view
sector_perf = await connector.get_sector_performance()

# Get top stocks for watchlist
available = await connector.get_available_stocks()
lq45_stocks = [s for s in available if s.get("is_lq45")]
```

## Data Sources

The saham-mcp server uses a priority-based fallback architecture:

1. **GitHubDatasetSource** (Priority: HIGH)
   - Pulls from `wildangunawan/Dataset-Saham-IDX` repository
   - Coverage: 2019-2025
   - Cache TTL: 24 hours

2. **YahooFinanceSource** (Priority: HIGH)
   - Uses `yahoo-finance2` library
   - Real-time quotes and IHSG index
   - Cache TTL: 5 minutes

3. **WebScrapingSource** (Priority: MEDIUM)
   - Built with `cheerio` + `axios`
   - Fallback when primary sources fail

## Error Handling

The connector implements comprehensive error handling:

- **Retry Policy**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Timeout Handling**: Configurable timeouts per data source
- **Graceful Degradation**: Falls back to cached data when sources fail
- **Error Logging**: All errors are logged with context for debugging

## Performance Considerations

- **Target Response Time**: Sub-2-second for all queries
- **Caching**: Multi-level caching (MCP server + connector)
- **Rate Limiting**: Respect Yahoo Finance rate limits
- **Batch Operations**: Use `compare_stocks` for multi-stock queries instead of individual calls

## Troubleshooting

### JSON Parsing Errors
Set `IDX_MCP_LOG_LEVEL=error` to suppress debug output that interferes with JSON-RPC.

### Historical Data Issues
```bash
# Clear cache and test
npx @baguskto/saham clear-cache
npx @baguskto/saham test
```

### Yahoo Finance Timeouts
Increase timeout values in config or enable debug mode:
```json
{
  "env": {
    "IDX_MCP_DEBUG": "true",
    "IDX_MCP_YAHOO_TIMEOUT": "20000"
  }
}
```

### Connection Issues
Verify the MCP server is accessible:
```bash
npx @baguskto/saham --version
```

## Security Considerations

- **No API Keys Required**: saham-mcp uses public data sources
- **Data Validation**: All responses are validated before returning to callers
- **Input Sanitization**: Ticker symbols are validated against allowed patterns
- **Logging**: Sensitive data is not logged

## References

- **saham-mcp Repository**: https://github.com/baguskto/saham-mcp
- **Dataset Source**: https://github.com/wildangunawan/Dataset-Saham-IDX
- **MCP Protocol**: https://modelcontextprotocol.io
- **Karsa Architecture**: See `docs/architecture/` for system design

## Support

For issues with:
- **saham-mcp server**: https://github.com/baguskto/saham-mcp/issues
- **Karsa integration**: Contact the Karsa development team
