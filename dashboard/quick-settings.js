/* quick-settings.js - công tắc BẬT/TẮT đọc trả lời bằng giọng (nhớ qua reload).
   Đồng bộ 3 chiều: nút loa header (#ttsToggle) ↔ công tắc sidebar (#qsTts) ↔ nút loa trên
   khung chat (#ttsToggleBar). Tách riêng để không đụng app.js. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function getVoice() { try { return (typeof voice !== "undefined") ? voice : null; } catch (e) { return null; } }
  function isOff() { return localStorage.getItem("javis.ttsEnabled") === "0"; }
  function persist(on) { try { localStorage.setItem("javis.ttsEnabled", on ? "1" : "0"); } catch (e) {} }

  // Cập nhật MỌI chỗ hiển thị trạng thái đọc-giọng (header + sidebar + nút trên khung chat).
  function reflect(on) {
    var qs = $("qsTts"); if (qs) qs.checked = on;
    var hdr = $("ttsToggle"); if (hdr) hdr.classList.toggle("muted", !on);
    var bar = $("ttsToggleBar");
    if (bar) { bar.classList.toggle("muted", !on); bar.title = on ? "Tắt giọng đọc" : "Bật giọng đọc"; }
  }
  function applyState(on) {
    persist(on);
    var v = getVoice();
    if (v) { v.ttsEnabled = on; if (!on && v.stopSpeaking) { try { v.stopSpeaking(); } catch (e) {} } }
    reflect(on);
  }

  function bind() {
    var on = !isOff();
    reflect(on);
    var v = getVoice(); if (v) v.ttsEnabled = on;

    var qs = $("qsTts"); if (qs) qs.addEventListener("change", function () { applyState(qs.checked); });

    // Nút loa trên khung chat: bấm là bật/tắt luôn (đi qua khung chat / màn 3D đều thấy).
    var bar = $("ttsToggleBar");
    if (bar) bar.addEventListener("click", function () { applyState(isOff()); });   // đang OFF → bật, đang ON → tắt

    // Nút loa header: app.js đã tự flip voice.ttsEnabled + class muted → ta chỉ đồng bộ lại + lưu.
    var hdr = $("ttsToggle");
    if (hdr) hdr.addEventListener("click", function () {
      setTimeout(function () {
        var nowOn = !hdr.classList.contains("muted");
        persist(nowOn); reflect(nowOn);
      }, 0);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
