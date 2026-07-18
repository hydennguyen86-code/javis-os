/* Test autolink URL tran trong mdToHtml. Chay tay / CI:
       node dashboard/test_chat_render.js
   KHONG can trinh duyet: chi test ham thuan mdToHtml(). */
const { mdToHtml } = require("./chat-render.js");

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}
function has(h, s) { return h.indexOf(s) !== -1; }

// ---- 1. URL tran -> link mo tab moi ----
let h = mdToHtml("Xem https://example.com nhe");
check("url tran: thanh the a", has(h, '<a href="https://example.com"'));
check("url tran: mo tab moi", has(h, 'target="_blank"') && has(h, 'rel="noopener"'));
check("url tran: chu link dung URL", has(h, ">https://example.com</a>"));

// ---- 2. Dau cau duoi URL nam NGOAI link ----
h = mdToHtml("Trang chu: https://example.com.");
check("dau cau: href khong dinh dau cham", has(h, '<a href="https://example.com"'));
check("dau cau: dau cham o ngoai the a", has(h, "</a>."));

// ---- 3. Link markdown van chay, KHONG bi linkify 2 lan ----
h = mdToHtml("[Google](https://google.com)");
check("md link: giu chu hien thi", has(h, ">Google</a>"));
check("md link: khong lo URL tho ra ngoai", !has(h, ">https://google.com</a>"));
check("md link: chi 1 the a", (h.match(/<a /g) || []).length === 1);

// ---- 4. URL trong inline code KHONG bi linkify ----
h = mdToHtml("Chay `curl https://api.example.com` di");
check("inline code: URL nam trong <code>", has(h, "<code>") && has(h, "https://api.example.com"));
check("inline code: KHONG tao the a", !has(h, "<a "));

// ---- 5. URL trong code fence KHONG bi linkify ----
h = mdToHtml("```\nfetch('https://api.example.com')\n```");
check("code fence: KHONG tao the a", !has(h, "<a "));

// ---- 6. Hai URL trong 1 doan -> ca hai thanh link ----
h = mdToHtml("A https://one.com va https://two.com");
check("hai url: ca hai thanh link", (h.match(/<a /g) || []).length === 2);
check("hai url: co one.com", has(h, 'href="https://one.com"'));
check("hai url: co two.com", has(h, 'href="https://two.com"'));

// ---- 7. http (khong s) cung nhan ----
h = mdToHtml("Cu http://localhost:8000 nhe");
check("http: thanh link", has(h, '<a href="http://localhost:8000"'));

// ---- 8. Khong co URL -> khong sinh the a ----
h = mdToHtml("Chi la van ban binh thuong.");
check("khong url: khong co the a", !has(h, "<a "));

// ---- 9. Link file vault CO KHOANG TRANG + NGOAC (nhu Javis gui that) ----
h = mdToHtml("[Cach Toi Lam Viec.md](06 - Sources/Cach Toi Lam Viec (Tu Duy Nguoc).md)");
check("path co space+ngoac: bat DUNG ca duong dan",
  has(h, 'data-vault-path="06 - Sources/Cach Toi Lam Viec (Tu Duy Nguoc).md"'));
check("path co space+ngoac: khong ro duoi .md) ra text", !has(h, ".md)</p>") && !has(h, ">.md)"));

// ---- 10. Path co khoang trang (khong ngoac) ----
h = mdToHtml("[ghi chu](06 - Sources/ghi chu.md)");
check("path co space: bat DUNG ca duong dan", has(h, 'data-vault-path="06 - Sources/ghi chu.md"'));

// ---- 11. Title markdown ("...") van bi cat khoi href URL ngoai ----
h = mdToHtml('[Trang](https://x.com "Tieu de")');
check("title md: href sach khong dinh title", has(h, 'href="https://x.com"'));
check("title md: khong lot chu Tieu de vao href", !has(h, 'Tieu de"'));

// ---- 12. Hai link vault tren 1 dong khong nuot lan nhau ----
h = mdToHtml("[a](thu muc/a.md) va [b](thu muc/b.md)");
check("hai link vault: dung 2 link", (h.match(/jv-floc/g) || []).length === 2);
check("hai link vault: path a dung", has(h, 'data-vault-path="thu muc/a.md"'));
check("hai link vault: path b dung", has(h, 'data-vault-path="thu muc/b.md"'));

if (fails.length) {
  console.log("\nFAIL - " + fails.length + " test: " + fails.join(", "));
  process.exit(1);
}
console.log("\nOK - test_chat_render: tat ca pass");
