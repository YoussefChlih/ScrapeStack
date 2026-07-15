import Link from "next/link";
import {
  Globe,
  BarChart3,
  Sparkles,
  Download,
  ArrowRight,
  Layers,
  Shield,
  Zap,
} from "lucide-react";

const features = [
  {
    icon: Globe,
    title: "Page-by-Page Crawling",
    description:
      "Submit a URL and our engine crawls every page, extracting titles, headings, links, images, and structured data.",
  },
  {
    icon: BarChart3,
    title: "Smart Analytics Dashboard",
    description:
      "Visualize word counts, link ratios, heading distributions, and content quality metrics in real time.",
  },
  {
    icon: Sparkles,
    title: "AI Recommendations",
    description:
      "Get actionable SEO, accessibility, and content quality recommendations powered by AI analysis.",
  },
  {
    icon: Download,
    title: "Export Anywhere",
    description:
      "Download your scraped data as JSON, CSV, or XLSX. Share reports with your team instantly.",
  },
  {
    icon: Shield,
    title: "Respectful Crawling",
    description:
      "Honors robots.txt by default, with configurable delays between requests. Ethical scraping built in.",
  },
  {
    icon: Zap,
    title: "Live Progress",
    description:
      "Watch your crawl progress in real time. See pages discovered and data extracted as it happens.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                <Layers className="w-5 h-5 text-accent" />
              </div>
              <span className="text-lg font-bold font-[family-name:var(--font-mono)] tracking-tight">
                ScrapeStack
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/login" className="btn-ghost text-sm">
                Log in
              </Link>
              <Link href="/signup" className="btn-primary text-sm">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8 grid-bg overflow-hidden">
        <div className="radial-fade absolute inset-0 pointer-events-none" />
        
        {/* Floating accent orbs */}
        <div className="absolute top-40 left-1/4 w-64 h-64 bg-accent/5 rounded-full blur-3xl animate-float" />
        <div className="absolute top-60 right-1/4 w-48 h-48 bg-info/5 rounded-full blur-3xl animate-float delay-300" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-surface/50 text-sm text-muted-foreground mb-8 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-accent animate-glow-pulse" />
            Now with AI-powered insights
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight mb-6 animate-fade-in delay-100">
            Scrape, Analyze, and{" "}
            <span className="gradient-text">Optimize</span> Any Website
          </h1>

          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in delay-200">
            Submit a URL. Our engine crawls every page, extracts structured data,
            and delivers AI-powered recommendations to improve your site&apos;s SEO,
            accessibility, and content quality.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in delay-300">
            <Link
              href="/signup"
              className="btn-primary inline-flex items-center gap-2 text-base px-8 py-3"
            >
              Start Scraping Free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/login"
              className="btn-secondary inline-flex items-center gap-2 text-base px-8 py-3"
            >
              View Demo Dashboard
            </Link>
          </div>

          {/* Stats strip */}
          <div className="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto animate-fade-in delay-400">
            {[
              { value: "10K+", label: "Pages Scraped" },
              { value: "500+", label: "Sites Analyzed" },
              { value: "98%", label: "Uptime" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-bold font-[family-name:var(--font-mono)] text-accent">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
              Everything You Need to{" "}
              <span className="gradient-text">Extract & Analyze</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              A complete toolkit for web scraping, data extraction, and content
              analysis — with AI recommendations baked in.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <div
                key={feature.title}
                className="glass-card p-6 animate-fade-in"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-5 h-5 text-accent" />
                </div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-border">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
              How It Works
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Submit a URL",
                description:
                  "Enter any website URL and configure your crawl settings — max pages, domain scope, robots.txt compliance.",
              },
              {
                step: "02",
                title: "Watch It Crawl",
                description:
                  "Our engine visits every page, extracting headings, links, images, tables, and text content in real time.",
              },
              {
                step: "03",
                title: "Get Insights",
                description:
                  "View analytics charts, browse extracted data, read AI recommendations, and export everything.",
              },
            ].map((item, i) => (
              <div key={item.step} className="relative animate-fade-in" style={{ animationDelay: `${i * 150}ms` }}>
                <div className="text-5xl font-bold font-[family-name:var(--font-mono)] text-accent/20 mb-4">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center glass-card p-12 gradient-border">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Analyze Your Website?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-lg mx-auto">
            Start with the free plan — no credit card required. Scrape up to 100
            pages per job with full AI recommendations.
          </p>
          <Link
            href="/signup"
            className="btn-primary inline-flex items-center gap-2 text-base px-8 py-3"
          >
            Get Started Free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4 sm:px-6 lg:px-8 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-accent" />
            <span className="text-sm font-semibold font-[family-name:var(--font-mono)]">
              ScrapeStack
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} ScrapeStack. Built with Next.js, Supabase &amp; AI.
          </p>
        </div>
      </footer>
    </div>
  );
}
