const SECTION_DEFS = [
  {
    id: "breakout",
    label: "AI Breakout Products",
    aliases: ["breakout", "breakout_products", "ai breakout products", "ai黑马产品"],
  },
  {
    id: "hot-news",
    label: "AI Hot News",
    aliases: ["hot-news", "hot_news", "hot news", "ai hot news", "ai热点资讯"],
  },
  {
    id: "models-frontier",
    label: "AI Models Frontier",
    aliases: [
      "models-frontier",
      "models_frontier",
      "models frontier",
      "ai models frontier",
      "llm",
      "image_video",
      "multimodal",
      "foundation models",
      "ai基模与多模态",
      "ai基模或多模态",
    ],
  },
  {
    id: "product-updates",
    label: "Top AI Product Updates",
    aliases: [
      "product-updates",
      "product_updates",
      "product updates",
      "top ai product updates",
      "ai热门产品更新",
    ],
  },
];

const ALL_SECTION_IDS = SECTION_DEFS.map((section) => section.id);
const SECTION_BY_ID = new Map(SECTION_DEFS.map((section) => [section.id, section]));
const ALIAS_TO_ID = new Map();

for (const section of SECTION_DEFS) {
  for (const rawAlias of [section.id, ...section.aliases]) {
    const alias = String(rawAlias || "").trim().toLowerCase();
    if (alias) {
      ALIAS_TO_ID.set(alias, section.id);
    }
  }
}

for (const alias of ["all", "all modules", "all_sections", "all-sections", "full brief", "全部订阅"]) {
  ALIAS_TO_ID.set(alias, "all");
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  };
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders(),
    },
  });
}

function normalizeSectionIds(rawModules) {
  if (!Array.isArray(rawModules) || !rawModules.length) {
    return [...ALL_SECTION_IDS];
  }

  const canonical = [];
  for (const rawValue of rawModules) {
    const value = String(rawValue || "").trim().toLowerCase();
    if (!value) continue;
    const resolved = ALIAS_TO_ID.get(value);
    if (!resolved) continue;
    if (resolved === "all") {
      return [...ALL_SECTION_IDS];
    }
    if (!canonical.includes(resolved)) {
      canonical.push(resolved);
    }
  }

  if (!canonical.length) {
    return [...ALL_SECTION_IDS];
  }

  return ALL_SECTION_IDS.filter((sectionId) => canonical.includes(sectionId));
}

function sectionLabels(sectionIds) {
  return sectionIds
    .map((sectionId) => SECTION_BY_ID.get(sectionId))
    .filter(Boolean)
    .map((section) => section.label);
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function normalizedEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function hexFromArrayBuffer(buffer) {
  return [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(left, right) {
  const a = String(left || "");
  const b = String(right || "");
  if (a.length !== b.length) return false;

  let mismatch = 0;
  for (let index = 0; index < a.length; index += 1) {
    mismatch |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return mismatch === 0;
}

async function unsubscribeToken(email, env) {
  const secret = String(env.UNSUBSCRIBE_SECRET || env.SUPABASE_SERVICE_ROLE_KEY || "").trim();
  if (!secret) {
    throw new Error("Unsubscribe signing secret is missing");
  }

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(normalizedEmail(email)));
  return hexFromArrayBuffer(signature);
}

async function verifyUnsubscribeToken(email, token, env) {
  const expected = await unsubscribeToken(email, env);
  return timingSafeEqual(expected, String(token || "").trim());
}

async function upsertSubscription(env, record) {
  const baseUrl = String(env.SUPABASE_URL || "").trim().replace(/\/$/, "");
  const serviceRoleKey = String(env.SUPABASE_SERVICE_ROLE_KEY || "").trim();

  if (!baseUrl || !serviceRoleKey) {
    throw new Error("Supabase server environment variables are missing");
  }

  const response = await fetch(`${baseUrl}/rest/v1/subscriptions?on_conflict=email`, {
    method: "POST",
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=representation",
    },
    body: JSON.stringify(record),
  });

  if (!response.ok) {
    const message = await response.text().catch(() => "");
    throw new Error(message || "Supabase rejected the subscription");
  }

  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) && rows[0] ? rows[0] : record;
}

async function updateSubscriptionStatus(env, email, status) {
  const baseUrl = String(env.SUPABASE_URL || "").trim().replace(/\/$/, "");
  const serviceRoleKey = String(env.SUPABASE_SERVICE_ROLE_KEY || "").trim();

  if (!baseUrl || !serviceRoleKey) {
    throw new Error("Supabase server environment variables are missing");
  }

  const response = await fetch(`${baseUrl}/rest/v1/subscriptions?email=eq.${encodeURIComponent(normalizedEmail(email))}`, {
    method: "PATCH",
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify({ status }),
  });

  if (!response.ok) {
    const message = await response.text().catch(() => "");
    throw new Error(message || "Supabase rejected the unsubscribe request");
  }

  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

function unsubscribeHtml(title, message, status = 200) {
  return new Response(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    body{margin:0;min-height:100vh;display:grid;place-items:center;background:#07121f;color:#e5f7ff;font-family:Georgia,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',serif}
    main{width:min(680px,calc(100vw - 32px));border:1px solid rgba(103,232,249,.22);border-radius:28px;padding:42px;background:linear-gradient(135deg,rgba(15,23,42,.96),rgba(17,38,56,.96));box-shadow:0 28px 90px rgba(0,0,0,.35)}
    p{font-size:18px;line-height:1.7;color:#b8c7d8}
    a{color:#67e8f9}
  </style>
</head>
<body>
  <main>
    <p style="letter-spacing:.18em;text-transform:uppercase;color:#67e8f9;font-size:13px;margin:0 0 14px;">NextToken</p>
    <h1 style="font-size:42px;line-height:1.1;margin:0 0 16px;">${title}</h1>
    <p>${message}</p>
    <p><a href="/">Back to NextToken</a></p>
  </main>
</body>
</html>`, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      ...corsHeaders(),
    },
  });
}

async function handleHealth(env) {
  return jsonResponse({
    ok: true,
    runtime: "cloudflare-worker-assets",
    hasSupabaseUrl: Boolean(env.SUPABASE_URL),
    hasServiceRole: Boolean(env.SUPABASE_SERVICE_ROLE_KEY),
    hasUnsubscribeSecret: Boolean(env.UNSUBSCRIBE_SECRET || env.SUPABASE_SERVICE_ROLE_KEY),
  });
}

async function handleSubscriptions(request, env) {
  if (request.method === "GET") {
    return jsonResponse({
      ok: true,
      endpoint: "subscriptions",
    });
  }

  let payload = {};
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON payload" }, 400);
  }

  const email = String(payload.email || "").trim().toLowerCase();
  if (!isValidEmail(email)) {
    return jsonResponse({ ok: false, error: "Enter a valid email address" }, 400);
  }

  const sectionIds = normalizeSectionIds(payload.modules);
  const record = {
    email,
    status: "active",
    section_ids: sectionIds,
    section_labels: sectionLabels(sectionIds),
    source: "website",
  };

  try {
    const savedRecord = await upsertSubscription(env, record);
    return jsonResponse({
      ok: true,
      subscription: {
        email: savedRecord.email || record.email,
        status: savedRecord.status || record.status,
        section_ids: Array.isArray(savedRecord.section_ids) ? savedRecord.section_ids : record.section_ids,
        section_labels: Array.isArray(savedRecord.section_labels) ? savedRecord.section_labels : record.section_labels,
        source: savedRecord.source || record.source,
        created_at: savedRecord.created_at || null,
        updated_at: savedRecord.updated_at || null,
      },
    });
  } catch (error) {
    return jsonResponse(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Subscription write failed",
      },
      500,
    );
  }
}

async function handleUnsubscribe(request, env) {
  const url = new URL(request.url);
  let email = normalizedEmail(url.searchParams.get("email"));
  let token = String(url.searchParams.get("token") || "").trim();

  if (request.method === "POST") {
    const contentType = request.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      const payload = await request.json().catch(() => ({}));
      email = normalizedEmail(payload.email || email);
      token = String(payload.token || token).trim();
    }
  }

  const wantsJson = url.searchParams.get("format") === "json" || request.headers.get("Accept")?.includes("application/json");
  const fail = (message, status = 400) => wantsJson
    ? jsonResponse({ ok: false, error: message }, status)
    : unsubscribeHtml("We could not unsubscribe you", message, status);

  if (!isValidEmail(email) || !token) {
    return fail("The unsubscribe link is missing a valid email or token.");
  }

  try {
    const tokenIsValid = await verifyUnsubscribeToken(email, token, env);
    if (!tokenIsValid) {
      return fail("This unsubscribe link is invalid or has been modified.", 403);
    }

    await updateSubscriptionStatus(env, email, "inactive");
    if (wantsJson) {
      return jsonResponse({ ok: true, email, status: "inactive" });
    }
    return unsubscribeHtml(
      "You are unsubscribed",
      "You will no longer receive NextToken email briefs at this address. You can subscribe again anytime from the homepage.",
    );
  } catch (error) {
    return fail(error instanceof Error ? error.message : "Unsubscribe failed", 500);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS" && url.pathname.startsWith("/api/")) {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    if (url.pathname === "/api/health") {
      return handleHealth(env);
    }

    if (url.pathname === "/api/subscriptions") {
      return handleSubscriptions(request, env);
    }

    if (url.pathname === "/api/unsubscribe" || url.pathname === "/unsubscribe") {
      return handleUnsubscribe(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
