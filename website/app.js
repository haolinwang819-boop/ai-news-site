(function () {
  const siteData = window.__NEXTTOKEN_DATA__;
  if (!siteData) {
    return;
  }

  const legacySections = Array.isArray(siteData.sections) ? siteData.sections : [];
  const digests = Array.isArray(siteData.digests) && siteData.digests.length
    ? siteData.digests
    : [{
        date: siteData.digestDate || "",
        generatedAt: siteData.generatedAt || "",
        totalCount: siteData.totalCount || 0,
        sectionCount: siteData.sectionCount || legacySections.length,
        sections: legacySections,
      }];

  const digestMap = new Map(digests.map((digest) => [digest.date, digest]));
  const defaultDigestDate = digestMap.has(siteData.defaultDigestDate) ? siteData.defaultDigestDate : (digests[0] && digests[0].date) || "";
  const latestDigest = digestMap.get(defaultDigestDate) || digests[0] || { date: "", totalCount: 0, sections: [] };
  const archiveSections = Array.isArray(siteData.archiveSections) && siteData.archiveSections.length
    ? siteData.archiveSections
    : (latestDigest.sections || []);
  const archiveTotalCount = Number(siteData.archiveTotalCount || digests.reduce((sum, digest) => sum + Number(digest.totalCount || 0), 0));
  const archiveBriefCount = Number(siteData.briefCount || digests.length || 0);
  const supabaseConfig = siteData.supabase && siteData.supabase.enabled ? siteData.supabase : null;
  const pageType = document.body.dataset.page;
  const pageSize = 6;

  document.addEventListener("mousemove", (event) => {
    document.body.style.setProperty("--pointer-x", `${event.clientX}px`);
    document.body.style.setProperty("--pointer-y", `${event.clientY}px`);
  });

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getDigest(date) {
    return digestMap.get(date) || latestDigest;
  }

  function getSectionOrder(digest) {
    return Array.isArray(digest.sections) ? digest.sections.map((section) => section.id) : [];
  }

  function getSectionMap(digest) {
    return new Map((digest.sections || []).map((section) => [section.id, section]));
  }

  function ensureSectionId(digest, requestedId) {
    const sectionOrder = getSectionOrder(digest);
    if (!sectionOrder.length) return "";
    return sectionOrder.includes(requestedId) ? requestedId : sectionOrder[0];
  }

  function sectionAccent(section) {
    const map = {
      cyan: "eyebrow--cyan",
      gold: "eyebrow--gold",
      violet: "eyebrow--violet",
      lime: "eyebrow--lime",
    };
    return map[section.accent] || "eyebrow--cyan";
  }

  function createSectionTabs(container, digest, activeId, onClick) {
    if (!container) return;
    container.innerHTML = (digest.sections || [])
      .map((section) => {
        const activeClass = section.id === activeId ? " module-tab--active" : "";
        return `
          <button class="module-tab${activeClass}" type="button" data-section-id="${escapeHtml(section.id)}">
            <strong>${escapeHtml(section.label)}</strong>
            <span>${escapeHtml(section.cnLabel)} · ${section.count} stories</span>
          </button>
        `;
      })
      .join("");

    container.querySelectorAll("[data-section-id]").forEach((button) => {
      button.addEventListener("click", () => onClick(button.dataset.sectionId));
    });
  }

  function createDigestTabs(container, activeDate, onClick) {
    if (!container) return;
    container.innerHTML = digests
      .map((digest) => {
        const activeClass = digest.date === activeDate ? " date-tab--active" : "";
        return `
          <button class="date-tab${activeClass}" type="button" data-digest-date="${escapeHtml(digest.date)}">
            <strong>${escapeHtml(digest.date)}</strong>
            <span>${digest.totalCount} stories</span>
          </button>
        `;
      })
      .join("");

    container.querySelectorAll("[data-digest-date]").forEach((button) => {
      button.addEventListener("click", () => onClick(button.dataset.digestDate));
    });
  }

  function logoMarkup(item, className) {
    if (!item.logoUrl) return "";
    return `
      <div class="${className}">
        <img src="${escapeHtml(item.logoUrl)}" alt="${escapeHtml(item.title)} logo">
      </div>
    `;
  }

  function imageMarkup(item, className) {
    if (!item.imageUrl || item.visualType === "logo") return "";
    return `
      <div class="${className}">
        <img src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(item.title)}">
      </div>
    `;
  }

  function bulletsMarkup(item) {
    const points = Array.isArray(item.keyPoints) ? item.keyPoints.slice(0, 3) : [];
    if (!points.length) return "";
    return `<ul class="key-point-list">${points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>`;
  }

  function resultCard(item, section) {
    const badges = [
      item.sourceLabel,
      item.dateLabel,
      item.productRank ? `Rank #${item.productRank}` : "",
      item.modelTrack || "",
    ].filter(Boolean);

    const visualBlock = item.visualType === "logo"
      ? logoMarkup(item, "card-logo")
      : imageMarkup(item, "result-card__image");

    return `
      <article class="result-card">
        <div class="result-card__meta">
          <span class="micro-badge">${escapeHtml(section.shortLabel)}</span>
          ${badges.map((badge) => `<span>${escapeHtml(badge)}</span>`).join("")}
        </div>
        <h3 class="result-card__title">${escapeHtml(item.title)}</h3>
        <p class="result-card__summary">${escapeHtml(item.summary)}</p>
        ${bulletsMarkup(item)}
        ${visualBlock ? `<div class="result-card__visual">${visualBlock}</div>` : ""}
        <div class="result-card__actions">
          <a class="inline-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">Read source</a>
        </div>
      </article>
    `;
  }

  function renderArchiveHeroStats(container) {
    if (!container) return;
    const stats = [
      { value: archiveTotalCount, label: "stories in the archive" },
      { value: archiveBriefCount, label: "briefs stored" },
      { value: defaultDigestDate || "", label: "latest brief date" },
    ];
    container.innerHTML = stats
      .map((stat) => `
        <div class="stat-chip">
          <strong>${escapeHtml(String(stat.value))}</strong>
          <span>${escapeHtml(stat.label)}</span>
        </div>
      `)
      .join("");
  }

  function renderDigestHeroStats(container, digest) {
    if (!container) return;
    const stats = [
      { value: digest.totalCount || 0, label: "stories in the current brief" },
      { value: digest.sectionCount || ((digest.sections || []).length), label: "primary signal modules" },
      { value: digest.date || "", label: "brief date" },
    ];
    container.innerHTML = stats
      .map((stat) => `
        <div class="stat-chip">
          <strong>${escapeHtml(String(stat.value))}</strong>
          <span>${escapeHtml(stat.label)}</span>
        </div>
      `)
      .join("");
  }

  function renderModuleOverview() {
    const container = document.getElementById("module-overview");
    if (!container) return;
    container.innerHTML = archiveSections
      .map((section) => `
        <article class="module-card">
          <div class="module-card__kicker">${escapeHtml(section.cnLabel)}</div>
          <h3 class="module-card__title">${escapeHtml(section.label)}</h3>
          <p class="module-card__text">${escapeHtml(section.description)}</p>
          <div class="module-card__footer">
            <span>${section.count} stories</span>
            <a class="inline-link" href="./explore.html?date=${encodeURIComponent(defaultDigestDate)}&section=${escapeHtml(section.id)}">Open module</a>
          </div>
        </article>
      `)
      .join("");
  }

  function renderHomeStage(digest, activeId) {
    const sectionMap = getSectionMap(digest);
    const section = sectionMap.get(activeId) || (digest.sections || [])[0];
    const stage = document.getElementById("home-module-stage");
    const meta = document.getElementById("signal-meta");
    if (!stage || !section) return;

    const feature = (section.items || [])[0];
    const rest = (section.items || []).slice(1, 5);
    if (meta) {
      meta.textContent = `${section.count} stories · ${section.cnLabel} · ${digest.date || ""}`;
    }

    if (!feature) {
      stage.innerHTML = `<div class="empty-state">No items in this module yet.</div>`;
      return;
    }

    const featureVisual = feature.visualType === "logo"
      ? `
        <div class="stage-feature__visual">
          ${logoMarkup(feature, "visual-logo")}
          <div>
            <p class="eyebrow ${sectionAccent(section)}">${escapeHtml(section.cnLabel)}</p>
            <h3 style="margin:0;font-size:24px;">${escapeHtml(feature.sourceLabel)}</h3>
            <p class="hero__lede">${escapeHtml(feature.dateLabel)}</p>
          </div>
        </div>
      `
      : imageMarkup(feature, "visual-image");

    stage.innerHTML = `
      <article class="stage-feature">
        <div class="stage-feature__meta">
          <span class="micro-badge">${escapeHtml(section.label)}</span>
          <span>${escapeHtml(feature.sourceLabel)}</span>
          <span>${escapeHtml(feature.dateLabel)}</span>
        </div>
        <h3 class="stage-feature__title">${escapeHtml(feature.title)}</h3>
        <p class="stage-feature__summary">${escapeHtml(feature.summary)}</p>
        ${bulletsMarkup(feature)}
        ${featureVisual || ""}
        <div class="stage-feature__actions">
          <a class="primary-button" href="./explore.html?date=${encodeURIComponent(digest.date || defaultDigestDate)}&section=${escapeHtml(section.id)}">Open this module</a>
          <a class="ghost-button" href="${escapeHtml(feature.url)}" target="_blank" rel="noreferrer">Read source</a>
        </div>
      </article>
      <div class="stage-list">
        ${rest.map((item) => `
          <article class="stage-list__item">
            <div class="stage-feature__meta">
              <span>${escapeHtml(item.sourceLabel)}</span>
              <span>${escapeHtml(item.dateLabel)}</span>
            </div>
            <h4 style="margin:0;font-size:20px;line-height:1.2;">${escapeHtml(item.title)}</h4>
            <p class="stage-list__summary">${escapeHtml(item.summary)}</p>
            <a class="inline-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">Read source</a>
          </article>
        `).join("")}
      </div>
    `;
  }

  function subscriptionApiUrl() {
    if (window.location.protocol === "file:") {
      return "http://127.0.0.1:8765/api/subscriptions";
    }
    return new URL("/api/subscriptions", window.location.origin).toString();
  }

  async function saveSubscriptionToSupabase(payload) {
    if (!supabaseConfig) {
      throw new Error("Supabase subscription storage is not configured");
    }

    const modules = Array.isArray(payload.modules) ? payload.modules : [];
    const sectionLabels = (latestDigest.sections || [])
      .filter((section) => modules.includes(section.id))
      .map((section) => section.label);

    const response = await fetch(`${supabaseConfig.url}/rest/v1/subscriptions?on_conflict=email`, {
      method: "POST",
      headers: {
        "apikey": supabaseConfig.publishableKey,
        "Authorization": `Bearer ${supabaseConfig.publishableKey}`,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
      },
      body: JSON.stringify({
        email: payload.email,
        status: "active",
        section_ids: modules,
        section_labels: sectionLabels,
        source: "website",
      }),
    });

    if (!response.ok) {
      const message = await response.text().catch(() => "");
      throw new Error(message || "Supabase rejected the subscription");
    }

    return {
      email: payload.email,
      section_ids: modules,
      section_labels: sectionLabels,
    };
  }

  async function saveSubscription(payload) {
    try {
      const response = await fetch(subscriptionApiUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.ok) {
        return data.subscription || {};
      }
    } catch (error) {
      // Fall through for local file previews that do not have an API endpoint.
    }

    if (window.location.protocol === "file:" && supabaseConfig) {
      return saveSubscriptionToSupabase(payload);
    }

    throw new Error("Subscription service unavailable");
  }

  function subscriptionModuleOptions() {
    const container = document.getElementById("subscription-modules");
    if (!container) return;
    const selected = new Set(["all"]);
    const options = [
      {
        id: "all",
        label: "Full Brief",
        cnLabel: "全部订阅",
      },
      ...(latestDigest.sections || []).map((section) => ({
        id: section.id,
        label: section.label,
        cnLabel: section.cnLabel,
      })),
    ];

    function render() {
      container.innerHTML = options
        .map((option) => `
          <button type="button" class="chip${selected.has(option.id) ? " chip--active" : ""}" data-chip-id="${escapeHtml(option.id)}">
            <div class="chip__meta">
              <strong>${escapeHtml(option.label)}</strong>
              <span>${escapeHtml(option.cnLabel)}</span>
            </div>
          </button>
        `)
        .join("");

      container.querySelectorAll("[data-chip-id]").forEach((chip) => {
        chip.addEventListener("click", () => {
          const id = chip.dataset.chipId;
          if (id === "all") {
            selected.clear();
            selected.add("all");
          } else {
            selected.delete("all");
            if (selected.has(id)) {
              selected.delete(id);
            } else {
              selected.add(id);
            }
            if (!selected.size) {
              selected.add("all");
            }
          }
          render();
        });
      });
    }

    render();

    const form = document.getElementById("subscription-form");
    const feedback = document.getElementById("subscription-feedback");
    const submitButton = form ? form.querySelector("button[type='submit']") : null;
    if (!form || !feedback) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const emailInput = document.getElementById("subscriber-email");
      const email = emailInput && "value" in emailInput ? String(emailInput.value || "").trim() : "";
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        feedback.className = "subscribe__feedback";
        feedback.textContent = "Enter a valid email address to continue.";
        return;
      }

      const modules = selected.has("all")
        ? (latestDigest.sections || []).map((section) => section.id)
        : (latestDigest.sections || []).filter((section) => selected.has(section.id)).map((section) => section.id);

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Saving subscription...";
      }

      try {
        const subscription = await saveSubscription({
          email,
          modules,
        });
        const labels = Array.isArray(subscription.section_labels) ? subscription.section_labels : [];
        feedback.className = "subscribe__feedback subscribe__feedback--success";
        feedback.innerHTML = `
          <strong>${escapeHtml(email)}</strong><br>
          Saved to the subscriber registry with ${escapeHtml(labels.join(" · "))}.
        `;
        form.reset();
        selected.clear();
        selected.add("all");
        render();
      } catch (error) {
        feedback.className = "subscribe__feedback";
        feedback.textContent = window.location.protocol === "file:"
          ? `${error.message}. Start the local subscription service to persist signups.`
          : `${error.message}. Please try again in a moment.`;
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = "Subscribe to NextToken";
        }
      }
    });

    const emailInput = document.getElementById("subscriber-email");
    if (emailInput) {
      emailInput.addEventListener("input", () => {
        if (feedback.className.includes("subscribe__feedback--success")) {
          return;
        }
        feedback.className = "subscribe__feedback";
        feedback.textContent = "";
      });
    }
  }

  function renderHomePage() {
    document.getElementById("hero-eyebrow").textContent = siteData.brand.eyebrow;
    document.getElementById("hero-tagline").textContent = siteData.brand.tagline;
    renderArchiveHeroStats(document.getElementById("hero-stats"));
    renderModuleOverview();
    subscriptionModuleOptions();

    let activeSection = ensureSectionId(latestDigest, getSectionOrder(latestDigest)[0]);

    function syncHomeTabs() {
      createSectionTabs(document.getElementById("home-module-tabs"), latestDigest, activeSection, (sectionId) => {
        activeSection = sectionId;
        renderHomeStage(latestDigest, activeSection);
        syncHomeTabs();
      });
    }

    syncHomeTabs();
    renderHomeStage(latestDigest, activeSection);
  }

  function currentExploreState() {
    const params = new URLSearchParams(window.location.search);
    const requestedDate = params.get("date");
    const digest = getDigest(requestedDate);
    return {
      date: digest.date || defaultDigestDate,
      section: params.get("section") || ensureSectionId(digest, ""),
      query: (params.get("q") || "").trim().toLowerCase(),
      page: Math.max(1, Number(params.get("page") || 1) || 1),
    };
  }

  function updateExploreUrl(state) {
    const params = new URLSearchParams();
    params.set("date", state.date);
    params.set("section", state.section);
    if (state.query) params.set("q", state.query);
    if (state.page > 1) params.set("page", String(state.page));
    const nextUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, "", nextUrl);
  }

  function renderExplorePage() {
    const searchInput = document.getElementById("search-input");
    const resultsContainer = document.getElementById("explore-results");
    const paginationContainer = document.getElementById("pagination");
    const resultsMeta = document.getElementById("results-meta");
    const dateTabs = document.getElementById("explore-date-tabs");
    const archiveMeta = document.getElementById("explore-archive-meta");
    const archiveDate = document.getElementById("explore-current-date");
    if (!searchInput || !resultsContainer || !paginationContainer || !resultsMeta) return;

    let state = currentExploreState();
    searchInput.value = state.query;

    function render() {
      const digest = getDigest(state.date);
      state = {
        ...state,
        date: digest.date || defaultDigestDate,
        section: ensureSectionId(digest, state.section),
      };

      updateExploreUrl(state);
      renderDigestHeroStats(document.getElementById("explore-hero-stats"), digest);
      createDigestTabs(dateTabs, state.date, (digestDate) => {
        const nextDigest = getDigest(digestDate);
        state = {
          date: nextDigest.date || defaultDigestDate,
          section: ensureSectionId(nextDigest, state.section),
          query: state.query,
          page: 1,
        };
        render();
      });
      createSectionTabs(document.getElementById("explore-module-tabs"), digest, state.section, (sectionId) => {
        state = { date: state.date, section: sectionId, query: state.query, page: 1 };
        if (searchInput) searchInput.value = state.query;
        render();
      });

      if (archiveMeta) {
        archiveMeta.textContent = `${digests.length} archived briefs available`;
      }
      if (archiveDate) {
        archiveDate.textContent = digest.date || "";
      }

      const section = getSectionMap(digest).get(state.section) || (digest.sections || [])[0];
      const filtered = (section.items || [])
        .filter((item) => !state.query || item.searchText.includes(state.query))
        .sort((a, b) => b.sortTimestamp - a.sortTimestamp);

      const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      if (state.page > totalPages) state.page = totalPages;
      const start = (state.page - 1) * pageSize;
      const pageItems = filtered.slice(start, start + pageSize);

      resultsMeta.textContent = `${filtered.length} results · sorted by latest first · ${section.label} · ${digest.date}`;
      resultsContainer.innerHTML = pageItems.length
        ? pageItems.map((item) => resultCard(item, section)).join("")
        : `<div class="empty-state">No stories matched this search. Try another keyword, another module, or another brief date.</div>`;

      const buttons = [];
      buttons.push(`<button class="page-button" ${state.page === 1 ? "disabled" : ""} data-page-target="${state.page - 1}">Prev</button>`);
      for (let page = 1; page <= totalPages; page += 1) {
        const activeClass = page === state.page ? " page-button--active" : "";
        buttons.push(`<button class="page-button${activeClass}" data-page-target="${page}">${page}</button>`);
      }
      buttons.push(`<button class="page-button" ${state.page === totalPages ? "disabled" : ""} data-page-target="${state.page + 1}">Next</button>`);
      paginationContainer.innerHTML = buttons.join("");
      paginationContainer.querySelectorAll("[data-page-target]").forEach((button) => {
        button.addEventListener("click", () => {
          if (button.hasAttribute("disabled")) return;
          state = { ...state, page: Number(button.dataset.pageTarget) || 1 };
          render();
        });
      });
    }

    searchInput.addEventListener("input", () => {
      state = { ...state, query: searchInput.value.trim().toLowerCase(), page: 1 };
      render();
    });

    render();
  }

  if (pageType === "home") {
    renderHomePage();
  }

  if (pageType === "explore") {
    renderExplorePage();
  }
})();
