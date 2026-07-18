/* chat-render.js - bo render chat "chan that nhu Claude" cho Javis OS.
   Thay bo markdownToHtml regex cu trong app.js: markdown day du (heading h1-h6,
   danh sach co thu tu + long + checkbox, blockquote, duong ke ngang, in nghieng,
   gach ngang, link, anh), code block co nhan ngon ngu + to mau cu phap, render an
   toan khi dang stream (code fence chua dong van hien dep), va ARTIFACT: HTML/SVG/
   mermaid/code dai hien thanh the gon trong chat, bam mo panel ben phai (Xem truoc /
   Ma nguon / Copy / Tai ve). Tach rieng de khong dung logic khac cua app.js.

   An toan XSS: render theo whitelist (moi text deu escape, chi dung dung the ta sinh
   ra), href/src duoc loc; artifact HTML chay trong iframe sandbox co lap (khong
   allow-same-origin), SVG render trong iframe khong cho script. Khong phu thuoc CDN
   tru mermaid (lazy-load khi can, offline thi suy giam nhe nhang thanh ma nguon).
   Ghi chu: KHONG dung ky tu em dash o bat ky dau.

   Placeholder dung 2 ky tu vung private-use  /  lam moc (khong bao gio
   xuat hien trong text AI) -> tranh nuot nham chuoi kieu " 3 " trong cau. */
(function () {
  "use strict";

  var OPEN = String.fromCharCode(0xE000), CLOSE = String.fromCharCode(0xE001);   // sentinel placeholder (private-use, khong xuat hien trong text)

  // ---------------------------------------------------------------- helpers
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function safeHref(x) {
    x = String(x == null ? "" : x).trim();
    return /^(https?:\/\/|mailto:|\/)/i.test(x) ? x : "";
  }
  function brainPath() {
    try { return (typeof currentBrainPath === "function") ? currentBrainPath() : ""; }
    catch (e) { return ""; }
  }
  function fileUrl(p) {
    return "/files/raw?brain=" + encodeURIComponent(brainPath()) +
      "&path=" + encodeURIComponent(String(p || "").replace(/^\.?\//, ""));
  }
  function resolveSrc(s) {
    s = String(s || "").trim();
    return /^(https?:|data:|blob:|\/)/i.test(s) ? s : fileUrl(s);
  }
  // Path tro toi file/thu muc TRONG vault (khong phai URL ngoai / data / o dia)?
  function isVaultRel(p) {
    p = String(p == null ? "" : p).trim();
    return !!p && !/^(https?:|mailto:|data:|blob:|\/)/i.test(p);
  }
  // Thuoc tinh <a> mo trang Tep tin dung vi tri file/thu muc. Giu href deep-link (#open=..) de
  // Ctrl/giua chuot mo tab trinh duyet moi cung nhay dung cho; bam thuong -> mo trong app.
  function vaultLoc(rawpath) {
    var clean = String(rawpath || "").replace(/^\.?\//, "");
    return 'href="#open=' + esc(encodeURIComponent(clean)) + '" data-vault-path="' + esc(clean) +
      '" class="jv-floc" title="Mo vi tri trong Tep tin"';
  }
  // FNV-1a -> id ngan on dinh cho artifact (cung noi dung -> cung id qua cac lan re-render khi stream)
  function hashId(s) {
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 0x01000193) >>> 0; }
    return "a" + h.toString(36);
  }

  // ---------------------------------------------------------------- to mau cu phap (nhe, da ngon ngu)
  var KW = ("await async break case catch class const continue debugger default delete do else " +
    "export extends finally for from function if implements import in instanceof interface let " +
    "new package private protected public return static super switch this throw try typeof var " +
    "void while with yield def elif except lambda nonlocal global pass raise as assert del print " +
    "self and or not is None True False func fn fun struct type enum trait impl match where use " +
    "mut pub end then local echo require include namespace foreach when unless begin module").split(/\s+/);
  var KWSET = {}; KW.forEach(function (k) { KWSET[k] = 1; });
  var RE_HASH = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/|#[^\n]*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|([A-Za-z_$][A-Za-z0-9_$]*)|([\s\S])/g;
  var RE_NOHASH = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|([A-Za-z_$][A-Za-z0-9_$]*)|([\s\S])/g;
  function highlight(code, lang) {
    lang = (lang || "").toLowerCase();
    var useHash = /^(py|python|sh|bash|zsh|shell|yaml|yml|ruby|rb|toml|ini|conf|r|perl|pl|make|makefile|dockerfile|nginx|env|properties|cmake)$/.test(lang) || /^#!/.test(code);
    var re = useHash ? RE_HASH : RE_NOHASH;
    re.lastIndex = 0;
    var out = "", m;
    while ((m = re.exec(code)) !== null) {
      if (m[1] != null) out += '<span class="tok-c">' + esc(m[1]) + "</span>";
      else if (m[2] != null) out += '<span class="tok-s">' + esc(m[2]) + "</span>";
      else if (m[3] != null) out += '<span class="tok-n">' + esc(m[3]) + "</span>";
      else if (m[4] != null) out += (KWSET[m[4]] ? '<span class="tok-k">' + esc(m[4]) + "</span>" : esc(m[4]));
      else out += esc(m[5]);
      if (re.lastIndex === m.index) re.lastIndex++;   // chong ket vong lap
    }
    return out;
  }

  // ---------------------------------------------------------------- artifact registry + phat hien
  var registry = {};   // id -> { type, lang, code }
  function fenceType(lang, code) {
    lang = (lang || "").trim().toLowerCase();
    var head = code.slice(0, 400).replace(/^\s+/, "").toLowerCase();
    if (lang === "mermaid") return "mermaid";
    if (lang === "svg" || /^<svg[\s>]/.test(head)) return "svg";
    if (lang === "html" || lang === "xml" || /^<!doctype html|^<html[\s>]/.test(head)) return "html";
    var lines = code.split("\n").length;
    if (lines >= 24 || code.length >= 800) return "code";   // file code dai -> artifact
    return "";   // code ngan -> khoi code inline
  }
  function artTitle(type, lang) {
    if (type === "html") return "Trang HTML";
    if (type === "svg") return "Anh SVG";
    if (type === "mermaid") return "So do";
    return "Ma " + ((lang || "text").toUpperCase());
  }
  function artIcon(type) {
    return type === "html" ? "🌐" : type === "svg" ? "🖼" : type === "mermaid" ? "📊" : "📄";
  }
  function artifactCard(type, lang, code) {
    var id = hashId(type + "" + code);
    registry[id] = { type: type, lang: lang, code: code };
    var sub = code.split("\n").length + " dong · bam de xem";
    return '<div class="jv-art" role="button" tabindex="0" data-art="' + id + '">' +
      '<span class="jv-art-ic">' + artIcon(type) + "</span>" +
      '<span class="jv-art-meta"><span class="jv-art-title">' + esc(artTitle(type, lang)) + "</span>" +
      '<span class="jv-art-sub">' + esc(sub) + "</span></span>" +
      '<span class="jv-art-open">Mo ▸</span></div>';
  }

  function codeBlockHtml(lang, code, streaming) {
    var live = streaming ? " code-live" : "";
    return '<div class="code-wrap' + live + '">' +
      '<div class="code-head"><span class="code-lang">' + esc(lang || "text") + "</span>" +
      '<button class="code-copy" type="button">⧉ Copy</button></div>' +
      '<pre class="code-block">' + highlight(code, lang) + "</pre></div>";
  }
  function renderFence(info, code, streaming) {
    var lang = (info || "").trim().split(/\s+/)[0] || "";
    code = code.replace(/\n$/, "");
    if (streaming) return codeBlockHtml(lang, code, true);   // fence chua dong: khoi code song, chua thanh artifact
    var type = fenceType(lang, code);
    if (type) return artifactCard(type, lang, code);
    return codeBlockHtml(lang, code, false);
  }

  // ---------------------------------------------------------------- anh, link, bang
  function imgHtml(u, alt, rawpath) {
    var img = '<img class="chat-img" src="' + esc(u) + '" alt="' + esc(alt || "") + '" loading="lazy">';
    // Anh trong vault: bam mo VI TRI trong Tep tin (thay vi tai anh tho); van hien anh inline.
    if (rawpath && isVaultRel(rawpath)) return '<a ' + vaultLoc(rawpath) + ">" + img + "</a>";
    var h = safeHref(u);
    return h ? '<a href="' + esc(h) + '" target="_blank" rel="noopener">' + img + "</a>" : img;
  }
  function tableHtml(tbl) {
    var rows = tbl.trim().split("\n").filter(function (r) { return r.trim(); });
    var cells = function (r) { return r.replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); }); };
    var head = cells(rows[0]);
    var body = rows.slice(2).map(cells);
    var th = head.map(function (c) { return "<th>" + inline(c) + "</th>"; }).join("");
    var trs = body.map(function (r) {
      return "<tr>" + r.map(function (c) { return "<td>" + inline(c) + "</td>"; }).join("") + "</tr>";
    }).join("");
    return '<table class="md-table"><thead><tr>' + th + "</tr></thead><tbody>" + trs + "</tbody></table>";
  }

  // ---------------------------------------------------------------- inline (dam/nghieng/gach/xuong dong)
  function inline(s) {
    s = esc(s);
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
      .replace(/~~([^~]+)~~/g, "<del>$1</del>")
      .replace(/\b_([^_\n]+)_\b/g, "<em>$1</em>")
      .replace(/\n/g, "<br>");
    return s;
  }

  // ---------------------------------------------------------------- block parse (line-based, ben hon regex)
  function isListLine(s) { return /^(\s*)([-*+]|\d+[.)])\s+/.test(s); }
  function buildList(lines) {
    var items = [];
    for (var k = 0; k < lines.length; k++) {
      var m = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/.exec(lines[k]);
      if (m) {
        var indent = m[1].replace(/\t/g, "    ").length;
        var ordered = /\d/.test(m[2]);
        var content = m[3], chk = null;
        var cm = /^\[([ xX])\]\s+(.*)$/.exec(content);
        if (cm) { chk = /[xX]/.test(cm[1]); content = cm[2]; }
        items.push({ indent: indent, ordered: ordered, checked: chk, lines: [content], children: [] });
      } else if (items.length) {
        items[items.length - 1].lines.push(lines[k].trim());   // dong noi tiep cua item tren
      }
    }
    var root = { children: [], indent: -1 }, stack = [root];
    items.forEach(function (it) {
      while (stack.length > 1 && it.indent <= stack[stack.length - 1].indent) stack.pop();
      stack[stack.length - 1].children.push(it);
      stack.push(it);
    });
    return renderList(root.children);
  }
  function renderList(items) {
    if (!items.length) return "";
    var tag = items[0].ordered ? "ol" : "ul";
    var html = "<" + tag + ">";
    items.forEach(function (it) {
      var box = it.checked == null ? "" :
        '<input type="checkbox" disabled' + (it.checked ? " checked" : "") + "> ";
      var cls = it.checked == null ? "" : ' class="task-item"';
      html += "<li" + cls + ">" + box + inline(it.lines.join(" ")) +
        (it.children.length ? renderList(it.children) : "") + "</li>";
    });
    return html + "</" + tag + ">";
  }
  function blockParse(text) {
    var lines = text.split("\n"), out = [], i = 0, n = lines.length, para = [];
    function flushPara() { if (para.length) { out.push("<p>" + inline(para.join("\n")) + "</p>"); para = []; } }
    var BLOCK_ONLY = new RegExp("^\\s*" + OPEN + "\\d+" + CLOSE + "\\s*$");
    while (i < n) {
      var line = lines[i];
      if (/^\s*$/.test(line)) { flushPara(); i++; continue; }
      if (BLOCK_ONLY.test(line)) { flushPara(); out.push(line.trim()); i++; continue; }
      var h = /^(#{1,6})\s+(.*)$/.exec(line);
      if (h) { flushPara(); var lv = h[1].length; out.push("<h" + lv + ">" + inline(h[2].trim()) + "</h" + lv + ">"); i++; continue; }
      if (/^\s*([-*_])\s*(?:\1\s*){2,}$/.test(line)) { flushPara(); out.push("<hr>"); i++; continue; }
      if (/^\s*>\s?/.test(line)) {
        flushPara();
        var q = [];
        while (i < n && /^\s*>\s?/.test(lines[i])) { q.push(lines[i].replace(/^\s*>\s?/, "")); i++; }
        out.push("<blockquote>" + blockParse(q.join("\n")) + "</blockquote>");
        continue;
      }
      if (isListLine(line)) {
        flushPara();
        var block = [];
        while (i < n) {
          if (isListLine(lines[i]) || /^\s+\S/.test(lines[i])) { block.push(lines[i]); i++; continue; }
          if (/^\s*$/.test(lines[i]) && i + 1 < n && (isListLine(lines[i + 1]) || /^\s+\S/.test(lines[i + 1]))) { i++; continue; }
          break;
        }
        out.push(buildList(block));
        continue;
      }
      para.push(line); i++;
    }
    flushPara();
    return out.join("\n");
  }

  // ---------------------------------------------------------------- entry: markdown -> html
  function mdToHtml(raw) {
    raw = String(raw == null ? "" : raw);
    // Bo HTML comment (block JAVIS_METRICS luon vo hinh), ke ca comment chua dong luc stream
    raw = raw.replace(/<!--[\s\S]*?-->/g, "").replace(/<!--[\s\S]*$/, "");

    var ph = [];
    function put(html) { ph.push(html); return OPEN + (ph.length - 1) + CLOSE; }

    // 1) code fence hoan chinh (phai xu ly truoc moi thu)
    raw = raw.replace(/```([^\n]*)\n([\s\S]*?)```/g, function (_m, info, code) {
      return "\n" + put(renderFence(info, code, false)) + "\n";
    });
    // 1b) dang stream: fence mo chua dong o cuoi -> khoi code song
    raw = raw.replace(/```([^\n]*)\n([\s\S]*)$/, function (_m, info, code) {
      return "\n" + put(renderFence(info, code, true)) + "\n";
    });
    // 2) inline code (truoc bang/anh/link va truoc nhan manh)
    raw = raw.replace(/`([^`\n]+)`/g, function (_m, c) { return put("<code>" + esc(c) + "</code>"); });
    // 3) anh vault ![[..]] + anh markdown ![]() (giu URL qua placeholder de khong bi escape)
    raw = raw.replace(/!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]/g, function (_m, name) {
      name = name.trim();
      return put(imgHtml(resolveSrc(name), name, name));
    });
    // Duong dan trong () co the CO KHOANG TRANG + DAU NGOAC (vd "06 - Sources/Ten (Tu Duy Nguoc).md").
    // Bat ca cap ngoac can bang 1 tang, roi cat title markdown tuy chon o duoi ( "tieu de" / 'tieu de').
    raw = raw.replace(/!\[([^\]]*)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g, function (_m, alt, src) {
      src = src.replace(/\s+(["']).*\1\s*$/, "").trim();
      return put(imgHtml(resolveSrc(src), alt, src));
    });
    // 4) link []() : URL ngoai -> tab moi; file/thu muc vault -> mo dung vi tri trong Tep tin; con lai giu cu
    raw = raw.replace(/\[([^\]]+)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g, function (_m, t, href) {
      href = href.replace(/\s+(["']).*\1\s*$/, "").trim();
      if (/^(https?:|mailto:)/i.test(href)) return put('<a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(t) + "</a>");
      if (isVaultRel(href)) return put('<a ' + vaultLoc(href) + ">" + esc(t) + "</a>");
      return put('<a href="' + esc(resolveSrc(href)) + '" target="_blank" rel="noopener">' + esc(t) + "</a>");
    });
    // 4b) URL tran (AI go thang, khong boc markdown) -> tu thanh link mo tab moi. Chay SAU khi link/anh/
    //     code da cat vao placeholder (sentinel) nen khong dung vao chung; loai dau cau/ngoac o duoi URL.
    raw = raw.replace(new RegExp("(^|[^\\]\"'=/])(\\bhttps?:\\/\\/[^\\s<>()\\[\\]" + OPEN + CLOSE + "]+)", "g"), function (_m, pre, url) {
      var trail = "", tm = /[.,;:!?)\]}'"]+$/.exec(url);
      if (tm) { trail = tm[0]; url = url.slice(0, url.length - trail.length); }
      return pre + put('<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + "</a>") + trail;
    });
    // 5) bang markdown
    raw = raw.replace(/(^\|.+\|[ \t]*\n\|[ \t:|-]+\|[ \t]*\n(?:\|.*\|[ \t]*\n?)*)/gm, function (tbl) {
      return "\n" + put(tableHtml(tbl)) + "\n";
    });

    // 6) parse block phan con lai
    var html = blockParse(raw);

    // 7) tra lai placeholder (lap vai lan vi co the long: link trong bang, ...)
    var reIns = new RegExp(OPEN + "(\\d+)" + CLOSE, "g");
    var reHas = new RegExp(OPEN + "\\d+" + CLOSE);
    for (var pass = 0; pass < 6 && reHas.test(html); pass++) {
      html = html.replace(reIns, function (_m, idx) { return ph[+idx] != null ? ph[+idx] : ""; });
    }
    return html;
  }

  // ================================================================ ARTIFACT PANEL (chi trong trinh duyet)
  var panel = null, elTitle = null, elBody = null, curArt = null, curTab = "preview";

  function buildPanel() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.className = "jv-artpanel";
    panel.innerHTML =
      '<div class="jv-ap-head">' +
        '<span class="jv-ap-title">Artifact</span>' +
        '<span class="jv-ap-tabs">' +
          '<button class="jv-ap-tab active" data-tab="preview">Xem truoc</button>' +
          '<button class="jv-ap-tab" data-tab="code">Ma nguon</button>' +
        "</span>" +
        '<span class="jv-ap-actions">' +
          '<button class="jv-ap-btn" data-act="copy" title="Copy ma nguon">⧉</button>' +
          '<button class="jv-ap-btn" data-act="download" title="Tai ve">⇩</button>' +
          '<button class="jv-ap-btn jv-ap-close" data-act="close" title="Dong (Esc)">✕</button>' +
        "</span>" +
      "</div>" +
      '<div class="jv-ap-body"></div>';
    document.body.appendChild(panel);
    elTitle = panel.querySelector(".jv-ap-title");
    elBody = panel.querySelector(".jv-ap-body");
    panel.addEventListener("click", onPanelClick);
    return panel;
  }
  function syncTabs() {
    if (!panel) return;
    panel.querySelectorAll(".jv-ap-tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === curTab);
    });
  }
  function openArtifact(id) {
    var art = registry[id];
    if (!art) return;
    buildPanel();
    curArt = art;
    elTitle.textContent = artTitle(art.type, art.lang);
    var hasPreview = art.type !== "code";
    panel.classList.toggle("no-preview", !hasPreview);
    curTab = hasPreview ? "preview" : "code";
    syncTabs();
    renderTab();
    panel.classList.add("open");
    document.body.classList.add("jv-artpanel-open");
  }
  function closePanel() {
    if (!panel) return;
    panel.classList.remove("open");
    document.body.classList.remove("jv-artpanel-open");
    if (elBody) elBody.innerHTML = "";   // don iframe/srcdoc
    curArt = null;
  }
  function frame(sandbox, srcdoc) {
    var f = document.createElement("iframe");
    f.className = "jv-ap-frame";
    f.setAttribute("sandbox", sandbox);
    f.setAttribute("referrerpolicy", "no-referrer");
    f.srcdoc = srcdoc;
    return f;
  }
  function renderTab() {
    var art = curArt; if (!art || !elBody) return;
    if (curTab === "code" || art.type === "code") {
      elBody.innerHTML = '<pre class="jv-ap-code code-block">' + highlight(art.code, art.lang) + "</pre>";
      return;
    }
    if (art.type === "html") {
      elBody.innerHTML = "";
      elBody.appendChild(frame("allow-scripts allow-forms allow-popups allow-modals", art.code));
      return;
    }
    if (art.type === "svg") {
      elBody.innerHTML = "";
      elBody.appendChild(frame("",   // sandbox rong = KHONG chay script trong svg
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;height:100%;display:flex;' +
        "align-items:center;justify-content:center;background:#fff}svg{max-width:100%;max-height:100%}</style>" + art.code));
      return;
    }
    if (art.type === "mermaid") {
      elBody.innerHTML = '<div class="jv-ap-mermaid">Dang ve so do...</div>';
      renderMermaid(art.code, elBody.querySelector(".jv-ap-mermaid"));
      return;
    }
  }
  function onPanelClick(e) {
    var t = e.target.closest ? e.target.closest("[data-tab],[data-act]") : null;
    if (!t) return;
    if (t.dataset.tab) { curTab = t.dataset.tab; syncTabs(); renderTab(); return; }
    var act = t.dataset.act;
    if (act === "close") closePanel();
    else if (act === "copy" && curArt) copyText(curArt.code, t);
    else if (act === "download" && curArt) downloadArt(curArt);
  }
  function copyText(text, btn) {
    var run = (navigator.clipboard && window.isSecureContext)
      ? navigator.clipboard.writeText(text) : Promise.reject();
    run.catch(function () {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.cssText = "position:fixed;opacity:0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      ta.remove();
    }).then(function () {
      if (btn) { var o = btn.textContent; btn.textContent = "✓"; setTimeout(function () { btn.textContent = o; }, 1000); }
    });
  }
  function extFor(art) {
    if (art.type === "html") return "html";
    if (art.type === "svg") return "svg";
    if (art.type === "mermaid") return "mmd";
    var map = { javascript: "js", js: "js", typescript: "ts", ts: "ts", python: "py", py: "py",
      json: "json", css: "css", bash: "sh", sh: "sh", java: "java", go: "go", rust: "rs",
      c: "c", cpp: "cpp", html: "html", sql: "sql", yaml: "yml", yml: "yml", md: "md" };
    return map[(art.lang || "").toLowerCase()] || "txt";
  }
  function downloadArt(art) {
    var blob = new Blob([art.code], { type: "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = "artifact-" + hashId(art.code).slice(1, 7) + "." + extFor(art);
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 400);
  }

  // ---- mermaid: lazy-load, offline thi suy giam thanh ma nguon ----
  var mmState = 0, mmQueue = [], mmSeq = 0;   // 0 chua nap, 1 dang nap, 2 san sang, 3 hong
  function loadMermaid(cb) {
    if (mmState === 2) return cb(true);
    if (mmState === 3) return cb(false);
    mmQueue.push(cb);
    if (mmState === 1) return;
    mmState = 1;
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
    s.onload = function () {
      try { window.mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "strict" }); } catch (e) {}
      mmState = 2; var q = mmQueue; mmQueue = []; q.forEach(function (c) { c(true); });
    };
    s.onerror = function () { mmState = 3; var q = mmQueue; mmQueue = []; q.forEach(function (c) { c(false); }); };
    document.head.appendChild(s);
  }
  function renderMermaid(code, host) {
    if (!host) return;
    loadMermaid(function (ok) {
      if (!ok || !window.mermaid) {
        host.innerHTML = '<div class="jv-ap-note">Khong tai duoc thu vien so do (co the dang offline). Xem ma o tab Ma nguon.</div>' +
          '<pre class="code-block">' + esc(code) + "</pre>";
        return;
      }
      var id = "jvmm" + (++mmSeq);
      try {
        window.mermaid.render(id, code).then(function (res) { host.innerHTML = res.svg; })
          .catch(function () { host.innerHTML = '<div class="jv-ap-note">So do sai cu phap mermaid.</div><pre class="code-block">' + esc(code) + "</pre>"; });
      } catch (e) {
        host.innerHTML = '<div class="jv-ap-note">So do sai cu phap mermaid.</div><pre class="code-block">' + esc(code) + "</pre>";
      }
    });
  }

  // ---------------------------------------------------------------- wiring (chi khi co DOM)
  if (typeof document !== "undefined") {
    document.addEventListener("click", function (e) {
      // Dang SOAN trong editor (contenteditable/.ne-wys) hoac trong khung sua file -> khong mo gi ca,
      // de nguoi dung bam link/anh ma sua binh thuong (tranh bung editor long nhau).
      if (e.target.closest && e.target.closest('[contenteditable="true"], .jvfe-modal, .note-editor')) return;
      // Link file/thu muc vault: bam thuong -> mo trang Tep tin dung vi tri. Ctrl/Cmd/Shift/giua chuot
      // -> de trinh duyet dung deep-link href (#open=..) mo tab moi (chat van con o tab cu).
      var loc = e.target.closest ? e.target.closest("a.jv-floc") : null;
      if (loc && loc.getAttribute("data-vault-path") != null) {
        if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button > 0) return;
        e.preventDefault();
        var vp = loc.getAttribute("data-vault-path") || "";
        var isImg = !!(loc.querySelector && loc.querySelector("img"));   // anh inline -> giu hanh vi cu
        var trimmed = vp.replace(/\/+$/, "");
        var base = trimmed.split("/").pop();
        var isDir = /\/$/.test(vp) || base === "" || base.indexOf(".") < 0;   // co duoi -> FILE (nhu openFilesAt)
        // FILE co duoi -> bung khung sua giua man hinh; THU MUC / anh inline -> mo trang Tep tin dung vi tri.
        if (!isImg && !isDir && typeof window.JavisEditFile === "function") { window.JavisEditFile(trimmed); return; }
        if (typeof window.JavisOpenFiles === "function") window.JavisOpenFiles(vp);
        else window.open(loc.href, "_blank");   // du phong: mo tab moi neu console.js chua san sang
        return;
      }
      var card = e.target.closest ? e.target.closest(".jv-art") : null;
      if (card && card.dataset.art) { e.preventDefault(); openArtifact(card.dataset.art); }
    });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Enter" || e.key === " ") && document.activeElement &&
          document.activeElement.classList && document.activeElement.classList.contains("jv-art")) {
        e.preventDefault(); openArtifact(document.activeElement.dataset.art);
      }
    });
    // Esc dong panel TRUOC (capture) de khong thu nho luon khung chat phong to
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && panel && panel.classList.contains("open")) {
        e.stopPropagation(); closePanel();
      }
    }, true);
  }

  if (typeof window !== "undefined") {
    window.mdToHtml = mdToHtml;
    window.JavisArtifacts = { open: openArtifact, close: closePanel };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { mdToHtml: mdToHtml, highlight: highlight };
  }
})();
