/* chat-ask.js - khoi hoi-lai co lua chon cho khung chat Javis.

   Javis ket thuc cau tra loi bang mot khoi an:
     <!-- JAVIS_ASK: {"question":"...","header":"...","options":[{"label":"..","desc":".."}]} -->
   File nay boc khoi do ra, ve thanh hang chip duoi bong bong tra loi, va bat su kien bam.
   Bam mot chip = gui dung nhan do di nhu mot tin nhan nguoi dung binh thuong.

   Di theo dung vet khoi JAVIS_METRICS da chay san (app.js). KHONG dung MCP hub, khong
   dung engine -> chay tren moi bo nao chi nho system prompt.

   An toan: moi text trong khoi la do model sinh ra -> escape het truoc khi nhet vao HTML.
   Ghi chu: KHONG dung ky tu em dash o bat ky dau. */
(function () {
  "use strict";

  var ASK_RE = /<!--\s*JAVIS_ASK:\s*([\s\S]*?)\s*-->/;
  var MAX_OPTS = 4;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Boc khoi JAVIS_ASK khoi text. LUON tra clean da bo khoi (ke ca khi JSON hong) -
  // mot khoi sai cu phap KHONG duoc phep nuot mat cau tra loi cua Javis.
  function extract(text) {
    if (typeof text !== "string") return { clean: "", ask: null };
    var m = text.match(ASK_RE);
    if (!m) return { clean: text, ask: null };
    var clean = text.replace(ASK_RE, "").replace(/\n{3,}/g, "\n\n").trim();
    var ask = null;
    try {
      var o = JSON.parse(m[1]);
      var opts = (o && Array.isArray(o.options) ? o.options : [])
        .filter(function (x) { return x && typeof x.label === "string" && x.label.trim(); })
        .slice(0, MAX_OPTS)
        .map(function (x) {
          return { label: String(x.label).trim(), desc: String(x.desc == null ? "" : x.desc).trim() };
        });
      var q = (o && typeof o.question === "string") ? o.question.trim() : "";
      if (q && opts.length) {
        ask = { question: q, header: String((o && o.header) == null ? "" : o.header).trim(), options: opts };
      }
    } catch (e) {}
    return { clean: clean, ask: ask };
  }

  if (typeof window !== "undefined") {
    window.JavisAsk = { extract: extract };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { extract: extract };
  }
})();
