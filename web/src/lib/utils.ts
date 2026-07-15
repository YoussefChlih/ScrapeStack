import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string to a human-readable format.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a number with comma separators.
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "0";
  return num.toLocaleString();
}

/**
 * Calculate the duration between two timestamps in human-readable format.
 */
export function formatDuration(
  startStr: string | null | undefined,
  endStr: string | null | undefined
): string {
  if (!startStr || !endStr) return "—";
  const start = new Date(startStr).getTime();
  const end = new Date(endStr).getTime();
  const diff = end - start;

  if (diff < 1000) return "< 1s";
  if (diff < 60000) return `${Math.round(diff / 1000)}s`;
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000);
    const secs = Math.round((diff % 60000) / 1000);
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(diff / 3600000);
  const mins = Math.round((diff % 3600000) / 60000);
  return `${hours}h ${mins}m`;
}

/**
 * Extract the domain from a URL.
 */
export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/**
 * Validate a URL string.
 */
export function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}
