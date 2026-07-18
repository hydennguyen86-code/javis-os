/* file-editor.js - Khung sua file bung GIUA MAN HINH, goi tu link file trong chat.
   window.JavisEditFile(brainRelPath): mo modal doc /files/read, sua text (.md co nut gat
   Nguon/Xem), luu /files/write, xem truoc anh/pdf, file khac cho tai.

   Doc lap: tu chen CSS, gan modal vao <body> nen chay duoc tu MOI trang (chat toan trang,
   chat HUD, trang Tep tin) khong phu thuoc layout. Khong dung 2 editor cu (khong so vo).

   Quy uoc duong dan: link trong chat la TUONG DOI GOC BRAIN. /files/read nhan ca 2 quy uoc
   nhung /files/write chi tinh theo TRAN DUYET -> phai ghep tien to 'home' (nha cua brain) truoc
   khi doc/ghi de LUU dung cho (localhost tran = ca o dia). Tien to lay tu /files/list (truong home).

   Ghi chu: KHONG dung ky tu em dash o bat ky dau. */
(function () {
  "use strict";

  var IMG = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico"];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function brain() { return window.currentBrainPath ? (window.currentBrainPath() || "brain") : "brain"; }
  function extOf(p) {
    var b = String(p || "").replace(/\/+$/, "").split("/").pop();
    var i = b.lastIndexOf(".");
    return i >= 0 ? b.slice(i).toLowerCase() : "";
  }
  function baseOf(p) { return String(p || "").replace(/\/+$/, "").split("/").pop(); }

  // --- tien to 'home' (nha brain) tinh theo tran duyet, cache theo brain ---
  var homeCache = {};
  function getHome(b) {
    if (homeCache[b] != null) return Promise.resolve(homeCache[b]);
    return fetch("/files/list?brain=" + encodeURIComponent(b))
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) { var h = (d && d.home) || ""; homeCache[b] = h; return h; })
      .catch(function () { return ""; });   // that bai: tien to rong (dung khi tran == brain)
  }
  // brainRel -> path theo tran duyet (ghep home). Da la path tran thi giu nguyen.
  function ceilPath(home, brainRel) {
    var rel = String(brainRel || "").replace(/^\.?\//, "").replace(/\/+$/, "");
    return home ? home + "/" + rel : rel;
  }
  function rawUrl(b, ceilRel, dl) {
    return "/files/raw?brain=" + encodeURIComponent(b) + "&path=" + encodeURIComponent(ceilRel) + (dl ? "&dl=1" : "");
  }

  // ---------------------------------------------------------------- CSS (chen 1 lan)
  function injectCss() {
    if (document.getElementById("jvfe-css")) return;
    var s = document.createElement("style");
    s.id = "jvfe-css";
    s.textContent =
      ".jvfe-modal{position:fixed;inset:0;z-index:3000;display:none;align-items:center;justify-content:center;" +
      "background:rgba(0,0,0,.55);backdrop-filter:blur(3px);padding:24px;box-sizing:border-box}" +
      ".jvfe-modal.open{display:flex;animation:jvfeIn .16s ease}" +
      "@keyframes jvfeIn{from{opacity:.3}to{opacity:1}}" +
      ".jvfe-card{width:min(920px,94vw);max-height:88vh;display:flex;flex-direction:column;" +
      "background:var(--bg2,#151521);border:1px solid var(--border,#36364c);border-radius:14px;" +
      "box-shadow:0 24px 70px rgba(0,0,0,.6);overflow:hidden}" +
      ".jvfe-head{display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border,#36364c)}" +
      ".jvfe-title{font-weight:600;font-size:14px;color:var(--text,#f3f3fb);flex:1;overflow:hidden;" +
      "text-overflow:ellipsis;white-space:nowrap;display:flex;align-items:center;gap:7px}" +
      ".jvfe-actions{display:flex;gap:6px;flex:none;align-items:center}" +
      ".jvfe-seg{display:flex;gap:4px;margin-right:4px}" +
      ".jvfe-btn{background:var(--bg3,#20202e);border:1px solid var(--border,#36364c);color:var(--text2,#c7c9d6);" +
      "border-radius:7px;padding:5px 11px;font-size:13px;cursor:pointer;font-family:inherit}" +
      ".jvfe-btn:hover{color:#fff;border-color:var(--accent,#ff7a3c)}" +
      ".jvfe-btn.active{color:var(--accent,#ff7a3c);border-color:var(--accent,#ff7a3c)}" +
      ".jvfe-btn.icon{width:32px;height:32px;padding:0;font-size:14px}" +
      ".jvfe-btn.saved{color:#5fd08a;border-color:#5fd08a}" +
      ".jvfe-body{flex:1;min-height:0;overflow:auto;background:var(--bg,#0e0e16);display:flex;flex-direction:column}" +
      ".jvfe-text{flex:1;min-height:52vh;width:100%;box-sizing:border-box;border:0;outline:none;resize:none;" +
      "background:var(--bg,#0e0e16);color:var(--text,#f3f3fb);font-family:ui-monospace,Menlo,Consolas,monospace;" +
      "font-size:13.5px;line-height:1.6;padding:16px}" +
      ".jvfe-prev{padding:16px 20px;color:var(--text,#f3f3fb);line-height:1.7;overflow:auto}" +
      ".jvfe-prev h1,.jvfe-prev h2,.jvfe-prev h3,.jvfe-prev h4{margin:.7em 0 .35em;line-height:1.3}" +
      ".jvfe-prev pre{background:var(--bg2,#151521);padding:10px 12px;border-radius:8px;overflow:auto}" +
      ".jvfe-prev code{background:var(--bg2,#151521);padding:1px 5px;border-radius:4px;font-size:.92em}" +
      ".jvfe-prev pre code{background:none;padding:0}" +
      ".jvfe-prev img{max-width:100%;height:auto;border-radius:8px}" +
      ".jvfe-prev table{border-collapse:collapse}.jvfe-prev th,.jvfe-prev td{border:1px solid var(--border,#36364c);padding:5px 9px}" +
      ".jvfe-note{padding:18px;color:var(--text3,#8b8fa0);font-size:14px;line-height:1.6}" +
      ".jvfe-note a{color:var(--accent,#ff7a3c)}" +
      ".jvfe-img{padding:16px;text-align:center;overflow:auto}" +
      ".jvfe-img img{max-width:100%;height:auto;border-radius:8px}" +
      ".jvfe-frame{width:100%;height:72vh;border:0;background:#fff}";
    document.head.appendChild(s);
  }

  // ---------------------------------------------------------------- modal (dung 1 lan, tai su dung)
  var modal = null, card = null, elTitle = null, elActions = null, elBody = null, curSave = null;

  function build() {
    if (modal) return;
    injectCss();
    modal = document.createElement("div");
    modal.className = "jvfe-modal";
    modal.innerHTML =
      '<div class="jvfe-card" role="dialog" aria-modal="true">' +
        '<div class="jvfe-head"><span class="jvfe-title"></span><span class="jvfe-actions"></span></div>' +
        '<div class="jvfe-body"></div>' +
      "</div>";
    document.body.appendChild(modal);
    card = modal.querySelector(".jvfe-card");
    elTitle = modal.querySelector(".jvfe-title");
    elActions = modal.querySelector(".jvfe-actions");
    elBody = modal.querySelector(".jvfe-body");
    modal.addEventListener("mousedown", function (e) { if (e.target === modal) close(); });   // bam nen mo -> dong
    document.addEventListener("keydown", function (e) {
      if (!isOpen()) return;
      if (e.key === "Escape") { e.stopPropagation(); close(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault(); e.stopPropagation(); if (curSave) curSave();
      }
    }, true);
  }
  function isOpen() { return modal && modal.classList.contains("open"); }
  function close() {
    if (!modal) return;
    modal.classList.remove("open");
    elBody.innerHTML = ""; elActions.innerHTML = ""; curSave = null;   // don iframe/textarea
    document.body.classList.remove("jvfe-open");
  }
  function closeBtn() {
    var b = document.createElement("button");
    b.className = "jvfe-btn icon"; b.textContent = "✕"; b.title = "Dong (Esc)";
    b.onclick = close; return b;
  }

  // ---------------------------------------------------------------- mo file
  function open(brainRel) {
    if (!brainRel) return;
    build();
    var b = brain();
    elTitle.innerHTML = esc(baseOf(brainRel));
    elActions.innerHTML = ""; elBody.innerHTML = '<div class="jvfe-note">Dang mo…</div>';
    curSave = null;
    modal.classList.add("open");
    document.body.classList.add("jvfe-open");

    var ext = extOf(brainRel);
    getHome(b).then(function (home) {
      var ceil = ceilPath(home, brainRel);
      // Anh / PDF: xem truoc thang qua /files/raw (khong doc dang text).
      if (IMG.indexOf(ext) >= 0) { renderImage(b, ceil, brainRel); return; }
      if (ext === ".pdf") { renderPdf(b, ceil, brainRel); return; }
      // Con lai: doc noi dung.
      fetch("/files/read?brain=" + encodeURIComponent(b) + "&path=" + encodeURIComponent(ceil))
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!isOpen()) return;
          if (!res.ok || res.d.error) { renderError(b, ceil, brainRel, res.d && res.d.error); return; }
          if (res.d.editable) renderEditor(b, ceil, brainRel, res.d);
          else renderReadonly(b, ceil, brainRel, res.d);
        })
        .catch(function () { if (isOpen()) renderError(b, ceil, brainRel, null); });
    });
  }

  function renderImage(b, ceil, brainRel) {
    elActions.appendChild(dlLink(b, ceil)); elActions.appendChild(closeBtn());
    elBody.innerHTML = '<div class="jvfe-img"><img src="' + esc(rawUrl(b, ceil)) + '" alt="' + esc(baseOf(brainRel)) + '"></div>';
  }
  function renderPdf(b, ceil, brainRel) {
    elActions.appendChild(dlLink(b, ceil)); elActions.appendChild(closeBtn());
    elBody.innerHTML = '<iframe class="jvfe-frame" src="' + esc(rawUrl(b, ceil)) + '"></iframe>';
  }
  function renderReadonly(b, ceil, brainRel, d) {
    elActions.appendChild(dlLink(b, ceil)); elActions.appendChild(closeBtn());
    elBody.innerHTML = '<div class="jvfe-prev"><pre style="white-space:pre-wrap;margin:0">' + esc(d.content || "") + "</pre></div>";
  }
  function renderError(b, ceil, brainRel, msg) {
    elActions.innerHTML = ""; elActions.appendChild(closeBtn());
    elBody.innerHTML = '<div class="jvfe-note">' + esc(msg || "Khong doc duoc file.") +
      ' - <a href="' + esc(rawUrl(b, ceil)) + '" target="_blank" rel="noopener">Mo tab moi</a>' +
      ' · <a href="' + esc(rawUrl(b, ceil, 1)) + '">Tai ve</a></div>';
  }
  function dlLink(b, ceil) {
    var a = document.createElement("a");
    a.href = rawUrl(b, ceil, 1); a.title = "Tai ve";
    a.innerHTML = '<button class="jvfe-btn icon" type="button">⇩</button>';
    return a;
  }

  function renderEditor(b, ceil, brainRel, d) {
    var isMd = extOf(brainRel) === ".md";
    elActions.innerHTML = "";
    elBody.innerHTML =
      '<textarea class="jvfe-text" spellcheck="false"></textarea>' +
      '<div class="jvfe-prev" hidden></div>';
    var ta = elBody.querySelector(".jvfe-text");
    var prev = elBody.querySelector(".jvfe-prev");
    ta.value = d.content || "";

    // .md: nut gat Nguon / Xem (Xem = render doc bang window.mdToHtml san co)
    if (isMd && typeof window.mdToHtml === "function") {
      var seg = document.createElement("span"); seg.className = "jvfe-seg";
      var bSrc = document.createElement("button"); bSrc.className = "jvfe-btn active"; bSrc.textContent = "Nguon";
      var bView = document.createElement("button"); bView.className = "jvfe-btn"; bView.textContent = "Xem";
      bSrc.onclick = function () {
        prev.hidden = true; ta.hidden = false;
        bSrc.classList.add("active"); bView.classList.remove("active");
      };
      bView.onclick = function () {
        prev.innerHTML = window.mdToHtml(ta.value);
        ta.hidden = true; prev.hidden = false;
        bView.classList.add("active"); bSrc.classList.remove("active");
      };
      seg.appendChild(bSrc); seg.appendChild(bView); elActions.appendChild(seg);
    }

    var save = document.createElement("button");
    save.className = "jvfe-btn"; save.textContent = "💾 Luu"; save.title = "Luu (Ctrl+S)";
    curSave = function () {
      // textarea la nguon that; ban Xem chi render doc tu no nen ta.value luon la moi nhat
      var fd = new FormData();
      fd.append("brain", b); fd.append("path", ceil); fd.append("content", ta.value);
      save.textContent = "…"; save.disabled = true;
      fetch("/files/write", { method: "POST", body: fd })
        .then(function (r) { return r.json().catch(function () { return {}; }); })
        .then(function (r) {
          save.disabled = false;
          if (r && r.ok) {
            save.textContent = "✓ Da luu"; save.classList.add("saved");
            setTimeout(function () { save.textContent = "💾 Luu"; save.classList.remove("saved"); }, 1400);
          } else { save.textContent = "⚠ Loi"; setTimeout(function () { save.textContent = "💾 Luu"; }, 1600); }
        })
        .catch(function () { save.disabled = false; save.textContent = "⚠ Loi"; setTimeout(function () { save.textContent = "💾 Luu"; }, 1600); });
    };
    save.onclick = curSave;
    elActions.appendChild(save);
    elActions.appendChild(dlLink(b, ceil));
    elActions.appendChild(closeBtn());
    setTimeout(function () { try { ta.focus(); } catch (e) {} }, 30);
  }

  if (typeof window !== "undefined") {
    window.JavisEditFile = open;
    window.JavisFileEditor = { open: open, close: close };
  }
})();
