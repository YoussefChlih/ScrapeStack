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
    const { url } = body;

    if (!url) {
      return NextResponse.json(
        { error: "url is required" },
        { status: 400 }
      );
    }

    // Call the Python worker preview endpoint
    const workerUrl = process.env.WORKER_URL || "http://localhost:8000";
    const webhookSecret = process.env.WORKER_WEBHOOK_SECRET || "";

    const workerResponse = await fetch(`${workerUrl}/preview`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Webhook-Secret": webhookSecret,
      },
      body: JSON.stringify({ url }),
    });

    if (!workerResponse.ok) {
      const errorText = await workerResponse.text().catch(() => "Unknown error");
      console.error("Worker preview error:", errorText);
      return NextResponse.json(
        { error: "Failed to preview URL", details: errorText },
        { status: 502 }
      );
    }

    const result = await workerResponse.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Preview API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
