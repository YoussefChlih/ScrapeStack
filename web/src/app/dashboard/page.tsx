import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import {
  Plus,
  Globe,
  Clock,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { formatDate, extractDomain } from "@/lib/utils";
import type { ScrapeJob } from "@/lib/types";

function StatusBadge({ status }: { status: ScrapeJob["status"] }) {
  const styles: Record<string, string> = {
    queued: "bg-info/10 text-info border-info/20",
    running: "bg-warning/10 text-warning border-warning/20",
    completed: "bg-success/10 text-success border-success/20",
    failed: "bg-error/10 text-error border-error/20",
    cancelled: "bg-muted/10 text-muted-foreground border-muted/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status]}`}
    >
      {status === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-warning animate-pulse" />
      )}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default async function DashboardPage() {
  const supabase = await createClient();

  const { data: jobs } = await supabase
    .from("scrape_jobs")
    .select("*")
    .order("created_at", { ascending: false });

  const typedJobs = (jobs as ScrapeJob[]) || [];

  return (
    <div className="pt-2 lg:pt-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Your scrape jobs and analytics
          </p>
        </div>
        <Link
          href="/dashboard/new"
          className="btn-primary inline-flex items-center gap-2 self-start"
        >
          <Plus className="w-4 h-4" />
          New Scrape
        </Link>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          {
            label: "Total Jobs",
            value: typedJobs.length,
            icon: FileText,
          },
          {
            label: "Pages Scraped",
            value: typedJobs.reduce((sum, j) => sum + (j.pages_scraped || 0), 0),
            icon: Globe,
          },
          {
            label: "Running",
            value: typedJobs.filter((j) => j.status === "running").length,
            icon: Clock,
          },
          {
            label: "Failed",
            value: typedJobs.filter((j) => j.status === "failed").length,
            icon: AlertTriangle,
          },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-4 sm:p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                <stat.icon className="w-4.5 h-4.5 text-accent" />
              </div>
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                {stat.label}
              </span>
            </div>
            <div className="text-2xl sm:text-3xl font-bold font-[family-name:var(--font-mono)]">
              {stat.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Jobs list */}
      {typedJobs.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Globe className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-xl font-semibold mb-2">No scrape jobs yet</h2>
          <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
            Submit a URL to start your first website analysis. We&apos;ll crawl
            every page and extract structured data.
          </p>
          <Link
            href="/dashboard/new"
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Start Your First Scrape
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold mb-4">Recent Jobs</h2>
          {typedJobs.map((job, i) => (
            <Link
              key={job.id}
              href={`/dashboard/jobs/${job.id}`}
              className="glass-card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 animate-fade-in block"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Globe className="w-4 h-4 text-accent shrink-0" />
                  <span className="font-medium truncate">
                    {extractDomain(job.target_url)}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground truncate">
                  {job.target_url}
                </div>
              </div>

              <div className="flex items-center gap-4 sm:gap-6 text-sm">
                <div className="text-muted-foreground">
                  <span className="font-[family-name:var(--font-mono)] text-foreground">
                    {job.pages_scraped}
                  </span>
                  /{job.max_pages} pages
                </div>
                <StatusBadge status={job.status} />
                <span className="text-muted-foreground text-xs hidden sm:inline">
                  {formatDate(job.created_at)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
