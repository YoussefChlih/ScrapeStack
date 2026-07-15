"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { Profile } from "@/lib/types";
import { User, Mail, Shield, Save, Check } from "lucide-react";

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    async function loadProfile() {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        router.push("/login");
        return;
      }

      const { data } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", user.id)
        .single();

      if (data) {
        setProfile(data as Profile);
        setFullName(data.full_name || "");
      }
      setLoading(false);
    }
    loadProfile();
  }, [router, supabase]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;

    setSaving(true);
    const { error } = await supabase
      .from("profiles")
      .update({ full_name: fullName })
      .eq("id", profile.id);

    setSaving(false);
    if (!error) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  }

  const planBadges: Record<string, string> = {
    free: "bg-muted/10 text-muted-foreground border-muted/20",
    pro: "bg-accent/10 text-accent border-accent/20",
    enterprise: "bg-info/10 text-info border-info/20",
  };

  if (loading) {
    return (
      <div className="pt-2 lg:pt-0 max-w-2xl space-y-6">
        <div className="skeleton h-8 w-32" />
        <div className="skeleton h-64" />
      </div>
    );
  }

  return (
    <div className="pt-2 lg:pt-0 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your profile and account
        </p>
      </div>

      {/* Profile section */}
      <form onSubmit={handleSave} className="glass-card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-5 flex items-center gap-2">
          <User className="w-5 h-5 text-accent" />
          Profile
        </h2>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="fullName"
              className="block text-sm font-medium text-muted-foreground mb-1.5"
            >
              Full name
            </label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="input"
              placeholder="Your name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1.5">
              Email
            </label>
            <div className="flex items-center gap-2 input bg-surface-hover cursor-not-allowed">
              <Mail className="w-4 h-4 text-muted" />
              <span className="text-muted-foreground">
                {profile?.email || "—"}
              </span>
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
          >
            {saved ? (
              <>
                <Check className="w-4 h-4" />
                Saved!
              </>
            ) : saving ? (
              <>
                <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save changes
              </>
            )}
          </button>
        </div>
      </form>

      {/* Plan section */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-5 flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          Plan
        </h2>

        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Current plan:</span>
          <span
            className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border capitalize ${
              planBadges[profile?.plan || "free"]
            }`}
          >
            {profile?.plan || "free"}
          </span>
        </div>

        {profile?.plan === "free" && (
          <p className="text-sm text-muted-foreground mt-3">
            Free plan allows up to 100 pages per scrape job. Upgrade for higher
            limits and priority processing.
          </p>
        )}
      </div>
    </div>
  );
}
