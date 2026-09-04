const CATEGORIES = {
  online:   { label: "线上分享会", color: "var(--cat-online)" },
  offline:  { label: "线下聚会",   color: "var(--cat-offline)" },
  book:     { label: "读书会",     color: "var(--cat-book)" },
  workshop: { label: "工作坊",     color: "var(--cat-workshop)" },
  media:    { label: "自媒体/播客", color: "var(--cat-media)" },
  good:     { label: "公益/成长",  color: "var(--cat-good)" },
  other:    { label: "其他",       color: "var(--cat-other)" },
};
const ALL_EVENTS = [...EVENTS_UPCOMING, ...EVENTS_ONGOING, ...EVENTS_PAST];

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function buildFilters(containerId, dataList, onFilter) {
  const container = document.getElementById(containerId);
  const usedCats = Object.keys(CATEGORIES).filter(k => dataList.some(d => d.cat === k));

  const allChip = el("div", "chip active", "全部");
  allChip.dataset.cat = "all";
  allChip.style.background = "var(--text-primary)";
  allChip.style.color = "#fff";
  container.appendChild(allChip);

  usedCats.forEach(catKey => {
    const cat = CATEGORIES[catKey];
    const chip = el("div", "chip");
    chip.dataset.cat = catKey;
    const dot = el("span", "dot");
    dot.style.background = cat.color;
    chip.appendChild(dot);
    chip.appendChild(document.createTextNode(cat.label));
    container.appendChild(chip);
  });

  container.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      container.querySelectorAll(".chip").forEach(c => { c.classList.remove("active"); c.style.background = ""; c.style.color = ""; });
      chip.classList.add("active");
      const key = chip.dataset.cat;
      chip.style.background = key !== "all" ? CATEGORIES[key].color : "var(--text-primary)";
      chip.style.color = "#fff";
      onFilter(key);
    });
  });
}

function tagEl(catKey) {
  const cat = CATEGORIES[catKey];
  const tag = el("div", "tag");
  tag.appendChild(el("span", "dot"));
  tag.appendChild(document.createTextNode(cat.label));
  tag.style.background = cat.color;
  return tag;
}

function makeEventCard(ev) {
  const card = el("div", "card");
  card.dataset.cat = ev.cat;
  if (ev.status === "past") card.classList.add("past");
  if (NEW_SINCE.includes(ev.title)) card.classList.add("new");
  const STATUS = { upcoming: ["status-upcoming", "即将举行"], ongoing: ["status-ongoing", "长期 / 进行中"], past: ["status-past", "已举办"] };
  const sm = STATUS[ev.status] || STATUS.past;
  card.appendChild(el("div", `status-pill ${sm[0]}`, sm[1]));
  card.appendChild(tagEl(ev.cat));
  card.appendChild(el("h3", null, ev.title));
  const meta = el("div", "meta");
  ev.meta.forEach(m => meta.appendChild(el("span", null, m)));
  card.appendChild(meta);
  if (ev.thumb) {
    const img = document.createElement("img");
    img.className = "poster-thumb"; img.src = ev.thumb; img.alt = ev.title + " 海报"; img.loading = "lazy";
    card.appendChild(img);
  }
  card.appendChild(el("p", "desc", ev.desc));
  const actions = el("div", "actions");
  if (ev.calLink) {
    const a = document.createElement("a");
    a.className = "btn primary"; a.href = ev.calLink; a.target = "_blank"; a.rel = "noopener"; a.textContent = "＋ 加入 Google 日历";
    actions.appendChild(a);
  }
  if (ev.joinLink) {
    const a = document.createElement("a");
    a.className = "btn"; a.href = ev.joinLink; a.target = "_blank"; a.rel = "noopener"; a.textContent = ev.joinLabel || "参与方式";
    actions.appendChild(a);
  }
  if (actions.children.length) card.appendChild(actions);
  card.appendChild(el("div", "contact", ev.contact));
  return card;
}

function renderEvents() {
  const panels = { upcoming: EVENTS_UPCOMING, ongoing: EVENTS_ONGOING, past: EVENTS_PAST };
  Object.keys(panels).forEach(k => {
    const c = document.getElementById("events-" + k);
    c.innerHTML = "";
    if (!panels[k].length) c.appendChild(el("div", "empty", "暂无"));
    panels[k].forEach(ev => c.appendChild(makeEventCard(ev)));
    document.getElementById(`tab-${k}-count`).textContent = `(${panels[k].length})`;
  });
  document.getElementById("event-count").textContent = `(${ALL_EVENTS.length})`;
}

function setupEventTabs() {
  const tabs = document.querySelectorAll("#event-tabs .tab");
  const panels = ["upcoming", "ongoing", "past"];
  tabs.forEach(tab => tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    panels.forEach(k => document.getElementById("events-" + k).classList.toggle("hidden", k !== tab.dataset.tab));
  }));
}

function renderProjects() {
  const container = document.getElementById("projects-container");
  container.innerHTML = "";
  const ordered = [...PROJECTS.filter(p => NEW_SINCE.includes(p.name)), ...PROJECTS.filter(p => !NEW_SINCE.includes(p.name))];
  ordered.forEach(p => {
    const card = el("div", "card");
    card.dataset.cat = p.cat;
    if (NEW_SINCE.includes(p.name)) card.classList.add("new");
    card.appendChild(tagEl(p.cat));
    card.appendChild(el("h3", null, `${p.name}${p.city && p.city !== "—" ? ` · ${p.city}` : ""}`));
    card.appendChild(el("p", "desc", p.desc));
    card.appendChild(el("div", "contact", p.contact));
    container.appendChild(card);
  });
  document.getElementById("project-count").textContent = `(${PROJECTS.length})`;
}

function filterCards(containerId, cat) {
  document.querySelectorAll(`#${containerId} .card`).forEach(card => {
    card.classList.toggle("hidden", cat !== "all" && card.dataset.cat !== cat);
  });
}

renderEvents();
setupEventTabs();
renderProjects();
buildFilters("event-filters", ALL_EVENTS, cat => ["upcoming", "ongoing", "past"].forEach(k => filterCards("events-" + k, cat)));
buildFilters("project-filters", PROJECTS, cat => filterCards("projects-container", cat));
