// Khung lenh / cho khung chat web. Phan LOGIC thuan (parse/route/menu) test duoc headless;
// phan menu DOM o cuoi file chi chay trong trinh duyet. Pattern giong chat-ask.js.
(function () {
  var SESSION_COMMANDS = ["new", "reset", "stop"];

  // Nhan dien lenh: bat dau bang / + token [a-z0-9_-], phan sau la arg.
  function parseSlash(text) {
    if (typeof text !== "string") return null;
    var m = text.match(/^\/([a-zA-Z0-9_-]+)(?:\s+([\s\S]*))?$/);
    if (!m) return null;
    return { cmd: m[1].toLowerCase(), arg: (m[2] || "").trim() };
  }

  function classify(cmd) {
    return SESSION_COMMANDS.indexOf(cmd) !== -1 ? "session" : "skill";
  }

  // Khop DUNG mau fallback cua Telegram (server/main.py) de 2 kenh nhat quan.
  function buildSkillInvocation(cmd, arg) {
    return "Hãy dùng skill `" + cmd + "`" +
      (arg ? " với yêu cầu: " + arg : "") +
      ". Nếu không có skill tên này thì cứ xử lý yêu cầu của tôi bình thường.";
  }

  function route(text) {
    var p = parseSlash(text);
    if (!p) return { type: "passthrough" };
    if (classify(p.cmd) === "session") return { type: "session", cmd: p.cmd };
    return { type: "skill", cmd: p.cmd, message: buildSkillInvocation(p.cmd, p.arg) };
  }

  var SESSION_ITEMS = [
    { kind: "session", cmd: "new", name: "Hội thoại mới", desc: "Bắt đầu cuộc trò chuyện mới" },
    { kind: "session", cmd: "reset", name: "Reset phiên", desc: "Xoá ngữ cảnh, bắt đầu lại" },
    { kind: "session", cmd: "stop", name: "Dừng", desc: "Dừng lượt đang trả lời" },
  ];

  function buildMenu(skills) {
    var out = SESSION_ITEMS.slice();
    (skills || []).forEach(function (s) {
      if (!s || !s.slug) return;
      out.push({ kind: "skill", cmd: s.slug, name: s.name || s.slug, desc: s.description || "" });
    });
    return out;
  }

  function filterItems(items, query) {
    var q = (query || "").toLowerCase();
    if (!q) return (items || []).slice();
    var scored = [];
    (items || []).forEach(function (it) {
      var cmd = (it.cmd || "").toLowerCase();
      var name = (it.name || "").toLowerCase();
      var score = -1;
      if (cmd.indexOf(q) === 0) score = 0;            // cmd khop tien to - uu tien nhat
      else if (cmd.indexOf(q) !== -1) score = 1;      // cmd chua query
      else if (name.indexOf(q) !== -1) score = 2;     // ten chua query
      if (score >= 0) scored.push({ it: it, score: score });
    });
    scored.sort(function (a, b) { return a.score - b.score; });
    return scored.map(function (x) { return x.it; });
  }

  var api = {
    parseSlash: parseSlash,
    SESSION_COMMANDS: SESSION_COMMANDS,
    classify: classify,
    buildSkillInvocation: buildSkillInvocation,
    route: route,
    buildMenu: buildMenu,
    filterItems: filterItems,
  };

  if (typeof window !== "undefined") window.JavisSlash = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;

  // ===== Phan MENU DOM (chi trinh duyet) - dien o Task 3 =====
  if (typeof window !== "undefined" && typeof document !== "undefined") {
    if (window.JavisSlash) window.JavisSlash._initMenu = function () { /* Task 3 */ };
  }
})();
