function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
  };
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders(),
  });
}

export async function onRequestGet(context) {
  return new Response(
    JSON.stringify({
      ok: true,
      runtime: "cloudflare-pages",
      hasSupabaseUrl: Boolean(context.env.SUPABASE_URL),
      hasServiceRole: Boolean(context.env.SUPABASE_SERVICE_ROLE_KEY),
    }),
    {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        ...corsHeaders(),
      },
    },
  );
}
