/* Test panel "Nghe tin lien tuc" (Zalo) trong console.js. Chay tay / CI:
       node dashboard/test_zalo_panel.js

   console.js la mot IIFE lon nen khong require() duoc. Test nay lam 2 viec:
   (1) trich chinh ham esc() ra chay THAT de chac no escape du,
   (2) chot nguon: cho ve danh sach cuoc chat PHAI boc esc() quanh du lieu tu Zalo.

   Vi sao dang test: ten hien thi tren Zalo do NGUOI LA tu dat va duoc chen thang
   vao innerHTML cua dashboard. Mat esc() la ho XSS ngay tren may chu cua chu. */
const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "console.js"), "utf8");

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

// ---- 1. Ham esc() that su escape ----
// Lay TRON DONG: cat theo dau ';' se dut ngay giua chuoi "&amp;".
const escLine = src.split("\n").find(l => l.trim().startsWith("const esc = (s) =>"));
check("trich duoc ham esc() tu console.js", !!escLine);
const esc = escLine
  ? eval("(" + escLine.trim().replace(/^const esc = /, "").replace(/;\s*$/, "") + ")")
  : (x) => x;

check("esc: the script bi vo hieu",
  esc('<script>alert(1)</script>').indexOf("<script") === -1);
check("esc: img onerror bi vo hieu",
  esc('<img src=x onerror=alert(1)>').indexOf("<img") === -1);
check("esc: dau nhay kep bi escape (khong pha duoc thuoc tinh value=\"...\")",
  esc('" onmouseover="alert(1)').indexOf('"') === -1);
check("esc: dau nhay don bi escape", esc("' onfocus='x").indexOf("'") === -1);
check("esc: dau & escape truoc, khong tao entity kep",
  esc("&lt;script&gt;") === "&amp;lt;script&amp;gt;");
check("esc: chu tieng Viet co dau giu nguyen", esc("Khach hang Ha Loc gia") === "Khach hang Ha Loc gia");

// ---- 2. Chot nguon: cho ve roster phai boc esc() ----
// Phan ve mot dong roster nam trong ham row(). Neu doi ten/cau truc thi test nay phai
// duoc tro lai dung cho - dung xoa, vi day la rao XSS duy nhat cho du lieu tu Zalo.
const rosterStart = src.indexOf("const row = (t) =>");
const rosterBlock = src.slice(rosterStart, src.indexOf("const paintRoster"));
check("tim thay ham ve mot dong cuoc chat (row)", rosterStart !== -1 && rosterBlock.length > 0);
check("roster: ten cuoc chat duoc boc esc() (ten do nguoi la dat)",
  rosterBlock.indexOf("esc(t.name") !== -1);
check("roster: id cuoc chat trong value= duoc boc esc()",
  rosterBlock.indexOf('esc(t.id)') !== -1);
check("roster: KHONG chen thang bien nao vao HTML ma quen esc",
  !/\$\{[^}]*\}/.test(rosterBlock) && rosterBlock.indexOf("+ t.name") === -1
  && rosterBlock.indexOf("+ t.id") === -1);

// ---- 2b. Chong tai phat bug "o cuoc chat trong tron" ----
// Bug that (0.9.119): rosterKey khoi tao bang "" ma danh sach rong cung cho key "",
// nen lan ve DAU TIEN bi chan boi guard va dong huong dan khong bao gio hien ra -
// nguoi dung nhin thay mot o trong tron, khong biet phai lam gi.
check("guard: rosterKey khoi tao bang null, KHONG phai chuoi rong",
  /rosterKey = null/.test(src) && !/rosterKey = ""/.test(src));
check("guard: khoa ve lai co gom trang thai bat/tat (chi dan hai truong hop khac nhau)",
  /const key = \(st\.enabled \? "on" : "off"\)/.test(src));
check("o rong: co chi dan cho truong hop DANG TAT (bao bam Bat nghe)",
  src.indexOf("Danh sách này chỉ có khi đang nghe") !== -1);
check("o rong: co chi dan cho truong hop DANG NGHE (bao nho ai do nhan thu)",
  src.indexOf("Đang nghe nhưng chưa ai nhắn") !== -1);

// ---- 2c. Bat roi ma tien trinh khong chay: phai noi dung ten van de ----
// Trieu chung that tren VPS: nut hien "Tat" va o danh sach noi "Dang nghe" (enabled=true)
// nhung nhan trang thai lai la "Dang tat" (state=off). Hien "Dang tat" luc do la noi doi.
check("mau thuan: co nhan rieng cho truong hop da bat ma tien trinh chua chay",
  src.indexOf("Đã bật nhưng tiến trình chưa chạy") !== -1);
check("mau thuan: co bien stuck phat hien enabled=true nhung state=off",
  /const stuck = st\.enabled && st\.state === "off"/.test(src));
check("chan doan: co vung hien log tho cua sidecar", src.indexOf('id="zlLog"') !== -1);
check("chan doan: log chi hien khi dang truc trac, khong lam roi luc chay ngon",
  /const bad = st\.enabled && \(st\.error \|\|/.test(src));

// ---- 2d. Danh sach cuoc chat phai chiu duoc HANG TRAM nhom ----
check("danh sach: co o tim kiem", src.indexOf('id="zlSearch"') !== -1);
check("danh sach: chi hien san mot so it, con lai bam xem them",
  /const ZL_SHOW = \d+/.test(src) && src.indexOf("Xem thêm") !== -1);
check("danh sach: cai DA CHON luon ghim len dau va khong bi cat",
  src.indexOf("list.filter(t => modes[t.id])") !== -1);
check("danh sach: tim kiem chi loc phan CHUA chon (da chon van phai bo tick duoc)",
  /rest = rest\.filter\(t => \(t\.name \|\| t\.id\)\.toLowerCase\(\)\.includes\(q\)\)/.test(src));
check("danh sach: khoa ve lai gom ca tu khoa tim va co xem-them, khong thi thao tac bi guard chan",
  /const key = \(st\.enabled \? "on" : "off"\) \+ "\|" \+ \(showAll \? "all" : "top"\) \+ "\|" \+ q/.test(src));
check("danh sach: tim khong ra thi noi ro, khong de o trong", src.indexOf("Không có cuộc chat nào khớp") !== -1);

// ---- 3. Dong dau hieu: phai phan biet duoc "chua ai nhan" voi "dang hong" ----
check("dau hieu: co nhanh da noi nhung chua nhan tin nao",
  src.indexOf("Da noi, chua nhan tin nao") !== -1 || src.indexOf("chưa nhận tin nào") !== -1);
check("dau hieu: co hien moc thoi gian tin gan nhat",
  src.indexOf("Tin gần nhất nhận lúc") !== -1);

// ---- 4. Panel khong con o dm_only (da doi sang whitelist cuoc chat) ----
check("panel: da bo o 'chi tin rieng' (whitelist thay the)", src.indexOf("zlDm") === -1);

// ---- Thiet ke 2 trang thai cua chu: Chi doc / Tu phan hoi ----
check("2 trang thai: co dropdown dung 2 lua chon",
  /ZL_MODES = \[\["chi-doc", "Chỉ đọc"\], \["tu-phan-hoi", "Tự phản hồi"\]\]/.test(src));
check("2 trang thai: bat tu phan hoi PHAI xac nhan (tin gui di khong thu hoi duoc)",
  src.indexOf("Cho Javis TỰ NHẮN vào cuộc chat này?") !== -1);
check("2 trang thai: gui len server theo khuon modes (moi cuoc chat mot trang thai)",
  src.indexOf("modes: modes") !== -1);
check("2 trang thai: doc nguoc tu luat - chatbot la tu phan hoi",
  src.indexOf('x.mode === "chatbot" ? "tu-phan-hoi" : "chi-doc"') !== -1);
check("2 trang thai: chua chon thi dropdown bi khoa, khong bam nham",
  src.indexOf('(on ? "" : " disabled")') !== -1);
check("2 trang thai: khoa ve lai gom ca MODE, khong thi doi trang thai khong hien ra",
  src.indexOf('x.thread_id + ":" + x.mode') !== -1);
check("panel: co noi ro chua chon thi khong bao gi",
  src.indexOf("chưa chọn cái nào thì không báo gì") !== -1);

console.log();
if (fails.length) { console.log("THAT BAI " + fails.length + ": " + fails.join(", ")); process.exit(1); }
console.log("OK - test_zalo_panel: tat ca pass");
