"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { isValidUrl } from "@/lib/utils";
import { Globe, Sliders, ArrowRight, Eye, Loader2, CheckSquare, Square } from "lucide-react";

interface DetectedData {
  id: string;
  type: string;
  name: string;
  preview?: unknown;
  count?: number;
  selector?: string;
  [key: string]: unknown;
}

interface PreviewData {
  site_type: string;
  page_title: string;
  available_data: DetectedData[];
  pagination: {
    has_pagination: boolean;
    pages_found: number;
  };
}

export default function NewScrapePage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(50);
  const [crawlMode, setCrawlMode] = useState<"single_page" | "smart_crawl" | "full_site">("single_page");
  
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [selectedData, setSelectedData] = useState<Set<string>>(new Set());
  
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState("");
  
  const router = useRouter();
  const supabase = createClient();

  async function handlePreview() {
    setError("");
    
    let normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith("http")) {
      normalizedUrl = `https://${normalizedUrl}`;
    }

    if (!isValidUrl(normalizedUrl)) {
      setError("Please enter a valid URL");
      return;
    }

    setPreviewing(true);

    try {
      const response = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: normalizedUrl }),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        setError(result.error || "Failed to preview page");
        setPreviewing(false);
        return;
      }

      setPreviewData(result.data);
      setError("");
      
      // Auto-select all data by default
      const allIds = new Set<string>(result.data.available_data.map((d: DetectedData) => d.id));
      setSelectedData(allIds);
      
      // Set smart mode if pagination detected
      if (result.data.pagination?.has_pagination && result.data.pagination.pages_found > 1) {
        setCrawlMode("smart_crawl");
      }
      
    } catch {
      setError("Failed to preview page");
    } finally {
      setPreviewing(false);
    }
  }

  function toggleDataSelection(id: string) {
    const newSelection = new Set(selectedData);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedData(newSelection);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!previewData) {
      setError("Please preview the page first");
      return;
    }

    if (selectedData.size === 0) {
      setError("Please select at least one data type to scrape");
      return;
    }

    setLoading(true);

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      
      if (!user) {
        setError("You must be logged in.");
        setLoading(false);
        return;
      }

      // Build selected data array
      const selectedDataArray = previewData.available_data.filter(d => selectedData.has(d.id));

      // Insert the scrape job
      const { data: job, error: insertError } = await supabase
        .from("scrape_jobs")
        .insert({
          user_id: user.id,
          target_url: url.startsWith("http") ? url : `https://${url}`,
          max_pages: crawlMode === "single_page" ? 1 : maxPages,
          status: "queued",
          same_domain_only: true,
          respect_robots: true,
          crawl_mode: crawlMode,
          selected_data_types: selectedDataArray,
          preview_data: previewData,
        })
        .select()
        .single();

      if (insertError) {
        setError(insertError.message);
        setLoading(false);
        return;
      }

      // Trigger the worker
      const workerResponse = await fetch("/api/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.id }),
      });

      if (!workerResponse.ok) {
        const errData = await workerResponse.json().catch(() => ({}));
        console.warn("Worker trigger failed:", errData);
      }

      router.push(`/dashboard/jobs/${job.id}`);
    } catch {
      setError("Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="pt-2 lg:pt-0 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          New Scrape Job
        </h1>
        <p className="text-muted-foreground mt-1">
          Preview what data is available, select what you want, then start scraping
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: URL Input */}
        <div className="glass-card p-6">
          <label
            htmlFor="url"
            className="flex items-center gap-2 text-sm font-medium mb-3"
          >
            <Globe className="w-4 h-4 text-accent" />
            Website URL
          </label>
          <div className="flex gap-2">
            <input
              id="url"
              type="text"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setPreviewData(null);
                setSelectedData(new Set());
              }}
              className="input text-base flex-1"
              placeholder="https://example.com or linkedin.com/search/..."
              required
            />
            <button
              type="button"
              onClick={handlePreview}
              disabled={previewing || !url}
              className="btn-primary px-6 flex items-center gap-2 whitespace-nowrap disabled:opacity-50"
            >
              {previewing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Eye className="w-4 h-4" />
                  Preview
                </>
              )}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Click Preview to see what data is available on this page
          </p>
        </div>

        {/* Step 2: Preview Results */}
        {previewData && (
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold mb-4">
              Available Data on {previewData.page_title}
            </h3>
            
            {previewData.available_data.length === 0 ? (
              <p className="text-muted-foreground">No structured data detected. Try full-site crawl mode.</p>
            ) : (
              <div className="space-y-3">
                {previewData.available_data.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => toggleDataSelection(item.id)}
                    className="border border-border rounded-lg p-4 cursor-pointer hover:border-accent/50 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {selectedData.has(item.id) ? (
                          <CheckSquare className="w-5 h-5 text-accent" />
                        ) : (
                          <Square className="w-5 h-5 text-muted-foreground" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium">{item.name}</h4>
                          {item.count && (
                            <span className="text-xs bg-accent/20 text-accent px-2 py-1 rounded">
                              {item.count} items
                            </span>
                          )}
                        </div>
                        
                        {item.preview != null && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            {Array.isArray(item.preview) && item.preview.length > 0 && (
                              <div className="space-y-1">
                                {item.preview.slice(0, 2).map((p: unknown, idx: number) => (
                                  <div key={idx} className="bg-background/50 p-2 rounded">
                                    {typeof p === "string" ? p : JSON.stringify(p).substring(0, 100)}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {previewData.pagination?.has_pagination && (
              <div className="mt-4 p-3 bg-accent/10 border border-accent/20 rounded-lg text-sm">
                <p className="text-accent font-medium">
                  📄 Pagination detected ({previewData.pagination.pages_found} pages)
                </p>
                <p className="text-muted-foreground text-xs mt-1">
                  Smart Crawl mode will follow pagination links automatically
                </p>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Crawl Mode */}
        {previewData && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 text-sm font-medium mb-4">
              <Sliders className="w-4 h-4 text-accent" />
              Crawl Mode
            </div>
            
            <div className="space-y-3">
              <label className="flex items-start gap-3 cursor-pointer group border border-border rounded-lg p-4 hover:border-accent/50 transition-colors">
                <input
                  type="radio"
                  name="crawlMode"
                  value="single_page"
                  checked={crawlMode === "single_page"}
                  onChange={(e) => setCrawlMode(e.target.value as "single_page" | "smart_crawl" | "full_site")}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium">Single Page Only</span>
                  <p className="text-xs text-muted mt-1">
                    Scrape only this URL (fastest)
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer group border border-border rounded-lg p-4 hover:border-accent/50 transition-colors">
                <input
                  type="radio"
                  name="crawlMode"
                  value="smart_crawl"
                  checked={crawlMode === "smart_crawl"}
                  onChange={(e) => setCrawlMode(e.target.value as "single_page" | "smart_crawl" | "full_site")}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium">Smart Crawl</span>
                  <p className="text-xs text-muted mt-1">
                    Follow pagination and related links (recommended)
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer group border border-border rounded-lg p-4 hover:border-accent/50 transition-colors">
                <input
                  type="radio"
                  name="crawlMode"
                  value="full_site"
                  checked={crawlMode === "full_site"}
                  onChange={(e) => setCrawlMode(e.target.value as "single_page" | "smart_crawl" | "full_site")}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium">Full Site Crawl</span>
                  <p className="text-xs text-muted mt-1">
                    Crawl entire website following all links (slowest)
                  </p>
                </div>
              </label>
            </div>

            {crawlMode !== "single_page" && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="maxPages" className="text-sm text-muted-foreground">
                    Maximum pages to crawl
                  </label>
                  <span className="text-sm font-mono font-medium text-accent">
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
                    [&::-webkit-slider-thumb]:cursor-pointer"
                />
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {/* Submit */}
        {previewData && selectedData.size > 0 && (
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 text-base py-3 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting scrape...
              </>
            ) : (
              <>
                Start Scraping ({selectedData.size} data types selected)
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        )}
      </form>
    </div>
  );
}
