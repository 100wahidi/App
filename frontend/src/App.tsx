import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, CheckCircle, Database, FileSearch, RefreshCw, Upload, XCircle } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type KpiResult = {
  global_quality_completeness: number;
  global_quality_validity: number;
  specific_col_quality_completeness: Record<string, number>;
  specific_col_quality_validity: Record<string, number>;
};

type FailureCase = {
  column: string;
  index: number;
  value: string | null;
  consistency_pct: number;
};

type ColumnAnalysis = {
  column: string;
  error_count: number;
  status: "OK" | "Warning" | "Critical";
};

type DeadKriAlert = {
  kri_value: string | null;
  last_calculated_date: string | null;
  alert_type: string;
};

type EvoRow = Record<string, string | number>;

type ReportingResponse = {
  file_name: string;
  total_rows: number;
  total_columns: number;
  generated_at: string;
  global_score: number;
  kpis: KpiResult;
  consistency_issues: FailureCase[];
  column_analysis: ColumnAnalysis[];
  failure_cases: FailureCase[];
  accuracy_issues: Record<string, unknown>;
  dead_kri_alerts: DeadKriAlert[];
  kri_distribution_evolution: EvoRow[];
};

// ─── Colour helpers ───────────────────────────────────────────────────────────

function scoreColor(v: number) {
  if (v >= 80) return "text-emerald-600";
  if (v >= 60) return "text-amber-500";
  return "text-rose-600";
}

function scoreBg(v: number) {
  if (v >= 80) return "bg-emerald-50 border-emerald-200";
  if (v >= 60) return "bg-amber-50 border-amber-200";
  return "bg-rose-50 border-rose-200";
}

const STATUS_BADGE: Record<string, string> = {
  OK: "bg-emerald-100 text-emerald-700",
  Warning: "bg-amber-100 text-amber-700",
  Critical: "bg-rose-100 text-rose-700",
};

const CHART_COLORS = ["#e11d48", "#1f2937", "#334155", "#f43f5e", "#475569", "#be123c", "#64748b", "#9f1239"];

// ─── Small UI components ──────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 break-all text-xl font-bold leading-tight text-slate-800 md:text-2xl">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-3">
        <span className="text-rose-500">{icon}</span>
        <h2 className="text-base font-semibold text-slate-800">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

// ─── Score Gauge (mini pie) ───────────────────────────────────────────────────

function ScoreGauge({ score }: { score: number }) {
  const data = [
    { name: "Score", value: score },
    { name: "Rest", value: 100 - score },
  ];
  return (
    <div className="flex flex-col items-center">
      <PieChart width={140} height={140}>
        <Pie
          data={data}
          cx={65}
          cy={65}
          innerRadius={48}
          outerRadius={64}
          startAngle={90}
          endAngle={-270}
          dataKey="value"
          strokeWidth={0}
        >
          <Cell fill={score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444"} />
          <Cell fill="#f1f5f9" />
        </Pie>
      </PieChart>
      <div className={`-mt-2 text-2xl font-bold ${scoreColor(score)}`}>{score}%</div>
      <div className="mt-0.5 text-xs text-slate-400">Global Score</div>
    </div>
  );
}

// ─── KPI bar charts ───────────────────────────────────────────────────────────

function KpiCharts({
  kpis,
  selectedColumn,
  onSelectColumn,
}: {
  kpis: KpiResult;
  selectedColumn: string | null;
  onSelectColumn: (column: string) => void;
}) {
  const completenessData = Object.entries(kpis.specific_col_quality_completeness).map(([col, v]) => ({ col, value: v }));
  const validityData = Object.entries(kpis.specific_col_quality_validity).map(([col, v]) => ({ col, value: v }));

  const renderBar = (data: { col: string; value: number }[], title: string) => (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-500">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="col" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
          <Tooltip formatter={(v) => [`${v}%`, title]} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                cursor="pointer"
                onClick={() => onSelectColumn(entry.col)}
                fill={selectedColumn === entry.col ? "#be123c" : CHART_COLORS[i % CHART_COLORS.length]}
                fillOpacity={selectedColumn === null || selectedColumn === entry.col ? 1 : 0.35}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {renderBar(completenessData, "Completeness % per Column")}
      {renderBar(validityData, "Validity % per Column")}
    </div>
  );
}

function IssueRowsChart({ rows }: { rows: FailureCase[] }) {
  const chartData = rows.slice(0, 500).map((row) => ({
    rowIndex: row.index,
    severity: Math.round(100 - row.consistency_pct),
  }));

  if (!chartData.length) {
    return <p className="text-sm text-slate-500">No issue rows for this column.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="rowIndex" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} unit="%" />
        <Tooltip formatter={(value) => [`${value}%`, "Issue Severity"]} />
        <Bar dataKey="severity" name="Issue Severity" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.severity > 70 ? "#be123c" : entry.severity > 40 ? "#f97316" : "#334155"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── KRI Distribution Evolution chart ────────────────────────────────────────

function KriEvoChart({ rows }: { rows: EvoRow[] }) {
  if (!rows.length) return <p className="text-sm text-slate-400">No evolution data.</p>;

  const keys = Object.keys(rows[0]);
  const indexKey = keys[0];
  const barKeys = keys.slice(1);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 4, right: 12, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey={indexKey} tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
        <YAxis tick={{ fontSize: 10 }} />
        <Tooltip />
        <Legend />
        {barKeys.map((k, i) => (
          <Bar
            key={k}
            dataKey={k}
            stackId="a"
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={i === barKeys.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

type Mode = "idle" | "loading" | "done" | "error";

export default function App() {
  const [mode, setMode] = useState<Mode>("idle");
  const [error, setError] = useState("");
  const [report, setReport] = useState<ReportingResponse | null>(null);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadRef, setUploadRef] = useState<File | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedIssueColumn, setSelectedIssueColumn] = useState<string | null>(null);

  const topFailureCases = useMemo(() => (report ? report.failure_cases.slice(0, 300) : []), [report]);
  const selectedColumnIssues = useMemo(() => {
    if (!report || !selectedIssueColumn) return [] as FailureCase[];
    return report.failure_cases.filter((item) => item.column === selectedIssueColumn);
  }, [report, selectedIssueColumn]);

  // Auto-load the local dataset on first render
  useEffect(() => {
    loadLocal();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!report || report.column_analysis.length === 0) {
      setSelectedIssueColumn(null);
      return;
    }
    const firstProblematic = report.column_analysis.find((item) => item.error_count > 0);
    setSelectedIssueColumn(firstProblematic?.column ?? report.column_analysis[0].column);
  }, [report]);

  async function loadLocal() {
    setMode("loading");
    setError("");
    setReport(null);
    try {
      const res = await fetch("/api/reporting/local");
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Status ${res.status}`);
      }
      setReport(await res.json());
      setMode("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error");
      setMode("error");
    }
  }

  async function runUpload() {
    if (!uploadFile) return;
    setMode("loading");
    setError("");
    setReport(null);
    try {
      const fd = new FormData();
      fd.append("file", uploadFile);
      if (uploadRef) fd.append("reference_file", uploadRef);
      const res = await fetch("/api/reporting/upload-analyze", { method: "POST", body: fd });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Status ${res.status}`);
      }
      setReport(await res.json());
      setMode("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error");
      setMode("error");
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      {/* ── Header ── */}
      <header className="border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="h-6 w-6 text-rose-600" />
            <div>
              <h1 className="text-lg font-bold leading-none">KRI Data Quality Dashboard</h1>
              <p className="mt-0.5 text-xs text-slate-400">Powered by FastAPI · scripts.py engine</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowUpload((s) => !s)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <Upload className="h-4 w-4" />
              Upload file
            </button>
            <button
              onClick={loadLocal}
              disabled={mode === "loading"}
              className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
            >
              {mode === "loading" ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <FileSearch className="h-4 w-4" />
              )}
              Load local dataset
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 p-6">
        {/* ── Upload panel (collapsible) ── */}
        {showUpload && (
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold text-slate-600">Upload custom file</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-500">Main file (CSV / Excel)</span>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  className="w-full rounded-md border border-slate-300 p-2 text-sm"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-500">Reference file (optional)</span>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setUploadRef(e.target.files?.[0] ?? null)}
                  className="w-full rounded-md border border-slate-300 p-2 text-sm"
                />
              </label>
            </div>
            <button
              onClick={runUpload}
              disabled={!uploadFile || mode === "loading"}
              className="mt-4 rounded-md bg-rose-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {mode === "loading" ? "Analyzing…" : "Run analysis"}
            </button>
          </div>
        )}

        {/* ── Error banner ── */}
        {mode === "error" && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <XCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* ── Idle placeholder ── */}
        {mode === "idle" && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-24 text-slate-400">
            <Database className="mb-3 h-10 w-10" />
            <p className="text-sm">
              Click <strong>Load local dataset</strong> to run the quality report
            </p>
          </div>
        )}

        {/* ── Loading spinner ── */}
        {mode === "loading" && (
          <div className="flex items-center justify-center py-24 text-rose-600">
            <RefreshCw className="mr-2 h-6 w-6 animate-spin" />
            <span className="text-sm font-medium">Running analysis…</span>
          </div>
        )}

        {/* ── Dashboard ── */}
        {report && mode === "done" && (
          <div className="space-y-4">
            {report.global_score === 0 && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                Quality score is 0%. Data loaded correctly, but current quality rules mark all rows invalid or incomplete.
              </div>
            )}

            {/* Summary row */}
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div className={`col-span-2 flex items-center justify-center rounded-xl border p-4 md:col-span-1 ${scoreBg(report.global_score)}`}>
                <ScoreGauge score={report.global_score} />
              </div>
              <div className="col-span-2 md:col-span-4">
                <div className="grid h-full grid-cols-2 gap-4 md:grid-cols-4">
                  <StatCard label="Dataset" value={report.file_name} />
                  <StatCard label="Rows" value={report.total_rows.toLocaleString()} />
                  <StatCard label="Columns" value={String(report.total_columns)} />
                  <StatCard
                    label="Completeness"
                    value={`${report.kpis.global_quality_completeness}%`}
                    sub={`Validity ${report.kpis.global_quality_validity}%`}
                  />
                </div>
              </div>
            </div>

            {/* KPI Charts */}
            <Section title="KPI — Completeness & Validity per Column" icon={<CheckCircle className="h-4 w-4" />}>
              <KpiCharts
                kpis={report.kpis}
                selectedColumn={selectedIssueColumn}
                onSelectColumn={(column) => setSelectedIssueColumn(column)}
              />
            </Section>

            {/* Column Analysis */}
            <Section title="Column Analysis" icon={<FileSearch className="h-4 w-4" />}>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                      <th className="pb-2 pr-4">Column</th>
                      <th className="pb-2 pr-4">Errors</th>
                      <th className="pb-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.column_analysis.length > 0 ? (
                      report.column_analysis.map((row) => (
                        <tr
                          key={row.column}
                          onClick={() => setSelectedIssueColumn(row.column)}
                          className={`cursor-pointer border-b border-slate-50 transition-colors ${
                            selectedIssueColumn === row.column ? "bg-rose-50" : "hover:bg-slate-50"
                          }`}
                        >
                          <td className="py-2 pr-4 font-mono text-xs">{row.column}</td>
                          <td className="py-2 pr-4">{row.error_count}</td>
                          <td className="py-2">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[row.status] ?? ""}`}>
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="py-4 text-center text-slate-400">
                          No column issues detected.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Section>

            {selectedIssueColumn && (
              <Section
                title={`Issue Drilldown — ${selectedIssueColumn} (${selectedColumnIssues.length} rows)`}
                icon={<AlertTriangle className="h-4 w-4 text-rose-600" />}
              >
                <IssueRowsChart rows={selectedColumnIssues} />
                <div className="mt-4 max-h-72 overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-2 pr-4">Row</th>
                        <th className="pb-2 pr-4">Value</th>
                        <th className="pb-2">Consistency %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedColumnIssues.length > 0 ? (
                        selectedColumnIssues.map((row, idx) => (
                          <tr key={`${row.index}-${idx}`} className="border-b border-slate-50">
                            <td className="py-2 pr-4 text-slate-600">{row.index}</td>
                            <td className="py-2 pr-4">{row.value ?? <span className="text-slate-400">NULL</span>}</td>
                            <td
                              className={`py-2 font-medium ${
                                row.consistency_pct < 50
                                  ? "text-rose-600"
                                  : row.consistency_pct < 80
                                    ? "text-orange-600"
                                    : "text-slate-700"
                              }`}
                            >
                              {row.consistency_pct}%
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={3} className="py-4 text-center text-slate-400">
                            No problematic rows in this column.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Section>
            )}

            {/* Dead KRI Alerts */}
            {report.dead_kri_alerts.length > 0 && (
              <Section
                title={`Dead KRI Alerts (${report.dead_kri_alerts.length})`}
                icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
              >
                <div className="max-h-64 overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-2 pr-4">KRI</th>
                        <th className="pb-2 pr-4">Last Date</th>
                        <th className="pb-2">Alert Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.dead_kri_alerts.map((a, i) => (
                        <tr key={i} className="border-b border-slate-50">
                          <td className="py-2 pr-4 font-medium">{a.kri_value ?? "—"}</td>
                          <td className="py-2 pr-4 text-xs text-slate-500">
                            {a.last_calculated_date ? new Date(a.last_calculated_date).toLocaleDateString() : "—"}
                          </td>
                          <td className="py-2">
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                              {a.alert_type}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            )}

            {/* KRI Distribution Evolution */}
            {report.kri_distribution_evolution.length > 0 && (
              <Section title="KRI Distribution Evolution" icon={<Database className="h-4 w-4" />}>
                <KriEvoChart rows={report.kri_distribution_evolution} />
              </Section>
            )}

            {/* Failure Cases */}
            <Section
              title={`Consistency Failure Cases (showing ${topFailureCases.length} of ${report.failure_cases.length})`}
              icon={<XCircle className="h-4 w-4 text-rose-400" />}
            >
              <div className="max-h-80 overflow-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                      <th className="pb-2 pr-4">Row</th>
                      <th className="pb-2 pr-4">Column</th>
                      <th className="pb-2 pr-4">Value</th>
                      <th className="pb-2">Consistency %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topFailureCases.length > 0 ? (
                      topFailureCases.map((row, idx) => (
                        <tr key={`${row.column}-${row.index}-${idx}`} className="border-b border-slate-50">
                          <td className="py-2 pr-4 text-slate-400">{row.index}</td>
                          <td className="py-2 pr-4 font-mono text-xs">{row.column}</td>
                          <td className="py-2 pr-4">{row.value ?? <span className="text-slate-400">NULL</span>}</td>
                          <td className="py-2">{row.consistency_pct}%</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="py-4 text-center text-slate-400">
                          No failure cases.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Section>
          </div>
        )}
      </main>
    </div>
  );
}