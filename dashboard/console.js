// ============================================
// JAVIS OS - Console layer (sidebar + router)
// Bọc ngoài cockpit: rail điều hướng + trang quản lý. KHÔNG sửa app.js.
// Graph 3D tự pause khi rời cockpit (qua window.__javisGraph). Alpine cho UI.
// Thêm trang mới = thêm 1 mục vào RAIL_ITEMS + 1 case trong renderPage().
// ============================================
(function () {
  "use strict";

  // ---- Khai báo các mục trên rail (mở rộng = thêm dòng ở đây) ----
  // type 'view' = render trong cview ; có launch() = nút mở overlay/modal sẵn có.
  const APP_VERSION = "0.4.3";   // fallback hiển thị tức thời; nguồn thật là /version (file VERSION)

  // Icon SVG line-style đồng bộ (thay cho lẫn lộn emoji + ký tự)
  const _svg = (p) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  const ICON = {
    home:        _svg('<path d="M12 2l8.66 5v10L12 22 3.34 17V7L12 2z"/>'),
    chat:        _svg('<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 1 1 21 11.5z"/>'),
    overview:    _svg('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
    workflows:   _svg('<path d="M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l0-8z"/>'),
    agents:      _svg('<rect x="5" y="7" width="14" height="13" rx="2"/><path d="M12 7V3M8 3h8"/><circle cx="9.2" cy="13" r="1.1"/><circle cx="14.8" cy="13" r="1.1"/>'),
    skills:      _svg('<path d="M12 3l2.4 5.6L20 11l-5.6 2.4L12 19l-2.4-5.6L4 11l5.6-2.4L12 3z"/>'),
    automations: _svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    models:      _svg('<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>'),
    channels:    _svg('<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>'),
    mcp:         _svg('<path d="M9 2v6M15 2v6"/><path d="M7 8h10v3a5 5 0 0 1-10 0V8z"/><path d="M12 16v6"/>'),
    logs:        _svg('<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>'),
    account:     _svg('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6.5 8-6.5s8 2.5 8 6.5"/>'),
    files:       _svg('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>'),
    selfimprove: _svg('<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/>'),
    plugins:     _svg('<path d="M14 4a2 2 0 1 0-4 0v2H6a1 1 0 0 0-1 1v3H4a2 2 0 1 0 0 4h1v3a1 1 0 0 0 1 1h3v-1a2 2 0 1 1 4 0v1h3a1 1 0 0 0 1-1v-4h1a2 2 0 1 0 0-4h-1V7a1 1 0 0 0-1-1h-3V4z"/>'),
    learn:       _svg('<path d="M12 3v18"/><path d="M5 7h14"/><path d="M4 12h16"/><circle cx="12" cy="12" r="9"/>'),
    kanban:      _svg('<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="10" rx="1"/><rect x="17" y="4" width="4" height="13" rx="1"/>'),
    settings:    _svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
  };

  const RAIL_ITEMS = [
    { id: "home",        icon: ICON.home,        label: "Javis" },
    { id: "chat",        icon: ICON.chat,        label: "Trò chuyện" },
    { id: "overview",    icon: ICON.overview,    label: "Tổng quan" },
    { id: "settings",    icon: ICON.settings,    label: "Cài đặt" },
    { id: "workflows",   icon: ICON.workflows,   label: "Workflows" },
    { id: "agents",      icon: ICON.agents,      label: "Agents" },
    { id: "skills",      icon: ICON.skills,      label: "Skills" },
    { id: "files",       icon: ICON.files,       label: "Tệp tin" },
    { id: "selfimprove", icon: ICON.selfimprove, label: "Loop" },
    { id: "learn",       icon: ICON.learn,       label: "Tự học" },
    { id: "kanban",      icon: ICON.kanban,      label: "Việc" },
    { id: "automations", icon: ICON.automations, label: "Lịch" },
    { id: "models",      icon: ICON.models,      label: "Models" },
    { id: "channels",    icon: ICON.channels,    label: "Kênh" },
    { id: "mcp",         icon: ICON.mcp,         label: "Kết nối" },
    { id: "plugins",     icon: ICON.plugins,     label: "Plugins" },
    { id: "logs",        icon: ICON.logs,        label: "Cập nhật" },
    { id: "account",     icon: ICON.account,     label: "Tài khoản" },
  ];

  const VIEW_META = {
    home:        { icon: "⬡", label: "Javis OS", sub: "" },
    chat:        { icon: "💬", label: "Trò chuyện", sub: "Khung chat rộng · lịch sử hội thoại" },
    overview:    { icon: "◎", label: "Tổng quan", sub: "Trạng thái hệ thống" },
    settings:    { icon: "⚙", label: "Cài đặt", sub: "Giọng nói · avatar · tên miền" },
    workflows:   { icon: "⚡", label: "Workflows", sub: "Chuỗi agent tự động" },
    agents:      { icon: "🤖", label: "Agents", sub: "Trợ lý chuyên biệt" },
    skills:      { icon: "🧩", label: "Skills", sub: "Kỹ năng khả dụng" },
    files:       { icon: "🗂", label: "Tệp tin", sub: "Duyệt · sửa · tải file trong brain" },
    selfimprove: { icon: "♻", label: "Loop", sub: "Nhiệm vụ lặp tự động chạy nền" },
    learn:       { icon: "🧠", label: "Tự học", sub: "Rewire Memory · Wiki · Skill (an toàn, undo được)" },
    kanban:      { icon: "🗂", label: "Việc (Kanban)", sub: "Backlog + dispatcher tự làm task nền" },
    automations: { icon: "⏰", label: "Lịch tự động", sub: "Cron · trigger · routine" },
    models:      { icon: "◈", label: "Models", sub: "Main model & providers" },
    channels:    { icon: "✉", label: "Kênh kết nối", sub: "Telegram & hơn nữa" },
    mcp:         { icon: "🔌", label: "Kết nối", sub: "Nguồn dữ liệu & công cụ" },
    plugins:     { icon: "🧰", label: "Plugins", sub: "Tool/hook native cho mọi engine" },
    logs:        { icon: "🗒", label: "Nhật ký cập nhật", sub: "Phiên bản & tính năng mới" },
    account:     { icon: "⚙", label: "Tài khoản", sub: "Đăng nhập & workspace" },
  };

  // 4 trang tách từ Studio cũ - render container rồi gọi loader trong studio.js (window.JavisStudio).
  const STUDIO_PAGES = ["workflows", "agents", "skills", "automations"];

  let _settings = null;
  let _renderGen = 0;         // token chống race: mỗi lần đổi trang tăng 1; render async cũ tự bỏ
  let _fmPending = null;       // { dir, file } - vị trí mở sẵn cho trang Tệp tin (khi bấm link file/thư mục trong chat)
  let graphEnabled = true;
  const isNarrow = () => window.matchMedia("(max-width: 860px)").matches;
  const liteMode = () => !graphEnabled || isNarrow();

  const esc = (s) => (s || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  // Chỉ cho link http(s) (chặn javascript:/data: XSS); dùng kèm esc() khi nhúng vào href.
  const safeHref = (u) => /^https?:\/\//i.test((u || "").toString().trim()) ? u : "#";
  const _shield = (on) => on
    ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V5l8-3z"/><path d="M9 12l2 2 4-4"/></svg>'
    : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V5l8-3z"/></svg>';
  const body = () => document.getElementById("cviewBody");

  // Pause SỚM (chạy ngay khi parse, không chờ Alpine tải): màn hẹp → graph app.js vừa dựng
  // dừng luôn, khỏi ngốn pin/GPU trong lúc Alpine đang tải. _animate có guard _paused nên
  // dù load() chạy xong gọi lại cũng không bật lại.
  if (isNarrow() && window.__javisGraph) { try { window.__javisGraph.pause(); } catch (e) {} }

  // ---- Điều khiển graph: chỉ chạy khi đang ở cockpit + không lite + không mở Studio ----
  function recomputeGraph() {
    const g = window.__javisGraph;
    if (!g) return;
    const studioOpen = !!document.getElementById("studio")?.classList.contains("open");
    const active = window.Alpine ? Alpine.store("nav").active : "home";
    const shouldRun = !liteMode() && active === "home" && !studioOpen;
    if (shouldRun) g.wake(); else g.pause();
  }

  // ---- Chuyển trang (có View Transition cho mượt) ----
  // Hook "rời trang": trang nào mượn DOM dùng chung (vd tab Trò chuyện mượn khung chat của
  // cockpit) đặt _pageLeave để TRẢ node về chỗ cũ TRƯỚC khi cviewBody bị ghi đè / cview bị ẩn.
  let _pageLeave = null;
  function navigateTo(id) {
    const store = Alpine.store("nav");
    if (store.active === id) return;   // đang ở trang này → khỏi đổi (tránh nháy + mượn/trả node thừa)
    const swap = () => {
      const leave = _pageLeave; _pageLeave = null;
      if (leave) { try { leave(); } catch (e) {} }   // dọn trang cũ trước khi thay nội dung
      store.active = id;
      // Nút điều khiển cockpit (⚙🔊↻) chỉ hiện ở trang Javis, không hiện navbar trang quản lý
      document.body.classList.toggle("in-console", id !== "home");
      // Rời trang Cài đặt → cất #quickSet về holder TRƯỚC khi cviewBody bị ghi đè (giữ node + handler).
      if (id !== "settings") parkQuickSet();
      if (id !== "home") renderPage(id);
      recomputeGraph();
    };
    // Dính tab Trò chuyện thì BỎ View Transition: nó chụp snapshot cảnh 3D nặng của home rồi
    // cross-fade → loé orb ~1s (bitmap chụp trước cả khi ẩn graph). Swap thẳng cho sạch, tức thì.
    const skipVT = (id === "chat" || store.active === "chat");
    if (document.startViewTransition && !skipVT) document.startViewTransition(swap);
    else swap();
  }

  // Mở trang Tệp tin ĐÚNG vị trí một file/thư mục (gọi từ link trong chat qua window.JavisOpenFiles,
  // hoặc từ deep-link #open=<đường-dẫn> khi mở ở tab trình duyệt mới). fullPath tương đối GỐC BRAIN
  // (đúng quy ước AI ghi trong chat); trang Tệp tin sẽ tự ghép tiền tố brain để ra path tương đối trần.
  function openFilesAt(fullPath) {
    const raw = String(fullPath == null ? "" : fullPath);
    const clean = raw.replace(/^\.?\//, "").replace(/\/+$/, "");
    const i = clean.lastIndexOf("/");
    const base = i >= 0 ? clean.slice(i + 1) : clean;
    const parent = i >= 0 ? clean.slice(0, i) : "";
    const isDir = /\/$/.test(raw) || (base !== "" && base.indexOf(".") < 0);   // gạch chéo cuối hoặc không có đuôi → thư mục
    _fmPending = isDir ? { dir: clean, file: "" } : { dir: parent, file: base };
    // Chat mở dạng overlay phóng to (chat-stage) sẽ che trang Tệp tin → thu lại trước cho thấy kết quả.
    try { if (window.JavisChatStage && window.JavisChatStage.isOpen()) window.JavisChatStage.collapse(); } catch (e) {}
    const active = window.Alpine ? Alpine.store("nav").active : "";
    if (active === "files") renderPage("files");   // đã ở trang Tệp tin → nạp lại để nhảy tới vị trí mới
    else navigateTo("files");
  }
  if (typeof window !== "undefined") window.JavisOpenFiles = openFilesAt;
  // Mở note trong editor cây (dùng cho click node đồ thị) từ đường dẫn TƯƠNG ĐỐI GỐC BRAIN (như openNodePopup).
  if (typeof window !== "undefined") window.JavisOpenNote = function (brainRel) {
    if (!brainRel) return;
    const ceilingRel = _vtHome ? _vtHome + "/" + brainRel : brainRel;   // ghép tiền tố trần như cây
    const name = brainRel.split("/").pop();
    const ext = name.includes(".") ? "." + name.split(".").pop().toLowerCase() : ".md";
    openNote(ceilingRel, { name: name, ext: ext, type: "file" });
  };

  // ============================================
  // Render từng trang vào #cviewBody
  // ============================================
  async function renderPage(id) {
    let el = body();
    if (!el) return;
    // Thay #cviewBody bằng node MỚI mỗi lần đổi trang: renderer async của trang CŨ (đang await
    // fetch) nếu ghi trễ (el.innerHTML=...) sẽ ghi vào node cũ ĐÃ THÁO RỜI → vô hại, không phá
    // nội dung/nút của trang mới. Đặc biệt bảo vệ các node chat mà tab Trò chuyện mượn vào
    // cviewBody (trước đây bị 1 render async trễ xoá mất → chat vỡ). Cũng hết nháy nội dung cũ.
    const fresh = el.cloneNode(false); el.parentNode.replaceChild(fresh, el); el = fresh;
    _renderGen++;   // đổi trang → vô hiệu mọi render async đang dở (guard bổ sung cho renderer đã có)
    if (id === "chat")     return renderChat(el);
    if (STUDIO_PAGES.includes(id)) return renderStudioPage(el, id);
    if (id === "overview") return renderOverview(el);
    if (id === "settings") return renderSettings(el);
    if (id === "models")   return renderModels(el);
    if (id === "mcp")      return renderConnect(el);
    if (id === "plugins")  return renderPlugins(el);
    if (id === "channels") return renderChannels(el);
    if (id === "account")  return renderAccount(el);
    if (id === "files")    return renderFiles(el);
    if (id === "selfimprove") return renderSelfImprove(el);
    if (id === "learn")    return renderLearn(el);
    if (id === "kanban")   return renderKanban(el);
    if (id === "logs")     return renderLogs(el);
    el.innerHTML = placeholder(id);
  }

  // Trang Studio: tạo panel-<id> trong cview rồi gọi loader cũ (studio.js fill vào đó).
  function renderStudioPage(el, id) {
    el.innerHTML = `<div class="stab-panel" id="panel-${id}"></div>`;
    const fn = window.JavisStudio && window.JavisStudio[id];
    if (fn) { try { fn(); } catch (e) { el.innerHTML = placeholder(id, "Lỗi nạp: " + e.message); } }
    else el.innerHTML = placeholder(id, "studio.js chưa sẵn sàng.");
  }

  function placeholder(id, note) {
    const m = VIEW_META[id] || {};
    return `<div class="cview-placeholder">
      <div class="ph-ico">${m.icon || "✦"}</div>
      <div><b>${esc(m.label || id)}</b> - đang phát triển</div>
      <div style="max-width:380px;font-size:14px;opacity:.7">${esc(note || "Trang này là chỗ cắm chức năng mở rộng sau. Khung điều hướng đã sẵn sàng.")}</div>
    </div>`;
  }

  // ============================================
  // Trang Cập nhật (Nhật ký phiên bản / changelog)
  // ============================================
  let _clCss = false;
  function _injectChangelogCss() {
    if (_clCss) return; _clCss = true;
    const css = `
    .cl-wrap{max-width:760px}
    .cl-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px}
    .cl-cur{font-size:15px;color:#cdd8ee}
    .cl-badge{padding:3px 11px;border-radius:20px;font-size:13px;font-weight:600;border:1px solid rgba(255,255,255,.14)}
    .cl-badge.up{background:rgba(120,180,255,.14);border-color:rgba(120,180,255,.5);color:#bcd2ff}
    .cl-badge.ok{background:rgba(44,122,75,.15);border-color:#2c7a4b;color:#8fe3ad}
    .cl-note{font-size:14px;color:#8a97b4;margin:2px 0 18px}
    .cl-note code{background:rgba(255,255,255,.06);padding:1px 6px;border-radius:5px}
    .cl-rel{position:relative;padding:0 0 6px 22px;border-left:2px solid rgba(120,180,255,.22);margin-left:6px}
    .cl-rel:last-child{border-left-color:transparent}
    .cl-rel:before{content:"";position:absolute;left:-8px;top:5px;width:12px;height:12px;border-radius:50%;background:#0a0f1c;border:2px solid rgba(120,180,255,.5)}
    .cl-rel.cur:before{background:#2c7a4b;border-color:#3fdc86;box-shadow:0 0 0 4px rgba(63,220,134,.14)}
    .cl-rel.new:before{background:#3b6fd0;border-color:#7fb0ff}
    .cl-rtop{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
    .cl-ver{font-size:18px;font-weight:700;color:#e7eefc}
    .cl-date{font-size:13px;color:#7d8aa6}
    .cl-tag{font-size:12px;padding:2px 9px;border-radius:12px;font-weight:600}
    .cl-tag.cur{background:rgba(63,220,134,.16);color:#8fe3ad}
    .cl-tag.new{background:rgba(120,180,255,.16);color:#bcd2ff}
    .cl-sec{margin:0 0 12px}
    .cl-sec h4{margin:8px 0 5px;font-size:14px;color:#aebbd6;font-weight:600}
    .cl-sec ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:5px}
    .cl-sec li{font-size:14.5px;color:#cdd8ee;line-height:1.5;padding-left:24px;position:relative}
    .cl-sec li:before{position:absolute;left:0;top:0}
    .cl-sec.feat li:before{content:"✨"} .cl-sec.fix li:before{content:"🔧"}
    .cl-sec.imp li:before{content:"⚡"} .cl-sec.sec li:before{content:"🔒"}
    .cl-sec.doc li:before{content:"📖"} .cl-sec.other li:before{content:"•"}
    .cl-empty{color:#8a97b4;font-size:15px}`;
    const s = document.createElement("style"); s.textContent = css; document.head.appendChild(s);
  }
  function _clSecClass(title) {
    const t = (title || "").toLowerCase();
    if (t.includes("thêm") || t.includes("mới")) return "feat";
    if (t.includes("sửa") || t.includes("lỗi") || t.includes("fix")) return "fix";
    if (t.includes("cải thiện") || t.includes("improve")) return "imp";
    if (t.includes("bảo mật") || t.includes("security")) return "sec";
    if (t.includes("tài liệu") || t.includes("doc")) return "doc";
    return "other";
  }
  async function renderLogs(el) {
    _injectChangelogCss();
    const myGen = _renderGen;
    el.innerHTML = `<div class="cl-wrap"><div class="cl-note">Đang tải nhật ký cập nhật...</div></div>`;
    let d;
    try {
      const r = await fetch("/changelog");
      d = await r.json();
    } catch (e) {
      if (myGen !== _renderGen) return;
      el.innerHTML = `<div class="cl-wrap"><div class="cl-empty">Không tải được nhật ký cập nhật. Hãy tải lại trang.</div></div>`;
      return;
    }
    if (myGen !== _renderGen) return;   // đã đổi trang trong lúc chờ
    const cur = d.current || "?";
    const upBadge = d.update_available
      ? `<span class="cl-badge up">Có bản mới: v${esc(d.latest)}</span>`
      : `<span class="cl-badge ok">Đang ở bản mới nhất</span>`;
    const upNote = d.update_available
      ? `<div class="cl-note">Cập nhật ở mục <b>Tổng quan</b>: bản có Watchtower bấm "Cập nhật ngay"; bản Docker khác thì <b>Redeploy</b> (Hostinger) hoặc <code>docker compose up -d --pull always</code>; bản VPS chạy <code>./update.sh</code>.</div>`
      : "";
    const rels = d.releases || [];
    const timeline = rels.length ? rels.map(rel => {
      const cls = rel.is_current ? "cur" : (rel.installed ? "" : "new");
      const tag = rel.is_current ? `<span class="cl-tag cur">đang dùng</span>`
        : (!rel.installed ? `<span class="cl-tag new">bản mới</span>` : "");
      const secs = (rel.sections || []).map(s => {
        const items = (s.items || []).map(it => `<li>${esc(it)}</li>`).join("");
        return `<div class="cl-sec ${_clSecClass(s.title)}"><h4>${esc(s.title)}</h4><ul>${items}</ul></div>`;
      }).join("");
      return `<div class="cl-rel ${cls}">
        <div class="cl-rtop"><span class="cl-ver">v${esc(rel.version)}</span>${rel.date ? `<span class="cl-date">${esc(rel.date)}</span>` : ""}${tag}</div>
        ${secs || '<div class="cl-empty">(không có chi tiết)</div>'}
      </div>`;
    }).join("") : `<div class="cl-empty">Chưa có nhật ký. Thêm file <code>CHANGELOG.md</code> ở gốc dự án.</div>`;
    el.innerHTML = `<div class="cl-wrap">
      <div class="cl-head"><span class="cl-cur">Đang cài: <b>v${esc(cur)}</b></span>${upBadge}</div>
      ${upNote}
      ${timeline}
    </div>`;
  }

  const fbrain = () => (window.currentBrainPath ? currentBrainPath() : "brain");

  // ============================================
  // Trang Tệp tin (File Manager)
  // ============================================
  function _humanSize(n) { if (n < 1024) return n + " B"; if (n < 1048576) return (n / 1024).toFixed(1) + " KB"; return (n / 1048576).toFixed(1) + " MB"; }
  function _fileIcon(ext) {
    if ([".md", ".txt"].includes(ext)) return "📝";
    if ([".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"].includes(ext)) return "🖼";
    if ([".json", ".yaml", ".yml", ".toml", ".ini", ".env"].includes(ext)) return "⚙";
    if ([".js", ".ts", ".py", ".sh", ".bat", ".css", ".html"].includes(ext)) return "📜";
    if ([".mp3", ".wav", ".ogg"].includes(ext)) return "🎵";
    if (ext === ".pdf") return "📕";
    return "📄";
  }
  let _fmCss = false;
  function _injectExtraCss() {
    if (_fmCss) return; _fmCss = true;
    const css = `
    .fm-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
    .fm-crumb{flex:1;min-width:160px;font-size:15px;color:#9fb0cf}
    .fm-crumb a{color:#bcd2ff;cursor:pointer;text-decoration:none} .fm-crumb a:hover{text-decoration:underline}
    .fm-actions{display:flex;gap:6px;flex-wrap:wrap}
    .fm-uplabel{cursor:pointer}
    .fm-list{display:flex;flex-direction:column;border:1px solid rgba(255,255,255,.08);border-radius:10px;overflow:hidden}
    .fm-row{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid rgba(255,255,255,.05);cursor:default}
    .fm-row:last-child{border-bottom:none} .fm-row:hover{background:rgba(120,180,255,.06)}
    .fm-ico{flex:none} .fm-name{flex:1;color:#e7eefc;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .fm-row.is-dir .fm-ico,.fm-row.is-dir .fm-name{cursor:pointer}
    .fm-row.fm-target{box-shadow:inset 3px 0 0 #7fb0ff;background:rgba(120,180,255,.10);animation:fmFlash 1.7s ease}
    @keyframes fmFlash{0%,45%{background:rgba(120,180,255,.42)}100%{background:rgba(120,180,255,.10)}}
    .fm-size{color:#7d8aa6;font-size:13px;min-width:60px;text-align:right}
    .fm-row-act{display:flex;gap:5px;opacity:0;transition:.15s} .fm-row:hover .fm-row-act{opacity:1}
    .fm-row-act button{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);color:#aebbd6;cursor:pointer;font-size:13px;padding:3px 9px;border-radius:6px;white-space:nowrap} .fm-row-act button:hover{color:#fff;border-color:rgba(120,180,255,.5)}
    .fm-row-act button.danger:hover{color:#ff9a9a;border-color:rgba(255,120,120,.5)}
    .fm-modal{position:fixed;inset:0;z-index:9999;display:none;background:rgba(4,8,18,.62);backdrop-filter:blur(3px);align-items:center;justify-content:center;padding:24px}
    .fm-modal.open{display:flex}
    .fm-modal-card{width:min(920px,94vw);max-height:86vh;display:flex;flex-direction:column;background:#0a0f1c;border:1px solid rgba(120,180,255,.3);border-radius:12px;box-shadow:0 24px 70px rgba(0,0,0,.6);overflow:hidden}
    .fm-vhead{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 14px;border-bottom:1px solid rgba(255,255,255,.08);color:#e7eefc;font-size:16px}
    .fm-vhead b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .fm-vhead button{background:none;border:1px solid rgba(255,255,255,.15);color:#cfe0ff;border-radius:6px;cursor:pointer;padding:4px 10px;margin-left:6px} .fm-vhead button:hover{border-color:rgba(120,180,255,.6)}
    .fm-modal-card textarea{width:100%;flex:1;min-height:56vh;background:#070b16;color:#dce6fb;border:none;outline:none;padding:14px;font:15px/1.55 ui-monospace,Consolas,monospace;resize:none}
    .fm-readbox{padding:16px;color:#9ab;overflow:auto;max-height:70vh}
    .si-grid{display:flex;flex-direction:column;gap:14px;max-width:640px}
    .si-field label{display:block;font-size:14px;color:#9fb0cf;margin-bottom:5px}
    .si-field select,.si-field input,.si-field textarea{width:100%;padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.12);background:#070b16;color:#dce6fb;font-size:15px;outline:none}
    .si-field textarea{min-height:80px;resize:vertical;font-family:inherit}
    .si-row{display:flex;gap:10px;flex-wrap:wrap}
    .si-chip{padding:7px 14px;border-radius:20px;border:1px solid rgba(255,255,255,.14);background:rgba(15,22,40,.6);color:#cfe0ff;cursor:pointer;font-size:14px}
    .si-chip.sel{border-color:#ff8a3c;background:rgba(255,138,60,.15);color:#ffd0a8}
    .si-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}
    .si-status{margin-top:16px;padding:12px 14px;border-radius:10px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);font-size:15px;color:#cdd8ee}
    .si-log{margin-top:16px} .si-log .le{padding:10px 12px;border-left:2px solid rgba(120,180,255,.4);background:rgba(255,255,255,.02);margin-bottom:8px;border-radius:0 8px 8px 0;font-size:14px;white-space:pre-wrap;color:#bcc8e2}`;
    const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  }

  async function renderFiles(el) {
    _injectExtraCss();
    let cur = "";
    el.innerHTML = `<div class="cview-section">
      <div class="fm-bar">
        <div class="fm-crumb" id="fmCrumb"></div>
        <div class="fm-actions">
          <button class="s-btn-ghost" id="fmUp">↑ Lên</button>
          <button class="s-btn-ghost" id="fmHome" title="Về thư mục brain">⌂ Brain</button>
          <button class="s-btn-ghost" id="fmNewDir">+ Thư mục</button>
          <button class="s-btn-ghost" id="fmNewFile">+ File</button>
          <label class="s-btn-ghost fm-uplabel">⤓ Tải lên<input type="file" id="fmUpload" hidden multiple></label>
          <button class="s-btn-ghost" id="fmRefresh">↻</button>
        </div>
      </div>
      <div id="fmList" class="fm-list">Đang tải...</div>
    </div>
    <div id="fmModal" class="fm-modal"><div class="fm-modal-card" id="fmModalCard"></div></div>`;
    const listEl = el.querySelector("#fmList"), crumbEl = el.querySelector("#fmCrumb");
    const modal = el.querySelector("#fmModal"), card = el.querySelector("#fmModalCard");
    const closeModal = () => modal.classList.remove("open");
    modal.onclick = (e) => { if (e.target === modal) closeModal(); };
    const TEXT_EDIT_EXTS = [".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".js", ".ts", ".py", ".html", ".css", ".toml", ".ini", ".log", ".sh", ".bat", ".xml", ".svg", ".env"];
    const IMG_EXTS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico"];   // .svg = sửa text
    // URL tĩnh phục vụ file inline (ảnh hiện, pdf mở tab). dl=1 → ép tải về.
    const rawUrl = (rel, dl) => `/files/raw?brain=${encodeURIComponent(fbrain())}&path=${encodeURIComponent(rel)}${dl ? "&dl=1" : ""}`;

    // upTarget: đường dẫn nút "Lên" sẽ tới (null = đã ở trần → ẩn nút). Do server tính (parent).
    let upTarget = null;
    async function load(path) {
      // path === undefined → điểm vào mặc định (brain); "" = trần (ổ đĩa); chuỗi = tương đối trần
      listEl.innerHTML = "Đang tải...";
      const qp = (path === undefined || path === null) ? "" : `&path=${encodeURIComponent(path)}`;
      let resp, d;
      try { resp = await fetch(`/files/list?brain=${encodeURIComponent(fbrain())}${qp}`); d = await resp.json().catch(() => ({})); }
      catch (e) { listEl.innerHTML = `<div class="empty" style="padding:20px;color:#d98">Lỗi kết nối: ${esc(e.message)}</div>`; return; }
      if (!resp.ok || d.error) {
        const msg = d.error || (resp.status === 404
          ? "Máy chủ Javis chưa có chức năng Tệp tin - hãy KHỞI ĐỘNG LẠI server (stop-javis.bat → start-javis.vbs) rồi tải lại trang."
          : resp.status === 401 ? "Phiên đăng nhập hết hạn - tải lại trang & đăng nhập."
          : "Lỗi máy chủ (" + resp.status + ").");
        listEl.innerHTML = `<div class="empty" style="padding:20px;color:#d98">⚠ ${esc(msg)}</div>`; return;
      }
      cur = d.path || ""; upTarget = d.parent;
      const upBtn = el.querySelector("#fmUp"); if (upBtn) upBtn.style.display = (upTarget === null || upTarget === undefined) ? "none" : "";
      crumb(d.root);
      const items = d.items || [];
      if (!items.length) { listEl.innerHTML = `<div class="empty" style="padding:20px;text-align:center;color:#6b7894">Thư mục trống.</div>`; return; }
      listEl.innerHTML = ""; items.forEach(it => listEl.appendChild(row(it)));
    }
    function crumb(rootName) {
      const parts = cur ? cur.split("/") : []; let acc = "";
      let html = `<a data-p="">🏠 ${esc(rootName || "brain")}</a>`;
      parts.forEach(p => { acc = acc ? acc + "/" + p : p; html += ` / <a data-p="${esc(acc)}">${esc(p)}</a>`; });
      crumbEl.innerHTML = html;
      crumbEl.querySelectorAll("a").forEach(a => a.onclick = () => load(a.dataset.p));
    }
    function row(it) {
      const div = document.createElement("div"); div.className = "fm-row" + (it.type === "dir" ? " is-dir" : "");
      const rel = cur ? cur + "/" + it.name : it.name;
      const editable = it.type === "file" && TEXT_EDIT_EXTS.includes(it.ext);
      const viewable = it.type === "file" && (IMG_EXTS.includes(it.ext) || it.ext === ".pdf");
      let acts = "";
      if (editable) acts += '<button data-act="edit" title="Sửa nội dung">Sửa</button>';
      else if (viewable) acts += '<button data-act="view" title="Xem trước">Xem</button>';
      else if (it.type === "file") acts += '<button data-act="open" title="Mở trong tab mới">Mở</button>';
      acts += '<button data-act="ren" title="Đổi tên">Đổi tên</button>';
      if (it.type === "file") acts += '<button data-act="dl" title="Tải về">Tải</button>';
      acts += '<button data-act="del" class="danger" title="Xoá">Xoá</button>';
      div.innerHTML = `<span class="fm-ico">${it.type === "dir" ? "📁" : _fileIcon(it.ext)}</span>
        <span class="fm-name">${esc(it.name)}</span>
        <span class="fm-size">${it.type === "dir" ? "" : _humanSize(it.size)}</span>
        <span class="fm-row-act">${acts}</span>`;
      // Click TÊN: thư mục → mở vào; ảnh/pdf/text → xem trước; file khác → mở tab mới.
      const nameGo = it.type === "dir" ? () => load(rel)
        : (editable || viewable) ? () => openFile(rel, it)
        : () => window.open(rawUrl(rel), "_blank");
      div.querySelector(".fm-name").onclick = nameGo; div.querySelector(".fm-ico").onclick = nameGo;
      div.querySelectorAll("[data-act]").forEach(b => b.onclick = (e) => {
        e.stopPropagation(); const a = b.dataset.act;
        if (a === "edit" || a === "view") openFile(rel, it);
        else if (a === "open") window.open(rawUrl(rel), "_blank");
        else if (a === "dl") window.open(rawUrl(rel, 1), "_blank");
        else if (a === "ren") doRename(rel, it.name);
        else if (a === "del") doDelete(rel, it.name);
      });
      return div;
    }
    async function openFile(rel, it) {
      modal.classList.add("open");
      const _raw = rawUrl(rel), _ext = it.ext || "";
      const _vhead = `<div class="fm-vhead"><b>${esc(it.name)}</b><span><a href="${_raw}" target="_blank"><button>↗ Tab mới</button></a> <a href="${rawUrl(rel, 1)}"><button>⤓ Tải</button></a> <button id="fmVClose">✕</button></span></div>`;
      // Ảnh / PDF: xem trước ngay qua /files/raw (không cần đọc dạng text).
      if (IMG_EXTS.includes(_ext)) {
        card.innerHTML = _vhead + `<div class="fm-readbox" style="text-align:center;overflow:auto"><img src="${_raw}" alt="${esc(it.name)}" style="max-width:100%;height:auto;border-radius:8px"></div>`;
        card.querySelector("#fmVClose").onclick = closeModal; return;
      }
      if (_ext === ".pdf") {
        card.innerHTML = _vhead + `<iframe src="${_raw}" style="width:100%;height:72vh;border:0;background:#fff"></iframe>`;
        card.querySelector("#fmVClose").onclick = closeModal; return;
      }
      card.innerHTML = `<div class="fm-vhead"><b>${esc(it.name)}</b><button id="fmVClose">✕</button></div><div class="fm-readbox">Đang mở...</div>`;
      card.querySelector("#fmVClose").onclick = closeModal;
      let resp, d;
      try { resp = await fetch(`/files/read?brain=${encodeURIComponent(fbrain())}&path=${encodeURIComponent(rel)}`); d = await resp.json().catch(() => ({})); }
      catch (e) { card.querySelector(".fm-readbox").innerHTML = `<span style="color:#d98">Lỗi: ${esc(e.message)}</span>`; return; }
      const dlUrl = `/files/download?brain=${encodeURIComponent(fbrain())}&path=${encodeURIComponent(rel)}`;
      if (!resp.ok || d.error) {
        const m = d.error || (resp.status === 404 ? "Server chưa có chức năng Tệp tin - khởi động lại server Javis."
          : resp.status === 401 ? "Hết phiên đăng nhập - tải lại trang." : "Lỗi (" + resp.status + ")");
        card.querySelector(".fm-readbox").innerHTML = `<span>${esc(m)} - <a href="${_raw}" target="_blank" style="color:#bcd2ff">Mở trong tab mới</a> · <a href="${rawUrl(rel, 1)}" style="color:#bcd2ff">Tải về</a></span>`;
        return;
      }
      const head = `<div class="fm-vhead"><b>${esc(d.name)}</b><span>${d.editable ? '<button id="fmSave">💾 Lưu</button>' : '<a href="' + dlUrl + '" target="_blank"><button>⤓ Tải</button></a>'}<button id="fmVClose">✕</button></span></div>`;
      if (d.editable) {
        card.innerHTML = head + `<textarea id="fmText" spellcheck="false">${esc(d.content)}</textarea>`;
        card.querySelector("#fmSave").onclick = async () => {
          const f = new FormData(); f.append("brain", fbrain()); f.append("path", rel); f.append("content", card.querySelector("#fmText").value);
          const r = await (await fetch("/files/write", { method: "POST", body: f })).json();
          const b = card.querySelector("#fmSave"); b.textContent = r.ok ? "✓ Đã lưu" : "⚠ Lỗi"; setTimeout(() => b.textContent = "💾 Lưu", 1500);
        };
      } else {
        card.innerHTML = head + `<div class="fm-readbox"><pre style="white-space:pre-wrap;margin:0;color:#cdd8ee">${esc(d.content || "")}</pre></div>`;
      }
      card.querySelector("#fmVClose").onclick = closeModal;
    }
    async function doRename(rel, oldname) {
      const nn = prompt("Tên mới:", oldname); if (!nn || nn === oldname) return;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel); fd.append("newname", nn);
      await fetch("/files/rename", { method: "POST", body: fd }); load(cur);
    }
    async function doDelete(rel, name) {
      if (!confirm(`Xoá "${name}"? Không thể hoàn tác.`)) return;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel);
      await fetch("/files/delete", { method: "POST", body: fd }); load(cur);
    }
    el.querySelector("#fmUp").onclick = () => { if (upTarget !== null && upTarget !== undefined) load(upTarget); };
    el.querySelector("#fmHome").onclick = () => load(undefined);   // undefined = về brain (điểm vào mặc định)
    el.querySelector("#fmRefresh").onclick = () => load(cur);
    el.querySelector("#fmNewDir").onclick = async () => {
      const n = prompt("Tên thư mục mới:"); if (!n) return;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", cur); fd.append("name", n);
      await fetch("/files/mkdir", { method: "POST", body: fd }); load(cur);
    };
    el.querySelector("#fmNewFile").onclick = async () => {
      const n = prompt("Tên file mới (vd ghi-chu.md):"); if (!n) return;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", (cur ? cur + "/" : "") + n); fd.append("content", "");
      await fetch("/files/write", { method: "POST", body: fd }); load(cur);
    };
    el.querySelector("#fmUpload").onchange = async (e) => {
      for (const f of e.target.files) {
        const fd = new FormData(); fd.append("file", f); fd.append("brain", fbrain()); fd.append("path", cur);
        await fetch("/files/upload", { method: "POST", body: fd });
      }
      load(cur);
    };
    // Sau khi nạp thư mục: cuộn tới đúng file mục tiêu + tô sáng để "tìm thấy vị trí" ngay.
    function revealFile(name) {
      let hit = null;
      listEl.querySelectorAll(".fm-row").forEach(r => {
        r.classList.remove("fm-target");
        const nm = r.querySelector(".fm-name");
        if (nm && nm.textContent === name) hit = r;
      });
      if (!hit) return;
      hit.classList.add("fm-target");
      try { hit.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (e) {}
    }
    // Mở đúng vị trí một mục tiêu từ chat: path trong chat tương đối GỐC BRAIN, còn load() tính theo
    // TRẦN duyệt → cần ghép tiền tố brain (home) mà /files/list trả về.
    async function openVaultTarget(brainRelDir, fileName) {
      let home = "";
      try { const d = await (await fetch(`/files/list?brain=${encodeURIComponent(fbrain())}`)).json(); home = d.home || ""; }
      catch (e) {}
      const full = brainRelDir ? (home ? home + "/" + brainRelDir : brainRelDir) : (home || undefined);
      await load(full);
      if (fileName) revealFile(fileName);
    }
    const pend = _fmPending; _fmPending = null;
    if (pend) openVaultTarget(pend.dir, pend.file);
    else load();   // undefined → điểm vào mặc định = brain (dù trần duyệt có thể là cả ổ đĩa)
  }

  // ============================================
  // Trang Tự cải thiện (Nhiệm vụ tự động chạy nền)
  // ============================================
  // ============================================
  // Trang PLUGINS - tool/hook native cho mọi engine (bundled / toàn cục / brain)
  // ============================================
  async function renderPlugins(el) {
    _injectExtraCss();
    const myGen = _renderGen;   // chống race: đổi trang → load dở tự bỏ
    el.innerHTML = `<div class="cview-section"><div class="empty">Đang tải...</div></div>`;

    const SRC = { bundled: ["Có sẵn", "#3fdc86"], user: ["Toàn cục", "#6ea8ff"], vault: ["Brain này", "#e0a04a"] };
    const srcBadge = (s) => {
      const [t, c] = SRC[s] || [s, "#9fb0cf"];
      return `<span style="font-size:11px;padding:2px 7px;border-radius:99px;border:1px solid ${c}55;color:${c}">${esc(t)}</span>`;
    };
    const chip = (t) => `<span style="font-size:11px;padding:2px 7px;border-radius:6px;background:rgba(255,255,255,.06);color:#b9c6e2;margin:0 4px 4px 0;display:inline-block">${esc(t)}</span>`;
    const MM = { readonly: "chỉ đọc", safe: "ghi (safe)", full: "toàn quyền" };

    function card(p) {
      const status = p.error ? `<span style="color:#e0664a">⚠ lỗi</span>`
        : p.gated ? `<span style="color:#e0a04a">⚠ chờ bật env</span>`
        : p.loaded ? `<span style="color:#3fdc86">● đang chạy</span>`
        : p.enabled ? `<span style="color:#e0a04a">● bật (chưa nạp)</span>`
        : `<span style="color:#6b7894">○ tắt</span>`;
      const meta = [MM[p.min_mode] ? `quyền tối thiểu: ${MM[p.min_mode]}` : "",
                    p.version ? `v${esc(p.version)}` : "", p.author ? esc(p.author) : ""].filter(Boolean).join(" · ");
      const chips = (p.tools || []).map(t => chip("🔧 " + t)).join("") + (p.hooks || []).map(h => chip("🪝 " + h)).join("");
      const div = document.createElement("div");
      div.className = "wf-card" + (p.loaded ? "" : " off");
      div.innerHTML = `
        <div class="wf-top">
          <div class="wf-name">🧩 ${esc(p.name)} <span class="dim" style="font-size:12px">${esc(p.slug)}</span> ${srcBadge(p.source)}</div>
          <div>${status}</div>
        </div>
        <div class="wf-desc">${esc(p.description || "")}</div>
        <div class="wf-steps">${meta}${chips ? `<div style="margin-top:8px">${chips}</div>` : ""}${p.error ? `<div style="margin-top:6px;color:#e0664a">${esc(p.error)}</div>` : ""}</div>
        <div class="wf-actions"><button class="s-btn-ghost tgl">${p.enabled ? "Tắt" : "Bật"}</button></div>`;
      div.querySelector(".tgl").onclick = async () => {
        const fd = new FormData();
        fd.append("slug", p.slug); fd.append("enabled", p.enabled ? "0" : "1"); fd.append("brain", fbrain());
        let r = {}; try { r = await (await fetch("/plugins/toggle", { method: "POST", body: fd })).json(); } catch (e) { r = { error: e.message }; }
        if (r && r.error) alert("⚠ " + r.error);
        else if (r && r.note) alert(r.note);
        load();
      };
      return div;
    }

    async function load() {
      if (myGen !== _renderGen) return;
      let d = { plugins: [] };
      try { d = await (await fetch(`/plugins?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) {}
      if (myGen !== _renderGen) return;
      const intro = `<p style="color:#9fb0cf;font-size:15px;max-width:720px;margin:0 0 12px">Plugin thêm <b>tool</b> (công cụ engine gọi được) và <b>hook</b> native cho Javis mà không sửa lõi - dùng được ở MỌI engine (Claude Code, Codex, API) qua hub, tôn trọng 3 mức quyền như tool khác.</p>`;
      const gateBanner = (!d.user_gate) ? `<div style="margin-bottom:14px;padding:11px 13px;border:1px solid rgba(224,160,74,.5);border-radius:10px;background:rgba(224,160,74,.08);color:#ffd9a0;font-size:13px;line-height:1.55"><b>⚠ Plugin do bạn cài đang bị chặn.</b> Plugin toàn cục/brain chạy code Python thật trong server nên mặc định TẮT. Để bật: đặt biến môi trường <code>JAVIS_ENABLE_USER_PLUGINS=true</code> rồi khởi động lại Javis. Plugin có sẵn (bundled) vẫn chạy bình thường.</div>` : "";
      const dirHint = `<p style="color:#6b7894;font-size:12.5px;margin:0 0 14px">Thả plugin TOÀN CỤC (dùng cho MỌI brain) vào <code>${esc(d.global_dir || "")}</code> · mỗi plugin gồm <code>plugin.yaml</code> + <code>plugin.py</code>. Hoặc bảo Javis trong khung chat: "tạo plugin ...".</p>`;
      const plugins = (d.plugins || []).slice();
      const order = { bundled: 0, user: 1, vault: 2 };
      plugins.sort((a, b) => (order[a.source] ?? 9) - (order[b.source] ?? 9) || (a.name || "").localeCompare(b.name || ""));
      const wrap = document.createElement("div");
      wrap.className = "cview-section";
      wrap.innerHTML = intro + gateBanner + dirHint + `<div id="plCards"></div>`;
      const host = wrap.querySelector("#plCards");
      if (!plugins.length) host.innerHTML = `<div class="empty">Chưa có plugin nào. Thả một thư mục plugin vào ${esc(d.global_dir || "thư mục plugins toàn cục")} rồi tải lại.</div>`;
      else plugins.forEach(p => host.appendChild(card(p)));
      el.innerHTML = "";
      el.appendChild(wrap);
    }
    load();
  }

  async function renderSelfImprove(el) {
    _injectExtraCss();
    const myGen = _renderGen;   // chống race: đổi trang → mọi loadLoops/loadLog dở tự bỏ
    let pollTimer = null;       // 1 chuỗi poll duy nhất (clearTimeout trước khi đặt lại)
    el.innerHTML = `<div class="cview-section"><div class="empty">Đang tải...</div></div>`;
    const GNAME = { business: "Kinh doanh", brain: "Bộ não", product: "Cải thiện Javis", custom: "Tự định nghĩa" };
    const fmtT = ts => ts ? new Date(ts * 1000).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) : "-";

    el.innerHTML = `<div class="cview-section">
      <p style="color:#9fb0cf;font-size:15px;max-width:680px;margin:0 0 14px">Nhiều <b>loop</b> chạy ngầm: mỗi loop tự thức theo chu kỳ, làm <b>một việc</b> anh mô tả, tự kiểm chứng rồi ghi log. Thực thi <b>tuần tự</b> (1 vòng/lúc). Loop <b>đọc được dữ liệu thật qua MCP</b> (POS, quảng cáo, lịch...) để làm việc, nhưng KHÔNG tự tạo đơn/tiêu tiền/đăng bài - chỉ ghi nháp để anh duyệt. Loop bật sẽ hiện ở tab <b>Lịch</b>.</p>
      <div class="si-actions" style="margin-bottom:14px">
        <button class="s-btn" id="lpNew">+ Loop mới</button>
        <button class="s-btn-ghost" id="lpStop">■ Dừng vòng đang chạy</button>
      </div>
      <div id="lpForm" style="display:none;margin-bottom:14px;padding:14px;border:1px solid rgba(255,255,255,.1);border-radius:10px;background:rgba(255,255,255,.03)">
        <input type="hidden" id="lpSlug">
        <div class="si-grid">
          <div class="si-field"><label>Tên loop</label><input id="lpName" placeholder="VD: Đọc source mỗi 2 tiếng"></div>
          <div class="si-field"><label>Mô tả nhiệm vụ (mỗi vòng Javis làm đúng việc này)</label>
            <textarea id="lpBody" placeholder="VD: Mỗi vòng đọc 1 source chưa xử lý trong 06 - Sources rồi đề xuất Wiki page nên tạo. Hoặc: đọc số đơn hôm nay qua MCP POS, nếu thấp thì soạn nháp 1 caption đẩy hàng vào 05 - Projects."></textarea></div>
          <div class="si-row" style="gap:14px;flex-wrap:wrap">
            <div class="si-field"><label>Chế độ</label><div class="si-row" id="lpModes">
              <button class="si-chip" data-mode="suggest">Đề xuất (chỉ đọc)</button>
              <button class="si-chip" data-mode="auto">Tự làm (an toàn)</button>
              <button class="si-chip" data-mode="full" style="border-color:rgba(224,102,74,.5)">⚠ Toàn quyền</button></div></div>
            <div class="si-field"><label>Chu kỳ (phút, tối thiểu 5)</label><input type="number" id="lpInterval" min="5" value="120" style="max-width:120px"></div>
          </div>
          <div id="lpFullWarn" style="display:none;margin-top:4px;padding:10px 12px;border:1px solid rgba(224,102,74,.5);border-radius:8px;background:rgba(224,102,74,.08);color:#ffb59e;font-size:13px;line-height:1.5">
            <b>⚠ CHẾ ĐỘ TOÀN QUYỀN - rủi ro cao.</b> Loop sẽ tự thao tác THẬT qua MCP không cần hỏi: có thể <b>tạo/sửa đơn hàng, chạy quảng cáo (tiêu tiền thật), gửi tin nhắn/email, đăng bài</b>. Nó chạy nền theo lịch, KHÔNG có người duyệt từng bước, và <b>hành động thật không hoàn tác được</b>. Chỉ bật khi anh đã tin tưởng loop này và mô tả nhiệm vụ thật rõ ràng, giới hạn phạm vi. Nên chạy thử ở "Đề xuất" hoặc "Tự làm (an toàn)" trước.
          </div>
          <div class="dim" style="font-size:12px;color:#6b7894;margin-top:2px">Đề xuất = chỉ đọc + gợi ý. Tự làm (an toàn) = ghi nháp file + đọc MCP, KHÔNG tiền/đơn/đăng bài. Toàn quyền = tự thao tác mọi thứ. · Tinh chỉnh nâng cao (giờ im lặng, trần vòng/ngày, thư mục code): sửa file <code>Javis/loops/&lt;tên&gt;.md</code>.</div>
          <div class="si-actions"><button class="s-btn" id="lpSave">💾 Lưu loop</button><button class="s-btn-ghost" id="lpCancel">Huỷ</button><span class="dim" id="lpFormMsg" style="font-size:13px;color:#e0a04a"></span></div>
        </div>
      </div>
      <div id="lpCards">Đang tải...</div>
      <div class="si-log"><h3 style="font-size:15px;color:#cdd8ee">Nhật ký gần đây · <select id="lpLogFilter" class="loop-sel" style="font-size:13px"><option value="">Tất cả loop</option></select></h3><div id="lpLog">Đang tải...</div></div>
    </div>`;

    let fcur = { mode: "suggest" };
    function syncFormChips() {
      el.querySelectorAll("#lpModes .si-chip").forEach(x => x.classList.toggle("sel", x.dataset.mode === fcur.mode));
      const w = el.querySelector("#lpFullWarn"); if (w) w.style.display = (fcur.mode === "full") ? "block" : "none";
    }
    el.querySelectorAll("#lpModes .si-chip").forEach(c => c.onclick = () => { fcur.mode = c.dataset.mode; syncFormChips(); });

    function openForm(lp) {
      fcur = { mode: lp ? lp.mode : "suggest" };
      el.querySelector("#lpSlug").value = lp ? lp.slug : "";
      el.querySelector("#lpName").value = lp ? lp.name : "";
      el.querySelector("#lpBody").value = lp ? (lp.body || "") : "";
      el.querySelector("#lpInterval").value = lp ? lp.interval_min : 120;
      el.querySelector("#lpFormMsg").textContent = "";
      syncFormChips();
      el.querySelector("#lpForm").style.display = "block";
      el.querySelector("#lpName").focus();
    }
    el.querySelector("#lpNew").onclick = () => openForm(null);
    el.querySelector("#lpCancel").onclick = () => { el.querySelector("#lpForm").style.display = "none"; };

    el.querySelector("#lpSave").onclick = async () => {
      const name = el.querySelector("#lpName").value.trim();
      const body = el.querySelector("#lpBody").value.trim();
      if (!name) { el.querySelector("#lpFormMsg").textContent = "Nhập tên loop"; return; }
      if (!body) { el.querySelector("#lpFormMsg").textContent = "Nhập mô tả nhiệm vụ (Javis cần biết mỗi vòng làm gì)"; return; }
      if (fcur.mode === "full" && !confirm(`Bật CHẾ ĐỘ TOÀN QUYỀN cho loop "${name}"?\n\nLoop sẽ tự thao tác THẬT qua MCP không cần hỏi: tạo/sửa đơn, chạy quảng cáo (tiêu tiền thật), gửi tin, đăng bài. Chạy nền theo lịch, KHÔNG duyệt từng bước, hành động KHÔNG hoàn tác được.\n\nAnh chắc chắn chứ?`)) return;
      const fd = new FormData();
      fd.append("slug", el.querySelector("#lpSlug").value);
      fd.append("name", name);
      fd.append("mode", fcur.mode);
      fd.append("interval_min", el.querySelector("#lpInterval").value || "120");
      fd.append("body", body);
      fd.append("brain", fbrain());
      // Không gửi goal/workspace/tools_profile/quiet/maxruns → server giữ giá trị cũ (khi sửa)
      // hoặc mặc định an toàn (tạo mới: goal=custom, vault + MCP đọc).
      const b = el.querySelector("#lpSave"); b.textContent = "Đang lưu...";
      let r = {}; try { r = await (await fetch("/loops", { method: "POST", body: fd })).json(); } catch (e) { r = { error: e.message }; }
      b.textContent = "💾 Lưu loop";
      if (!r.ok) { el.querySelector("#lpFormMsg").textContent = "⚠ " + (r.error || "Lưu lỗi"); return; }
      el.querySelector("#lpForm").style.display = "none";
      loadLoops(); loadLog();
    };

    el.querySelector("#lpStop").onclick = async () => { await fetch("/loops/stop", { method: "POST" }); loadLoops(); };

    function loopCard(lp) {
      const paused = !!lp.auto_paused_reason;
      const dot = lp.running ? `<span style="color:#3fdc86">⏳ đang chạy</span>`
        : paused ? `<span style="color:#e0a04a">⚠ tự tạm dừng</span>`
        : lp.enabled ? `<span style="color:#3fdc86">● bật</span>` : `<span style="color:#6b7894">○ tắt</span>`;
      const verify = lp.last_status && lp.last_status !== "ok"
        ? ` · ${esc(lp.last_status.slice(0, 90))}` : (lp.last_status === "ok" ? " · ok" : "");
      const last = lp.last_run ? `lần cuối ${fmtT(lp.last_run)}` : "chưa chạy";
      const next = (lp.enabled && !paused && lp.next_run) ? ` · kế tiếp ~${fmtT(lp.next_run)}` : "";
      const modeLbl = lp.mode === "full" ? `<span style="color:#e0664a;font-weight:600">⚠ toàn quyền</span>`
        : lp.mode === "auto" ? "tự làm (an toàn)" : "đề xuất";
      const extra = [
        `${modeLbl} · mỗi ${lp.interval_min} phút`,
        (lp.goal && lp.goal !== "custom") ? (GNAME[lp.goal] || lp.goal) : "",
        lp.quiet_hours ? `im lặng ${lp.quiet_hours}` : "",
        lp.max_runs_per_day ? `tối đa ${lp.max_runs_per_day}/ngày (đã ${lp.runs_today})` : "",
        lp.tools_profile === "code" ? `⚙ code · ${esc(lp.workspace)}` : "",
      ].filter(Boolean).join(" · ");
      const div = document.createElement("div");
      div.className = "wf-card" + (lp.enabled ? "" : " off");
      div.innerHTML = `
        <div class="wf-top"><div class="wf-name">🔁 ${esc(lp.name)} <span class="dim" style="font-size:12px">${esc(lp.slug)}</span></div><div>${dot}</div></div>
        <div class="wf-desc">${extra}</div>
        <div class="wf-steps">${last}${verify}${next}${paused ? `<br>⚠ ${esc(lp.auto_paused_reason)}` : ""}</div>
        <div class="wf-actions">
          <button class="s-btn-ghost tgl">${lp.enabled ? "Tắt" : "Bật"}</button>
          <button class="s-btn-ghost run">▶ Chạy ngay</button>
          <button class="s-btn-ghost edit">Sửa</button>
          <button class="s-btn-ghost del" style="color:#e0664a">Xoá</button>
        </div>`;
      div.querySelector(".tgl").onclick = async () => {
        // Bật loop TOÀN QUYỀN = xác nhận rủi ro (tắt thì khỏi hỏi)
        if (!lp.enabled && lp.mode === "full" &&
            !confirm(`Bật loop TOÀN QUYỀN "${lp.name}"?\n\nNó sẽ tự thao tác THẬT qua MCP (tạo đơn, tiêu tiền quảng cáo, gửi tin, đăng bài) theo lịch, không duyệt từng bước. Chắc chứ?`)) return;
        await fetch("/loops/toggle", { method: "POST", body: (() => { const f = new FormData(); f.append("slug", lp.slug); f.append("brain", fbrain()); return f; })() });
        loadLoops();
      };
      div.querySelector(".run").onclick = async (e) => {
        e.target.disabled = true; e.target.textContent = "Đang chạy...";
        await fetch("/loops/run-now", { method: "POST", body: (() => { const f = new FormData(); f.append("slug", lp.slug); f.append("brain", fbrain()); return f; })() });
        setTimeout(() => { loadLoops(); loadLog(); }, 2500);
      };
      div.querySelector(".edit").onclick = () => openForm(lp);
      div.querySelector(".del").onclick = async () => {
        if (!confirm(`Xoá loop "${lp.name}"? File Javis/loops/${lp.slug}.md sẽ bị xoá.`)) return;
        await fetch("/loops/delete", { method: "POST", body: (() => { const f = new FormData(); f.append("slug", lp.slug); f.append("brain", fbrain()); return f; })() });
        loadLoops(); loadLog();
      };
      return div;
    }

    async function loadLoops() {
      if (myGen !== _renderGen) return;   // đã rời trang
      let d = { loops: [] };
      try { d = await (await fetch(`/loops?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) {}
      if (myGen !== _renderGen) return;   // đổi trang trong lúc chờ fetch
      const box = el.querySelector("#lpCards");
      if (!box) return;
      box.innerHTML = "";
      if (!(d.loops || []).length) {
        box.innerHTML = `<div class="empty">Chưa có loop nào. Bấm <b>+ Loop mới</b>, hoặc nói với Javis trong chat (vd "tạo loop mỗi 2 tiếng đọc 1 source rồi đề xuất").</div>`;
      } else {
        d.loops.forEach(lp => box.appendChild(loopCard(lp)));
      }
      const sel = el.querySelector("#lpLogFilter");
      const cur = sel.value;
      sel.innerHTML = `<option value="">Tất cả loop</option>` +
        (d.loops || []).map(lp => `<option value="${esc(lp.slug)}" ${lp.slug === cur ? "selected" : ""}>${esc(lp.name)}</option>`).join("");
      clearTimeout(pollTimer);
      if (d.running) pollTimer = setTimeout(loadLoops, 5000);   // đang có vòng chạy → tự refresh (1 chuỗi)
    }
    async function loadLog() {
      if (myGen !== _renderGen) return;
      const slug = el.querySelector("#lpLogFilter").value;
      let d = { entries: [] };
      try { d = await (await fetch(`/loops/log?brain=${encodeURIComponent(fbrain())}&slug=${encodeURIComponent(slug)}&limit=10`)).json(); } catch (e) { }
      if (myGen !== _renderGen) return;
      const box = el.querySelector("#lpLog");
      if (!box) return;
      box.innerHTML = (d.entries || []).length ? d.entries.map(e => `<div class="le">${esc(e)}</div>`).join("") : `<div class="dim" style="color:#6b7894">Chưa có nhật ký.</div>`;
    }
    el.querySelector("#lpLogFilter").onchange = loadLog;
    loadLoops(); loadLog();
  }

  // ============================================
  // Trang Tự học (rewire Memory/Wiki/Skill - an toàn, undo được)
  // ============================================
  async function renderLearn(el) {
    _injectExtraCss();
    el.innerHTML = `<div class="cview-section"><div class="empty">Đang tải...</div></div>`;
    let cfg = {};
    try { cfg = await (await fetch("/learn/config")).json(); } catch (e) {}
    const caps = cfg.capabilities || {};
    const MODES = [
      ["dry-run", "Chạy thử", "Chỉ ghi nhật ký 'sẽ học gì' - KHÔNG đụng file. An toàn nhất."],
      ["suggest", "Đề xuất", "Như chạy thử, để bạn xem trước khi cho ghi."],
      ["auto", "Tự ghi", "Ghi thẳng vào Memory/Wiki - git-commit + undo được."],
    ];
    const modeChips = MODES.map(([v, l]) => `<button class="si-chip ${cfg.mode === v ? "sel" : ""}" data-mode="${v}">${l}</button>`).join("");
    const modeDesc = (MODES.find(m => m[0] === cfg.mode) || MODES[0])[2];
    const capRow = [["memory", "Ký ức (Memory)"], ["wiki", "Tri thức (Wiki)"], ["skill", "Kỹ năng (Skill)"], ["task", "Việc (Kanban)"]]
      .map(([k, l]) => `<button class="si-chip ${caps[k] ? "sel" : ""}" data-cap="${k}">${caps[k] ? "● " : "○ "}${l}</button>`).join("");
    const gitWarn = cfg.git_available ? "" : `<div class="dim" style="color:#7d8aa6;font-size:13px;margin-top:6px">ℹ Máy chưa có <code>git</code>: Tự học VẪN chạy bình thường, chỉ là chưa có hoàn tác 1-chạm/backup lên GitHub. Cài git để bật undo + sao lưu brain.</div>`;

    el.innerHTML = `<div class="cview-section">
      <p style="color:#9fb0cf;font-size:15px;max-width:660px;margin:0 0 14px">Sau mỗi hội thoại, Javis tự rút <b>ký ức</b>, đúc <b>tri thức Wiki</b>, <b>kỹ năng</b> và <b>việc</b> - qua tiến trình học <b>chỉ-đọc, cô lập</b> (0 MCP, không xoá). Người ghi file là code tin cậy. Mặc định <b>bật sẵn + tự ghi</b>; nếu brain có git thì mỗi lần học còn được <b>git-commit để hoàn tác 1 chạm</b>.</p>
      <div class="si-grid">
        <div class="si-field"><label>Bật tự học</label>
          <button class="si-chip ${cfg.enabled ? "sel" : ""}" id="lnEnabled">${cfg.enabled ? "● Đang bật" : "○ Đang tắt"}</button>
          <div class="dim" id="lnEnableNote" style="font-size:13px;margin-top:6px;color:#7d8aa6">Học chạy được ngay cả khi chưa có git. Có git thì thêm undo + sao lưu.</div></div>
        <div class="si-field"><label>Chế độ ghi</label><div class="si-row" id="lnModes">${modeChips}</div>
          <div class="dim" id="lnModeDesc" style="font-size:14px;margin-top:6px;color:#7d8aa6">${esc(modeDesc)}</div>${gitWarn}</div>
        <div class="si-field"><label>Học cái gì</label><div class="si-row" id="lnCaps">${capRow}</div>
          <div class="dim" style="font-size:13px;margin-top:6px;color:#7d8aa6">Wiki/Skill nên bật sau khi đã quen với Ký ức (lộ trình Phase 2/3). Việc = học xong đề xuất task nền vào bảng Việc (Kanban) - chỉ tạo thật ở chế độ Tự ghi, và task luôn chờ bạn duyệt.</div></div>
        <div class="si-field"><label>Curator (bảo trì định kỳ)</label>
          <button class="si-chip ${(cfg.curator||{}).enabled ? "sel" : ""}" id="lnCurator">${(cfg.curator||{}).enabled ? "● Bật" : "○ Tắt"}</button>
          <div class="dim" style="font-size:13px;margin-top:6px;color:#7d8aa6">Dọn index, LINT Wiki (chỉ đề xuất), nén MEMORY.md. Không xoá.</div></div>
        <div class="si-actions">
          <button class="s-btn" id="lnSave">💾 Lưu cấu hình</button>
          <button class="s-btn-ghost" id="lnRun">▶ Học ngay</button>
          <button class="s-btn-ghost" id="lnCuratorRun">🧹 Curator ngay</button>
          <button class="s-btn-ghost" id="lnStop">■ Dừng</button>
          <button class="s-btn-ghost" id="lnUndo" style="color:#e0a04a">↶ Hoàn tác lần học gần nhất</button>
        </div>
      </div>
      <div class="si-status" id="lnMetrics"></div>

      <div class="si-log" id="lnBackupBox">
        <h3 style="font-size:15px;color:#cdd8ee">⇅ Đồng bộ brain với GitHub (2 chiều)</h3>
        <p style="color:#9fb0cf;font-size:14px;max-width:680px;margin:2px 0 10px">Đồng bộ <b>TẤT CẢ brain trong thư mục brains</b> (mọi bộ não, ghi chú, Wiki, ký ức) với 1 repo GitHub <b>riêng tư</b>: vừa đẩy thay đổi của máy này lên, vừa kéo thay đổi từ máy khác về (dùng chung cho máy nhà + VPS, các máy tự khớp nhau). Sửa trùng 1 file ở 2 nơi thì bản mới hơn thắng, bản kia được giữ thành file <code>.conflict-*</code> ngay cạnh. Máy mới cấu hình repo rồi bấm đồng bộ là khôi phục được toàn bộ. Hướng dẫn: <a href="https://github.com/blogminhquy/javis-os/blob/main/docs/18-sao-luu-github.md" target="_blank" style="color:#7fb0ff">docs/18-sao-luu-github.md</a>.</p>
        <ol style="color:#9fb0cf;font-size:13.5px;line-height:1.7;max-width:680px;margin:0 0 12px;padding-left:20px">
          <li>Tạo repo GitHub <b>Private</b> (trống, KHÔNG thêm README) - vd <code>javis-brain-backup</code>.</li>
          <li>Tạo token: GitHub → Settings → Developer settings → <b>Fine-grained tokens</b> → chọn đúng repo đó → quyền <b>Contents: Read and write</b> → tạo và copy token (dạng <code>github_pat_...</code>).</li>
          <li>Dán URL repo + token vào đây, bấm <b>Kiểm tra</b>, rồi <b>Đồng bộ ngay</b>. Bật tự động để định kỳ tự khớp giữa các máy.</li>
        </ol>
        <div class="si-grid">
          <div class="si-field"><label>URL repo (https)</label><input id="bkRepo" placeholder="https://github.com/blogminhquy/javis-brain-backup"></div>
          <div class="si-field"><label>GitHub token (fine-grained, quyền Contents)</label><input id="bkToken" type="password" placeholder="github_pat_..."></div>
          <div class="si-row" style="gap:14px;flex-wrap:wrap">
            <div class="si-field"><label>Nhánh</label><input id="bkBranch" value="main" style="max-width:120px"></div>
            <div class="si-field"><label>Tự đồng bộ mỗi (giờ)</label><input type="number" id="bkInterval" min="1" value="6" style="max-width:120px"></div>
            <div class="si-field"><label>Tự động</label><button class="si-chip" id="bkAuto">○ Tắt</button></div>
          </div>
          <div class="si-actions">
            <button class="s-btn-ghost" id="bkTest">🔌 Kiểm tra kết nối</button>
            <button class="s-btn" id="bkNow">⇅ Đồng bộ ngay</button>
            <button class="s-btn-ghost" id="bkSave">💾 Lưu cấu hình</button>
          </div>
          <div class="dim" id="bkStatus" style="font-size:13px;color:#7d8aa6"></div>
          <div class="dim" id="bkWarn" style="font-size:12px;color:#e0a04a;margin-top:2px">⚠ Brain có thể chứa số liệu/thông tin cá nhân - CHỈ dùng repo Private. Token lưu nội bộ (không đẩy lên repo).</div>
        </div>
      </div>

      <div class="si-log"><h3 style="font-size:15px;color:#cdd8ee">Javis đã tự học gì (commit gần nhất)</h3><div id="lnReview">Đang tải...</div></div>
      <div class="si-log"><h3 style="font-size:15px;color:#cdd8ee">Nhật ký học</h3><div id="lnLog">Đang tải...</div></div>
    </div>`;

    let cur = { enabled: !!cfg.enabled, mode: cfg.mode || "dry-run",
                caps: { memory: !!caps.memory, wiki: !!caps.wiki, skill: !!caps.skill, task: !!caps.task },
                curator: !!(cfg.curator || {}).enabled };
    const modeDescEl = el.querySelector("#lnModeDesc");
    el.querySelectorAll("#lnModes .si-chip").forEach(c => c.onclick = () => {
      cur.mode = c.dataset.mode;
      el.querySelectorAll("#lnModes .si-chip").forEach(x => x.classList.toggle("sel", x === c));
      modeDescEl.textContent = (MODES.find(m => m[0] === cur.mode) || MODES[0])[2];
    });
    el.querySelectorAll("#lnCaps .si-chip").forEach(c => c.onclick = () => {
      const k = c.dataset.cap; cur.caps[k] = !cur.caps[k];
      c.classList.toggle("sel", cur.caps[k]);
      c.textContent = (cur.caps[k] ? "● " : "○ ") + c.textContent.slice(2);
    });
    const curBtn = el.querySelector("#lnCurator");
    curBtn.onclick = () => { cur.curator = !cur.curator; curBtn.classList.toggle("sel", cur.curator); curBtn.textContent = cur.curator ? "● Bật" : "○ Tắt"; };
    const enBtn = el.querySelector("#lnEnabled");
    enBtn.onclick = async () => {
      if (!cur.enabled) {
        enBtn.textContent = "Đang git-init...";
        let r = {}; try { r = await (await fetch("/learn/enable", { method: "POST", body: (()=>{const f=new FormData();f.append("brain",fbrain());return f;})() })).json(); } catch (e) {}
        cur.enabled = true; el.querySelector("#lnEnableNote").textContent = r.note || "Đã bật.";
      } else {
        cur.enabled = false;
        const f = new FormData(); f.append("enabled", "0"); f.append("brain", fbrain());
        await fetch("/learn/config", { method: "POST", body: f });
      }
      enBtn.classList.toggle("sel", cur.enabled); enBtn.textContent = cur.enabled ? "● Đang bật" : "○ Đang tắt";
    };

    async function save() {
      const f = new FormData();
      f.append("enabled", cur.enabled ? "1" : "0"); f.append("mode", cur.mode);
      f.append("cap_memory", cur.caps.memory ? "1" : "0");
      f.append("cap_wiki", cur.caps.wiki ? "1" : "0");
      f.append("cap_skill", cur.caps.skill ? "1" : "0");
      f.append("cap_task", cur.caps.task ? "1" : "0");
      f.append("curator_enabled", cur.curator ? "1" : "0");
      f.append("brain", fbrain());
      return (await fetch("/learn/config", { method: "POST", body: f })).json();
    }
    el.querySelector("#lnSave").onclick = async () => { const b = el.querySelector("#lnSave"); b.textContent = "Đang lưu..."; await save(); b.textContent = "✓ Đã lưu"; setTimeout(() => b.textContent = "💾 Lưu cấu hình", 1500); };
    const brainForm = () => { const f = new FormData(); f.append("brain", fbrain()); return f; };
    el.querySelector("#lnRun").onclick = async () => {
      const b = el.querySelector("#lnRun"); b.disabled = true; b.textContent = "Đang học...";
      await save(); await fetch("/learn/run-now", { method: "POST", body: brainForm() });
      setTimeout(() => { b.disabled = false; b.textContent = "▶ Học ngay"; loadAll(); }, 2500);
    };
    el.querySelector("#lnCuratorRun").onclick = async () => {
      const b = el.querySelector("#lnCuratorRun"); b.disabled = true; b.textContent = "Đang dọn...";
      await fetch("/learn/curator-now", { method: "POST", body: brainForm() });
      setTimeout(() => { b.disabled = false; b.textContent = "🧹 Curator ngay"; loadAll(); }, 2500);
    };
    el.querySelector("#lnStop").onclick = async () => { await fetch("/learn/stop", { method: "POST" }); };
    el.querySelector("#lnUndo").onclick = async () => {
      if (!confirm("Hoàn tác (git revert) lần học gần nhất?")) return;
      const b = el.querySelector("#lnUndo"); b.disabled = true; b.textContent = "Đang hoàn tác...";
      let r = {}; try { r = await (await fetch("/learn/undo", { method: "POST", body: brainForm() })).json(); } catch (e) { r = { error: e.message }; }
      b.disabled = false; b.textContent = "↶ Hoàn tác lần học gần nhất";
      alert(r.ok ? ("Đã hoàn tác: " + (r.subject || r.reverted)) : ("Không hoàn tác được: " + (r.error || "?")));
      loadAll();
    };

    async function loadMetrics() {
      let m = {}; try { m = await (await fetch(`/learn/metrics?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) { }
      el.querySelector("#lnMetrics").innerHTML =
        `<b>Chỉ số</b> · Ký ức: <b>${m.facts ?? "?"}</b> · Wiki: <b>${m.wiki ?? "?"}</b> · MEMORY.md: ${(m.memory_bytes||0)}B` +
        ` · Fork hôm nay: ${m.fork_today ?? 0} · Token ước tính: ${m.token_today ?? 0} · Commit học: ${m.learn_commits ?? 0}`;
    }
    async function loadReview() {
      let d = { commits: [] }; try { d = await (await fetch(`/learn/review?brain=${encodeURIComponent(fbrain())}&limit=12`)).json(); } catch (e) { }
      const box = el.querySelector("#lnReview");
      if (!d.git_repo) { box.innerHTML = `<div class="dim" style="color:#e0a04a">Brain chưa phải git repo - bật Tự học để git-init (mới xem/undo được commit).</div>`; return; }
      box.innerHTML = (d.commits || []).length ? d.commits.map(c => {
        const when = c.ts ? new Date(c.ts * 1000).toLocaleString() : "";
        const files = (c.files || []).slice(0, 6).map(f => `<code style="font-size:11px">${esc(f)}</code>`).join(" ");
        return `<div class="le"><b>${esc(c.subject)}</b> <span class="dim" style="color:#6b7894">${esc(c.hash)} · ${esc(when)}</span><br>${files}</div>`;
      }).join("") : `<div class="dim" style="color:#6b7894">Chưa có commit học nào.</div>`;
    }
    async function loadLog() {
      let d = { entries: [] }; try { d = await (await fetch(`/learn/log?brain=${encodeURIComponent(fbrain())}&limit=10`)).json(); } catch (e) { }
      el.querySelector("#lnLog").innerHTML = (d.entries || []).length ? d.entries.map(e => `<div class="le">${esc(e)}</div>`).join("") : `<div class="dim" style="color:#6b7894">Chưa có nhật ký học.</div>`;
    }
    // ── Backup GitHub ──
    let bkAutoOn = false;
    const bkAutoBtn = el.querySelector("#bkAuto");
    bkAutoBtn.onclick = () => { bkAutoOn = !bkAutoOn; bkAutoBtn.classList.toggle("sel", bkAutoOn); bkAutoBtn.textContent = bkAutoOn ? "● Bật" : "○ Tắt"; };
    async function bkSaveCfg() {
      const f = new FormData();
      f.append("repo_url", el.querySelector("#bkRepo").value.trim());
      const tk = el.querySelector("#bkToken").value.trim();
      if (tk && !tk.startsWith("••••")) f.append("token", tk);   // chỉ gửi token mới, không gửi chuỗi che
      f.append("branch", el.querySelector("#bkBranch").value.trim() || "main");
      f.append("interval_hours", el.querySelector("#bkInterval").value || "6");
      f.append("enabled", bkAutoOn ? "1" : "0");
      return (await fetch("/backup/config", { method: "POST", body: f })).json();
    }
    el.querySelector("#bkSave").onclick = async () => { const b = el.querySelector("#bkSave"); b.textContent = "Đang lưu..."; await bkSaveCfg(); b.textContent = "✓ Đã lưu"; setTimeout(() => b.textContent = "💾 Lưu cấu hình", 1500); loadBackup(); };
    el.querySelector("#bkTest").onclick = async () => {
      const b = el.querySelector("#bkTest"); b.disabled = true; b.textContent = "Đang kiểm tra..."; await bkSaveCfg();
      let r = {}; try { r = await (await fetch("/backup/test", { method: "POST" })).json(); } catch (e) { r = { error: e.message }; }
      b.disabled = false; b.textContent = "🔌 Kiểm tra kết nối";
      el.querySelector("#bkStatus").innerHTML = r.ok ? `<span style="color:#3fdc86">✓ Kết nối OK - token + repo hợp lệ.</span>` : `<span style="color:#e0664a">✗ ${esc(r.error || "không kết nối được")}</span>`;
    };
    el.querySelector("#bkNow").onclick = async () => {
      const b = el.querySelector("#bkNow"); b.disabled = true; b.textContent = "Đang đồng bộ 2 chiều..."; await bkSaveCfg();
      let r = {}; try { r = await (await fetch("/backup/now", { method: "POST", body: brainForm() })).json(); } catch (e) { r = { error: e.message }; }
      b.disabled = false; b.textContent = "⇅ Đồng bộ ngay";
      if (r.ok) {
        const bits = [];
        if (r.applied) bits.push(`nhận về ${r.applied} file`);
        if (r.deleted) bits.push(`xoá ${r.deleted} file (máy khác đã xoá)`);
        if (r.pushed) bits.push("đã đẩy lên GitHub");
        if (r.restored) bits.push("khôi phục từ backup");
        const cf = (r.conflicts || []).length
          ? ` · <span style="color:#e0a04a">⚠ ${r.conflicts.length} file sửa trùng 2 nơi - bản mới hơn thắng, bản kia lưu thành .conflict-* (xem: ${esc(r.conflicts.slice(0, 3).map(c => c.path).join(", "))}${r.conflicts.length > 3 ? "..." : ""})</span>` : "";
        el.querySelector("#bkStatus").innerHTML = `<span style="color:#3fdc86">✓ Đồng bộ xong${bits.length ? " - " + bits.join(", ") : " - hai bên đã khớp nhau"}.</span>${cf}`;
      } else {
        el.querySelector("#bkStatus").innerHTML = `<span style="color:#e0664a">✗ ${esc(r.error || "lỗi")}</span>`;
      }
    };
    async function loadBackup() {
      let s = {}; try { s = await (await fetch(`/backup/status?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) { return; }
      el.querySelector("#bkRepo").value = s.repo_url || "";
      el.querySelector("#bkBranch").value = s.branch || "main";
      el.querySelector("#bkInterval").value = s.interval_hours || 6;
      if (s.token_set && !el.querySelector("#bkToken").value) el.querySelector("#bkToken").placeholder = "•••• (đã lưu, để trống nếu giữ nguyên)";
      bkAutoOn = !!s.enabled; bkAutoBtn.classList.toggle("sel", bkAutoOn); bkAutoBtn.textContent = bkAutoOn ? "● Bật" : "○ Tắt";
      const when = s.last_backup ? new Date(s.last_backup * 1000).toLocaleString() : "chưa đồng bộ";
      const gitNote = s.has_git ? "" : " · ⚠ máy chưa cài git (cần git để đồng bộ)";
      const brainsNote = s.brains_count != null ? ` · ${s.brains_count} brain trong thư mục brains` : "";
      el.querySelector("#bkStatus").innerHTML = `Lần cuối: ${esc(when)}${s.last_status ? " · " + esc(s.last_status) : ""}${brainsNote}${gitNote}`;
    }

    function loadAll() { loadMetrics(); loadReview(); loadLog(); loadBackup(); }
    loadAll();
  }

  // ============================================
  // Trang Việc (Kanban) - backlog + dispatcher tự làm task nền
  // ============================================
  const _KCOLS = [
    ["todo", "Chờ (todo)", "#8a97b4"], ["ready", "Sẵn sàng", "#e0b34a"],
    ["running", "Đang chạy", "#3fdc86"], ["review", "Chờ duyệt", "#7fb0ff"],
    ["blocked", "Bị chặn", "#e0664a"], ["done", "Xong", "#6b7894"],
  ];
  const _PRIO = { 1: "🔺", 2: "🔼", 3: "🔽" };
  async function renderKanban(el) {
    _injectExtraCss();
    el.innerHTML = `<div class="cview-section"><div class="empty">Đang tải...</div></div>`;
    let wfs = [];
    try { wfs = (await (await fetch(`/workflows?brain=${encodeURIComponent(fbrain())}`)).json()).workflows || []; } catch (e) {}
    const routeOpts = `<option value="auto">Trực tiếp (Javis tự làm, chỉ file)</option>` +
      wfs.map(w => `<option value="wf:${esc(w.slug)}">Workflow: ${esc(w.name || w.slug)}</option>`).join("");

    el.innerHTML = `<div class="cview-section">
      <p style="color:#9fb0cf;font-size:15px;max-width:680px;margin:0 0 12px">Backlog + <b>dispatcher</b>: Javis giữ danh sách việc, tự chọn việc ưu tiên rồi điều phối xuống workflow/agent làm. <b>An toàn:</b> chạy nền chỉ thao tác FILE (không MCP tiền/đơn); việc xong dừng ở <b>Chờ duyệt</b> để bạn kiểm rồi mới tính là xong.</p>
      <div class="si-grid" style="margin-bottom:14px">
        <div class="si-field"><label>Điều phối tự động</label><div class="si-row" id="knOrch"></div>
          <div class="dim" style="font-size:13px;margin-top:6px;color:#7d8aa6">off = chỉ dọn dẹp · manual = chỉ chạy khi bấm Nudge · auto = tự chạy theo lịch (30s/nhịp, 1 việc/lần).</div></div>
        <div class="si-actions">
          <button class="s-btn" id="knAdd">+ Thêm việc</button>
          <button class="s-btn-ghost" id="knNudge">⚡ Nudge dispatcher</button>
          <button class="s-btn-ghost" id="knRefresh">↻ Làm mới</button>
          <button class="s-btn-ghost" id="knStop" style="color:#e0a04a">■ Dừng</button>
        </div>
      </div>
      <div id="knForm" style="display:none;margin-bottom:14px;padding:14px;border:1px solid rgba(255,255,255,.1);border-radius:10px;background:rgba(255,255,255,.03)">
        <div class="si-field"><label>Tiêu đề</label><input id="knTitle" placeholder="VD: Soạn 3 post từ sản phẩm bán chạy tuần này"></div>
        <div class="si-field"><label>Mô tả việc (intent - Javis đọc để làm)</label><textarea id="knIntent" placeholder="Mô tả rõ việc cần làm + ghi kết quả nháp vào đâu (vd 05 - Projects)."></textarea></div>
        <div class="si-row" style="gap:14px;flex-wrap:wrap">
          <div class="si-field" style="flex:1;min-width:220px"><label>Cách làm (route)</label><select id="knRoute" class="loop-sel">${routeOpts}</select></div>
          <div class="si-field"><label>Ưu tiên</label><select id="knPrio" class="loop-sel"><option value="1">🔺 Cao</option><option value="2" selected>🔼 Vừa</option><option value="3">🔽 Thấp</option></select></div>
          <div class="si-field"><label>Cần duyệt trước khi xong</label><label class="auto-learn" style="margin-top:8px"><input type="checkbox" id="knApprove" checked><span>Dừng ở Chờ duyệt</span></label></div>
        </div>
        <div class="si-actions"><button class="s-btn" id="knSave">Lưu việc</button><button class="s-btn-ghost" id="knCancel">Huỷ</button></div>
      </div>
      <div id="knBoard" style="display:flex;gap:12px;overflow-x:auto;padding-bottom:10px;align-items:flex-start"></div>
    </div>`;

    const bf = () => { const f = new FormData(); f.append("brain", fbrain()); return f; };
    const post = async (url, extra) => { const f = bf(); for (const k in (extra || {})) f.append(k, extra[k]); return (await fetch(url, { method: "POST", body: f })).json(); };

    el.querySelector("#knAdd").onclick = () => { const b = el.querySelector("#knForm"); b.style.display = b.style.display === "none" ? "block" : "none"; };
    el.querySelector("#knCancel").onclick = () => { el.querySelector("#knForm").style.display = "none"; };
    el.querySelector("#knRefresh").onclick = () => load();
    el.querySelector("#knStop").onclick = async () => { await fetch("/kanban/stop", { method: "POST" }); load(); };
    el.querySelector("#knNudge").onclick = async () => { const b = el.querySelector("#knNudge"); b.disabled = true; b.textContent = "Đang chạy..."; await post("/kanban/nudge"); setTimeout(() => { b.disabled = false; b.textContent = "⚡ Nudge dispatcher"; load(); }, 2500); };
    el.querySelector("#knSave").onclick = async () => {
      const title = el.querySelector("#knTitle").value.trim();
      if (!title) { alert("Nhập tiêu đề"); return; }
      await post("/kanban/task", {
        title, intent: el.querySelector("#knIntent").value.trim() || title,
        route: el.querySelector("#knRoute").value, priority: el.querySelector("#knPrio").value,
        needs_approval: el.querySelector("#knApprove").checked ? "1" : "0",
      });
      el.querySelector("#knTitle").value = ""; el.querySelector("#knIntent").value = "";
      el.querySelector("#knForm").style.display = "none"; load();
    };

    function cardHtml(t) {
      const acts = [];
      if (["todo", "ready", "blocked"].includes(t.status)) acts.push(`<button data-act="run" data-id="${t.id}">▶ Chạy</button>`);
      if (t.status === "review") { acts.push(`<button data-act="done" data-id="${t.id}">✓ Duyệt</button>`); acts.push(`<button data-act="ready" data-id="${t.id}">↩ Làm lại</button>`); }
      if (t.status === "blocked") acts.push(`<button data-act="ready" data-id="${t.id}">↻ Bỏ chặn</button>`);
      acts.push(`<button data-act="archive" data-id="${t.id}">🗄</button>`);
      const res = t.result ? `<div class="dim" style="font-size:12px;color:#8aa;margin-top:6px;max-height:54px;overflow:hidden">${esc(t.result.slice(0, 180))}</div>` : "";
      const br = t.block_reason ? ` · <span style="color:#e0664a">${esc(t.block_reason)}</span>` : "";
      const rt = t.route && t.route !== "auto" ? esc(t.route) : "trực tiếp";
      return `<div class="le" style="margin-bottom:8px" title="${esc(t.intent || "")}">
        <div style="display:flex;justify-content:space-between;gap:6px"><b style="font-size:13.5px">${_PRIO[t.priority] || ""} ${esc(t.title)}</b></div>
        <div class="dim" style="font-size:11px;color:#6b7894;margin-top:2px">${rt} · ${esc(t.created_by || "")}${br}</div>
        ${res}
        <div class="kn-acts" style="display:flex;gap:5px;margin-top:7px;flex-wrap:wrap">${acts.join("")}</div>
      </div>`;
    }

    async function load() {
      let d = { columns: {}, orchestration: "off", counts: {} };
      try { d = await (await fetch(`/kanban?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) {}
      const orch = el.querySelector("#knOrch");
      orch.innerHTML = [["off", "Tắt"], ["manual", "Thủ công"], ["auto", "Tự động"]]
        .map(([v, l]) => `<button class="si-chip ${d.orchestration === v ? "sel" : ""}" data-orch="${v}">${l}</button>`).join("");
      orch.querySelectorAll(".si-chip").forEach(c => c.onclick = async () => { await post("/kanban/orchestration", { mode: c.dataset.orch }); load(); });
      const board = el.querySelector("#knBoard");
      board.innerHTML = _KCOLS.map(([s, label, color]) => {
        const arr = (d.columns && d.columns[s]) || [];
        const cards = arr.length ? arr.map(cardHtml).join("") : `<div class="dim" style="font-size:12px;color:#556;text-align:center;padding:14px 0">- trống -</div>`;
        return `<div style="min-width:210px;max-width:240px;flex:1;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:10px">
          <div style="font-size:13px;font-weight:600;color:${color};margin-bottom:8px;display:flex;justify-content:space-between"><span>● ${label}</span><span>${arr.length}</span></div>
          ${cards}</div>`;
      }).join("");
      board.querySelectorAll("button[data-act]").forEach(b => b.onclick = async () => {
        const id = b.dataset.id, act = b.dataset.act;
        if (act === "run") await post("/kanban/run", { id });
        else if (act === "archive") await post("/kanban/task/delete", { id });
        else await post("/kanban/task/move", { id, status: act });
        setTimeout(load, act === "run" ? 2000 : 200);
      });
    }
    load();
  }

  async function freshSettings() {
    // Timeout 6s: nếu /settings chậm/treo thì KHÔNG để panel kẹt "Đang tải..." mãi - dùng cache cũ
    // (hoặc {}) để vẫn hiện providers/cấu hình ngay, refresh lần sau.
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 6000);
      const r = await fetch("/settings", { signal: ctrl.signal });
      clearTimeout(t);
      _settings = await r.json();
    } catch (e) { /* giữ _settings cũ */ }
    return _settings || {};
  }

  // ---- Trang Tổng quan ----
  async function renderOverview(el) {
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">◎</div><div>Đang tải...</div></div>`;
    const s = await freshSettings();
    const m = s.model || {};
    const eng = m.engine === "openrouter" ? "OpenRouter (chat thuần)" : "Claude CLI (đầy đủ MCP)";
    const curModel = m.engine === "openrouter" ? (m.openrouter_model || "-") : (m.claude_model || "mặc định");
    const tg = s.telegram || {};
    const dash = s.dashboard || {};
    const gOn = dash.graph_enabled !== false;
    const gMode = (((typeof localStorage !== "undefined" && localStorage.getItem("javis.graphMode")) || dash.graph_mode || "2d") === "3d") ? "3d" : "2d";
    el.innerHTML = `
      <div class="cview-section">
        <h3>Phiên bản</h3>
        <div class="gcard" style="max-width:560px">
          <div class="gcard-top"><span class="gcard-name">Javis OS</span><span class="gcard-tag" id="ovVerTag">…</span></div>
          <div class="gcard-meta" id="ovVerMeta">Đang kiểm tra bản mới…</div>
          <div class="js-actions">
            <button class="gcard-btn ghost" id="ovVerCheck">Kiểm tra lại</button>
            <button class="gcard-btn" id="ovVerUpdate" style="display:none">⬆ Cập nhật ngay</button>
          </div>
          <div class="gcard-meta" id="ovVerStatus"></div>
        </div>
      </div>
      <div class="cview-section">
        <h3>Hệ thống</h3>
        <div class="cgrid">
          <div class="gcard"><div class="gcard-top"><span class="gcard-name">Engine</span></div><div class="gcard-meta">${esc(eng)}</div></div>
          <div class="gcard"><div class="gcard-top"><span class="gcard-name">Model</span></div><div class="gcard-meta">${esc(curModel)}</div></div>
          <div class="gcard"><div class="gcard-top"><span class="gcard-name">Workspace</span></div><div class="gcard-meta">${esc(s.workspace_name || "Javis OS")}</div></div>
          <div class="gcard"><div class="gcard-top"><span class="gcard-name">Telegram</span></div><div class="gcard-meta">${tg.enabled ? "● Bật" : "○ Tắt"}${tg.chat_id ? " · " + esc(tg.chat_id) : ""}</div></div>
        </div>
      </div>
      <div class="cview-section">
        <h3>Hiệu năng</h3>
        <div class="cgrid">
          <div class="gcard">
            <div class="gcard-top"><span class="gcard-name">Đồ thị não</span><span class="gcard-tag">${gOn ? (gMode === "3d" ? "3D" : "2D") : "tắt"}</span></div>
            <div class="gcard-meta">2D là canvas thuần, nhẹ và đỡ lag; 3D đẹp hơn nhưng nặng máy (render trên máy anh, không phải VPS). Tắt hẳn để nhẹ nhất. ${isNarrow() ? "Màn hình hẹp đang tự ép lite-mode." : ""}</div>
            <div class="js-actions">
              <button class="gcard-btn ${gOn && gMode === "2d" ? "" : "ghost"}" id="ovGraph2d">2D</button>
              <button class="gcard-btn ${gOn && gMode === "3d" ? "" : "ghost"}" id="ovGraph3d">3D</button>
              <button class="gcard-btn ghost" id="ovGraphToggle">${gOn ? "Tắt hẳn" : "Bật lại"}</button>
            </div>
          </div>
        </div>
      </div>
      <div class="cview-section" id="ovAutostartSec" style="display:none">
        <h3>Khởi động cùng máy</h3>
        <div class="cgrid">
          <div class="gcard">
            <div class="gcard-top"><span class="gcard-name">Tự bật Javis khi mở máy</span><span class="gcard-tag" id="ovAutoTag">…</span></div>
            <div class="gcard-meta" id="ovAutoMeta">Đang kiểm tra…</div>
            <button class="gcard-btn" id="ovAutoToggle" style="display:none"></button>
            <div class="gcard-meta" id="ovAutoStatus" style="margin-top:8px"></div>
          </div>
        </div>
      </div>
      <div class="cview-section">
        <h3>Cấu trúc brain</h3>
        <div class="cgrid">
          <div class="gcard">
            <div class="gcard-top"><span class="gcard-name">Chuẩn hóa thư mục</span></div>
            <div class="gcard-meta">Gom <code>agents/ workflows/ memory/ skills/</code> về dạng phẳng đồng nhất cho brain đang chọn. An toàn: chỉ di chuyển khi đích chưa có.</div>
            <button class="gcard-btn" id="ovMigrate">Chuẩn hóa brain đang chọn</button>
            <div class="gcard-meta" id="ovMigrateResult" style="margin-top:8px"></div>
          </div>
        </div>
      </div>`;
    // ---- Phiên bản + cập nhật trong UI ----
    const MODE_LBL = { docker: "Docker / VPS", native: "Linux (systemd)", windows: "Windows" };
    async function ovLoadVersion() {
      const tag = document.getElementById("ovVerTag");
      const meta = document.getElementById("ovVerMeta");
      const upd = document.getElementById("ovVerUpdate");
      if (!tag) return;
      meta.textContent = "Đang kiểm tra bản mới…";
      let j = {};
      try { j = await (await fetch("/version", { cache: "no-store" })).json(); }
      catch (e) { meta.textContent = "⚠ Không kiểm tra được (mạng)."; return; }
      tag.textContent = "v" + (j.current || "?");
      const ml = MODE_LBL[j.mode] || j.mode || "";
      if (j.update_available) {
        const base = "🆕 Có bản mới <b>v" + esc(j.latest) + "</b> (đang chạy v" + esc(j.current) + ") · " + esc(ml);
        if (j.can_self_update) {
          meta.innerHTML = base;
          upd.style.display = "";
        } else {
          // Docker không có Watchtower: cập nhật bằng REDEPLOY (kéo lại image mới nhất).
          meta.innerHTML = base + '<div style="margin-top:8px;line-height:1.55">↻ Cập nhật bằng cách <b>Redeploy</b>: trên Hostinger bấm nút <b>Redeploy</b> trong Docker Manager; trên VPS chạy <code>docker compose up -d --pull always</code>.</div>';
          upd.style.display = "none";
        }
      } else if (j.latest) {
        meta.innerHTML = "✅ Đang dùng bản mới nhất (v" + esc(j.current) + ") · " + esc(ml);
        upd.style.display = "none";
      } else {
        meta.innerHTML = "v" + esc(j.current) + " · " + esc(ml) + (j.error ? " · chưa so được với GitHub" : "");
        upd.style.display = "none";
      }
    }
    const verCheck = document.getElementById("ovVerCheck");
    if (verCheck) verCheck.onclick = ovLoadVersion;
    const verUpd = document.getElementById("ovVerUpdate");
    if (verUpd) verUpd.onclick = async () => {
      if (!confirm("Cập nhật Javis lên bản mới nhất?\nApp sẽ tự khởi động lại (~20-40 giây), trang sẽ tự tải lại.")) return;
      const st = document.getElementById("ovVerStatus");
      verUpd.disabled = true;
      st.textContent = "⏳ Đang chuẩn bị cập nhật…";
      let resp;
      try { resp = await (await fetch("/update", { method: "POST" })).json(); }
      catch (e) { resp = { ok: true, _dropped: true }; }   // kết nối đứt = server đang restart, bình thường
      if (resp && resp.ok === false) {
        verUpd.disabled = false;
        st.innerHTML = "⚠ " + esc(resp.error || "Không cập nhật được.") + (resp.manual ? " Chạy: <code>" + esc(resp.manual) + "</code>" : "");
        return;
      }
      st.textContent = "⏳ Đang tải bản mới + khởi động lại… (đừng tắt trang)";
      let tries = 0, backButOld = 0;
      const poll = setInterval(async () => {
        tries++;
        try {
          const j = await (await fetch("/version", { cache: "no-store" })).json();
          if (j && j.update_available === false) {          // đã lên bản mới → xong
            clearInterval(poll);
            st.textContent = "✅ Đã cập nhật xong. Đang tải lại trang…";
            setTimeout(() => location.reload(), 1500);
            return;
          }
          backButOld++;                                     // server sống lại nhưng vẫn bản cũ
          if (backButOld >= 3) {
            clearInterval(poll);
            st.innerHTML = "⚠ Server đã lên lại nhưng phiên bản chưa đổi - cập nhật có thể thất bại. Xem <code>update.log</code> / <code>docker compose logs</code>.";
          }
        } catch (e) { backButOld = 0; /* server đang restart - tiếp tục chờ */ }
        if (tries > 45) { clearInterval(poll); st.innerHTML = "Server chưa lên lại sau ~3 phút - thử tải lại trang."; }
      }, 4000);
    };
    ovLoadVersion();

    // ---- Tự khởi động cùng máy (chỉ Windows) ----
    async function ovLoadAutostart() {
      const sec = document.getElementById("ovAutostartSec");
      if (!sec) return;
      let j = {};
      try { j = await (await fetch("/autostart", { cache: "no-store" })).json(); }
      catch (e) { sec.style.display = "none"; return; }
      if (!j.supported) { sec.style.display = "none"; return; }   // Docker/Linux: ẩn hẳn
      sec.style.display = "";
      const on = !!j.enabled;
      document.getElementById("ovAutoTag").textContent = on ? "bật" : "tắt";
      const meta = document.getElementById("ovAutoMeta");
      meta.innerHTML = on
        ? "Javis tự chạy nền mỗi khi anh đăng nhập Windows - không cần bật tay. Chạy ẩn, mở <code>localhost:7777</code> để dùng."
        : "Bật để Javis tự khởi động mỗi khi mở máy. Chạy ẩn ở nền, không hiện cửa sổ.";
      if (j.stale) meta.innerHTML += '<br><span class="dim">⚠ Đường dẫn cài đặt đã đổi - bấm bật lại để cập nhật.</span>';
      const btn = document.getElementById("ovAutoToggle");
      btn.style.display = "";
      btn.disabled = false;
      btn.textContent = on ? "Tắt tự khởi động" : "Bật tự khởi động";
      btn.onclick = async () => {
        btn.disabled = true;
        const st = document.getElementById("ovAutoStatus");
        st.textContent = "Đang lưu…";
        const fd = new FormData(); fd.append("enabled", on ? "0" : "1");
        let r = {};
        try { r = await (await fetch("/autostart", { method: "POST", body: fd })).json(); }
        catch (e) { r = { ok: false, error: e.message }; }
        if (r.ok) { st.textContent = ""; ovLoadAutostart(); }
        else { st.textContent = "⚠ " + esc(r.error || "Lỗi"); btn.disabled = false; }
      };
    }
    ovLoadAutostart();

    const btn = document.getElementById("ovGraphToggle");
    if (btn) btn.onclick = async () => {
      btn.disabled = true;
      const next = !(s.dashboard && s.dashboard.graph_enabled !== false);
      await saveSetting("dashboard", { graph_enabled: next });
      graphEnabled = next;
      recomputeGraph();
      renderOverview(el);
    };
    // Đổi 2D/3D: lưu localStorage (bền ngay, không cần restart server) + lưu server (bền lâu) + dựng lại đồ thị.
    const setGraphMode = async (mode) => {
      try { localStorage.setItem("javis.graphMode", mode); } catch (e) {}
      graphEnabled = true;
      try { await saveSetting("dashboard", { graph_mode: mode, graph_enabled: true }); } catch (e) {}
      if (window.reinitGraph) { try { await window.reinitGraph(mode); } catch (e) {} }
      recomputeGraph();
      renderOverview(el);
    };
    const b2d = document.getElementById("ovGraph2d");
    if (b2d) b2d.onclick = () => setGraphMode("2d");
    const b3d = document.getElementById("ovGraph3d");
    if (b3d) b3d.onclick = () => setGraphMode("3d");
    const mig = document.getElementById("ovMigrate");
    if (mig) mig.onclick = async () => {
      const brain = (window.currentBrainPath ? currentBrainPath() : "brain");
      if (!confirm("Chuẩn hóa cấu trúc brain đang chọn?\n(Di chuyển Javis/agents→agents, Javis/workflows→workflows, Memory→memory. Có git backup.)")) return;
      mig.disabled = true; mig.textContent = "Đang chuẩn hóa...";
      const fd = new FormData(); fd.append("brain", brain);
      let r = {};
      try { r = await (await fetch("/brain/migrate", { method: "POST", body: fd })).json(); } catch (e) { r = { ok: false, error: e.message }; }
      const res = document.getElementById("ovMigrateResult");
      if (r.ok) res.innerHTML = `✅ ${(r.moved || []).length ? "Đã di chuyển: " + r.moved.join(", ") : "Không có gì cần di chuyển (đã chuẩn)."}` + ((r.skipped || []).length ? `<br><span class="dim">Bỏ qua: ${r.skipped.join("; ")}</span>` : "");
      else res.textContent = "⚠ Lỗi: " + (r.error || "không rõ");
      mig.disabled = false; mig.textContent = "Chuẩn hóa brain đang chọn";
    };
  }

  // ---- Trang Models: (A) Main Model + (B) Providers ----
  async function renderModels(el) {
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">◈</div><div>Đang tải...</div></div>`;
    const s = await freshSettings();
    const m = s.model || {};
    const providers = m.providers || [];
    const main = m.main || {};
    const mainP = providers.find(p => p.id === main.provider) || {};
    const aux = (m.auxiliary || {}).model || "";
    const auxModels = (providers.find(p => p.id === "anthropic-cli") || {}).models || ["opus", "sonnet", "haiku", "fable"];
    const auxChips = ['<button class="aux-chip ' + (!aux ? "sel" : "") + '" data-aux="">Mặc định</button>']
      .concat(auxModels.map(mod => `<button class="aux-chip ${aux === mod ? "sel" : ""}" data-aux="${esc(mod)}">${esc(mod)}</button>`)).join("");
    const reasoning = m.reasoning || "off";
    const reasonChips = [["off", "Tắt"], ["low", "Thấp"], ["medium", "Vừa"], ["high", "Cao"]]
      .map(([v, l]) => `<button class="aux-chip ${reasoning === v ? "sel" : ""}" data-reason="${v}">${l}</button>`).join("");

    const KEYFIELD = { "openrouter": "openrouter_key", "anthropic-api": "anthropic_api_key", "openai": "openai_api_key", "gemini": "gemini_api_key" };
    const provHead = (p, on, kindLabel, statusText) => `
        <div class="prov-head">
          <span class="prov-shield ${on ? "on" : ""}">${_shield(on)}</span>
          <div class="prov-info">
            <div class="prov-name">${esc(p.label)} <span class="prov-kind">${kindLabel}</span></div>
            <div class="prov-status ${on ? "on" : ""}">${statusText}</div>
          </div>
          ${p.is_main ? '<span class="prov-badge">MAIN</span>' : ""}
        </div>`;
    const provCard = (p) => {
      const on = p.configured;
      if (p.kind === "oauth") {
        const st = on
          ? "● Đã kết nối" + (p.plan ? " · " + esc(p.plan) : "") + " · " + p.models.length + " model"
          : "○ Chưa kết nối · " + p.models.length + " model";
        return `<div class="prov-card ${p.is_main ? "main" : ""}">
          ${provHead(p, on, "Device code", st)}
          <div class="prov-action">
            ${on
              ? `<button class="gcard-btn" data-oauth-disc="1" style="background:transparent;opacity:.75">Ngắt</button>`
              : `<button class="gcard-btn" data-oauth-login="1">Đăng nhập ChatGPT</button>`}
            <span id="oauthMsg" class="gcard-meta" style="margin-left:10px;flex:1"></span>
          </div>
        </div>`;
      }
      if (p.kind === "cli") {   // Claude Code - trạng thái + login/logout nạp động qua /claude/status
        return `<div class="prov-card ${p.is_main ? "main" : ""}">
          <div class="prov-head">
            <span class="prov-shield on">${_shield(true)}</span>
            <div class="prov-info">
              <div class="prov-name">${esc(p.label)} <span class="prov-kind">MCP/skill</span></div>
              <div class="prov-status" id="cliStatus">đang kiểm tra…</div>
            </div>
            ${p.is_main ? '<span class="prov-badge">MAIN</span>' : ""}
          </div>
          <div class="prov-action" id="cliAction"></div>
        </div>`;
      }
      const masked = (m[KEYFIELD[p.id]] || "").slice(-4);
      return `<div class="prov-card ${p.is_main ? "main" : ""}">
        ${provHead(p, on, p.kind === "cli" ? "MCP/skill" : "chat", (on ? "● Đã kết nối" : "○ Chưa kết nối") + " · " + p.models.length + " model")}
        ${p.needs_key
          ? `<div class="prov-action"><input class="js-input" id="pk-${p.id}" type="password" placeholder="${on ? "đổi key (•••" + esc(masked) + ")" : "dán API key để kết nối"}"><button class="gcard-btn" data-pk="${p.id}">${on ? "Đổi key" : "Kết nối"}</button>${on ? `<button class="gcard-btn" data-disc="${p.id}" style="background:transparent;opacity:.75">Ngắt</button>` : ""}</div>`
          : `<div class="prov-note">Dùng đăng nhập Claude Code - không cần key</div>`}
      </div>`;
    };

    el.innerHTML = `
      <div class="cview-section">
        <h3>◆ Main Model <span style="opacity:.5">model chính cho hội thoại</span></h3>
        <div class="gcard current" style="max-width:540px">
          <div class="gcard-top"><span class="gcard-name">${esc(main.model || "-")}</span><span class="gcard-tag">${esc(mainP.label || main.provider || "")}</span></div>
          <div class="gcard-meta">${mainP.kind === "cli" ? "Qua Claude Code - đầy đủ MCP/skill/loop" : (mainP.kind === "api" ? "Gọi API thẳng - chat thuần (không MCP)" : "")}</div>
          <button class="gcard-btn" id="mdChange">Đổi model ▾</button>
        </div>
      </div>
      <div class="cview-section">
        <h3>◆ Providers <span style="opacity:.5">đăng nhập / kết nối nhà cung cấp model</span></h3>
        <div class="prov-list">${providers.map(provCard).join("")}</div>
      </div>
      <div class="cview-section">
        <h3>◆ Auxiliary <span style="opacity:.5">model việc nền: loop · metrics · ingest</span></h3>
        <div class="gcard" style="max-width:540px">
          <div class="gcard-meta">Chọn model rẻ cho việc chạy nền để tiết kiệm. "Mặc định" = dùng model mặc định của Claude Code.</div>
          <div class="aux-chips">${auxChips}</div>
        </div>
      </div>
      <div class="cview-section">
        <h3>◆ Suy nghĩ <span style="opacity:.5">độ sâu reasoning khi trả lời</span></h3>
        <div class="gcard" style="max-width:540px">
          <div class="gcard-meta">Bật để model suy nghĩ kỹ hơn trước khi trả lời - chính xác hơn nhưng chậm & tốn token hơn. Claude API/OpenRouter dùng adaptive thinking + effort; OpenAI chỉ áp cho model o-series; Gemini áp cho model 2.5 trở lên; Claude Code chèn gợi ý think/ultrathink.</div>
          <div class="aux-chips">${reasonChips}</div>
        </div>
      </div>`;

    const chg = document.getElementById("mdChange");
    if (chg) chg.onclick = () => openModelPicker(providers, main, () => renderModels(el));
    el.querySelectorAll(".aux-chip[data-aux]").forEach(b => b.onclick = async () => {
      await saveSetting("model", { auxiliary: { model: b.dataset.aux } });
      renderModels(el);
    });
    el.querySelectorAll(".aux-chip[data-reason]").forEach(b => b.onclick = async () => {
      await saveSetting("model", { reasoning: b.dataset.reason });
      renderModels(el);
    });
    el.querySelectorAll(".gcard-btn[data-pk]").forEach(b => {
      b.onclick = async () => {
        const pid = b.dataset.pk;
        const inp = document.getElementById("pk-" + pid);
        const val = (inp && inp.value || "").trim();
        if (!val) { if (inp) inp.focus(); return; }
        b.disabled = true; b.textContent = "Đang lưu...";
        await saveSetting("model", { [KEYFIELD[pid]]: val });
        renderModels(el);
      };
    });
    el.querySelectorAll(".gcard-btn[data-disc]").forEach(b => {
      b.onclick = async () => {
        b.disabled = true; b.textContent = "Đang ngắt...";
        await saveSetting("model", { clear_key: b.dataset.disc });
        renderModels(el);
      };
    });
    const ol = el.querySelector("[data-oauth-login]");
    if (ol) ol.onclick = () => startOauthLogin(el);
    const od = el.querySelector("[data-oauth-disc]");
    if (od) od.onclick = async () => {
      od.disabled = true; od.textContent = "Đang ngắt...";
      try { await fetch("/oauth/openai/disconnect", { method: "POST" }); } catch (e) {}
      renderModels(el);
    };
    refreshClaudeCard(el);   // nạp trạng thái đăng nhập Claude Code (bất đồng bộ)
  }

  // ---- Card Claude Code: status + login/logout (giống OpenAI OAuth) ----
  async function refreshClaudeCard(el) {
    const st = el.querySelector("#cliStatus"), act = el.querySelector("#cliAction");
    if (!st || !act) return;
    let d;
    try { d = await (await fetch("/claude/status")).json(); }
    catch (e) { st.textContent = "không kiểm tra được"; return; }
    if (d.connected) {
      st.className = "prov-status on";
      st.textContent = "● Đã kết nối" + (d.email ? " · " + d.email : "") + (d.plan ? " · " + d.plan : "");
      act.innerHTML = `<button class="gcard-btn" id="cliLogout" style="background:transparent;opacity:.75">Ngắt</button>`;
      el.querySelector("#cliLogout").onclick = async () => {
        const b = el.querySelector("#cliLogout"); b.disabled = true; b.textContent = "Đang ngắt…";
        try { await fetch("/claude/logout", { method: "POST" }); } catch (e) {}
        refreshClaudeCard(el);
      };
    } else {
      st.className = "prov-status";
      st.textContent = d.error ? "○ " + esc(d.error) : "○ Chưa đăng nhập";
      act.innerHTML = `
        <button class="gcard-btn" id="cliLogin">Đăng nhập Claude</button>
        <button class="gcard-btn" id="cliRecheck" style="background:transparent;opacity:.75">↻ Kiểm tra lại</button>
        <span id="cliMsg" class="gcard-meta" style="margin-left:10px;flex:1"></span>
        <div class="prov-note" style="margin-top:8px;line-height:1.6">
          Bấm <b>Đăng nhập Claude</b> → hiện link → mở link đăng nhập claude.ai → dán code (nếu trang yêu cầu) vào ô.
          Chạy được cả trên VPS. (Hoặc terminal: <code>claude auth login --claudeai</code>.)
        </div>`;
      el.querySelector("#cliLogin").onclick = () => startClaudeLogin(el);
      el.querySelector("#cliRecheck").onclick = () => refreshClaudeCard(el);
    }
  }

  async function startClaudeLogin(el) {
    const act = el.querySelector("#cliAction");
    const msg = el.querySelector("#cliMsg");
    if (msg) msg.textContent = "Đang lấy link đăng nhập…";
    let r;
    try { r = await (await fetch("/claude/login-start", { method: "POST" })).json(); }
    catch (e) { if (msg) msg.textContent = "Lỗi mạng."; return; }
    if (!r.ok) { if (msg) msg.textContent = "⚠ " + (r.error || "Không bắt đầu được đăng nhập."); return; }
    if (act) act.innerHTML = `
      <div class="prov-note" style="line-height:1.7">
        <b>1)</b> Mở link này để đăng nhập claude.ai:<br>
        <a href="${esc(safeHref(r.url))}" target="_blank" rel="noopener" style="color:#7aa2ff;word-break:break-all">${esc(r.url || "(không có link)")}</a><br>
        <b>2)</b> Đăng nhập xong, nếu trang hiện <b>một mã code</b> thì dán vào đây:
        <div style="margin-top:6px;display:flex;gap:8px;max-width:520px">
          <input class="js-input" id="cliCode" placeholder="dán code (nếu có)" style="flex:1">
          <button class="gcard-btn" id="cliCodeBtn">Gửi code</button>
        </div>
        <span id="cliMsg2" class="gcard-meta"></span>
      </div>`;
    const m2 = el.querySelector("#cliMsg2");
    let stopped = false;
    const t0 = Date.now();
    const poll = async () => {   // tự hoàn tất (một số luồng không cần dán code)
      if (stopped) return;
      if (Date.now() - t0 > 5 * 60 * 1000) { if (m2) m2.textContent = "Hết thời gian, thử lại."; return; }
      let d; try { d = await (await fetch("/claude/status")).json(); } catch (e) { setTimeout(poll, 3000); return; }
      if (d.connected) { stopped = true; refreshClaudeCard(el); return; }
      setTimeout(poll, 3000);
    };
    setTimeout(poll, 3000);
    const cb = el.querySelector("#cliCodeBtn");
    if (cb) cb.onclick = async () => {
      const code = (el.querySelector("#cliCode").value || "").trim();
      if (m2) m2.textContent = "Đang xác nhận…";
      const fd = new FormData(); fd.append("code", code);
      let rr;
      try { rr = await (await fetch("/claude/login-code", { method: "POST", body: fd })).json(); }
      catch (e) { if (m2) m2.textContent = "Lỗi mạng."; return; }
      if (rr.ok) { stopped = true; refreshClaudeCard(el); }
      else if (m2) m2.textContent = "⚠ " + (rr.error || "Code sai, thử lại.");
    };
  }

  // ---- ChatGPT OAuth device-code: lấy mã → mở link → poll tới khi kết nối ----
  async function startOauthLogin(el) {
    const msg = el.querySelector("#oauthMsg");
    if (msg) msg.textContent = "Đang khởi tạo…";
    let d;
    try { d = await (await fetch("/oauth/openai/start", { method: "POST" })).json(); }
    catch (e) { if (msg) msg.textContent = "Lỗi kết nối server."; return; }
    if (d.error) { if (msg) msg.textContent = "Lỗi: " + d.error; return; }
    try { window.open(d.verification_uri, "_blank"); } catch (e) {}
    if (msg) msg.innerHTML = `Mở <a href="${esc(safeHref(d.verification_uri))}" target="_blank">${esc(d.verification_uri)}</a> · nhập mã <b style="font-size:1.15em;letter-spacing:1px">${esc(d.user_code)}</b> <span style="opacity:.6">- đang chờ…</span>`;
    const iv = Math.max(2, (d.interval || 5)) * 1000;
    const t0 = Date.now();
    const poll = async () => {
      if (Date.now() - t0 > 16 * 60 * 1000) { if (msg) msg.textContent = "Hết hạn, thử lại."; return; }
      let p;
      try { p = await (await fetch("/oauth/openai/poll", { method: "POST" })).json(); }
      catch (e) { setTimeout(poll, iv); return; }
      if (p.status === "connected") { if (msg) msg.textContent = "✓ Đã kết nối!"; renderModels(el); return; }
      if (p.status === "error") { if (msg) msg.textContent = "Lỗi: " + (p.error || ""); return; }
      setTimeout(poll, iv);
    };
    setTimeout(poll, iv);
  }

  // ---- Picker model (kiểu Hermes SET MAIN MODEL) ----
  function openModelPicker(providers, main, onDone) {
    let modal = document.getElementById("modelPicker");
    if (!modal) { modal = document.createElement("div"); modal.id = "modelPicker"; modal.className = "mp-overlay"; document.body.appendChild(modal); }
    let selProv = main.provider || (providers[0] && providers[0].id);
    let selModel = (providers.find(p => p.id === selProv) || {}).is_main ? main.model : null;
    const liveCache = {};      // pid -> {models:[], live:bool} - model load động từ API provider
    let loadingProv = null;

    const modelsFor = (pid) => (liveCache[pid] && liveCache[pid].models) || (providers.find(x => x.id === pid) || {}).models || [];
    const tagFor = (pid) => {
      if (loadingProv === pid && !liveCache[pid]) return " · đang tải…";
      if (!liveCache[pid]) return "";
      return liveCache[pid].live ? " · live" : " · catalog";
    };

    async function ensureModels(pid) {
      if (liveCache[pid]) { draw(); return; }
      loadingProv = pid; draw();
      let res = null;
      try { res = await (await fetch("/provider/models?provider=" + encodeURIComponent(pid))).json(); } catch (e) {}
      const stat = (providers.find(x => x.id === pid) || {}).models || [];
      liveCache[pid] = (res && res.models && res.models.length)
        ? { models: res.models, live: !!res.live } : { models: stat, live: false };
      if (loadingProv === pid) loadingProv = null;
      if (pid === selProv) {   // model đang chọn không còn trong list mới → reset
        const ms = liveCache[pid].models;
        if (!selModel || ms.indexOf(selModel) < 0)
          selModel = (pid === main.provider && ms.indexOf(main.model) >= 0) ? main.model : (ms[0] || null);
      }
      draw();
    }

    const draw = () => {
      const models = modelsFor(selProv);
      modal.innerHTML = `
        <div class="mp-box">
          <div class="mp-head">
            <div><div class="mp-title">SET MAIN MODEL</div><div class="mp-sub">hiện tại: ${esc(main.model || "-")} · ${esc(main.provider || "")}</div></div>
            <button class="mp-x" data-act="close">✕</button>
          </div>
          <input class="mp-filter" placeholder="Lọc provider / model…">
          <div class="mp-body">
            <div class="mp-provs">${providers.map(p => `
              <button class="mp-prov ${p.id === selProv ? "active" : ""}" data-prov="${p.id}">
                <div class="mp-prov-l">${esc(p.label)}</div>
                <div class="mp-prov-c">${esc(p.id)}${p.is_main ? " · CURRENT" : ""}${esc(tagFor(p.id))}${p.configured ? "" : " · ⚠ cần kết nối"}</div>
              </button>`).join("")}</div>
            <div class="mp-models">${models.length ? models.map(mod => `
              <button class="mp-model ${mod === selModel ? "sel" : ""}" data-mod="${esc(mod)}">${esc(mod)}${(selProv === main.provider && mod === main.model) ? ' <span class="mp-cur">CURRENT</span>' : ""}</button>`).join("")
                : (loadingProv === selProv ? '<div class="mp-empty">Đang tải model…</div>' : '<div class="mp-empty">Provider chưa kết nối hoặc không có model. Kết nối ở Providers (hoặc thêm vào settings.json → model.catalog).</div>')}</div>
          </div>
          <div class="mp-foot">
            <span class="mp-note">Model load động theo provider · lưu cho phiên mới</span>
            <div><button class="mp-btn" data-act="close">Huỷ</button><button class="mp-btn primary" data-act="switch" ${selModel ? "" : "disabled"}>Switch</button></div>
          </div>
        </div>`;
      modal.querySelectorAll(".mp-prov").forEach(b => b.onclick = () => {
        selProv = b.dataset.prov;
        const ms = modelsFor(selProv);
        selModel = (selProv === main.provider && ms.indexOf(main.model) >= 0) ? main.model : (liveCache[selProv] ? (ms[0] || null) : null);
        ensureModels(selProv);
      });
      modal.querySelectorAll(".mp-model").forEach(b => b.onclick = () => { selModel = b.dataset.mod; draw(); });
      modal.querySelectorAll('[data-act="close"]').forEach(b => b.onclick = () => modal.classList.remove("open"));
      modal.querySelector(".mp-filter").oninput = (e) => {
        const q = (e.target.value || "").toLowerCase();
        modal.querySelectorAll(".mp-prov,.mp-model").forEach(x => { x.style.display = (!q || x.textContent.toLowerCase().includes(q)) ? "" : "none"; });
      };
      const sw = modal.querySelector('[data-act="switch"]');
      if (sw) sw.onclick = async () => {
        if (!selModel) return;
        sw.disabled = true; sw.textContent = "Đang đổi...";
        await saveSetting("model", { main: { provider: selProv, model: selModel } });
        modal.classList.remove("open");
        if (onDone) onDone();
      };
    };
    ensureModels(selProv);
    modal.classList.add("open");
  }

  // ---- Trang MCP - quản lý server công cụ ngoài cho engine Claude Code ----
  async function postJson(url, obj) {
    try { return await (await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj || {}) })).json(); }
    catch (e) { return { ok: false, error: String(e) }; }
  }
  function parseKV(text, sep) {
    const o = {};
    (text || "").split("\n").forEach(line => {
      line = line.trim(); if (!line) return;
      let i = line.indexOf(sep); if (i < 0 && sep === ":") i = line.indexOf("=");
      if (i < 0) return;
      const k = line.slice(0, i).trim(), v = line.slice(i + 1).trim();
      if (k) o[k] = v;
    });
    return o;
  }
  // ==== Trang Kết nối: kho connector + đa tài khoản (qua MCP hub) ====
  const PERM_META = {
    readonly: { label: "Chỉ đọc", color: "#4da3ff" },
    safe: { label: "Ghi nháp", color: "#d9a521" },
    full: { label: "Toàn quyền", color: "#e06c5a" },
  };
  const AUTH_BADGE = { apikey: "API key", qr: "QR Zalo", oauth: "OAuth", none: "Tự do" };
  let _connPoll = null;

  function closeConnModal() {
    const m = document.getElementById("connectModal");
    if (m) m.classList.remove("open");
    if (_connPoll) { clearInterval(_connPoll); _connPoll = null; }
  }
  function connModal(html, maxw) {
    let m = document.getElementById("connectModal");
    if (!m) { m = document.createElement("div"); m.id = "connectModal"; m.className = "mp-overlay"; document.body.appendChild(m); }
    m.innerHTML = '<div class="mp-box" style="max-width:' + (maxw || 520) + 'px">' + html + '</div>';
    m.classList.add("open");
    m.querySelectorAll('[data-act="close"]').forEach(b => b.onclick = closeConnModal);
    return m;
  }
  function mHead(title) {
    return '<div class="mp-head"><div class="mp-title">' + title + '</div><button class="mp-x" data-act="close">✕</button></div>';
  }
  function permChip(p) {
    const m = PERM_META[p] || PERM_META.full;
    return '<span class="perm-chip" style="color:' + m.color + ';border-color:' + m.color + '55">' + m.label + '</span>';
  }
  function iconInner(con) {
    // icon là URL/đường dẫn ảnh (logo hãng) → render <img>; còn lại là emoji → in thẳng.
    const ic = (con && con.icon) || "🔌";
    return /^(https?:|\/)/.test(ic) ? '<img class="ico-img" src="' + esc(ic) + '" alt="" loading="lazy">' : ic;
  }
  function connChip(c) {
    return '<button class="conn-chip' + (c.enabled ? "" : " off") + '" data-conn="' + c.id + '">'
      + '<span class="cdot' + (c.enabled ? " on" : "") + '">●</span> ' + esc(c.label || c.name || "?")
      + (c.is_default ? ' <span class="cstar">★</span>' : "") + " " + permChip(c.perm) + '</button>';
  }
  function connectorCard(con, conns) {
    const chips = conns.map(connChip).join("")
      + '<button class="conn-chip add" data-addacc="' + esc(con.id) + '">＋ Thêm tài khoản</button>';
    return '<div class="prov-card conn-card">'
      + '<div class="prov-head"><span class="conn-ico">' + iconInner(con) + '</span>'
      + '<div class="prov-info"><div class="prov-name">' + esc(con.name || con.id) + '</div>'
      + '<div class="prov-status">' + esc(con.description || "") + '</div></div></div>'
      + '<div class="conn-accounts">' + chips + '</div></div>';
  }
  function catalogCard(con) {
    const soon = con.status === "soon";
    const badge = '<span class="prov-kind">' + (AUTH_BADGE[con.auth_type] || con.auth_type || "") + '</span>'
      + (con.status === "beta" ? ' <span class="prov-kind" style="color:#d9a521">beta</span>' : "")
      + (soon ? ' <span class="prov-kind">sắp có</span>' : "");
    return '<div class="cat-card' + (soon ? " soon" : "") + '" data-cat="' + esc(con.category || "Khác") + '">'
      + '<div class="cat-ico">' + iconInner(con) + '</div>'
      + '<div class="cat-name">' + esc(con.name) + ' ' + badge + '</div>'
      + '<div class="cat-desc">' + esc(con.description || "") + '</div>'
      + (soon
        ? '<button class="gcard-btn" disabled style="opacity:.5">Sắp có</button>'
          + (con.guide_url ? ' <a class="cat-doc" href="' + esc(con.guide_url) + '" target="_blank">docs ↗</a>' : "")
        : '<button class="gcard-btn" data-connect="' + esc(con.id) + '">Kết nối</button>')
      + '</div>';
  }

  function openAddFlow(el, con, isFirst) {
    if (!con) return;
    if (con.id === "custom") return openMcpForm(el);
    if (con.auth_type === "qr") return openQrFlow(el, con, isFirst);
    if (con.auth_type === "oauth") return openOauthFlow(el, con);
    openApikeyFlow(el, con, isFirst);
  }

  function openApikeyFlow(el, con, isFirst) {
    const fields = (con.fields || []).map(f =>
      '<label class="mcp-lb">' + esc(f.label || f.key)
      + (f.multiline
        ? '<textarea class="js-input" data-f="' + esc(f.key) + '" rows="5" placeholder="' + esc(f.placeholder || "") + '"></textarea>'
        : '<input class="js-input" data-f="' + esc(f.key) + '" placeholder="' + esc(f.placeholder || "") + '">')
      + '</label>').join("");
    const m = connModal(mHead("KẾT NỐI " + esc((con.name || "").toUpperCase()))
      + '<div class="conn-form">'
      + (con.guide ? '<div class="conn-guide">' + esc(con.guide) + (con.guide_url ? ' <a href="' + esc(con.guide_url) + '" target="_blank">Hướng dẫn ↗</a>' : "") + '</div>' : "")
      + fields
      + '<label class="mcp-lb">Tên gợi nhớ (tuỳ chọn - bỏ trống sẽ tự lấy tên tài khoản/shop)<input class="js-input" id="cLabel"></label>'
      + '</div>'
      + '<div class="mp-foot"><span class="mp-note" id="cErr"></span><div><button class="mp-btn" data-act="close">Huỷ</button><button class="mp-btn primary" id="cGo">Kết nối</button></div></div>');
    m.querySelector("#cGo").onclick = async () => {
      const fieldsVal = {};
      let missing = "";
      m.querySelectorAll("[data-f]").forEach(inp => {
        const k = inp.dataset.f, v = inp.value.trim();
        fieldsVal[k] = v;
        const fd = (con.fields || []).find(x => x.key === k) || {};
        if (!v && !fd.optional) missing = fd.label || k;
      });
      const err = m.querySelector("#cErr"), go = m.querySelector("#cGo");
      if (missing) { err.textContent = "Thiếu: " + missing; return; }
      go.disabled = true; go.textContent = "Đang kiểm tra key…"; err.textContent = "";
      const r = await postJson("/connect/add", { connector_id: con.id, fields: fieldsVal, label: m.querySelector("#cLabel").value.trim() });
      if (!r.ok) { err.textContent = r.error || "Lỗi"; go.disabled = false; go.textContent = "Kết nối"; return; }
      m.querySelector(".conn-form").innerHTML = '<div class="conn-ok">✓ Đã kết nối: <b>' + esc(r.label || con.name) + '</b> (' + (r.tools || 0) + ' công cụ)'
        + (isFirst ? '<div class="conn-hint">Sang trang Javis hỏi thử: "Hôm nay bán được bao nhiêu?"</div>' : "") + '</div>';
      go.style.display = "none";
      setTimeout(() => { closeConnModal(); renderConnect(el); }, 1600);
    };
  }

  function openQrFlow(el, con, isFirst) {
    const risk = con.risk ? '<div class="conn-risk">⚠ ' + esc(con.risk) + '</div>' : "";
    const m = connModal(mHead("KẾT NỐI " + esc((con.name || "").toUpperCase()))
      + '<div class="conn-form">' + risk
      + '<label class="mcp-lb">Tên gợi nhớ (tuỳ chọn)<input class="js-input" id="qLabel"></label>'
      + '<button class="mp-btn primary" id="qGo">' + (con.risk ? "Tôi hiểu rủi ro, hiện mã QR" : "Hiện mã QR") + '</button>'
      + '<div id="qrZone"></div></div>'
      + '<div class="mp-foot"><span class="mp-note" id="qErr"></span><button class="mp-btn" data-act="close">Đóng</button></div>');
    m.querySelector("#qGo").onclick = async () => {
      const err = m.querySelector("#qErr");
      err.textContent = "";
      const r = await postJson("/connect/zalo/start", { label: m.querySelector("#qLabel").value.trim() });
      if (!r.ok) { err.textContent = r.error || "Lỗi"; return; }
      m.querySelector("#qGo").style.display = "none";
      const zone = m.querySelector("#qrZone");
      zone.innerHTML = '<div class="mp-note" style="margin-top:8px">Đang khởi động… (lần đầu hơi lâu do phải tải công cụ)</div>';
      _connPoll = setInterval(async () => {
        let st;
        try { st = await (await fetch("/connect/zalo/status?sid=" + encodeURIComponent(r.sid))).json(); } catch (e) { return; }
        if (st.state === "qr" && st.qr) {
          zone.innerHTML = '<img class="qr-img" src="' + st.qr + '"><div class="mp-note">Mở Zalo trên điện thoại > biểu tượng QR góc trên > quét mã này</div>';
        } else if (st.state === "done") {
          clearInterval(_connPoll); _connPoll = null;
          zone.innerHTML = '<div class="conn-ok">✓ Đã đăng nhập: <b>' + esc(st.label || "Zalo") + '</b>'
            + (isFirst ? '<div class="conn-hint">Sang trang Javis nhắn thử: "Đọc tin nhắn Zalo mới nhất"</div>' : "") + '</div>';
          setTimeout(() => { closeConnModal(); renderConnect(el); }, 1800);
        } else if (st.state === "error") {
          clearInterval(_connPoll); _connPoll = null;
          zone.innerHTML = "";
          err.textContent = st.error || "Lỗi đăng nhập";
          m.querySelector("#qGo").style.display = "";
        }
      }, 1500);
    };
  }

  function openOauthFlow(el, con) {
    // Provider không tự đăng ký client (vd Google) khai sẵn fields client_id/secret user tự tạo.
    const fields = (con.fields || []).map(f =>
      '<label class="mcp-lb">' + esc(f.label || f.key)
      + '<input class="js-input" data-f="' + esc(f.key) + '" placeholder="' + esc(f.placeholder || "") + '"></label>').join("");
    const m = connModal(mHead("KẾT NỐI " + esc((con.name || "").toUpperCase()))
      + '<div class="conn-form"><div class="conn-guide">' + esc(con.guide || "Đăng nhập bằng tài khoản của nhà cung cấp.")
      + (con.guide_url ? ' <a href="' + esc(con.guide_url) + '" target="_blank">Hướng dẫn ↗</a>' : "") + '</div>'
      + fields
      + '<button class="mp-btn primary" id="oGo">' + (fields ? "Lưu & mở trang đăng nhập" : "Mở trang đăng nhập") + '</button></div>'
      + '<div class="mp-foot"><span class="mp-note" id="oErr"></span><button class="mp-btn" data-act="close">Đóng</button></div>');
    m.querySelector("#oGo").onclick = async () => {
      const err = m.querySelector("#oErr"), go = m.querySelector("#oGo");
      const fieldsVal = {};
      let missing = "";
      m.querySelectorAll("[data-f]").forEach(inp => {
        const k = inp.dataset.f, v = inp.value.trim();
        fieldsVal[k] = v;
        const fd = (con.fields || []).find(x => x.key === k) || {};
        if (!v && !fd.optional) missing = fd.label || k;
      });
      if (missing) { err.textContent = "Thiếu: " + missing; return; }
      go.disabled = true; err.textContent = "";
      const r = await postJson("/connect/oauth/start", { connector_id: con.id, fields: fieldsVal });
      go.disabled = false;
      if (!r.ok) { err.textContent = r.error || "Lỗi"; return; }
      window.open(r.url, "_blank");
      err.textContent = "Hoàn tất đăng nhập ở tab mới, xong quay lại bấm Làm mới trang này.";
    };
  }

  function openPermPicker(el, c, con) {
    const DESC = { readonly: "chỉ xem số liệu, không đụng dữ liệu thật", safe: "được ghi nháp, CHẶN hành động tiền/đơn/gửi tin", full: "thao tác THẬT: tạo đơn, gửi tin, publish…" };
    const opts = ["readonly", "safe", "full"].map(p =>
      '<button class="conn-menu-btn" data-p="' + p + '">' + permChip(p) + ' <span class="mp-note">' + DESC[p] + '</span></button>').join("");
    const m = connModal(mHead("QUYỀN: " + esc(c.label || "")) + '<div class="conn-menu">' + opts + '</div>'
      + '<div class="mp-foot"><button class="mp-btn" data-act="close">Huỷ</button></div>');
    m.querySelectorAll("[data-p]").forEach(b => b.onclick = async () => {
      const p = b.dataset.p;
      if (p === "full") return openFullAck(el, c, con);
      await postJson("/connect/update", { id: c.id, perm: p });
      closeConnModal(); renderConnect(el);
    });
  }
  function openFullAck(el, c, con) {
    const text = (con && con.risk) ? con.risk
      : "Mức này cho phép Javis thao tác THẬT ra ngoài qua kết nối này: tạo đơn, gửi tin, chạy quảng cáo, publish… Hành động có thể KHÔNG hoàn tác được.";
    const m = connModal(mHead("⚠ BẬT TOÀN QUYỀN")
      + '<div class="conn-form"><div class="conn-risk">' + esc(text) + '</div>'
      + '<label style="display:flex;gap:8px;align-items:center;cursor:pointer;font-size:14px"><input type="checkbox" id="ackChk"> Tôi hiểu rủi ro và tự chịu trách nhiệm</label></div>'
      + '<div class="mp-foot"><button class="mp-btn" data-act="close">Huỷ</button><button class="mp-btn primary" id="ackGo" disabled>Bật Toàn quyền</button></div>');
    m.querySelector("#ackChk").onchange = (e) => { m.querySelector("#ackGo").disabled = !e.target.checked; };
    m.querySelector("#ackGo").onclick = async () => {
      await postJson("/connect/update", { id: c.id, perm: "full" });
      closeConnModal(); renderConnect(el);
    };
  }

  function openAccountMenu(el, c, con) {
    const m = connModal(mHead(esc(c.label || "Tài khoản"))
      + '<div class="conn-menu">'
      + '<button class="conn-menu-btn" data-m="test">🔄 Test kết nối</button>'
      + '<button class="conn-menu-btn" data-m="default"' + (c.is_default ? " disabled" : "") + '>★ Đặt làm mặc định</button>'
      + '<button class="conn-menu-btn" data-m="rename">✏ Đổi tên</button>'
      + '<button class="conn-menu-btn" data-m="perm">🛡 Đổi quyền (' + ((PERM_META[c.perm] || {}).label || c.perm) + ')</button>'
      + '<button class="conn-menu-btn" data-m="deny">⛔ Chặn tool cụ thể' + ((c.deny_tools || []).length ? " (" + c.deny_tools.length + ")" : "") + '</button>'
      + '<button class="conn-menu-btn" data-m="audit">📜 Nhật ký gọi tool</button>'
      + '<button class="conn-menu-btn" data-m="toggle">' + (c.enabled ? "○ Tắt tạm" : "● Bật lại") + '</button>'
      + '<button class="conn-menu-btn danger" data-m="del">🗑 Xoá kết nối</button>'
      + '</div><div class="mp-foot"><span class="mp-note" id="cmNote"></span><button class="mp-btn" data-act="close">Đóng</button></div>');
    const note = m.querySelector("#cmNote");
    m.querySelectorAll("[data-m]").forEach(b => b.onclick = async () => {
      const act = b.dataset.m;
      if (act === "test") {
        note.textContent = "Đang test…";
        const r = await postJson("/connect/test", { id: c.id });
        note.textContent = r.ok ? "✓ OK - " + (r.tools || 0) + " công cụ" + (r.label ? " (" + r.label + ")" : "") : "⚠ " + (r.error || "lỗi");
      } else if (act === "default") {
        await postJson("/connect/default", { id: c.id }); closeConnModal(); renderConnect(el);
      } else if (act === "rename") {
        const v = prompt("Tên mới:", c.label || ""); if (v === null) return;
        await postJson("/connect/update", { id: c.id, label: v.trim() }); closeConnModal(); renderConnect(el);
      } else if (act === "perm") {
        openPermPicker(el, c, con);
      } else if (act === "deny") {
        const v = prompt("Tên tool cần CHẶN riêng cho kết nối này, cách nhau dấu phẩy.\nVD: pos_order, pos_transaction\n(Để trống = bỏ chặn)", (c.deny_tools || []).join(", "));
        if (v === null) return;
        await postJson("/connect/update", { id: c.id, deny_tools: v.split(",").map(x => x.trim()).filter(Boolean) });
        closeConnModal(); renderConnect(el);
      } else if (act === "audit") {
        openAuditModal(c);
      } else if (act === "toggle") {
        await postJson("/connect/toggle", { id: c.id }); closeConnModal(); renderConnect(el);
      } else if (act === "del") {
        if (!confirm('Xoá kết nối "' + (c.label || "") + '"?')) return;
        await postJson("/connect/delete", { id: c.id }); closeConnModal(); renderConnect(el);
      }
    });
  }

  async function openAuditModal(c) {
    const m = connModal(mHead("NHẬT KÝ: " + esc(c.label || "")) + '<div class="conn-audit" id="audBody">Đang tải…</div>'
      + '<div class="mp-foot"><button class="mp-btn" data-act="close">Đóng</button></div>', 640);
    let d;
    try { d = await (await fetch("/connect/audit?limit=80&id=" + encodeURIComponent(c.id))).json(); } catch (e) { d = { entries: [] }; }
    const rows = (d.entries || []).map(e =>
      '<div class="aud-row' + (e.ok ? "" : " bad") + '"><span class="aud-ts">' + esc((e.ts || "").replace("T", " ")) + '</span> '
      + esc(e.tool || "") + ' <span class="mp-note">' + esc(e.mode || "") + "/" + esc(e.cls || "") + " · " + (e.ms || 0) + "ms</span>"
      + (e.ok ? "" : '<div class="aud-err">' + esc(e.err || "") + '</div>') + '</div>').join("");
    m.querySelector("#audBody").innerHTML = rows || '<div class="mp-note">Chưa có lượt gọi nào.</div>';
  }
  function ambientCard(s) {   // MCP sẵn trong Claude Code - chỉ hiển thị
    const ok = s.connected;
    return `<div class="prov-card" style="opacity:.92">
      <div class="prov-head">
        <span class="prov-shield ${ok ? "on" : ""}">${_shield(ok)}</span>
        <div class="prov-info">
          <div class="prov-name">${esc(s.name)} <span class="prov-kind">claude code</span></div>
          <div class="prov-status ${ok ? "on" : ""}">${ok ? "● " : "⚠ "}${esc(s.status)}${s.url ? " · " + esc(s.url) : ""}</div>
        </div>
      </div>
    </div>`;
  }
  async function renderConnect(el) {
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">🔌</div><div>Đang tải...</div></div>`;
    let d;
    try { d = await (await fetch("/connect/catalog")).json(); } catch (e) { el.innerHTML = placeholder("mcp", "Không tải được."); return; }
    const cat = d.catalog || [];
    const conns = d.connections || [];
    const byId = {};
    cat.forEach(c => byId[c.id] = c);
    byId.custom = { id: "custom", name: "Tự thêm (nâng cao)", icon: "🧩", category: "Khác",
                    description: "Server MCP tự khai URL/lệnh/header - dành cho người rành kỹ thuật.", auth_type: "apikey" };
    const st = await freshSettings();
    const main = (st.model && st.model.main) || {};
    const provs = (st.model && st.model.providers) || [];
    const MCP_PROVIDERS = ["anthropic-cli", "openrouter", "openai", "anthropic-api"];
    const mainLabel = (provs.find(p => p.id === main.provider) || {}).label || main.provider || "-";
    let warn = "";
    if (main.provider === "openai-oauth") {
      warn = `<div class="gcard" style="border:1px solid #2c7a4b;background:rgba(44,122,75,.10);max-width:740px;margin-bottom:14px"><div class="gcard-meta" style="opacity:1">✓ <b>ChatGPT (gói subscription)</b> chạy qua <b>Codex CLI</b> - Javis tự đẩy kho Kết nối sang Codex qua hub, nên vẫn dùng được đầy đủ.</div></div>`;
    } else if (!MCP_PROVIDERS.includes(main.provider)) {
      warn = `<div class="gcard" style="border:1px solid #b9821f;background:rgba(185,130,31,.10);max-width:740px;margin-bottom:14px"><div class="gcard-meta" style="opacity:1">⚠ Main Model đang là <b>${esc(mainLabel)}</b> - chưa hỗ trợ gọi công cụ. Đổi ở trang <b>Models</b>.</div></div>`;
    } else if (main.provider !== "anthropic-cli") {
      warn = `<div class="gcard" style="border:1px solid #2c7a4b;background:rgba(44,122,75,.10);max-width:740px;margin-bottom:14px"><div class="gcard-meta" style="opacity:1">✓ <b>${esc(mainLabel)}</b> dùng được kho Kết nối (qua vòng gọi tool + hub), kèm cả tool file và skill.</div></div>`;
    }
    const groups = {};
    conns.forEach(c => { const k = c.connector_id || "custom"; (groups[k] = groups[k] || []).push(c); });
    const connectedHtml = Object.keys(groups).map(cid =>
      connectorCard(byId[cid] || { id: cid, name: cid, icon: "🔌" }, groups[cid])).join("");
    const cats = Array.from(new Set(cat.map(c => c.category || "Khác")));
    el.innerHTML = warn
      + '<div class="cview-section"><h3>◆ Đã kết nối <span style="opacity:.5">' + conns.length + ' tài khoản</span></h3>'
      + '<div class="gcard-meta" style="max-width:740px">Một dịch vụ nối được NHIỀU tài khoản (nhiều shop, nhiều số Zalo…). Mọi bộ não - Claude Code, ChatGPT/Codex, OpenRouter, API - dùng chung kho này qua MCP hub, kèm phân quyền và nhật ký.'
      + '<label style="margin-left:8px;cursor:pointer"><input type="checkbox" id="mcpStrict" ' + (d.strict ? "checked" : "") + '> Chỉ dùng kết nối của Javis (bỏ MCP sẵn của máy)</label></div>'
      + '<div class="prov-list" style="margin-top:12px">' + (connectedHtml || '<div class="mp-empty">Chưa đấu nguồn nào - chọn một dịch vụ trong Kho bên dưới để bắt đầu.</div>') + '</div></div>'
      + '<div class="cview-section"><h3>◆ Kho kết nối</h3>'
      + '<div class="cat-tools"><input class="js-input" id="catQ" placeholder="Tìm dịch vụ…" style="max-width:220px">'
      + '<span class="cat-filter"><button class="cat-chip on" data-catf="">Tất cả</button>' + cats.map(x => '<button class="cat-chip" data-catf="' + esc(x) + '">' + esc(x) + '</button>').join("") + '</span></div>'
      + '<div class="cat-grid" id="catGrid">' + cat.map(catalogCard).join("") + catalogCard(byId.custom) + '</div></div>'
      + '<div class="cview-section"><h3>◆ MCP từ Claude Code <span style="opacity:.5">tài khoản - chỉ hiển thị</span></h3>'
      + '<div class="gcard-meta" style="max-width:740px">Các MCP anh đã kết nối sẵn trong Claude Code (đồng bộ từ claude.ai). Engine Claude Code tự dùng các cái "Connected". Đăng nhập/quản lý trong app Claude, không sửa ở đây.</div>'
      + '<div class="prov-list" id="mcpAmbient" style="margin-top:12px"><div class="mp-empty">Đang tải… (kiểm tra sức khoẻ MCP, hơi lâu)</div></div></div>';
    document.getElementById("mcpStrict").onchange = (e) => postJson("/mcp/strict", { strict: e.target.checked });
    const isFirst = conns.length === 0;
    el.querySelectorAll("[data-connect]").forEach(b => b.onclick = () => openAddFlow(el, byId[b.dataset.connect], isFirst));
    el.querySelectorAll("[data-addacc]").forEach(b => b.onclick = () => openAddFlow(el, byId[b.dataset.addacc], false));
    el.querySelectorAll("[data-conn]").forEach(b => b.onclick = () => {
      const c = conns.find(x => x.id === b.dataset.conn);
      if (c) openAccountMenu(el, c, byId[c.connector_id]);
    });
    const applyFilter = () => {
      const q = (document.getElementById("catQ").value || "").toLowerCase();
      const onChip = el.querySelector(".cat-chip.on");
      const cf = onChip ? (onChip.dataset.catf || "") : "";
      el.querySelectorAll("#catGrid .cat-card").forEach(card => {
        const okQ = !q || card.textContent.toLowerCase().includes(q);
        const okC = !cf || card.dataset.cat === cf;
        card.style.display = (okQ && okC) ? "" : "none";
      });
    };
    document.getElementById("catQ").oninput = applyFilter;
    el.querySelectorAll(".cat-chip").forEach(ch => ch.onclick = () => {
      el.querySelectorAll(".cat-chip").forEach(x => x.classList.remove("on"));
      ch.classList.add("on");
      applyFilter();
    });
    fetch("/mcp/ambient").then(r => r.json()).then(a => {
      const box = document.getElementById("mcpAmbient"); if (!box) return;
      const list = a.servers || [];
      box.innerHTML = list.length ? list.map(ambientCard).join("") : '<div class="mp-empty">Không có (hoặc Claude CLI chưa cài).</div>';
    }).catch(() => { const box = document.getElementById("mcpAmbient"); if (box) box.innerHTML = '<div class="mp-empty">Không tải được.</div>'; });
  }
  function openMcpForm(el, server) {
    const edit = !!server;
    let modal = document.getElementById("mcpAddModal");
    if (!modal) { modal = document.createElement("div"); modal.id = "mcpAddModal"; modal.className = "mp-overlay"; document.body.appendChild(modal); }
    const keys = edit ? (server.header_keys || []).concat(server.env_keys || []) : [];
    const credPh = edit && keys.length ? "Để trống = giữ key cũ (" + esc(keys.join(", ")) + ")" : "Authorization: Bearer xxxxx";
    modal.innerHTML = `
      <style>#mcpAddModal .mcp-lb{display:flex;flex-direction:column;gap:4px;font-size:14px;opacity:.85}#mcpAddModal .mcp-lb input,#mcpAddModal .mcp-lb select,#mcpAddModal .mcp-lb textarea{width:100%}</style>
      <div class="mp-box" style="max-width:560px">
        <div class="mp-head"><div class="mp-title">${edit ? "SỬA MCP SERVER" : "THÊM MCP SERVER"}</div><button class="mp-x" data-act="close">✕</button></div>
        <div style="padding:14px 18px;display:flex;flex-direction:column;gap:10px">
          <label class="mcp-lb">Tên<input class="js-input" id="mName" placeholder="pancake-pos-shop-2" value="${edit ? esc(server.name) : ""}"></label>
          <label class="mcp-lb">Transport<select class="js-input" id="mTransport"><option value="http">HTTP</option><option value="sse">SSE</option><option value="stdio">stdio</option></select></label>
          <label class="mcp-lb" id="mUrlWrap">URL<input class="js-input" id="mUrl" placeholder="https://mcp-pos.pancake.biz/mcp" value="${edit ? esc(server.url || "") : ""}"></label>
          <label class="mcp-lb" id="mCmdWrap" style="display:none">Lệnh (stdio)<input class="js-input" id="mCmd" placeholder="npx my-mcp-server (args cách nhau bằng dấu cách)" value="${edit ? esc(((server.command || "") + " " + (server.args || []).join(" ")).trim()) : ""}"></label>
          <label class="mcp-lb" id="mCredWrap">Header (mỗi dòng, vd Authorization: Bearer xxx)<textarea class="js-input" id="mCred" rows="3" placeholder="${credPh}"></textarea></label>
        </div>
        <div class="mp-foot"><span class="mp-note" id="mErr"></span><div><button class="mp-btn" data-act="close">Huỷ</button><button class="mp-btn primary" id="mSave">${edit ? "Lưu" : "Thêm"}</button></div></div>
      </div>`;
    const $ = (id) => modal.querySelector(id);
    if (edit) $("#mTransport").value = server.transport || "http";
    const sync = () => {
      const t = $("#mTransport").value;
      $("#mUrlWrap").style.display = (t === "stdio") ? "none" : "";
      $("#mCmdWrap").style.display = (t === "stdio") ? "" : "none";
      $("#mCredWrap").childNodes[0].nodeValue = (t === "stdio") ? "Env KEY=VALUE (mỗi dòng)" : "Header (mỗi dòng, vd Authorization: Bearer xxx)";
    };
    $("#mTransport").onchange = sync; sync();
    modal.querySelectorAll('[data-act="close"]').forEach(b => b.onclick = () => modal.classList.remove("open"));
    $("#mSave").onclick = async () => {
      const t = $("#mTransport").value;
      const body = { name: $("#mName").value.trim(), transport: t, url: $("#mUrl").value.trim() };
      if (!body.name) { $("#mErr").textContent = "Thiếu tên"; return; }
      const cred = $("#mCred").value.trim();
      if (t === "stdio") {
        const parts = $("#mCmd").value.trim().split(/\s+/).filter(Boolean);
        body.command = parts[0] || ""; body.args = parts.slice(1); body.auth = "env";
        if (cred || !edit) body.env = parseKV(cred, "=");
      } else {
        body.auth = "header";
        if (cred || !edit) body.headers = parseKV(cred, ":");   // edit + để trống = giữ key cũ
      }
      $("#mSave").disabled = true; $("#mSave").textContent = "Đang lưu…";
      let r;
      if (edit) { body.id = server.id; r = await postJson("/mcp/update", body); }
      else r = await postJson("/mcp/add", body);
      if (!r.ok) { $("#mErr").textContent = r.error || "Lỗi"; $("#mSave").disabled = false; $("#mSave").textContent = edit ? "Lưu" : "Thêm"; return; }
      modal.classList.remove("open");
      renderConnect(el);
    };
    modal.classList.add("open");
  }

  // ---- Trang Kênh (Telegram) - form đầy đủ ----
  async function renderChannels(el) {
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">✉</div><div>Đang tải...</div></div>`;
    const s = await freshSettings();
    const tg = s.telegram || {};
    el.innerHTML = `
      <div class="cview-section">
        <h3>Telegram</h3>
        <div class="gcard" style="max-width:560px">
          <label class="js-row"><span>Bật bot Telegram</span><input type="checkbox" id="tgEnabled" ${tg.enabled ? "checked" : ""}></label>
          <label class="js-lbl">Bot token ${tg.token_set ? '<span class="dim">(đã đặt)</span>' : ""}</label>
          <input class="js-input" id="tgToken" type="password" placeholder="${tg.token_set ? "để trống nếu không đổi" : "123456:ABC..."}">
          <label class="js-lbl">Chat ID được phép dùng <span class="dim">(nhiều ID cách nhau dấu phẩy - mỗi người /start bot rồi thêm ID vào đây)</span></label>
          <input class="js-input" id="tgChat" value="${esc(tg.chat_id || "")}" placeholder="vd 123456789, 987654321">
          <div class="js-actions"><button class="gcard-btn" id="tgSave">Lưu & bật</button><button class="gcard-btn ghost" id="tgTest">Gửi test</button></div>
          <div class="gcard-meta" id="tgStatus"></div>
        </div>
      </div>
      ${placeholder("channels", "Sắp tới: thêm kênh Zalo, web widget… mỗi kênh là 1 card ở đây.")}`;
    const st = document.getElementById("tgStatus");
    async function refreshTgStatus() {
      let d; try { d = await (await fetch("/telegram/status")).json(); } catch (e) { return; }
      let line;
      if (!d.enabled) line = "⚪ Bot CHƯA bật - tích 'Bật bot Telegram' rồi Lưu (test gửi được KHÔNG có nghĩa bot đang nhận tin).";
      else if (!d.token_set) line = "⚪ Chưa có bot token.";
      else if (d.status === "polling") {
        const n = (d.chat_ids || []).length;
        line = `🟢 Bot đang nhận tin - ${n ? n + " chat ID được phép" : "MỌI NGƯỜI nhắn được (chưa giới hạn ID)"} - nhắn cho bot là Javis trả lời.`;
      }
      else if (d.status === "conflict") line = "🔴 409: " + (d.last_error || "token bị poll nơi khác hoặc còn webhook") + " - bot tự xoá webhook khi khởi động; nếu vẫn lỗi thì có nơi khác đang poll cùng token.";
      else if (d.status === "error") line = "⚠ Lỗi bot: " + (d.last_error || "");
      else if (d.status === "starting") line = "⏳ Đang khởi động bot…";
      else line = "⚪ Bot đã tắt.";
      st.textContent = line;
    }
    refreshTgStatus();
    document.getElementById("tgSave").onclick = async () => {
      const data = { enabled: document.getElementById("tgEnabled").checked, chat_id: document.getElementById("tgChat").value.trim() };
      const tok = document.getElementById("tgToken").value.trim();
      if (tok) data.token = tok;
      st.textContent = "Đang lưu...";
      const r = await saveSetting("telegram", data);
      st.textContent = r.ok ? "✅ Đã lưu, đang khởi động bot…" : "⚠ Lỗi lưu.";
      if (r.ok) setTimeout(refreshTgStatus, 1800);
    };
    document.getElementById("tgTest").onclick = async () => {
      st.textContent = "Đang gửi test...";
      try {
        const r = await (await fetch("/telegram/test", { method: "POST" })).json();
        st.textContent = r.ok
          ? (r.total > 1 ? `✅ Đã gửi tin test tới ${r.sent}/${r.total} ID.` + (r.error ? " Lỗi: " + r.error : "") : "✅ Đã gửi tin test.")
          : "⚠ " + (r.error || "Chưa cấu hình bot.");
      }
      catch (e) { st.textContent = "⚠ Lỗi mạng."; }
    };
  }

  // ---- Trang Tài khoản: workspace + đăng nhập ----
  async function renderAccount(el) {
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">⚙</div><div>Đang tải...</div></div>`;
    const s = await freshSettings();
    const auth = s.auth || {};
    el.innerHTML = `
      <div class="cview-section">
        <h3>Workspace</h3>
        <div class="gcard" style="max-width:560px">
          <label class="js-lbl">Tên workspace</label>
          <input class="js-input" id="acWs" value="${esc(s.workspace_name || "Javis OS")}">
          <button class="gcard-btn" id="acWsSave">Lưu</button>
          <div class="gcard-meta" id="acWsStatus"></div>
        </div>
      </div>
      <div class="cview-section">
        <h3>Tài khoản đăng nhập</h3>
        <div class="gcard" style="max-width:560px">
          <div class="gcard-meta">${auth.has_password ? "🔒 Đã đặt mật khẩu · tài khoản: <b>" + esc(auth.username || "admin") + "</b>" : "Chưa đặt mật khẩu - ai mở dashboard cũng dùng được. Đặt mật khẩu nếu đưa lên VPS."}</div>
          <label class="js-lbl">Tài khoản</label><input class="js-input" id="acUser" value="${esc(auth.username || "")}" placeholder="admin">
          <label class="js-lbl">Mật khẩu</label><input class="js-input" id="acPass" type="password" placeholder="${auth.has_password ? "đổi mật khẩu" : "đặt mật khẩu"}">
          <div class="js-actions">
            <button class="gcard-btn" id="acSave">${auth.has_password ? "Đổi mật khẩu" : "Đặt mật khẩu"}</button>
            ${auth.has_password ? '<button class="gcard-btn ghost" id="acLogout">Đăng xuất</button><button class="gcard-btn ghost" id="acDisable">Tắt đăng nhập</button>' : ""}
          </div>
          <div class="gcard-meta" id="acStatus"></div>
        </div>
      </div>`;
    const wsStatus = document.getElementById("acWsStatus");
    document.getElementById("acWsSave").onclick = async () => {
      wsStatus.textContent = "Đang lưu...";
      const r = await saveSetting("general", { workspace_name: document.getElementById("acWs").value.trim() });
      wsStatus.textContent = r.ok ? "✅ Đã lưu." : "⚠ Lỗi.";
      const wn = document.getElementById("workspaceName"); if (wn) wn.textContent = document.getElementById("acWs").value.trim() || "Javis OS";
    };
    const acStatus = document.getElementById("acStatus");
    document.getElementById("acSave").onclick = async () => {
      const user = document.getElementById("acUser").value.trim() || "admin";
      const pass = document.getElementById("acPass").value;
      if (!pass || pass.length < 4) { acStatus.textContent = "⚠ Mật khẩu tối thiểu 4 ký tự."; return; }
      acStatus.textContent = "Đang lưu...";
      // /auth/setup cấp cookie ngay → tránh tự khoá khi bật auth lần đầu
      const fd = new FormData(); fd.append("username", user); fd.append("password", pass);
      try { const r = await (await fetch("/auth/setup", { method: "POST", body: fd })).json(); acStatus.textContent = r.ok ? "✅ Đã lưu tài khoản." : "⚠ " + (r.error || "Lỗi."); renderAccount(el); }
      catch (e) { acStatus.textContent = "⚠ Lỗi mạng."; }
    };
    const lo = document.getElementById("acLogout");
    if (lo) lo.onclick = async () => { await fetch("/auth/logout", { method: "POST" }); location.reload(); };
    const dis = document.getElementById("acDisable");
    if (dis) dis.onclick = async () => { if (confirm("Tắt đăng nhập? Ai mở dashboard cũng dùng được.")) { await fetch("/auth/disable", { method: "POST" }); renderAccount(el); } };
  }

  // ---- Lưu 1 section settings ----
  async function saveSetting(section, dataObj) {
    const fd = new FormData();
    fd.append("section", section);
    fd.append("data", JSON.stringify(dataObj));
    try { return await (await fetch("/settings", { method: "POST", body: fd })).json(); }
    catch (e) { return { ok: false }; }
  }

  // ---- Cất #quickSet (avatar/tên miền/giọng nói) về holder ẩn khi rời trang Cài đặt ----
  // Node giữ nguyên → mọi handler đã gắn ở app.js/branding.js/quick-settings.js vẫn sống.
  function parkQuickSet() {
    const qs = document.getElementById("quickSet");
    const holder = document.getElementById("quickSetHolder");
    if (qs && holder && qs.parentNode !== holder) holder.appendChild(qs);
  }

  // ---- Trang Cài đặt: nhúng #quickSet + bộ chọn nhà cung cấp giọng đọc ----
  async function renderSettings(el) {
    const gen = _renderGen;               // chốt token: nếu user đổi trang trong lúc await → bỏ render này
    parkQuickSet();                       // giữ #quickSet an toàn TRƯỚC khi ghi đè cviewBody
    el.innerHTML = `<div class="cview-placeholder"><div class="ph-ico">⚙</div><div>Đang tải...</div></div>`;
    const s = await freshSettings();
    if (gen !== _renderGen) return;       // đã sang trang khác → KHÔNG ghi đè trang mới bằng nội dung cũ
    const v = s.voice || {};
    const prov = v.tts_provider || "edge";
    const oaSet = !!(s.model && s.model.openai_api_key_set);
    const elSet = !!v.elevenlabs_key_set;
    const opt = (val, label, cur) => `<option value="${esc(val)}"${val === cur ? " selected" : ""}>${esc(label)}</option>`;
    const oaVoices = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"];
    // Nhà cung cấp giọng đọc - gộp NGAY trong nhóm giọng nói (render vào #ttsProviderHost), không tách section riêng.
    const provHtml = `
      <div class="qs-block">
        <div class="popover-label">NHÀ CUNG CẤP GIỌNG ĐỌC</div>
        <select class="js-input" id="vpProvider">
          ${opt("edge", "Edge TTS - miễn phí (mặc định)", prov)}
          ${opt("openai", "OpenAI - mượt, đa ngôn ngữ", prov)}
          ${opt("elevenlabs", "ElevenLabs - tự nhiên nhất", prov)}
        </select>
        <div id="vpOpenai" style="display:none">
          <label class="js-lbl">OpenAI API key ${oaSet ? '<span class="dim">(đã có - để trống nếu không đổi)</span>' : ""}</label>
          <input class="js-input" id="vpOaKey" type="password" placeholder="sk-...">
          <label class="js-lbl">Giọng OpenAI</label>
          <select class="js-input" id="vpOaVoice">${oaVoices.map(x => opt(x, x, v.openai_tts_voice || "alloy")).join("")}</select>
        </div>
        <div id="vpEleven" style="display:none">
          <label class="js-lbl">ElevenLabs API key ${elSet ? '<span class="dim">(đã có - để trống nếu không đổi)</span>' : ""}</label>
          <input class="js-input" id="vpElKey" type="password" placeholder="dán API key ElevenLabs">
          <label class="js-lbl">Voice ID <span class="dim">(lấy ở ElevenLabs → Voices)</span></label>
          <input class="js-input" id="vpElVoice" value="${esc(v.elevenlabs_voice || "")}" placeholder="21m00Tcm4TlvDq8ikWAM (Rachel)">
        </div>
        <div class="js-actions"><button class="gcard-btn" id="vpSave">Lưu nhà cung cấp</button></div>
        <div class="gcard-meta" id="vpStatus">Đang dùng: <b>${esc(prov)}</b>. Provider trả phí lỗi sẽ tự về Edge. Bấm ▶ Nghe thử ở dưới để nghe.</div>
      </div>`;
    el.innerHTML = `
      <div class="cview-section">
        <h3>Giọng nói, ảnh đại diện &amp; tên miền</h3>
        <div class="cs-host"></div>
      </div>`;
    const host = el.querySelector(".cs-host");
    const qs = document.getElementById("quickSet");
    if (qs && host) host.appendChild(qs);         // nhúng bộ điều khiển cũ vào trang (giữ handler)
    if (window.__javisRefreshExtras) { try { window.__javisRefreshExtras(); } catch (e) {} }  // nạp lại avatar/tên miền
    const provHost = document.getElementById("ttsProviderHost");   // điểm neo trong nhóm giọng nói (index.html)
    if (provHost) provHost.innerHTML = provHtml;

    const provSel = document.getElementById("vpProvider");
    if (provSel) {   // guard: thiếu điểm neo (vd cache index.html cũ) thì avatar/tên miền vẫn chạy, không sập trang
      const showFields = () => {
        const p = provSel.value;
        document.getElementById("vpOpenai").style.display = p === "openai" ? "block" : "none";
        document.getElementById("vpEleven").style.display = p === "elevenlabs" ? "block" : "none";
        // Giọng HoaiMy/NamMinh chỉ áp dụng cho Edge. Provider khác chọn giọng ngay trong khối trên
        // (vpOaVoice / vpElVoice) nên ẩn khối này cho gọn. Radio vẫn nằm trong DOM + giữ 'checked'
        // để app.js đọc input[name=voice] không lỗi; server dùng provider đã lưu nên giá trị này vô hại.
        const edgeVoice = document.getElementById("edgeVoiceSection");
        if (edgeVoice) edgeVoice.style.display = p === "edge" ? "" : "none";
      };
      provSel.onchange = showFields; showFields();

      const st = document.getElementById("vpStatus");
      document.getElementById("vpSave").onclick = async () => {
        st.textContent = "Đang lưu...";
        const data = {
          tts_provider: provSel.value,
          openai_tts_voice: document.getElementById("vpOaVoice").value,
          elevenlabs_voice: document.getElementById("vpElVoice").value.trim(),
        };
        const elKey = document.getElementById("vpElKey").value.trim();
        if (elKey) data.elevenlabs_key = elKey;
        const r = await saveSetting("voice", data);
        const oaKey = document.getElementById("vpOaKey").value.trim();
        if (oaKey) await saveSetting("model", { openai_api_key: oaKey });   // key OpenAI dùng chung với chat
        _settings = null;
        st.innerHTML = r.ok
          ? "✅ Đã lưu. Đang dùng: <b>" + esc(provSel.value) + "</b>. Bấm ▶ Nghe thử."
          : "⚠ Lỗi lưu.";
      };
    }
  }

  // ============================================
  // Trang TRÒ CHUYỆN - khung chat toàn khung (mượn node chat của cockpit + sidebar lịch sử)
  // Không nhân đôi bộ máy chat: relocate chính #chatArea/#attachBar/#modelBar/#hudVoice
  // (giữ nguyên mọi handler + WebSocket + streaming đã gắn trong app.js) rồi TRẢ về HUD khi
  // rời trang. Cùng một cuộc trò chuyện hiển thị ở cả màn 3D lẫn tab này.
  // ============================================
  const CHAT_NODE_IDS = ["chatArea", "attachBar", "modelBar", "hudVoice"];
  let _chatSlots = [];        // vị trí gốc từng node để trả về đúng chỗ trong HUD
  let _chatEngObs = null;     // theo dõi engineBadge gốc để phản chiếu badge trong tab

  function _injectChatCss() {
    if (document.getElementById("cp-css")) return;
    const css = `
    body.on-chat .cview-head{ display:none; }
    body.on-chat .cview-body{ padding:0; overflow:hidden; }
    /* Ẩn hẳn THÂN HUD (metrics/orb 3D/panels) khi ở tab chat. cview fade-in 200ms của Alpine
       + canvas WebGL bị đẩy lớp compositing có thể để lộ HUD phía sau (loé orb) lúc mở tab. Giữ
       .hud-top (thanh trên toàn cục) hiển thị. Rời tab (bỏ .on-chat) HUD tự hiện lại + graph thức. */
    body.on-chat .hud-body{ visibility:hidden; }
    .chatpage{ display:flex; height:100%; min-height:0; position:relative; }
    .chatpage-side{ width:280px; flex:none; display:flex; flex-direction:column; gap:10px;
      min-height:0; padding:14px 12px; border-right:1px solid var(--glass-brd); background:rgba(255,255,255,.015); }
    .chatpage-main{ flex:1 1 auto; min-width:0; display:flex; flex-direction:column; min-height:0; padding:14px 20px 16px; }
    .chatpage-bar{ display:flex; align-items:center; gap:10px; padding:0 4px 10px; flex:none; }
    .cp-title{ font-family:var(--font); font-weight:700; letter-spacing:.5px; color:var(--text); }
    .cp-engine{ margin-left:auto; font-size:12px; color:var(--text2); font-family:var(--font); white-space:nowrap; }
    .cp-ico-btn{ background:none; border:1px solid var(--border); color:var(--text2); border-radius:8px;
      padding:4px 10px; cursor:pointer; font-size:14px; line-height:1; }
    .cp-ico-btn:hover{ color:var(--accent); border-color:var(--accent); }
    .cp-side-toggle{ display:none; }
    .chatpage-slot{ flex:1 1 auto; min-height:0; display:flex; flex-direction:column; gap:10px; }
    .chatpage-slot > *{ width:100%; max-width:900px; margin-left:auto; margin-right:auto; }
    .chatpage-slot .transcript{ flex:1 1 auto; min-height:0; max-height:none; background:transparent; }
    .chatpage-slot .hud-voice{ background:rgba(24,24,34,.6); border:1px solid var(--border); border-radius:12px; }
    .chatpage-slot .attach-bar{ flex:none; }
    @media (max-width:860px){
      .cp-side-toggle{ display:inline-block; }
      .chatpage-side{ position:absolute; left:0; top:0; bottom:0; z-index:6; width:min(84vw,300px);
        transform:translateX(-105%); transition:transform .2s ease; box-shadow:10px 0 40px rgba(0,0,0,.5); background:var(--bg); }
      .chatpage.side-open .chatpage-side{ transform:none; }
      .chatpage-main{ padding:10px 12px 12px; }
    }`;
    const st = document.createElement("style"); st.id = "cp-css"; st.textContent = css; document.head.appendChild(st);
  }

  function _borrowChatNodes(into) {
    _chatSlots = [];
    CHAT_NODE_IDS.forEach(id => {
      const n = document.getElementById(id);
      if (!n) return;
      _chatSlots.push({ node: n, parent: n.parentNode, next: n.nextSibling });
      into.appendChild(n);
    });
  }
  function _returnChatNodes() {
    if (_chatEngObs) { try { _chatEngObs.disconnect(); } catch (e) {} _chatEngObs = null; }
    for (let i = _chatSlots.length - 1; i >= 0; i--) {
      const s = _chatSlots[i];
      if (!s.parent) continue;
      if (s.next && s.next.parentNode === s.parent) s.parent.insertBefore(s.node, s.next);
      else s.parent.appendChild(s.node);
    }
    _chatSlots = [];
    document.body.classList.remove("on-chat");
  }

  function renderChat(el) {
    _injectChatCss();
    // Vào lại trang này (vd đổi brain gọi thẳng renderPage) trong khi node đang mượn ở cviewBody
    // cũ → TRẢ về HUD trước, nếu không el.innerHTML bên dưới sẽ xoá luôn #chatArea đang nằm trong đó.
    if (_chatSlots.length) _returnChatNodes();
    // chat-zoom overlay cũng mượn cùng các node → thu lại trước cho khỏi giành
    try { if (window.JavisChatStage && window.JavisChatStage.isOpen()) window.JavisChatStage.collapse(); } catch (e) {}
    document.body.classList.add("on-chat");
    el.innerHTML =
      '<div class="chatpage" id="chatPage">' +
        '<aside class="chatpage-side" id="chatPageSide"></aside>' +
        '<div class="chatpage-main">' +
          '<div class="chatpage-bar">' +
            '<button class="cp-ico-btn cp-side-toggle" type="button" title="Ẩn/hiện lịch sử">🕘</button>' +
            '<span class="cp-title">Trò chuyện với Javis</span>' +
            '<span class="cp-engine" id="cpEngine"></span>' +
          '</div>' +
          '<div class="chatpage-slot" id="chatPageSlot"></div>' +
        '</div>' +
      '</div>';
    const page = el.querySelector("#chatPage");
    const slot = el.querySelector("#chatPageSlot");
    _borrowChatNodes(slot);

    // Sidebar lịch sử hội thoại (dùng lại module chung của chat workspace)
    try { if (window.JavisChatSide) window.JavisChatSide.mount(el.querySelector("#chatPageSide")); } catch (e) {}

    // Badge engine: phản chiếu từ badge gốc trong HUD (không mượn node để khỏi phá HUD)
    const eb = document.getElementById("engineBadge"), cpe = el.querySelector("#cpEngine");
    if (eb && cpe) {
      const sync = () => { cpe.textContent = (eb.textContent || "").trim(); };
      sync();
      try { _chatEngObs = new MutationObserver(sync); _chatEngObs.observe(eb, { childList: true, characterData: true, subtree: true }); } catch (e) {}
    }

    // Mobile: nút 🕘 mở/đóng drawer lịch sử; bấm vào vùng chat thì đóng drawer
    const isNar = () => window.matchMedia("(max-width: 860px)").matches;
    el.querySelector(".cp-side-toggle").onclick = () => page.classList.toggle("side-open");
    slot.addEventListener("click", () => { if (isNar() && page.classList.contains("side-open")) page.classList.remove("side-open"); });
    el.querySelector("#chatPageSide").addEventListener("click", (e) => {
      if (isNar() && e.target.closest(".cside-item")) page.classList.remove("side-open");
    });

    // Cuộn xuống đáy + focus ô nhập cho tiện gõ ngay
    const ca = document.getElementById("chatArea"); if (ca) ca.scrollTop = ca.scrollHeight;
    const ci = document.getElementById("chatInput"); if (ci) { try { ci.focus(); } catch (e) {} }

    _pageLeave = _returnChatNodes;   // rời tab → trả node về HUD trước khi cviewBody bị ghi đè
  }

  // ============================================
  // Alpine store + boot
  // ============================================
  document.addEventListener("alpine:init", () => {
    Alpine.store("nav", {
      active: "home",
      items: RAIL_ITEMS,
      get meta() { return VIEW_META[this.active] || VIEW_META.home; },
      go(id) {
        const item = RAIL_ITEMS.find(i => i.id === id);
        if (item && item.launch) { item.launch(); recomputeGraph(); return; }  // launcher: không đổi view
        navigateTo(id);
      },
    });
  });

  // ============================================================
  // VAULT EXPLORER (cột trái) - cây lazy + tìm note + editor overlay đè lên não
  // Tái dùng thẳng esc / _fileIcon / fbrain / recomputeGraph (đều trong IIFE này).
  // KHÔNG đụng renderFiles/openVaultTarget (deep-link chat) - openNote là luồng riêng, additive.
  // ============================================================
  const VT_IMG_EXTS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico"];
  const VT_TEXT_EXTS = [".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".js", ".ts", ".py",
    ".html", ".css", ".toml", ".ini", ".log", ".sh", ".bat", ".xml", ".svg", ".env"];
  let _vtHome = "";            // đường dẫn (theo trần duyệt) của gốc brain
  let _vtCache = new Map();    // key -> items[] (cache con thư mục đã nạp)
  let _vtActivePath = null;    // file .md đang mở (để tô sáng trong cây)
  let _vtWired = false;        // đã gắn handler search/toolbar chưa
  let _vtIndex = null;         // chỉ mục file toàn vault (crawl client) - cho tìm theo Tên không cần server restart
  let _neSaveFn = null;        // hàm lưu của editor đang mở (cho Ctrl+S)
  const _vtRaw = (rel, dl) => `/files/raw?brain=${encodeURIComponent(fbrain())}&path=${encodeURIComponent(rel)}${dl ? "&dl=1" : ""}`;
  const _vtNoAccent = (s) => (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[đĐ]/g, "d").toLowerCase();

  async function _vtList(path) {
    const key = (path == null) ? " home" : path;
    if (_vtCache.has(key)) return _vtCache.get(key);
    const qp = (path == null) ? "" : `&path=${encodeURIComponent(path)}`;
    let items = [];
    try {
      const d = await (await fetch(`/files/list?brain=${encodeURIComponent(fbrain())}${qp}`)).json();
      if (d && !d.error) { items = d.items || []; if (path == null && d.home != null) _vtHome = d.home; }
    } catch (e) {}
    _vtCache.set(key, items);
    return items;
  }

  // Dựng lại cây nhưng GIỮ NGUYÊN các thư mục đang mở (thêm/sửa/xoá không làm sập cây).
  // revealDir (tuỳ chọn) = thư mục cần mở thêm để thấy file vừa tạo.
  async function _vtRebuildReExpand(revealDir) {
    const tree = document.getElementById("vaultTree"); if (!tree) return;
    const escSel = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/"/g, '\\"');
    // 1. Ghi lại các thư mục đang mở (childBox không ẩn).
    const wanted = new Set();
    tree.querySelectorAll(".vt-branch > .vt-children:not(.vt-hidden)").forEach(box => {
      const node = box.previousElementSibling;
      if (node && node.dataset && node.dataset.rel) wanted.add(node.dataset.rel);
    });
    // 2. Thêm chuỗi thư mục cha của revealDir (để thấy file mới dù thư mục đó đang đóng).
    if (revealDir != null && revealDir !== "") {
      let inner;
      if (_vtHome && revealDir.indexOf(_vtHome + "/") === 0) inner = revealDir.slice(_vtHome.length + 1);
      else if (!_vtHome) inner = revealDir;
      else inner = (revealDir === _vtHome ? "" : revealDir);
      const segs = inner ? inner.split("/") : [];
      let acc = _vtHome || "";
      for (const seg of segs) { acc = acc ? acc + "/" + seg : seg; wanted.add(acc); }
    }
    // 3. Dựng lại (tươi) rồi mở lại từ NÔNG tới SÂU (cha trước con).
    _vtCache.clear(); _vtIndex = null;
    await renderVaultTree();
    const list = [...wanted].sort((a, b) => a.split("/").length - b.split("/").length);
    for (const rel of list) {
      const node = tree.querySelector(`.vt-node[data-rel="${escSel(rel)}"]`);
      if (!node) continue;
      const box = node.parentElement && node.parentElement.querySelector(":scope > .vt-children");
      if (box && box.classList.contains("vt-hidden")) {
        node.click();
        for (let i = 0; i < 25 && (box.classList.contains("vt-hidden") || !box.children.length); i++) await new Promise(r => setTimeout(r, 30));
      }
    }
  }

  async function _vtAddFile(rel, isDir) {
    // Bấm ở thư mục → tạo file BÊN TRONG; bấm ở file → tạo CÙNG thư mục (thư mục cha của file).
    const dir = isDir ? rel : (rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "");
    let n = prompt("Tên file mới (vd ghi-chu):");
    if (!n) return;
    if (!/\.[a-z0-9]+$/i.test(n)) n += ".md";   // mặc định file markdown
    const path = dir ? dir + "/" + n : n;
    const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", path); fd.append("content", "");
    try { await fetch("/files/write", { method: "POST", body: fd }); } catch (e) {}
    await _vtRebuildReExpand(dir);               // giữ thư mục đang mở + bung tới thư mục vừa tạo
    const ext = "." + n.split(".").pop().toLowerCase();
    openNote(path, { name: n, ext: ext, type: "file" });
  }

  async function _vtRename(rel, oldname) {
    const nn = prompt("Tên mới:", oldname);
    if (!nn || nn === oldname) return;
    const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel); fd.append("newname", nn);
    try { await fetch("/files/rename", { method: "POST", body: fd }); } catch (e) {}
    await _vtRebuildReExpand(null);   // giữ nguyên các thư mục đang mở
  }
  async function _vtDelete(rel, name, isDir) {
    if (!confirm(`Xoá "${name}"${isDir ? " và toàn bộ bên trong" : ""}? Không hoàn tác được.`)) return;
    const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel);
    try { await fetch("/files/delete", { method: "POST", body: fd }); } catch (e) {}
    if (_vtActivePath === rel) closeNote();
    await _vtRebuildReExpand(null);   // giữ nguyên các thư mục đang mở
  }

  function _vtRowEl(it, parentPath, depth) {
    const rel = parentPath ? parentPath + "/" + it.name : it.name;
    const isDir = it.type === "dir";
    const wrap = document.createElement("div"); wrap.className = "vt-branch";
    const node = document.createElement("div");
    node.className = "vt-node"; node.dataset.rel = rel; node.dataset.name = it.name;
    node.style.paddingLeft = (6 + depth * 13) + "px";
    node.innerHTML = `<span class="vt-chev ${isDir ? "" : "leaf"}">▸</span>`
      + `<span class="vt-ico">${isDir ? "📁" : _fileIcon(it.ext)}</span>`
      + `<span class="vt-name">${esc(it.name)}</span>`
      + `<span class="vt-act"><button data-a="add" title="Thêm file ${isDir ? "trong thư mục này" : "cùng thư mục"}">＋</button><button data-a="ren" title="Đổi tên">✎</button><button data-a="del" title="Xoá">🗑</button></span>`;
    if (!isDir && rel === _vtActivePath) node.classList.add("active");
    node.querySelectorAll(".vt-act button").forEach(b => b.onclick = (e) => {
      e.stopPropagation();
      const a = b.dataset.a;
      if (a === "add") _vtAddFile(rel, isDir);
      else if (a === "ren") _vtRename(rel, it.name);
      else _vtDelete(rel, it.name, isDir);
    });
    wrap.appendChild(node);
    if (isDir) {
      const childBox = document.createElement("div"); childBox.className = "vt-children vt-hidden";
      wrap.appendChild(childBox);
      let loaded = false;
      node.onclick = async () => {
        const chev = node.querySelector(".vt-chev");
        const willOpen = childBox.classList.contains("vt-hidden");
        childBox.classList.toggle("vt-hidden", !willOpen);
        chev.classList.toggle("open", willOpen);
        if (willOpen && !loaded) {
          loaded = true;
          const kids = await _vtList(rel);
          if (!kids.length) childBox.innerHTML = `<div class="vt-info" style="padding-left:${18 + depth * 13}px">trống</div>`;
          else kids.forEach(k => childBox.appendChild(_vtRowEl(k, rel, depth + 1)));
        }
      };
    } else {
      node.onclick = () => openNote(rel, it);
    }
    return wrap;
  }

  // Crawl toàn vault qua /files/list (đã sống) → chỉ mục file để tìm theo TÊN không cần server restart.
  // Bám trong gốc brain (bắt đầu từ home), có trần chống treo trên vault lớn. Cache lại sau lần đầu.
  async function _vtBuildIndex() {
    if (_vtIndex) return _vtIndex;
    const SKIP = new Set([".git", "node_modules", "__pycache__", ".obsidian", ".trash", ".venv"]);
    if (!_vtHome && !_vtCache.has(" home")) await _vtList(null);
    const out = []; const queue = [_vtHome || ""]; let guard = 0;
    while (queue.length && out.length < 3000 && guard < 600) {
      guard++;
      const dir = queue.shift();
      const items = await _vtList(dir);
      for (const it of items) {
        const rel = dir ? dir + "/" + it.name : it.name;
        if (it.type === "dir") { if (!it.name.startsWith(".") && !SKIP.has(it.name)) queue.push(rel); }
        else out.push({ name: it.name, ext: it.ext, path: rel, dir: dir });
      }
    }
    _vtIndex = out;
    return out;
  }

  function _vtRelHome(dir) {
    if (!dir) return "";
    if (_vtHome && dir === _vtHome) return "";
    if (_vtHome && dir.indexOf(_vtHome + "/") === 0) return dir.slice(_vtHome.length + 1);
    return dir;
  }

  function _vtRenderResults(box, list, withSnippet) {
    box.innerHTML = "";
    list.forEach(it => {
      const el = document.createElement("div"); el.className = "vr-item";
      const sub = withSnippet ? (it.snippet || "") : _vtRelHome(it.dir);
      el.innerHTML = `<div class="vr-name"><span class="vt-ico">${_fileIcon(it.ext)}</span>${esc(it.name)}</div>`
        + (sub ? `<div class="vr-snip">${esc(sub)}</div>` : "");
      el.onclick = () => openNote(it.path, { name: it.name, ext: it.ext, type: "file" });
      box.appendChild(el);
    });
  }

  async function _vtNameSearch(q) {
    const box = document.getElementById("vaultResults"); if (!box) return;
    box.innerHTML = `<div class="vr-empty">Đang tìm…</div>`;
    const idx = await _vtBuildIndex();
    const nq = _vtNoAccent(q);
    const hits = idx.filter(f => _vtNoAccent(f.name).includes(nq)).slice(0, 120);
    if (!hits.length) { box.innerHTML = `<div class="vr-empty">Không thấy note nào tên khớp "${esc(q)}".</div>`; return; }
    _vtRenderResults(box, hits, false);
  }

  async function _vtSearchContent(q) {
    const box = document.getElementById("vaultResults"); if (!box) return;
    box.innerHTML = `<div class="vr-empty">Đang tìm…</div>`;
    let resp, d = {};
    try { resp = await fetch(`/files/search?brain=${encodeURIComponent(fbrain())}&q=${encodeURIComponent(q)}&limit=60`); d = await resp.json().catch(() => ({})); }
    catch (e) { resp = null; }
    if (!resp || resp.status === 404) {
      box.innerHTML = `<div class="vr-empty">Tìm theo <b>nội dung</b> cần khởi động lại Javis một lần (chạy start-javis.bat) để bật. Tạm thời hãy tìm theo <b>Tên</b>.</div>`;
      return;
    }
    if (!resp.ok) { box.innerHTML = `<div class="vr-empty">Lỗi tìm kiếm (${resp.status}).</div>`; return; }
    const items = (d && d.items) || [];
    if (!items.length) { box.innerHTML = `<div class="vr-empty">Không thấy note nào chứa "${esc(q)}".</div>`; return; }
    _vtRenderResults(box, items, true);
  }

  function _vtWire() {
    if (_vtWired) return; _vtWired = true;
    const input = document.getElementById("vaultSearch");
    const clearBtn = document.getElementById("vaultSearchClear");
    const chipName = document.getElementById("vsModeName");
    const chipContent = document.getElementById("vsModeContent");
    const tree = document.getElementById("vaultTree");
    const results = document.getElementById("vaultResults");
    if (!input || !tree) return;
    let mode = "name", t = null;
    const apply = () => {
      const q = input.value.trim();
      if (clearBtn) clearBtn.hidden = !q;
      if (!q) { results.hidden = true; tree.hidden = false; return; }   // rỗng → về cây
      tree.hidden = true; results.hidden = false;
      if (mode === "name") _vtNameSearch(q); else _vtSearchContent(q);
    };
    const deb = () => { clearTimeout(t); t = setTimeout(apply, mode === "name" ? 150 : 280); };
    input.addEventListener("input", deb);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { clearTimeout(t); apply(); }
      else if (e.key === "Escape") { input.value = ""; apply(); }
    });
    if (clearBtn) clearBtn.onclick = () => { input.value = ""; apply(); input.focus(); };
    const setMode = (m) => { mode = m; chipName.classList.toggle("active", m === "name"); chipContent.classList.toggle("active", m === "content"); apply(); };
    chipName.onclick = () => setMode("name");
    chipContent.onclick = () => setMode("content");
    const nf = document.getElementById("vtNewFile"), nd = document.getElementById("vtNewDir"), rf = document.getElementById("vtRefresh");
    if (rf) rf.onclick = () => { _vtCache.clear(); _vtIndex = null; renderVaultTree(); };
    if (nf) nf.onclick = async () => {
      let n = prompt("Tên file mới (vd ghi-chu):"); if (!n) return;
      if (!/\.[a-z0-9]+$/i.test(n)) n += ".md";   // mặc định file markdown
      const rel = _vtHome ? _vtHome + "/" + n : n;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel); fd.append("content", "");
      await fetch("/files/write", { method: "POST", body: fd });
      await _vtRebuildReExpand(_vtHome || "");   // giữ thư mục đang mở
      const ext = "." + n.split(".").pop().toLowerCase();
      openNote(rel, { name: n, ext: ext, type: "file" });
    };
    if (nd) nd.onclick = async () => {
      const n = prompt("Tên thư mục mới:"); if (!n) return;
      const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", _vtHome || ""); fd.append("name", n);
      await fetch("/files/mkdir", { method: "POST", body: fd }); _vtCache.clear(); renderVaultTree();
    };
  }

  async function renderVaultTree() {
    const tree = document.getElementById("vaultTree"); if (!tree) return;
    _vtWire();
    tree.hidden = false;
    const results = document.getElementById("vaultResults"); if (results) results.hidden = true;
    tree.innerHTML = `<div class="vt-info">Đang tải…</div>`;
    const items = await _vtList(null);
    tree.innerHTML = "";
    if (!items.length) { tree.innerHTML = `<div class="vt-info">Vault trống.</div>`; return; }
    items.forEach(it => tree.appendChild(_vtRowEl(it, _vtHome || "", 0)));
  }

  function _vtMarkActive(rel) {
    _vtActivePath = rel;
    const tree = document.getElementById("vaultTree"); if (!tree) return;
    tree.querySelectorAll(".vt-node.active").forEach(n => n.classList.remove("active"));
    if (rel) {
      const sel = (window.CSS && CSS.escape) ? CSS.escape(rel) : rel.replace(/"/g, '\\"');
      const n = tree.querySelector(`.vt-node[data-rel="${sel}"]`); if (n) n.classList.add("active");
    }
  }

  function _neKeyHandler(e) {
    const ed = document.getElementById("noteEditor"); if (!ed || ed.hidden) return;
    if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) { e.preventDefault(); if (_neSaveFn) _neSaveFn(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeNote(); }
  }
  function closeNote() {
    const ed = document.getElementById("noteEditor"); if (!ed) return;
    ed.hidden = true; ed.classList.remove("ne-full");
    document.getElementById("neBody").innerHTML = ""; document.getElementById("neActions").innerHTML = "";
    _neSaveFn = null;
    document.removeEventListener("keydown", _neKeyHandler, true);
    _vtMarkActive(null);
    try { recomputeGraph(); } catch (e) {}   // chạy lại não (đã gate active===home + không lite + studio đóng)
  }
  function _neCommonBtns(actions, rel, it) {
    const mk = (label, title, fn) => { const b = document.createElement("button"); b.textContent = label; if (title) b.title = title; b.onclick = fn; return b; };
    const ed = document.getElementById("noteEditor");
    actions.appendChild(mk("↗", "Mở tab mới", () => window.open(_vtRaw(rel), "_blank")));
    actions.appendChild(mk("⤓", "Tải về", () => window.open(_vtRaw(rel, 1), "_blank")));
    actions.appendChild(mk("⛶", "Phóng to / thu nhỏ", () => ed.classList.toggle("ne-full")));
    actions.appendChild(mk("✕", "Đóng (Esc)", closeNote));
  }
  function _neRenderDownload(body, actions, rel, it) {
    body.className = "ne-body";
    body.innerHTML = `<div class="ne-dl"><div class="ne-dl-ico">${_fileIcon(it.ext)}</div>`
      + `<div>Loại file này không xem trực tiếp - hãy tải về.<br><b>${esc(it.name)}</b></div>`
      + `<div><a href="${_vtRaw(rel, 1)}">⤓ Tải về</a> &nbsp;·&nbsp; <a href="${_vtRaw(rel)}" target="_blank">↗ Mở tab mới</a></div></div>`;
    _neCommonBtns(actions, rel, it);
  }

  // Nạp turndown (HTML→markdown) LAZY, chỉ khi cần lưu bản WYSIWYG. + plugin GFM (bảng).
  let _tdPromise = null, _td = null;
  function _ensureTurndown() {
    if (window.TurndownService) return Promise.resolve();
    if (_tdPromise) return _tdPromise;
    const load = (src) => new Promise((res) => { const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = res; document.head.appendChild(s); });
    _tdPromise = load("https://unpkg.com/turndown@7.2.0/dist/turndown.js")
      .then(() => load("https://unpkg.com/turndown-plugin-gfm@1.0.2/dist/turndown-plugin-gfm.js"));
    return _tdPromise;
  }
  // HTML (bản render đang sửa) → markdown. GIỮ [[wikilink]] và ![[ảnh]] qua luật riêng theo data-vault-path.
  function _mdFromHtml(html) {
    if (!window.TurndownService) return null;
    if (!_td) {
      _td = new window.TurndownService({ headingStyle: "atx", bulletListMarker: "-", codeBlockStyle: "fenced", emDelimiter: "*" });
      try { if (window.turndownPluginGfm) _td.use(window.turndownPluginGfm.gfm); } catch (e) {}
      _td.addRule("wikilink", { filter: (n) => n.nodeName === "A" && n.getAttribute("data-vault-path") != null,
        replacement: (c, n) => "[[" + n.getAttribute("data-vault-path") + "]]" });
      _td.addRule("wikiimg", { filter: (n) => n.nodeName === "IMG" && n.getAttribute("data-vault-path") != null,
        replacement: (c, n) => "![[" + n.getAttribute("data-vault-path") + "]]" });
    }
    try { return _td.turndown(html); } catch (e) { return null; }
  }

  // Thanh công cụ markdown - hoạt động CẢ trên bản render (WYSIWYG, execCommand) LẪN nguồn thô (chèn cú pháp).
  function _neBuildToolbar(host, ctx) {
    if (!host) return;
    const ta = ctx.ta, wys = ctx.wys, isWys = () => ctx.mode() === "wys";
    const exec = (cmd, val) => { try { wys.focus(); document.execCommand(cmd, false, val || null); } catch (e) {} };
    const wrapTa = (b, a, ph) => {
      const s = ta.selectionStart, e = ta.selectionEnd, sel = ta.value.slice(s, e) || ph || "";
      ta.value = ta.value.slice(0, s) + b + sel + a + ta.value.slice(e);
      ta.selectionStart = s + b.length; ta.selectionEnd = s + b.length + sel.length; ta.focus();
    };
    const lineTa = (prefix) => {
      const s = ta.selectionStart, e = ta.selectionEnd, v = ta.value, ls = v.lastIndexOf("\n", s - 1) + 1;
      const block = v.slice(ls, e).split("\n").map((ln, i) => prefix.replace("{n}", i + 1) + ln).join("\n");
      ta.value = v.slice(0, ls) + block + v.slice(e); ta.focus();
    };
    const insTa = (t) => { const s = ta.selectionStart; ta.value = ta.value.slice(0, s) + t + ta.value.slice(s); ta.selectionStart = ta.selectionEnd = s + t.length; ta.focus(); };
    const B = (fn) => () => { fn(); };
    const BTNS = [
      ["B", "Đậm", () => isWys() ? exec("bold") : wrapTa("**", "**", "chữ đậm"), "font-weight:700"],
      ["I", "Nghiêng", () => isWys() ? exec("italic") : wrapTa("*", "*", "chữ nghiêng"), "font-style:italic"],
      ["H1", "Tiêu đề 1", () => isWys() ? exec("formatBlock", "H1") : lineTa("# ")],
      ["H2", "Tiêu đề 2", () => isWys() ? exec("formatBlock", "H2") : lineTa("## ")],
      ["H3", "Tiêu đề 3", () => isWys() ? exec("formatBlock", "H3") : lineTa("### ")],
      ["•", "Gạch đầu dòng", () => isWys() ? exec("insertUnorderedList") : lineTa("- ")],
      ["1.", "Danh sách số", () => isWys() ? exec("insertOrderedList") : lineTa("{n}. ")],
      ["❝", "Trích dẫn", () => isWys() ? exec("formatBlock", "BLOCKQUOTE") : lineTa("> ")],
      ["</>", "Code", () => isWys() ? exec("insertHTML", "<code>code</code>") : wrapTa("`", "`", "code")],
      ["🔗", "Link", () => { const u = prompt("URL:", "https://"); if (!u) return; isWys() ? exec("createLink", u) : wrapTa("[", "](" + u + ")", "chữ"); }],
      ["―", "Kẻ ngang", () => isWys() ? exec("insertHorizontalRule") : insTa("\n---\n")],
    ];
    host.innerHTML = "";
    BTNS.forEach(([label, title, fn, style]) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = label; b.title = title;
      if (style) b.style.cssText += style;
      b.onmousedown = (e) => e.preventDefault();
      b.onclick = fn;
      host.appendChild(b);
    });
  }

  async function openNote(rel, it) {
    const ed = document.getElementById("noteEditor"); if (!ed) return;
    it = it || {}; const ext = (it.ext || "").toLowerCase();
    ed.hidden = false; ed.classList.remove("ne-full");
    document.removeEventListener("keydown", _neKeyHandler, true);
    document.addEventListener("keydown", _neKeyHandler, true);
    try { if (window.__javisGraph && window.__javisGraph.pause) window.__javisGraph.pause(); } catch (e) {}
    document.getElementById("neTitle").innerHTML = `<span class="vt-ico">${_fileIcon(ext)}</span>${esc(it.name || rel)}`;
    const actions = document.getElementById("neActions"); const body = document.getElementById("neBody");
    actions.innerHTML = ""; body.innerHTML = ""; body.className = "ne-body"; _neSaveFn = null;

    if (VT_IMG_EXTS.includes(ext)) {
      body.innerHTML = `<div class="ne-img"><img src="${_vtRaw(rel)}" alt="${esc(it.name || "")}"></div>`;
      _neCommonBtns(actions, rel, it); _vtMarkActive(null); return;
    }
    if (VT_TEXT_EXTS.includes(ext)) {
      body.innerHTML = `<div class="vt-info" style="padding:16px">Đang mở…</div>`;
      let resp, d = {};
      try { resp = await fetch(`/files/read?brain=${encodeURIComponent(fbrain())}&path=${encodeURIComponent(rel)}`); d = await resp.json().catch(() => ({})); }
      catch (e) { _neRenderDownload(body, actions, rel, it); return; }
      if (!resp.ok || d.error || d.content == null) { _neRenderDownload(body, actions, rel, it); return; }
      const isMd = ext === ".md";
      if (isMd) { try { await _ensureTurndown(); } catch (e) {} }   // để lưu bản render (WYSIWYG) → markdown
      const wysOk = isMd && !!window.TurndownService;
      body.className = "ne-body" + (isMd ? (wysOk ? " ne-md mode-wys" : " ne-md mode-source") : " mode-source");
      body.innerHTML = isMd
        ? `<div class="ne-fmt"></div><div class="ne-panes"><div class="ne-prev ne-wys" id="neWys" contenteditable="true" spellcheck="false"></div><div class="ne-src"><textarea id="neText" spellcheck="false"></textarea></div></div>`
        : `<div class="ne-src"><textarea id="neText" spellcheck="false"></textarea></div>`;
      const ta = document.getElementById("neText"); ta.value = d.content || "";
      let mdGetter = null;
      if (isMd) {
        const wys = document.getElementById("neWys");
        wys.innerHTML = window.mdToHtml ? window.mdToHtml(ta.value) : esc(ta.value);
        let curMode = wysOk ? "wys" : "source";
        const wysToSrc = () => { const md = _mdFromHtml(wys.innerHTML); if (md != null) ta.value = md; };
        const srcToWys = () => { wys.innerHTML = window.mdToHtml ? window.mdToHtml(ta.value) : esc(ta.value); };
        _neBuildToolbar(body.querySelector(".ne-fmt"), { mode: () => curMode, ta, wys });   // thanh công cụ chạy cả 2 chế độ
        mdGetter = () => (curMode === "wys" ? (_mdFromHtml(wys.innerHTML) != null ? _mdFromHtml(wys.innerHTML) : ta.value) : ta.value);
        const seg = document.createElement("span"); seg.className = "ne-seg";
        [["Sửa", "mode-wys"], ["Nguồn", "mode-source"]].forEach(([lbl, cls]) => {
          const b = document.createElement("button"); b.textContent = lbl; b.classList.toggle("active", cls === (curMode === "wys" ? "mode-wys" : "mode-source"));
          b.onclick = () => {
            const toSrc = cls === "mode-source";
            if (toSrc && curMode === "wys") wysToSrc();
            else if (!toSrc && curMode === "source") srcToWys();
            curMode = toSrc ? "source" : "wys";
            body.className = "ne-body ne-md " + cls;
            seg.querySelectorAll("button").forEach(x => x.classList.remove("active")); b.classList.add("active");
          };
          seg.appendChild(b);
        });
        actions.appendChild(seg);
      }
      const saveBtn = document.createElement("button"); saveBtn.textContent = "💾 Lưu"; saveBtn.title = "Lưu (Ctrl+S)";
      _neSaveFn = async () => {
        const content = mdGetter ? mdGetter() : ta.value;
        const fd = new FormData(); fd.append("brain", fbrain()); fd.append("path", rel); fd.append("content", content);
        try {
          const r = await (await fetch("/files/write", { method: "POST", body: fd })).json();
          if (r.ok) { saveBtn.textContent = "✓ Đã lưu"; saveBtn.classList.add("ne-saved"); setTimeout(() => { saveBtn.textContent = "💾 Lưu"; saveBtn.classList.remove("ne-saved"); }, 1400); }
          else saveBtn.textContent = "⚠ Lỗi";
        } catch (e) { saveBtn.textContent = "⚠ Lỗi"; }
      };
      saveBtn.onclick = _neSaveFn;
      actions.appendChild(saveBtn);
      _neCommonBtns(actions, rel, it);
      _vtMarkActive(isMd ? rel : null);
      ta.focus();
      return;
    }
    _neRenderDownload(body, actions, rel, it); _vtMarkActive(null);
  }

  function boot() {
    document.body.classList.add("has-rail");
    const ver = document.getElementById("railVersion");
    if (ver) {
      ver.textContent = "v" + APP_VERSION;   // hiện tạm, thay ngay bằng phiên bản thật từ server
      fetch("/version").then(r => r.json()).then(d => { if (d && d.current) ver.textContent = "v" + d.current; }).catch(() => {});
    }
    // Theo dõi Studio mở/đóng → bật/tắt graph theo
    const st = document.getElementById("studio");
    if (st) new MutationObserver(recomputeGraph).observe(st, { attributes: true, attributeFilter: ["class"] });
    // Màn hình co/giãn qua ngưỡng mobile → tính lại
    window.matchMedia("(max-width: 860px)").addEventListener("change", () => {
      if (liteMode() && Alpine.store("nav").active === "home") navigateTo("overview");
      recomputeGraph();
    });
    // Đổi brain (Select Brain) → nạp lại trang quản lý đang xem theo brain mới (không cần F5)
    const gs = document.getElementById("graphSource");
    if (gs) gs.addEventListener("change", () => {
      const active = Alpine.store("nav").active;
      if (active !== "home") renderPage(active);
      // Cây vault ở cột trái sống ngoài hệ cview → tự làm mới theo brain mới
      _vtCache.clear(); _vtIndex = null; _vtActivePath = null; renderVaultTree();
    });

    // Cột trái = Vault explorer (luôn có trong DOM ở màn home) → nạp cây ngay khi khởi động
    renderVaultTree();

    freshSettings().then(s => {
      graphEnabled = !(s.dashboard && s.dashboard.graph_enabled === false);
      // Lite-mode (cờ tắt hoặc màn hẹp) → vào thẳng Tổng quan, không hiện graph
      if (liteMode()) navigateTo("overview");
      recomputeGraph();
      // Deep-link mở tab mới từ link file trong chat: #open=<đường-dẫn-vault> → mở thẳng Tệp tin đúng vị trí
      try {
        const m = /^#open=(.+)$/.exec(location.hash || "");
        if (m) openFilesAt(decodeURIComponent(m[1]));
      } catch (e) {}
    });
  }

  if (window.Alpine && Alpine.version) boot();           // Alpine đã sẵn (hiếm)
  else document.addEventListener("alpine:initialized", boot);
})();
