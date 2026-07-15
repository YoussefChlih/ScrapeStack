"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";
import {
  Layers,
  LayoutDashboard,
  Plus,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  { href: "/dashboard/new", label: "New Scrape", icon: Plus },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

interface DashboardNavProps {
  user: User;
}

export function DashboardNav({ user }: DashboardNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname.startsWith(href);
  };

  const displayName =
    user.user_metadata?.full_name || user.email?.split("@")[0] || "User";
  const initials = displayName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <>
      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 glass border-b border-border h-14 flex items-center px-4">
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="btn-ghost p-2"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
        <div className="flex items-center gap-2 ml-2">
          <Layers className="w-5 h-5 text-accent" />
          <span className="font-bold font-[family-name:var(--font-mono)] text-sm">
            ScrapeStack
          </span>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/50"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-full w-64 z-50 flex flex-col",
          "bg-surface border-r border-border",
          "transition-transform duration-300 ease-in-out",
          "lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center gap-2 px-6 border-b border-border shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
            <Layers className="w-5 h-5 text-accent" />
          </div>
          <span className="text-lg font-bold font-[family-name:var(--font-mono)] tracking-tight">
            ScrapeStack
          </span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = isActive(item.href, item.exact);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  active
                    ? "bg-accent/10 text-accent"
                    : "text-muted-foreground hover:bg-surface-hover hover:text-foreground"
                )}
              >
                <item.icon className="w-4.5 h-4.5 shrink-0" />
                {item.label}
                {item.label === "New Scrape" && (
                  <span className="ml-auto w-5 h-5 rounded bg-accent/20 text-accent flex items-center justify-center text-xs font-bold">
                    +
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-border p-3 shrink-0">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-hover transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-xs font-bold shrink-0">
                {initials}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="text-sm font-medium truncate">
                  {displayName}
                </div>
                <div className="text-xs text-muted truncate">{user.email}</div>
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-muted transition-transform shrink-0",
                  userMenuOpen && "rotate-180"
                )}
              />
            </button>

            {userMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-1 glass-card p-1 animate-scale-in">
                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-error hover:bg-error/10 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Spacer for mobile top bar */}
      <div className="lg:hidden h-14 shrink-0" />
    </>
  );
}
