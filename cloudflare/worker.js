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

async function handleHealth(env) {
  return jsonResponse({
    ok: true,
    runtime: "cloudflare-worker-assets",
    hasSupabaseUrl: Boolean(env.SUPABASE_URL),
    hasServiceRole: Boolean(env.SUPABASE_SERVICE_ROLE_KEY),
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

    return env.ASSETS.fetch(request);
  },
};
