import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  try {
    const supabase = await createClient();

    // Verify the user is authenticated
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { job_id } = body;

    if (!job_id) {
      return NextResponse.json(
        { error: "job_id is required" },
        { status: 400 }
      );
    }

    // Verify the job belongs to the user
    const { data: job } = await supabase
      .from("scrape_jobs")
      .select("id, user_id")
      .eq("id", job_id)
      .single();

    if (!job || job.user_id !== user.id) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    // Call the Python worker
    const workerUrl = process.env.WORKER_URL || "http://localhost:8000";
    const webhookSecret = process.env.WORKER_WEBHOOK_SECRET || "";

    const workerResponse = await fetch(`${workerUrl}/scrape`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Webhook-Secret": webhookSecret,
      },
      body: JSON.stringify({ job_id }),
    });

    if (!workerResponse.ok) {
      const errorText = await workerResponse.text().catch(() => "Unknown error");
      console.error("Worker error:", errorText);
      return NextResponse.json(
        { error: "Failed to start scrape worker", details: errorText },
        { status: 502 }
      );
    }

    const result = await workerResponse.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Scrape API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
