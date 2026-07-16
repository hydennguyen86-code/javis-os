// ============================================
// JAVIS OS - Graph 2D "Tinh vân bộ não" (force-graph / d3-force, kiểu Obsidian)
// Engine d3-force (giống Obsidian + bản 3D). Thiết kế: node = sao phát sáng, TÔ MÀU THEO DANH MỤC
// (thư mục cha, khớp nhãn PERSONAL/BUSINESS...), hover = rọi đèn vùng liên quan (synapse), thở nhẹ
// lúc nghỉ, nhãn chỉ hiện khi hover / zoom sát / vài hub lớn. Cùng interface JavisGraph3D.
// ============================================

// --- Bảng màu danh mục: rực nhưng hài hoà trên nền tối; gán theo tên danh mục (ổn định) ---
const CAT_COLORS = ["#8b93ff", "#3fdc9a", "#f0a24a", "#ff7a9c", "#4aa8ff", "#b98cff",
  "#f0c853", "#5ad1c4", "#e07ad1", "#7ed957", "#ff9f6b", "#9fb0cf"];

function _catOf(node) {
  const segs = (node.path || "").split("/");
  let cat = segs.length >= 2 ? segs[segs.length - 2] : "root";
  cat = cat.replace(/^\d+\s*[-_.]\s*/, "").trim().toLowerCase();   // bỏ tiền tố "07 - "
  return cat || "root";
}
function _hash(s) { let h = 0; s = String(s || ""); for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }

// Dùng CHUNG cho bản 3D: gán màu danh mục (tuần tự theo danh mục) vào n.color của từng node.
// Cùng thứ tự data.nodes như 2D → màu 2D và 3D khớp nhau.
window.JavisCatColorize = function (nodes) {
  const map = {}; let next = 0;
  (nodes || []).forEach(n => {
    const segs = (n.path || "").split("/");
    let cat = (segs.length >= 2 ? segs[segs.length - 2] : "root").replace(/^\d+\s*[-_.]\s*/, "").trim().toLowerCase() || "root";
    if (!(cat in map)) { map[cat] = CAT_COLORS[next % CAT_COLORS.length]; next++; }
    n.color = map[cat];   // ghi đè màu tím backend bằng màu danh mục
  });
  window.__javisCatMap = map;   // để nhãn danh mục tô chữ khớp màu (bản 3D)
  return map;
};

// --- Sprite quầng sáng (cache theo màu) → vẽ bằng drawImage (rẻ), tạo hiệu ứng tinh vân ---
const _glowCache = {};
function _hexA(hex, a) {
  const m = String(hex || "#9d7aff").replace("#", "");
  const r = parseInt(m.substring(0, 2), 16), g = parseInt(m.substring(2, 4), 16), b = parseInt(m.substring(4, 6), 16);
  return `rgba(${r || 157},${g || 122},${b || 255},${a})`;
}
function _glowSprite(color) {
  if (_glowCache[color]) return _glowCache[color];
  const s = 64, cv = document.createElement("canvas"); cv.width = cv.height = s;
  const ctx = cv.getContext("2d");
  const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
  g.addColorStop(0, "rgba(255,255,255,0.95)");   // lõi trắng nóng
  g.addColorStop(0.28, _hexA(color, 0.9));
  g.addColorStop(0.6, _hexA(color, 0.32));
  g.addColorStop(1, _hexA(color, 0));            // viền tan vào nền
  ctx.fillStyle = g; ctx.fillRect(0, 0, s, s);
  _glowCache[color] = cv; return cv;
}

// Lực kéo mọi node về tâm (0,0) tỉ lệ khoảng cách → cả mạng co lại thành hình tròn ở giữa,
// node bị kéo ra sẽ tự trôi về. (d3 custom force: hàm(alpha) + initialize(nodes)).
function _centerGravity(strength) {
  let _nodes = [];
  const force = (alpha) => {
    const k = strength * alpha;
    for (let i = 0; i < _nodes.length; i++) { const n = _nodes[i]; n.vx -= n.x * k; n.vy -= n.y * k; }
  };
  force.initialize = (ns) => { _nodes = ns; };
  return force;
}

class JavisGraph {
  constructor(container, tooltip) {
    this.container = container;
    this.tooltip = tooltip;
    this.graph = null;
    this.level = 0;
    this._thinking = false;
    this._fitted = false;
    this._t0 = 0;
    this._hoverId = null;
    this._nbrs = new Set();
    this._catFilter = null;
    window.__javisGraph = this;
    try { window.dispatchEvent(new Event("javis-graph-created")); } catch (e) {}
  }

  _prep(nodes) {
    nodes = nodes || [];
    if (!this._catMap) { this._catMap = {}; this._catNext = 0; }
    const markHubs = nodes.length > 6;                          // chỉ đánh dấu hub khi nạp cả mạng
    const hubIds = markHubs
      ? new Set([...nodes].sort((a, b) => (b.links || 0) - (a.links || 0)).slice(0, 4).map(n => n.id))
      : null;
    nodes.forEach(n => {
      const cat = _catOf(n);
      // Gán màu TUẦN TỰ theo danh mục (mỗi danh mục một màu khác nhau) - không hash để tránh trùng.
      if (!(cat in this._catMap)) { this._catMap[cat] = CAT_COLORS[this._catNext % CAT_COLORS.length]; this._catNext++; }
      n.__cat = cat;
      n.__c = this._catMap[cat];
      n.__r = 3 + Math.sqrt(Math.min(55, n.links || 0)) * 1.9;   // chấm sáng vừa (glow tinh linh)
      n.__ph = (_hash(n.id) % 628) / 100;                       // pha thở lệch nhau
      if (markHubs) n.__hub = hubIds.has(n.id);
    });
  }

  async load(query = "source=all") {
    const res = await fetch(`/graph?${query}&orphans=1`);   // 2D hiện CẢ note cô đơn (như graph view Obsidian)
    const data = await res.json();
    this._catMap = null;                     // gán lại màu danh mục tươi cho mỗi lần nạp
    this._prep(data.nodes || []);
    window.__javisCatMap = this._catMap;     // để nhãn danh mục (app.js) tô chữ khớp màu node
    const links = (data.edges || []).map(e => ({ source: e.source, target: e.target }));

    if (!this.graph) {
      if (!window.ForceGraph) throw new Error("Thư viện đồ thị 2D chưa tải (kiểm tra mạng)");
      const self = this;
      this.graph = ForceGraph()(this.container)
        .backgroundColor("rgba(0,0,0,0)")
        .autoPauseRedraw(false)                             // vẽ liên tục → hover nhạy tức thì + thở mượt
        .nodeId("id")
        .nodeRelSize(1)
        .nodeVal(n => { const r = (n.__r || 4) + 5; return r * r; })   // vùng bắt hover rộng hơn hình (dễ trỏ)
        .warmupTicks(24)
        .cooldownTime(5000)
        .linkColor(l => {
          if (self._hoverId != null) {
            const s = (l.source && l.source.id) || l.source, t = (l.target && l.target.id) || l.target;
            return (s === self._hoverId || t === self._hoverId) ? "rgba(175,155,255,0.4)" : "rgba(140,140,200,0.02)";
          }
          return "rgba(150,140,220,0.07)";          // dây nối mờ hơn (đỡ đậm)
        })
        .linkWidth(l => {
          if (self._hoverId != null) {
            const s = (l.source && l.source.id) || l.source, t = (l.target && l.target.id) || l.target;
            if (s === self._hoverId || t === self._hoverId) return 1;   // hover cũng mảnh (trước 1.8)
          }
          return 0.4;                               // dây mảnh hơn
        })
        .nodeCanvasObjectMode(() => "replace")
        .nodeCanvasObject((n, ctx, scale) => self._drawNode(n, ctx, scale))
        .onNodeHover(n => {
          self._hoverId = n ? n.id : null;
          self._nbrs = new Set();
          if (n) {
            self.graph.graphData().links.forEach(l => {
              const s = (l.source && l.source.id) || l.source, t = (l.target && l.target.id) || l.target;
              if (s === n.id) self._nbrs.add(t); else if (t === n.id) self._nbrs.add(s);
            });
          }
          self.container.style.cursor = n ? "pointer" : "grab";
        })
        .onNodeClick(n => { if (window.onGraphNodeClick) window.onGraphNodeClick(n); })   // chỉ mở note, KHÔNG lia camera
        .onNodeDragEnd(n => { n.fx = null; n.fy = null; })                                // thả kéo → node tự trôi về
        .onBackgroundClick(() => { self._catFilter = null; })                            // KHÔNG recenter → bấm được node viền
        .minZoom(0.05).maxZoom(3)                                                         // min nâng lên = mức fit sau khi lắng
        .onEngineStop(() => {
          if (self._fitted) return;
          self._fitted = true;
          try {
            self.graph.zoomToFit(500, 70);                                               // canh cho MỌI node vừa khung
            // sau khi fit: chặn zoom-out nhỏ hơn mức "mọi node vừa khung"
            setTimeout(() => { try { self.graph.minZoom(Math.min(self.graph.zoom() * 0.95, 1.2)); } catch (e) {} }, 600);
          } catch (e) {}
        });

      // Lực đẩy vừa (node gần nhau, không văng) + hút MẠNH về tâm (co thành khối TRÒN, kéo node lẻ vào)
      // + link ngắn (cụm liên kết bám sát). Cân bằng để tròn co vào giữa như Obsidian mà chấm vẫn tách.
      try { this.graph.d3Force("charge").strength(-70); } catch (e) {}
      try { const lf = this.graph.d3Force("link"); if (lf) lf.distance(26); } catch (e) {}
      try { this.graph.d3Force("gravity", _centerGravity(0.1)); } catch (e) {}           // hút mạnh hơn → kéo cụm rời/xa vào gần
      this.resize();
    }

    this._fitted = false;
    this._t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
    try { this.graph.minZoom(0.05); } catch (e) {}   // mở lại giới hạn để lần fit mới không bị kẹp
    this.graph.graphData({ nodes: data.nodes, links });
    this.resize();
    return data;
  }

  _drawNode(n, ctx, scale) {
    if (n.x == null || n.y == null) return;
    const t = (typeof performance !== "undefined" ? performance.now() : Date.now());
    const ent = this._t0 ? Math.min(1, (t - this._t0) / 700) : 1;      // fade-in khi mở
    const hovering = this._hoverId != null;
    const isHover = n.id === this._hoverId;
    const isNbr = hovering && this._nbrs.has(n.id);
    const catDim = this._catFilter && n.__cat !== this._catFilter && !isHover && !isNbr;
    const dim = (hovering && !isHover && !isNbr) || catDim;
    const breathe = 1 + 0.05 * Math.sin(t / 650 + (n.__ph || 0));       // thở nhẹ, lệch pha
    const pulse = this._thinking ? (1 + (0.16 + 0.3 * this.level) * Math.sin(t / 220)) : (1 + 0.25 * this.level);
    let born = 1;
    if (n.__born) { const age = (t - n.__born) / 500; born = age < 1 ? age : 1; if (age >= 1) n.__born = 0; }  // nảy sinh
    const r = (n.__r || 5) * (isHover ? 1.35 : 1) * breathe * pulse * (0.4 + 0.6 * born);
    const alpha = (dim ? 0.14 : 1) * ent * (0.4 + 0.6 * born);

    // Quầng sáng
    ctx.globalAlpha = alpha;
    const spr = _glowSprite(n.__c || "#9d7aff");
    const gsz = r * 2.4;                       // quầng sáng tinh linh (to hơn) nhưng vẫn tách chấm
    ctx.drawImage(spr, n.x - gsz / 2, n.y - gsz / 2, gsz, gsz);
    // Lõi đặc
    ctx.globalAlpha = Math.min(1, alpha + 0.15);
    ctx.beginPath(); ctx.arc(n.x, n.y, r * 0.5, 0, Math.PI * 2);
    ctx.fillStyle = isHover ? "#ffffff" : (n.__c || "#b98cff");
    ctx.fill();
    ctx.globalAlpha = 1;

    // Nhãn: CHỈ note đang trỏ (như Obsidian). KHÔNG hiện-hết-khi-zoom (vừa loạn, vừa làm zoom khựng
    // do phải vẽ hàng trăm chữ mỗi frame).
    const showLabel = isHover;
    if (showLabel && n.label) {
      const la = (dim ? 0.16 : (isHover ? 1 : 0.85)) * ent;
      const fs = Math.max(9, 11 / scale);
      ctx.font = `${fs}px -apple-system, Segoe UI, sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      const ly = n.y + r + 2;
      ctx.globalAlpha = la;
      ctx.lineWidth = 3 / scale; ctx.strokeStyle = "rgba(4,6,12,0.85)";
      ctx.strokeText(n.label, n.x, ly);
      ctx.fillStyle = "rgba(233,235,246,0.96)";
      ctx.fillText(n.label, n.x, ly);
      ctx.globalAlpha = 1;
    }
  }

  resize() {
    if (!this.graph || !this.container) return;
    const p = this.container.parentElement;
    const w = this.container.clientWidth || (p ? p.clientWidth : 800);
    const h = this.container.clientHeight || (p ? p.clientHeight : 600);
    if (w && h) this.graph.width(w).height(h);
  }

  // --- Interface khớp JavisGraph3D ---
  pause() { if (this.graph) { try { this.graph.pauseAnimation(); } catch (e) {} } }
  wake() { if (this.graph) { try { this.graph.resumeAnimation(); } catch (e) {} } }
  resume() { this.wake(); }
  setThinking(active) { this._thinking = !!active; }
  setLevel(l) { this.level = l || 0; }

  // Rọi sáng một danh mục (bấm nhãn PERSONAL/SALES... quanh não). null = bỏ lọc.
  spotlightCategory(cat) {
    this._catFilter = cat ? String(cat).replace(/^\d+\s*[-_.]\s*/, "").trim().toLowerCase() : null;
    return this._catFilter;
  }

  nodeStats() {
    const d = this.graph ? this.graph.graphData() : { nodes: [], links: [] };
    return { nodes: d.nodes.length, links: d.links.length };
  }

  addOrUpdate(node, linkTargets, isNew) {
    if (!this.graph || !node || !node.id) return { created: false };
    const d = this.graph.graphData();
    let n = d.nodes.find(x => x.id === node.id);
    if (!n) {
      n = { ...node };
      this._prep([n]);
      n.__born = (typeof performance !== "undefined" ? performance.now() : Date.now());   // hiệu ứng nảy sinh
      d.nodes.push(n);
    } else {
      Object.assign(n, { label: node.label, path: node.path, links: node.links, color: node.color });
      this._prep([n]);
    }
    (linkTargets || []).forEach(tid => {
      const dup = d.links.some(l => {
        const s = (l.source && l.source.id) || l.source, t = (l.target && l.target.id) || l.target;
        return (s === node.id && t === tid) || (s === tid && t === node.id);
      });
      if (!dup) d.links.push({ source: node.id, target: tid });
    });
    this.graph.graphData({ nodes: d.nodes, links: d.links });
    return { created: !!isNew };
  }
}

window.JavisGraph = JavisGraph;
