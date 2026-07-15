"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  formatDate,
  formatDuration,
  formatNumber,
  extractDomain,
} from "@/lib/utils";
import type {
  ScrapeJob,
  ScrapedPage,
  Recommendation,
  Export as ExportType,
  ScrapedDataItem,
} from "@/lib/types";
import {
  Globe,
  FileText,
  Clock,
  AlertTriangle,
  BarChart3,
  Sparkles,
  Download,
  ExternalLink,
  ArrowLeft,
  Link as LinkIcon,
  Image as ImageIcon,
  Type,
} from "lucide-react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const TABS = ["Overview", "Pages", "Recommendations", "Exports"] as const;
type Tab = (typeof TABS)[number];

const CHART_COLORS = ["#00E5A0", "#3B82F6", "#FFB020", "#FF4D6A", "#8B5CF6", "#EC4899"];

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const supabase = createClient();

  const [job, setJob] = useState<ScrapeJob | null>(null);
  const [pages, setPages] = useState<ScrapedPage[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [exports, setExports] = useState<ExportType[]>([]);
  const [scrapedData, setScrapedData] = useState<ScrapedDataItem[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [loading, setLoading] = useState(true);
  const [pageSearch, setPageSearch] = useState("");
  const [pageSort, setPageSort] = useState<"url" | "word_count" | "status_code">("url");

  const fetchData = useCallback(async () => {
    const [jobRes, pagesRes, recsRes, exportsRes, dataRes] = await Promise.all([
      supabase.from("scrape_jobs").select("*").eq("id", jobId).single(),
      supabase.from("scraped_pages").select("*").eq("job_id", jobId).order("scraped_at"),
      supabase.from("recommendations").select("*").eq("job_id", jobId),
      supabase.from("exports").select("*").eq("job_id", jobId),
      supabase.from("scraped_data").select("*").eq("job_id", jobId),
    ]);

    if (jobRes.data) setJob(jobRes.data as ScrapeJob);
    if (pagesRes.data) setPages(pagesRes.data as ScrapedPage[]);
    if (recsRes.data) setRecommendations(recsRes.data as Recommendation[]);
    if (exportsRes.data) setExports(exportsRes.data as ExportType[]);
    if (dataRes.data) setScrapedData(dataRes.data as ScrapedDataItem[]);
    setLoading(false);
  }, [jobId]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "scrape_jobs",
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          setJob(payload.new as ScrapeJob);
          // Refresh all data when job completes
          if ((payload.new as ScrapeJob).status === "completed") {
            fetchData();
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [jobId, fetchData]);

  if (loading) {
    return (
      <div className="pt-2 lg:pt-0 space-y-6">
        <div className="skeleton h-8 w-48" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-28" />
          ))}
        </div>
        <div className="skeleton h-96" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="pt-2 lg:pt-0 text-center py-20">
        <h2 className="text-xl font-semibold mb-2">Job not found</h2>
        <Link href="/dashboard" className="text-accent hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  // Computed stats
  const totalWords = pages.reduce((sum, p) => sum + (p.word_count || 0), 0);
  const avgWords = pages.length ? Math.round(totalWords / pages.length) : 0;
  const brokenLinks = pages.filter(
    (p) => p.status_code && p.status_code >= 400
  ).length;
  const progress =
    job.max_pages > 0 ? Math.round((job.pages_scraped / job.max_pages) * 100) : 0;

  // Chart data
  const wordCountData = pages
    .filter((p) => p.word_count)
    .map((p) => ({
      name: extractDomain(p.url) === extractDomain(job.target_url)
        ? new URL(p.url).pathname.slice(0, 30) || "/"
        : extractDomain(p.url),
      words: p.word_count || 0,
    }))
    .slice(0, 20);

  // Link ratio from scraped_data
  const linkData = scrapedData.filter((d) => d.data_type === "link");
  const totalInternal = linkData.reduce(
    (sum, d) => sum + ((d.data as Record<string, number>).internal_count || 0),
    0
  );
  const totalExternal = linkData.reduce(
    (sum, d) => sum + ((d.data as Record<string, number>).external_count || 0),
    0
  );
  const linkRatioData = [
    { name: "Internal", value: totalInternal },
    { name: "External", value: totalExternal },
  ];

  // Image alt-text stats
  const imageData = scrapedData.filter((d) => d.data_type === "image");
  const totalImages = imageData.reduce(
    (sum, d) => sum + ((d.data as Record<string, unknown[]>).items?.length || 0),
    0
  );
  const missingAlt = imageData.reduce((sum, d) => {
    const items = (d.data as Record<string, unknown[]>).items || [];
    return sum + items.filter((img: unknown) => !(img as Record<string, boolean>).has_alt).length;
  }, 0);

  // Filtered and sorted pages
  const filteredPages = pages
    .filter(
      (p) =>
        p.url.toLowerCase().includes(pageSearch.toLowerCase()) ||
        (p.title || "").toLowerCase().includes(pageSearch.toLowerCase())
    )
    .sort((a, b) => {
      if (pageSort === "word_count") return (b.word_count || 0) - (a.word_count || 0);
      if (pageSort === "status_code") return (a.status_code || 0) - (b.status_code || 0);
      return a.url.localeCompare(b.url);
    });

  // Group recommendations by category
  const recsByCategory = recommendations.reduce(
    (acc, rec) => {
      if (!acc[rec.category]) acc[rec.category] = [];
      acc[rec.category].push(rec);
      return acc;
    },
    {} as Record<string, Recommendation[]>
  );

  const priorityColors: Record<string, string> = {
    high: "border-l-error text-error",
    medium: "border-l-warning text-warning",
    low: "border-l-success text-success",
  };

  return (
    <div className="pt-2 lg:pt-0">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to dashboard
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight truncate">
              {extractDomain(job.target_url)}
            </h1>
            <p className="text-sm text-muted-foreground truncate mt-1">
              {job.target_url}
            </p>
          </div>
          <StatusBadgeLarge status={job.status} />
        </div>
      </div>

      {/* Progress bar (when running) */}
      {job.status === "running" && (
        <div className="glass-card p-4 mb-6 animate-glow-pulse">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Crawling in progress...</span>
            <span className="font-[family-name:var(--font-mono)] text-accent font-medium">
              {job.pages_scraped}/{job.max_pages} pages
            </span>
          </div>
          <div className="w-full h-2 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={FileText} label="Pages Scraped" value={formatNumber(job.pages_scraped)} />
        <StatCard icon={Type} label="Total Words" value={formatNumber(totalWords)} />
        <StatCard icon={Clock} label="Duration" value={formatDuration(job.started_at, job.completed_at)} />
        <StatCard
          icon={AlertTriangle}
          label="Broken Pages"
          value={brokenLinks.toString()}
          alert={brokenLinks > 0}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap border-b-2 -mb-px ${
              activeTab === tab
                ? "border-accent text-accent"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
            {tab === "Recommendations" && recommendations.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-accent/10 text-accent">
                {recommendations.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Overview" && (
        <div className="space-y-6 animate-fade-in">
          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Word count chart */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-accent" />
                Word Count by Page
              </h3>
              {wordCountData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={wordCountData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E2D3D" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#6B7A8D", fontSize: 11 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis tick={{ fill: "#6B7A8D", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#1A2332",
                        border: "1px solid #1E2D3D",
                        borderRadius: "10px",
                        color: "#E8ECF4",
                      }}
                    />
                    <Bar dataKey="words" fill="#00E5A0" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground text-sm">
                  No page data yet
                </div>
              )}
            </div>

            {/* Link ratio pie chart */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
                <LinkIcon className="w-4 h-4 text-accent" />
                Internal vs External Links
              </h3>
              {totalInternal + totalExternal > 0 ? (
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width="60%" height={250}>
                    <PieChart>
                      <Pie
                        data={linkRatioData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {linkRatioData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "#1A2332",
                          border: "1px solid #1E2D3D",
                          borderRadius: "10px",
                          color: "#E8ECF4",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-3">
                    {linkRatioData.map((item, i) => (
                      <div key={item.name} className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ background: CHART_COLORS[i] }}
                        />
                        <span className="text-sm text-muted-foreground">
                          {item.name}
                        </span>
                        <span className="text-sm font-[family-name:var(--font-mono)] font-medium">
                          {formatNumber(item.value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">
                  No link data yet
                </div>
              )}
            </div>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MiniStat label="Avg Words/Page" value={formatNumber(avgWords)} />
            <MiniStat label="Total Images" value={formatNumber(totalImages)} />
            <MiniStat
              label="Missing Alt Text"
              value={formatNumber(missingAlt)}
              alert={missingAlt > 0}
            />
            <MiniStat
              label="Link Ratio (Int/Ext)"
              value={
                totalExternal > 0
                  ? `${(totalInternal / totalExternal).toFixed(1)}x`
                  : "—"
              }
            />
          </div>
        </div>
      )}

      {activeTab === "Pages" && (
        <div className="space-y-4 animate-fade-in">
          {/* Search & sort */}
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={pageSearch}
              onChange={(e) => setPageSearch(e.target.value)}
              placeholder="Search pages..."
              className="input flex-1"
            />
            <select
              value={pageSort}
              onChange={(e) => setPageSort(e.target.value as typeof pageSort)}
              className="input w-auto"
            >
              <option value="url">Sort by URL</option>
              <option value="word_count">Sort by Word Count</option>
              <option value="status_code">Sort by Status</option>
            </select>
          </div>

          {/* Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="px-4 py-3 font-medium">URL</th>
                    <th className="px-4 py-3 font-medium">Title</th>
                    <th className="px-4 py-3 font-medium text-right">Status</th>
                    <th className="px-4 py-3 font-medium text-right">Words</th>
                    <th className="px-4 py-3 font-medium text-right">Links</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPages.map((page) => (
                    <tr
                      key={page.id}
                      className="border-b border-border/50 hover:bg-surface-hover transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 max-w-xs">
                          <Globe className="w-3.5 h-3.5 text-muted shrink-0" />
                          <a
                            href={page.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent hover:underline truncate"
                          >
                            {new URL(page.url).pathname || "/"}
                          </a>
                          <ExternalLink className="w-3 h-3 text-muted shrink-0" />
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                        {page.title || "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`font-[family-name:var(--font-mono)] text-xs ${
                            (page.status_code || 0) >= 400
                              ? "text-error"
                              : (page.status_code || 0) >= 300
                                ? "text-warning"
                                : "text-success"
                          }`}
                        >
                          {page.status_code || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-[family-name:var(--font-mono)]">
                        {formatNumber(page.word_count)}
                      </td>
                      <td className="px-4 py-3 text-right font-[family-name:var(--font-mono)]">
                        {formatNumber(page.links_found)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredPages.length === 0 && (
              <div className="text-center py-12 text-muted-foreground text-sm">
                {pages.length === 0 ? "No pages scraped yet" : "No matching pages"}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "Recommendations" && (
        <div className="space-y-6 animate-fade-in">
          {Object.keys(recsByCategory).length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Sparkles className="w-10 h-10 text-accent/40 mx-auto mb-3" />
              <h3 className="font-semibold mb-1">No recommendations yet</h3>
              <p className="text-sm text-muted-foreground">
                {job.status === "completed"
                  ? "AI recommendations will appear here once generated."
                  : "Recommendations will be generated after the crawl completes."}
              </p>
            </div>
          ) : (
            Object.entries(recsByCategory).map(([category, recs]) => (
              <div key={category}>
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
                  {category}
                </h3>
                <div className="space-y-2">
                  {recs.map((rec) => (
                    <div
                      key={rec.id}
                      className={`glass-card p-4 border-l-4 ${priorityColors[rec.priority]}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h4 className="font-medium text-foreground mb-1">
                            {rec.title}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {rec.description}
                          </p>
                        </div>
                        <span
                          className={`text-xs font-medium uppercase px-2 py-0.5 rounded-full shrink-0 ${
                            rec.priority === "high"
                              ? "bg-error/10 text-error"
                              : rec.priority === "medium"
                                ? "bg-warning/10 text-warning"
                                : "bg-success/10 text-success"
                          }`}
                        >
                          {rec.priority}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "Exports" && (
        <div className="space-y-4 animate-fade-in">
          {exports.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Download className="w-10 h-10 text-accent/40 mx-auto mb-3" />
              <h3 className="font-semibold mb-1">No exports yet</h3>
              <p className="text-sm text-muted-foreground">
                {job.status === "completed"
                  ? "Exports will appear here once generated."
                  : "Exports will be available after the crawl completes."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {exports.map((exp) => (
                <a
                  key={exp.id}
                  href={exp.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="glass-card p-5 text-center hover:border-accent transition-colors"
                >
                  <Download className="w-8 h-8 text-accent mx-auto mb-3" />
                  <div className="font-medium mb-1">
                    {exp.format.toUpperCase()}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatDate(exp.created_at)}
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Sub-components ----

function StatusBadgeLarge({ status }: { status: ScrapeJob["status"] }) {
  const styles: Record<string, string> = {
    queued: "bg-info/10 text-info border-info/20",
    running: "bg-warning/10 text-warning border-warning/20 animate-glow-pulse",
    completed: "bg-success/10 text-success border-success/20",
    failed: "bg-error/10 text-error border-error/20",
    cancelled: "bg-muted/10 text-muted-foreground border-muted/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border ${styles[status]}`}
    >
      {status === "running" && (
        <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
      )}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  alert,
}: {
  icon: typeof FileText;
  label: string;
  value: string;
  alert?: boolean;
}) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${alert ? "text-error" : "text-accent"}`} />
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          {label}
        </span>
      </div>
      <div
        className={`text-2xl font-bold font-[family-name:var(--font-mono)] ${
          alert ? "text-error" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  alert,
}: {
  label: string;
  value: string;
  alert?: boolean;
}) {
  return (
    <div className="glass-card p-3">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div
        className={`text-lg font-bold font-[family-name:var(--font-mono)] ${
          alert ? "text-error" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}
