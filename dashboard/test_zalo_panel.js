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
const rosterBlock = src.slice(src.indexOf("box.innerHTML = list.map"),
                              src.indexOf("box.querySelectorAll(\".zl-th\")"));
check("tim thay doan ve danh sach cuoc chat", rosterBlock.length > 0);
check("roster: ten cuoc chat duoc boc esc() (ten do nguoi la dat)",
  rosterBlock.indexOf("esc(t.name") !== -1);
check("roster: id cuoc chat trong value= duoc boc esc()",
  rosterBlock.indexOf('esc(t.id)') !== -1);
check("roster: KHONG chen thang bien nao vao HTML ma quen esc",
  !/\$\{[^}]*\}/.test(rosterBlock) && rosterBlock.indexOf("+ t.name") === -1
  && rosterBlock.indexOf("+ t.id") === -1);

// ---- 3. Dong dau hieu: phai phan biet duoc "chua ai nhan" voi "dang hong" ----
check("dau hieu: co nhanh da noi nhung chua nhan tin nao",
  src.indexOf("Da noi, chua nhan tin nao") !== -1 || src.indexOf("chưa nhận tin nào") !== -1);
check("dau hieu: co hien moc thoi gian tin gan nhat",
  src.indexOf("Tin gần nhất nhận lúc") !== -1);

// ---- 4. Panel khong con o dm_only (da doi sang whitelist cuoc chat) ----
check("panel: da bo o 'chi tin rieng' (whitelist thay the)", src.indexOf("zlDm") === -1);
check("panel: co noi ro chua chon thi khong bao gi",
  src.indexOf("chưa chọn cái nào thì không báo gì") !== -1);

console.log();
if (fails.length) { console.log("THAT BAI " + fails.length + ": " + fails.join(", ")); process.exit(1); }
console.log("OK - test_zalo_panel: tat ca pass");
