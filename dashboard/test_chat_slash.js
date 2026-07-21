/* Test logic thuan cua khung lenh /. Chay: node dashboard/test_chat_slash.js
   KHONG can trinh duyet. */
const S = require("./chat-slash.js");

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

// ---- parseSlash ----
check("parse: /notes hello", (() => { const r = S.parseSlash("/notes hello"); return r && r.cmd === "notes" && r.arg === "hello"; })());
check("parse: /notes tron -> arg rong", (() => { const r = S.parseSlash("/notes"); return r && r.cmd === "notes" && r.arg === ""; })());
check("parse: chu HOA -> thuong", (() => { const r = S.parseSlash("/Notes X"); return r && r.cmd === "notes" && r.arg === "X"; })());
check("parse: dau / tron -> null", S.parseSlash("/") === null);
check("parse: khong phai lenh -> null", S.parseSlash("chao Javis") === null);
check("parse: khoang trang dau -> null", S.parseSlash("  /notes") === null);
check("parse: arg nhieu dong giu nguyen", (() => { const r = S.parseSlash("/notes dong1\ndong2"); return r && r.arg === "dong1\ndong2"; })());

// ---- classify ----
check("classify: new = session", S.classify("new") === "session");
check("classify: stop = session", S.classify("stop") === "session");
check("classify: notes = skill", S.classify("notes") === "skill");

// ---- buildSkillInvocation (khop mau Telegram) ----
check("invoke: co arg", S.buildSkillInvocation("notes", "mua sua") ===
  "Hãy dùng skill `notes` với yêu cầu: mua sua. Nếu không có skill tên này thì cứ xử lý yêu cầu của tôi bình thường.");
check("invoke: khong arg", S.buildSkillInvocation("notes", "") ===
  "Hãy dùng skill `notes`. Nếu không có skill tên này thì cứ xử lý yêu cầu của tôi bình thường.");

// ---- route ----
check("route: passthrough", S.route("chao").type === "passthrough");
check("route: session new", (() => { const r = S.route("/new"); return r.type === "session" && r.cmd === "new"; })());
check("route: skill notes co message", (() => { const r = S.route("/notes x"); return r.type === "skill" && r.cmd === "notes" && r.message.indexOf("skill `notes`") !== -1 && r.message.indexOf("x") !== -1; })());

// ---- buildMenu + filterItems ----
const menu = S.buildMenu([
  { slug: "notes", name: "Notes", description: "Luu note" },
  { slug: "ingest-source", name: "Ingest Source", description: "Tieu hoa source" },
]);
check("menu: co lenh phien new", menu.some(i => i.kind === "session" && i.cmd === "new"));
check("menu: co skill notes", menu.some(i => i.kind === "skill" && i.cmd === "notes"));
check("filter: 'no' ra notes", (() => { const r = S.filterItems(menu, "no"); return r.length >= 1 && r[0].cmd === "notes"; })());
check("filter: 'ingest' ra ingest-source", (() => { const r = S.filterItems(menu, "ingest"); return r.some(i => i.cmd === "ingest-source"); })());
check("filter: rong tra ve tat ca", S.filterItems(menu, "").length === menu.length);

if (fails.length) { console.log("\nFAIL - test_chat_slash: " + fails.length + " loi"); process.exit(1); }
console.log("\nOK - test_chat_slash: tat ca pass");
