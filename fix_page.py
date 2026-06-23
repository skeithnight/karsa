import re

with open("karsa-web/src/app/cio-dashboard/page.tsx", "r") as f:
    content = f.read()

# 1. Add imports
imports_to_add = """
import { DataTable } from '../../components/grid/DataTable';
import { ColDef } from 'ag-grid-community';
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '../../components/ui/chart';
"""

content = content.replace("import type {", imports_to_add + "import type {")

# 2. Add ColDefs and chartConfig
coldefs_and_config = """
const positionColumnDefs: ColDef<PositionViewModel>[] = [
  { field: 'symbol', headerName: 'Symbol', sortable: true, filter: true, flex: 1 },
  { field: 'quantityLots', headerName: 'Lots', sortable: true, valueFormatter: (p) => p.value?.toFixed(0) || '0', flex: 1 },
  { field: 'avgEntryPrice', headerName: 'Entry', sortable: true, valueFormatter: (p) => formatCurrency(p.value, 'IDR'), flex: 1 },
  { field: 'currentPrice', headerName: 'Current', sortable: true, valueFormatter: (p) => formatCurrency(p.value, 'IDR'), flex: 1 },
  { field: 'marketValueIdr', headerName: 'Mkt Value', sortable: true, valueFormatter: (p) => formatCurrency(p.value, 'IDR'), flex: 1.5 },
  { 
    field: 'unrealizedPnlIdr', 
    headerName: 'PnL', 
    sortable: true, 
    valueFormatter: (p) => formatCurrency(p.value, 'IDR'),
    cellClassRules: { 'text-emerald-600': 'x >= 0', 'text-red-600': 'x < 0' },
    flex: 1.5
  },
  { 
    field: 'unrealizedPnlPct', 
    headerName: 'PnL %', 
    sortable: true, 
    valueFormatter: (p) => p.value?.toFixed(2) + '%',
    cellClassRules: { 'text-emerald-600': 'x >= 0', 'text-red-600': 'x < 0' },
    flex: 1
  },
  { field: 'sector', headerName: 'Sector', sortable: true, filter: true, flex: 1.5 }
];

const sectorColumnDefs: ColDef[] = [
  { field: 'sectorName', headerName: 'Sector', sortable: true, filter: true, flex: 2 },
  { 
    field: 'netExposureIdr', 
    headerName: 'Net Exposure', 
    sortable: true,
    valueFormatter: (p) => formatCurrency(p.value, 'IDR'),
    cellClassRules: { 'text-emerald-600': 'x >= 0', 'text-red-600': 'x < 0' },
    flex: 1.5
  },
  { field: 'grossExposureIdr', headerName: 'Gross Exposure', sortable: true, valueFormatter: (p) => formatCurrency(p.value, 'IDR'), flex: 1.5 }
];

const chartConfig = {
  totalEquity: { label: "Equity", color: "hsl(var(--primary))" },
};

/** Tier 1: Executive Summary — 5-second comprehension */"""

content = content.replace("/** Tier 1: Executive Summary — 5-second comprehension */", coldefs_and_config)

# 3. Add Equity Curve Chart block
equity_chart_block = """      </div>

      {/* Equity Curve Chart */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Equity Curve</h3>
        {loadingEquity ? (
          <LoadingSkeleton variant="card" />
        ) : (equityCurve?.length ?? 0) > 0 ? (
          <div className="h-64 w-full">
            <ChartContainer config={chartConfig} className="h-full w-full">
              <LineChart data={equityCurve} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(val) => new Date(val).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })} 
                />
                <YAxis 
                  domain={['auto', 'auto']} 
                  tickFormatter={(val) => formatCurrency(val, 'IDR')} 
                  width={80}
                />
                <ChartTooltip content={<ChartTooltipContent labelFormatter={(val) => new Date(val).toLocaleTimeString('id-ID')} />} />
                <Line type="stepAfter" dataKey="totalEquity" stroke="var(--color-totalEquity)" strokeWidth={2} dot={false} />
              </LineChart>
            </ChartContainer>
          </div>
        ) : (
          <EmptyState title="No Data" description="Equity curve data unavailable" />
        )}
      </div>"""

content = content.replace("      </div>\n\n      {/* Open Positions Grid */}", equity_chart_block + "\n\n      {/* Open Positions Grid */}")

# 4. Replace Open Positions Grid
old_open_positions = """      {/* Open Positions Grid */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Open Positions</h3>
        {loadingPositions ? (
          <LoadingSkeleton variant="table" />
        ) : (positions?.length ?? 0) > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Symbol</th>
                  <th className="py-2 pr-4 text-right">Lots</th>
                  <th className="py-2 pr-4 text-right">Entry</th>
                  <th className="py-2 pr-4 text-right">Current</th>
                  <th className="py-2 pr-4 text-right">Mkt Value</th>
                  <th className="py-2 pr-4 text-right">PnL</th>
                  <th className="py-2 pr-4 text-right">PnL %</th>
                  <th className="py-2">Sector</th>
                </tr>
              </thead>
              <tbody>
                {positions!.map((pos) => (
                  <PositionRow key={pos.symbol} position={pos} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No Positions" description="No open positions" />
        )}
      </div>"""

new_open_positions = """      {/* Open Positions Grid */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Open Positions</h3>
        <DataTable
          rowData={positions || []}
          columnDefs={positionColumnDefs}
          isLoading={loadingPositions}
        />
      </div>"""

content = content.replace(old_open_positions, new_open_positions)

# 5. Replace Sector Exposure Grid
old_sector_exposure = """      {/* Sector Exposure */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Sector Exposure</h3>
        {loadingSectors ? (
          <LoadingSkeleton variant="table" />
        ) : (sectorExposures?.length ?? 0) > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {sectorExposures!.map((sector) => (
              <SectorCard key={sector.sectorName} sector={sector} />
            ))}
          </div>
        ) : (
          <EmptyState title="No Sector Data" description="Sector exposure unavailable" />
        )}
      </div>"""

new_sector_exposure = """      {/* Sector Exposure */}
      <div className="mt-6 border rounded-xl p-6 bg-white dark:bg-slate-900">
        <h3 className="text-lg font-semibold mb-4">Sector Exposure</h3>
        <DataTable
          rowData={sectorExposures || []}
          columnDefs={sectorColumnDefs}
          isLoading={loadingSectors}
        />
      </div>"""

content = content.replace(old_sector_exposure, new_sector_exposure)

# 6. Remove PositionRow and SectorCard components
position_row_pattern = re.compile(r"function PositionRow\(.*?return \(.*?</tr>\n  \);\n}\n", re.DOTALL)
sector_card_pattern = re.compile(r"function SectorCard\(.*?return \(.*?</div>\n  \);\n}\n", re.DOTALL)

content = position_row_pattern.sub("", content)
content = sector_card_pattern.sub("", content)

with open("karsa-web/src/app/cio-dashboard/page.tsx", "w") as f:
    f.write(content)

