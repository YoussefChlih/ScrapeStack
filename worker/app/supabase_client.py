"""Supabase client for the worker service (uses service role key to bypass RLS)."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_supabase() -> Client:
    """Get or create a Supabase client with service role key."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        _client = create_client(url, key)
    return _client
