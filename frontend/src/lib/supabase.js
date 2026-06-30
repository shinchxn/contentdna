import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Graceful no-op when credentials are not set (prototype mode)
const isConfigured =
  supabaseUrl &&
  supabaseAnonKey &&
  supabaseUrl !== "your_supabase_url" &&
  supabaseAnonKey !== "your_supabase_anon_key";

if (!isConfigured) {
  console.warn(
    "[ContentDNA] Supabase not configured — Realtime features disabled. " +
    "Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env to enable live alerts."
  );
}

// Export a real client if configured, else a stub that silently no-ops
export const supabase = isConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : {
      channel: () => ({
        on: function () { return this; },
        subscribe: () => {},
      }),
      removeChannel: () => {},
    };

export const supabaseEnabled = isConfigured;
