// ==UserScript==
// @name         HH.kz Collector v2 (RMT research)
// @namespace    rmt-skills-gap
// @version      2.2
// @description  Step 1: harvest vacancy cards from search result pages. Step 3: save full vacancies from an ID queue. Export to JSON.
// @match        https://hh.kz/*
// @match        https://*.hh.kz/*
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// ==/UserScript==

// Note: the regular expressions that contain Russian or Kazakh words are matched
// against the text of hh.kz pages, which are published in Russian/Kazakh.
// They are data patterns, not interface text.

(function () {
  'use strict';

  // ---------- Storage (separate keys so that large objects are not rewritten together) ----------
  const K_CARDS = 'rmt2_cards';     // { id: card }
  const K_SEARCH = 'rmt2_searches'; // { url: {header, pages:[], last_harvest} }
  const K_FULL = 'rmt2_full';       // { id: vacancy }
  const K_QUEUE = 'rmt2_queue';     // [id, ...]
  const K_HIST = 'rmt2_history';    // [id, ...] for undo
  const K_UI = 'rmt2_ui';           // { collapsed: bool }

  const get = (k, d) => { const v = GM_getValue(k, null); return v ? JSON.parse(v) : d; };
  const put = (k, v) => GM_setValue(k, JSON.stringify(v));

  const vacUrl = (id) => `https://hh.kz/vacancy/${id}`;
  const idFromHref = (href) => { const m = (href || '').match(/\/vacancy\/(\d+)/); return m ? m[1] : null; };
  const currentVacancyId = () => { const m = location.pathname.match(/^\/vacancy\/(\d+)/); return m ? m[1] : null; };
  const isAdvancedPage = () => /^\/search\/vacancy\/advanced/.test(location.pathname);
  const isSearchPage = () => !isAdvancedPage() &&
    (/^\/search\/vacancy/.test(location.pathname) || /^\/vacancies\//.test(location.pathname));

  const txtIn = (root, sel) => { const el = root.querySelector(sel); return el ? el.innerText.trim() : ''; };
  const firstIn = (root, sels) => { for (const s of sels) { const t = txtIn(root, s); if (t) return t; } return ''; };

  // =====================================================================
  // STEP 1. Cards from a search result page
  // =====================================================================

  // Card root: climb up while the element still links to only one vacancy
  const cardRoot = (a) => {
    let el = a;
    while (el.parentElement && el.parentElement !== document.body) {
      const p = el.parentElement;
      const ids = new Set([...p.querySelectorAll('a[href*="/vacancy/"]')].map((x) => idFromHref(x.href)).filter(Boolean));
      if (ids.size > 1) break;
      el = p;
    }
    return el;
  };

  const harvestPage = () => {
    const container = document.querySelector('[data-qa="vacancy-serp__results"]') || document.querySelector('main') || document.body;
    const cards = get(K_CARDS, {});
    const now = new Date().toISOString();
    const seenHere = new Set();
    let added = 0;

    for (const a of container.querySelectorAll('a[href*="/vacancy/"]')) {
      const id = idFromHref(a.href);
      if (!id || seenHere.has(id)) continue;
      seenHere.add(id);
      const root = cardRoot(a);
      const card = {
        id,
        title: firstIn(root, ['[data-qa="serp-item__title"]', '[data-qa="serp-item__title-text"]']) || a.innerText.trim(),
        company: firstIn(root, ['[data-qa="vacancy-serp__vacancy-employer"]', '[data-qa="vacancy-serp__vacancy-employer-text"]']),
        city: firstIn(root, ['[data-qa="vacancy-serp__vacancy-address"]', '[data-qa="vacancy-serp__vacancy-address_narrow"]']),
        experience: firstIn(root, ['[data-qa^="vacancy-serp__vacancy-work-experience"]']),
        salary: firstIn(root, ['[data-qa="vacancy-serp__compensation"]']),
        snippet: [
          txtIn(root, '[data-qa="vacancy-serp__vacancy_snippet_requirement"]'),
          txtIn(root, '[data-qa="vacancy-serp__vacancy_snippet_responsibility"]'),
        ].filter(Boolean).join(' | '),
        raw: root.innerText.replace(/\s+\n/g, '\n').trim().slice(0, 3000), // fallback: full card text
        search_url: location.href,
        harvested_at: now,
      };
      if (!cards[id]) added++;
      cards[id] = { ...(cards[id] || {}), ...card, first_seen: (cards[id] && cards[id].first_seen) || now };
    }
    put(K_CARDS, cards);

    // Search log: what hh reported in the result header
    const searches = get(K_SEARCH, {});
    const base = location.href.replace(/([?&])page=\d+&?/, '$1').replace(/[?&]$/, '');
    const header = firstIn(document, ['[data-qa="vacancies-search-header"]', 'h1']);
    const pageNum = (location.href.match(/[?&]page=(\d+)/) || [])[1] || '0';
    const s = searches[base] || { header, pages: [] };
    s.header = header || s.header;
    if (!s.pages.includes(pageNum)) s.pages.push(pageNum);
    s.last_harvest = now;
    searches[base] = s;
    put(K_SEARCH, searches);

    toast(`Page ${+pageNum + 1}: found ${seenHere.size}, new ${added}`);
    render();
    return seenHere.size;
  };

  const harvestAndNext = () => {
    const n = harvestPage();
    const next = document.querySelector('[data-qa="pager-next"]');
    if (!n) return toast('No cards found - check the page', true);
    if (next && next.href) setTimeout(() => { location.href = next.href; }, 400);
    else toast('Last page of the search reached ✔');
  };

  // =====================================================================
  // STEP 3. Full vacancies from the queue
  // =====================================================================

  const jsonLd = () => {
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const d = JSON.parse(s.textContent);
        const jp = (Array.isArray(d) ? d : [d]).find((x) => x && x['@type'] === 'JobPosting');
        if (jp) return jp;
      } catch (e) { /* ignore malformed blocks */ }
    }
    return null;
  };
  const htmlToText = (html) => {
    const prepared = html.replace(/<(br|\/p|\/li|\/h\d|\/div)[^>]*>/gi, '\n');
    const doc = new DOMParser().parseFromString(prepared, 'text/html');
    return (doc.body.textContent || '').replace(/\n{3,}/g, '\n\n').trim();
  };
  const extractSkills = () => {
    let els = [...document.querySelectorAll('[data-qa="skills-element"]')];
    if (!els.length) {
      // Fallback: tags under the "Key skills" heading (page language: RU / KZ / EN)
      const h = [...document.querySelectorAll('h2, h3')].find((x) => /ключевые навыки|негізгі дағдылар|key skills/i.test(x.innerText));
      if (h && h.parentElement) els = [...h.parentElement.querySelectorAll('li, span')].filter((e) => e.children.length === 0);
    }
    return [...new Set(els.map((e) => e.innerText.trim()).filter(Boolean))];
  };

  const extractVacancy = (id) => {
    const ld = jsonLd();
    const descEl = document.querySelector('[data-qa="vacancy-description"]');
    const description_html = descEl ? descEl.innerHTML : (ld && ld.description) || '';
    const description = descEl ? descEl.innerText.trim() : (description_html ? htmlToText(description_html) : '');
    return {
      id,
      url: vacUrl(id),
      title: firstIn(document, ['[data-qa="vacancy-title"]', 'h1']) || (ld && ld.title) || '',
      company: firstIn(document, ['[data-qa="vacancy-company-name"]']) || (ld && ld.hiringOrganization && ld.hiringOrganization.name) || '',
      location: firstIn(document, ['[data-qa="vacancy-view-raw-address"]', '[data-qa="vacancy-view-location"]']),
      experience: firstIn(document, ['[data-qa="vacancy-experience"]']),
      employment: firstIn(document, ['[data-qa="vacancy-view-employment-mode"]', '[data-qa="common-employment-text"]']),
      salary: firstIn(document, ['[data-qa="vacancy-salary"]']),
      published: (ld && ld.datePosted) || '',
      key_skills: extractSkills(),
      description,
      description_html,
      // Archived-vacancy notice on hh.kz pages (page text is in Russian)
      archived: /вакансия в архиве|вакансия закрыта/i.test(document.body.innerText.slice(0, 5000)),
    };
  };

  const goNextInQueue = (fromId) => {
    const queue = get(K_QUEUE, []);
    const full = get(K_FULL, {});
    const start = Math.max(0, queue.indexOf(fromId) + 1);
    for (let i = start; i < queue.length; i++) if (!full[queue[i]]) { location.href = vacUrl(queue[i]); return; }
    for (let i = 0; i < start; i++) if (!full[queue[i]]) { location.href = vacUrl(queue[i]); return; }
    toast('Queue completed ✔ Press E to export');
    render();
  };

  const saveVacancy = (status) => {
    const id = currentVacancyId();
    if (!id) return toast('This is not a vacancy page', true);
    const data = extractVacancy(id);
    if (status === 'saved' && !data.description) toast('⚠ Description not found - saved as is', true);
    const full = get(K_FULL, {});
    full[id] = { ...data, status, saved_at: new Date().toISOString() };
    put(K_FULL, full);
    const hist = get(K_HIST, []); hist.push(id); put(K_HIST, hist);
    goNextInQueue(id);
  };

  const undo = () => {
    const hist = get(K_HIST, []);
    const id = hist.pop();
    if (!id) return toast('Nothing to undo');
    const full = get(K_FULL, {}); delete full[id];
    put(K_FULL, full); put(K_HIST, hist);
    location.href = vacUrl(id);
  };

  const importQueue = () => {
    const raw = prompt('Paste candidate IDs (from candidates.txt). Any separator works:');
    if (!raw) return;
    const ids = [...new Set(raw.match(/\d{5,}/g) || [])];
    const queue = get(K_QUEUE, []);
    const known = new Set(queue);
    let added = 0;
    for (const id of ids) if (!known.has(id)) { queue.push(id); known.add(id); added++; }
    put(K_QUEUE, queue);
    toast(`Added to queue: ${added} (total ${queue.length})`);
    render();
  };

  const startQueue = () => {
    const queue = get(K_QUEUE, []);
    const full = get(K_FULL, {});
    const next = queue.find((id) => !full[id]);
    if (next) location.href = vacUrl(next); else toast('No unprocessed vacancies in the queue');
  };

  // =====================================================================
  // Export and reset
  // =====================================================================

  const download = (name, obj) => {
    const blob = new Blob([JSON.stringify(obj, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
  };
  const exportAll = () => {
    const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
    const cards = Object.values(get(K_CARDS, {}));
    const full = Object.values(get(K_FULL, {}));
    if (cards.length) download(`hh_cards_${stamp}.json`, { exported_at: new Date().toISOString(), searches: get(K_SEARCH, {}), cards });
    if (full.length) download(`hh_full_${stamp}.json`, { exported_at: new Date().toISOString(), vacancies: full });
    toast(`Exported: ${cards.length} cards, ${full.length} full vacancies`);
  };
  const resetAll = () => {
    if (!confirm('Delete ALL cards, the queue and saved vacancies? Export first (E).')) return;
    [K_CARDS, K_SEARCH, K_FULL, K_QUEUE, K_HIST].forEach((k) => put(k, k === K_QUEUE || k === K_HIST ? [] : {}));
    render();
  };

  // =====================================================================
  // Interface
  // =====================================================================

  let panel;
  const toast = (msg, warn) => {
    const t = document.createElement('div');
    t.textContent = msg;
    Object.assign(t.style, {
      position: 'fixed', bottom: '230px', left: '16px', zIndex: 2147483647,
      background: warn ? '#b3261e' : '#1f6f43', color: '#fff', padding: '8px 12px',
      borderRadius: '8px', font: '13px system-ui, sans-serif', boxShadow: '0 2px 8px rgba(0,0,0,.3)',
    });
    document.body.appendChild(t);
    setTimeout(() => t.remove(), warn ? 3500 : 2000);
  };

  const render = () => {
    const nCards = Object.keys(get(K_CARDS, {})).length;
    const full = get(K_FULL, {});
    const queue = get(K_QUEUE, []);
    const left = queue.filter((id) => !full[id]).length;
    const vid = currentVacancyId();
    let mode = 'Other page';
    let keys = '<b>E</b> export · <b>H</b> hide';
    if (isSearchPage()) {
      mode = 'Search results: step 1 (cards)';
      keys = '<b>N</b> harvest page and go to next<br><b>Q</b> harvest page only<br><b>E</b> export · <b>H</b> hide';
    } else if (vid) {
      const st = full[vid] ? ` · already: ${full[vid].status}` : '';
      mode = `Vacancy ${vid}: step 3${st}`;
      keys = '<b>S</b> save → next · <b>X</b> skip → next<br><b>U</b> undo · <b>G</b> start queue<br><b>I</b> import IDs · <b>E</b> export · <b>H</b> hide';
    }

    if (isAdvancedPage()) { if (panel) panel.style.display = 'none'; return; }
    if (!panel) {
      panel = document.createElement('div');
      Object.assign(panel.style, {
        position: 'fixed', bottom: '16px', left: '16px', zIndex: 2147483646,
        background: '#fff', color: '#222', border: '1px solid #ccc', borderRadius: '10px',
        font: '12px/1.45 system-ui, sans-serif', boxShadow: '0 2px 10px rgba(0,0,0,.2)',
      });
      document.body.appendChild(panel);
    }
    const ui = get(K_UI, { collapsed: false });
    if (ui.collapsed) {
      Object.assign(panel.style, { width: 'auto', padding: '6px 10px', cursor: 'pointer' });
      panel.innerHTML = `<b>RMT ▸</b> ${nCards} · ${left}/${queue.length} · ${Object.keys(full).length}`;
      panel.onclick = () => { put(K_UI, { collapsed: false }); render(); };
      return;
    }
    Object.assign(panel.style, { width: '290px', padding: '10px 12px', cursor: 'default' });
    panel.onclick = null;
    panel.innerHTML = `
      <span id="rmt-min" title="Collapse" style="float:right;cursor:pointer;padding:0 4px;font-weight:bold">—</span>
      <b>RMT collector v2</b><br>
      Cards: ${nCards} · Queue: ${left} of ${queue.length} · Full: ${Object.keys(full).length}
      <div style="margin:6px 0;color:#1f4f8f">${mode}</div>
      <div style="color:#666">${keys}</div>
      <button id="rmt-imp" style="margin-top:6px;font-size:11px">Import IDs</button>
      <button id="rmt-reset" style="margin-top:6px;font-size:11px">Reset all</button>`;
    panel.querySelector('#rmt-imp').onclick = importQueue;
    panel.querySelector('#rmt-reset').onclick = resetAll;
    panel.querySelector('#rmt-min').onclick = (e) => { e.stopPropagation(); put(K_UI, { collapsed: true }); render(); };
  };

  // Hotkeys bound to physical keys (work with any keyboard layout)
  document.addEventListener('keydown', (e) => {
    const t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const onSearch = isSearchPage();
    const onVac = !!currentVacancyId();
    const handlers = {
      KeyN: () => onSearch && harvestAndNext(),
      KeyQ: () => onSearch && harvestPage(),
      KeyS: () => onVac && saveVacancy('saved'),
      KeyX: () => onVac && saveVacancy('skipped'),
      KeyU: () => undo(),
      KeyG: () => startQueue(),
      KeyI: () => importQueue(),
      KeyE: () => exportAll(),
      KeyH: () => panel && (panel.style.display = panel.style.display === 'none' ? '' : 'none'),
    };
    if (handlers[e.code]) { e.preventDefault(); handlers[e.code](); }
  }, true);

  render();
})();
