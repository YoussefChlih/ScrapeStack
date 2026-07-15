"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { isValidUrl } from "@/lib/utils";
import { Globe, Sliders, ArrowRight, Shield, FileText } from "lucide-react";

export default function NewScrapePage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(50);
  const [respectRobots, setRespectRobots] = useState(true);
  const [sameDomainOnly, setSameDomainOnly] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Normalize URL
    let normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith("http")) {
      normalizedUrl = `https://${normalizedUrl}`;
    }

    if (!isValidUrl(normalizedUrl)) {
      setError("Please enter a valid URL (e.g., https://example.com)");
      return;
    }

    setLoading(true);

    try {
      // Get the current user
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        setError("You must be logged in.");
        setLoading(false);
        return;
      }

      // Insert the scrape job
      const { data: job, error: insertError } = await supabase
        .from("scrape_jobs")
        .insert({
          user_id: user.id,
          target_url: normalizedUrl,
          max_pages: maxPages,
          status: "queued",
          same_domain_only: sameDomainOnly,
          respect_robots: respectRobots,
        })
        .select()
        .single();

      if (insertError) {
        setError(insertError.message);
        setLoading(false);
        return;
      }

      // Trigger the worker via API route
      const workerResponse = await fetch("/api/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.id }),
      });

      if (!workerResponse.ok) {
        const errData = await workerResponse.json().catch(() => ({}));
        console.warn("Worker trigger failed:", errData);
        // Don't block — the job is queued, worker can be triggered manually
      }

      // Navigate to the job detail page
      router.push(`/dashboard/jobs/${job.id}`);
    } catch {
      setError("Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="pt-2 lg:pt-0 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          New Scrape Job
        </h1>
        <p className="text-muted-foreground mt-1">
          Enter a URL to crawl and configure your scraping settings
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* URL Input */}
        <div className="glass-card p-6">
          <label
            htmlFor="url"
            className="flex items-center gap-2 text-sm font-medium mb-3"
          >
            <Globe className="w-4 h-4 text-accent" />
            Website URL
          </label>
          <input
            id="url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="input text-base"
            placeholder="https://example.com"
            required
          />
          <p className="text-xs text-muted-foreground mt-2">
            We&apos;ll start from this page and follow internal links
          </p>
        </div>

        {/* Settings */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 text-sm font-medium mb-5">
            <Sliders className="w-4 h-4 text-accent" />
            Crawl Settings
          </div>

          {/* Max Pages */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="maxPages" className="text-sm text-muted-foreground">
                Maximum pages to crawl
              </label>
              <span className="text-sm font-[family-name:var(--font-mono)] font-medium text-accent">
                {maxPages}
              </span>
            </div>
            <input
              id="maxPages"
              type="range"
              min="1"
              max="100"
              value={maxPages}
              onChange={(e) => setMaxPages(parseInt(e.target.value))}
              className="w-full h-1.5 bg-border rounded-full appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none
                [&::-webkit-slider-thumb]:w-4
                [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-accent
                [&::-webkit-slider-thumb]:cursor-pointer
                [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(0,229,160,0.3)]"
            />
            <div className="flex justify-between text-xs text-muted mt-1">
              <span>1</span>
              <span>100</span>
            </div>
          </div>

          {/* Toggles */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={sameDomainOnly}
                  onChange={(e) => setSameDomainOnly(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-border rounded-full peer-checked:bg-accent/30 transition-colors" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-muted-foreground rounded-full peer-checked:translate-x-5 peer-checked:bg-accent transition-all" />
              </div>
              <div>
                <span className="text-sm font-medium group-hover:text-foreground transition-colors">
                  Same domain only
                </span>
                <p className="text-xs text-muted">
                  Only follow links on the same domain
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={respectRobots}
                  onChange={(e) => setRespectRobots(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-border rounded-full peer-checked:bg-accent/30 transition-colors" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-muted-foreground rounded-full peer-checked:translate-x-5 peer-checked:bg-accent transition-all" />
              </div>
              <div className="flex items-center gap-2">
                <div>
                  <span className="text-sm font-medium group-hover:text-foreground transition-colors">
                    Respect robots.txt
                  </span>
                  <p className="text-xs text-muted">
                    Skip pages disallowed by the site&apos;s robots.txt
                  </p>
                </div>
                <Shield className="w-4 h-4 text-accent shrink-0" />
              </div>
            </label>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 text-base py-3 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
              Starting crawl...
            </>
          ) : (
            <>
              Start Scraping
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        {/* Info */}
        <div className="flex items-start gap-3 text-xs text-muted-foreground">
          <FileText className="w-4 h-4 shrink-0 mt-0.5" />
          <p>
            After submission, we&apos;ll crawl the site page by page. You can watch
            the progress in real time. On completion, you&apos;ll get analytics,
            AI recommendations, and downloadable exports.
          </p>
        </div>
      </form>
    </div>
  );
}
