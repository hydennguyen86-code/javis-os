#!/usr/bin/env node
/*
 * webcake-build.js  (v2 - layout engine)
 * Sinh page_source Webcake từ "spec" rồi xuất .pke. Webcake = canvas TUYỆT ĐỐI (mobile 420 / desktop 960).
 *
 *   node webcake-build.js spec.json out.pke
 *
 * Bố cục: mọi phần tử được đặt tuyệt đối trong section (flat children). "Nhiều cột" = đặt left khác nhau
 * cùng top (desktop), còn mobile thì xếp dọc. Card/badge/window dùng <rectangle> làm nền + text đè lên.
 *
 * KIND hỗ trợ:
 *   heading | text | image | button | form | spacer
 *   badge                              -> viên thuốc (rectangle bo tròn + chữ)
 *   card   {icon,title,text,bg,radius} -> hộp nền bo góc + tiêu đề + mô tả
 *   window {title, lines[], align}     -> khung cửa sổ (thanh nút + các dòng chat)
 *   row    {gap, cols:[{w, items:[...]}]}  -> hàng nhiều cột (desktop cạnh nhau, mobile xếp dọc)
 *   cardsRow {gap, cards:[{icon,title,text,bg}]} -> đường tắt: 1 hàng gồm các card
 */
'use strict';
const fs = require('fs');
const { encodeMsgpack } = require('./webcake-pke.js');

const DESK_W = 960, MOB_W = 420;
const PADX_D = 40, PADX_M = 16;
const ID = 'abcdefghijklmnopqrstuvwxyz0123456789';
function id(){ let s=''; for(let i=0;i<8;i++) s+=ID[Math.floor(Math.random()*ID.length)]; return s; }

function measureText(html, fontSize, boxW){
  const plain = String(html==null?'':html).replace(/<br\s*\/?>/gi,'\n').replace(/<[^>]+>/g,'');
  const breaks = (String(html==null?'':html).match(/<br\s*\/?>/gi)||[]).length;
  const cpl = Math.max(6, Math.floor(boxW / (fontSize*0.56)));
  let lines = breaks + 1;
  for (const seg of plain.split('\n')) lines += Math.max(0, Math.ceil((seg.trim().length||1) / cpl) - 1);
  return Math.ceil(lines * fontSize * 1.5) + 6;
}
const anim = (name)=>({ repeat:null, name:name||'fadeInUp', duration:1, delay:0 });

/* ---- node factories ---- */
function textNode(html, o, xD,yD,wD, xM,yM,wM){
  const sizeD = o.sizeD, sizeM = o.sizeM;
  const st = (x,y,w,size)=>({
    width:w, top:Math.round(y), textAlign:o.align||'center', left:Math.round(x), height:0,
    fontWeight:o.bold?'bold':'normal', fontSize:String(size), color:o.color||'rgba(232,234,246,1)',
    borderWidth:0, borderStyle:'solid', borderColor:'rgba(229, 231, 235, 1)'
  });
  const hD = measureText(html,sizeD,wD), hM = measureText(html,sizeM,wM);
  return { node:{
    type:'text-block', specials:{ text:String(html==null?'':html), tag:o.tag||'p' }, runtime:{},
    responsive:{
      mobile:{ styles:st(xM,yM,wM,sizeM), config:{ virtualHeight:hM, notloaded:false, animation:anim() } },
      desktop:{ styles:st(xD,yD,wD,sizeD), config:{ virtualHeight:hD, notloaded:false, animation:anim() } }
    },
    properties:{ sync:true, name:o.name||'text', movable:true }, id:id(), events:[]
  }, hD, hM };
}
function rectNode(bg, o, xD,yD,wD,hD, xM,yM,wM,hM){
  const st = (x,y,w,h)=>({
    width:w, top:Math.round(y), textShadow:'', left:Math.round(x), height:Math.round(h), fontSize:'16',
    filter:o.filter||'', boxShadow:o.boxShadow||'', borderWidth:o.borderWidth!=null?o.borderWidth:0,
    borderStyle:'solid', borderRadius:(o.radius!=null?o.radius:16)+'px',
    borderColor:o.borderColor||'rgba(139, 92, 246, 0.25)', background:bg
  });
  return {
    type:'rectangle', specials:{}, runtime:{},
    responsive:{
      mobile:{ styles:st(xM,yM,wM,hM), config:{ notloaded:false, hiddenEffect:{}, bgHidden:{}, animation:anim('none') } },
      desktop:{ styles:st(xD,yD,wD,hD), config:{ notloaded:false, hiddenEffect:{}, bgHidden:{}, animation:anim('none') } }
    },
    properties:{ sync:true, name:o.name||'rectangle', movable:true }, id:id(), events:[]
  };
}
function imageNode(src, xD,yD,wD,hD, xM,yM,wM,hM){
  const bg = `center center/ cover no-repeat  content-box url(${src}) border-box`;
  const st = (x,y,w,h)=>({ zIndex:null, width:w, top:Math.round(y), textShadow:'', position:'absolute',
    left:Math.round(x), height:Math.round(h), filter:'', boxShadow:'', borderWidth:0, borderStyle:'solid',
    borderColor:'rgba(255, 255, 255, 1)', background:bg });
  const cfg = (w,h)=>({ widthBgImage:w, topBgImage:0, notloaded:false, leftBgImage:0, hiddenEffect:{},
    heightBgImage:h, borderColorHidden:{}, bgHidden:{}, animation:anim() });
  return { type:'image-block', specials:{ src, imageCompression:true, compressible:true }, runtime:{ checkedBlurImage:false },
    responsive:{ mobile:{ styles:st(xM,yM,wM,hM), config:cfg(wM,hM) }, desktop:{ styles:st(xD,yD,wD,hD), config:cfg(wD,hD) } },
    properties:{ sync:true, name:'image-block', movable:true }, id:id(), events:[] };
}
function buttonNode(el, xD,yD,wD,hD, xM,yM,wM,hM){
  const bg = el.bg || 'linear-gradient(135deg, rgba(139,92,246,1) 0%, rgba(109,40,217,1) 100%)';
  const events = el.href ? [{ type:'click', target:el.href, id:id(), hoverColor:'', appTarget:'', action:'link' }]
              : (el.scrollTo ? [{ type:'click', target:el.scrollTo, id:id(), hoverColor:'', appTarget:'', action:'scroll_to' }] : []);
  const st = (x,y,w,h,size)=>({ width:w, top:Math.round(y), left:Math.round(x), height:Math.round(h),
    fontWeight:'bold', fontSize:String(size), color:el.color||'rgba(255,255,255,1)',
    boxShadow:'0px 4px 18px rgba(139,92,246,0.35)', borderWidth:el.borderWidth!=null?el.borderWidth:0,
    borderStyle:'solid', borderRadius:(el.radius!=null?el.radius:12)+'px',
    borderColor:el.borderColor||'rgba(139,92,246,1)', background:bg });
  return { type:'button', specials:{ text:String(el.text||'BUTTON') }, runtime:{},
    responsive:{ mobile:{ styles:st(xM,yM,wM,hM,el.sizeMobile||15), config:{ notloaded:false, bgHidden:{}, animation:anim('flipInX') } },
                 desktop:{ styles:st(xD,yD,wD,hD,el.size||16), config:{ notloaded:false, bgHidden:{}, animation:anim('flipInX') } } },
    properties:{ sync:true, name:'button', movable:true }, id:id(), events };
}

/* ---- emit: đặt 1 item, trả {hD,hM}, đẩy node vào out ---- */
function emit(it, xD,yD,wD, xM,yM,wM, out){
  const k = (it.kind||'').toLowerCase();

  if (k==='row' || k==='cardsrow'){
    let cols;
    if (k==='cardsrow') cols = (it.cards||[]).map(c=>({ items:[{...c, kind:'card'}] }));
    else cols = it.cols || [];
    const n = cols.length || 1;
    const gapD = it.gap!=null?it.gap:22, gapM = Math.round((it.gap!=null?it.gap:22)*0.7);
    const availD = wD - gapD*(n-1);
    let cxD = xD, curYM = yM, maxHD = 0;
    for (let i=0;i<n;i++){
      const col = cols[i];
      const cwD = Math.round(availD*(col.w || 1/n));
      const r = stack(col.items||[], col.gap!=null?col.gap:12, cxD, yD, cwD, xM, curYM, wM, out);
      maxHD = Math.max(maxHD, r.hD);
      cxD += cwD + gapD;
      curYM += r.hM + gapM;
    }
    return { hD:maxHD, hM: curYM - yM - gapM };
  }

  if (k==='heading' || k==='text'){
    const isH = k==='heading';
    const sizeD = it.size || (isH?28:16);
    const sizeM = it.sizeMobile || Math.max(13, Math.round(sizeD*0.84));
    const r = textNode(it.text!=null?it.text:it.html, {
      sizeD, sizeM, align:it.align||'center', bold: it.bold!=null?it.bold:isH,
      color: it.color||(isH?'rgba(232,234,246,1)':'rgba(154,160,181,1)'), tag: it.tag||(isH?'h2':'p'),
      name: isH?'heading':'text'
    }, xD,yD,wD, xM,yM,wM);
    out.push(r.node); return { hD:r.hD, hM:r.hM };
  }

  if (k==='image'){
    const ratio = it.ratio || 1.4, frac = it.width || 1;
    const iwD = Math.round(wD*frac), iwM = Math.round(wM*frac);
    const ihD = Math.round(iwD/ratio), ihM = Math.round(iwM/ratio);
    out.push(imageNode(it.src, xD+(wD-iwD)/2,yD,iwD,ihD, xM+(wM-iwM)/2,yM,iwM,ihM));
    return { hD:ihD, hM:ihM };
  }

  if (k==='button'){
    const bwD = it.width? Math.round(wD*it.width) : wD;
    const bwM = it.widthMobile? Math.round(wM*it.widthMobile) : wM;
    const hD = it.height||56, hM = it.heightMobile||52;
    out.push(buttonNode(it, xD+(wD-bwD)/2,yD,bwD,hD, xM+(wM-bwM)/2,yM,bwM,hM));
    return { hD, hM };
  }

  if (k==='badge'){
    const sizeD = it.size||13, sizeM = Math.max(11,Math.round(sizeD*0.9));
    const txt = String(it.text||'');
    const padx = 20, ph = 16;
    const bwD = Math.min(wD, Math.round(txt.length*sizeD*0.62)+padx*2);
    const bwM = Math.min(wM, Math.round(txt.length*sizeM*0.62)+padx*2);
    const hD = sizeD+ph*2, hM = sizeM+ph*2;
    const align = it.align||'center';
    const bxD = align==='left'? xD : xD+(wD-bwD)/2;
    const bxM = align==='left'? xM : xM+(wM-bwM)/2;
    out.push(rectNode(it.bg||'rgba(16,18,43,0.7)', { radius:99, borderWidth:1, borderColor:it.borderColor||'rgba(139,92,246,0.35)', name:'badge-bg' },
      bxD,yD,bwD,hD, bxM,yM,bwM,hM));
    const t = textNode(txt, { sizeD, sizeM, align:'center', bold:true, color:it.color||'rgba(200,205,225,1)', name:'badge' },
      bxD, yD+ph-2, bwD, bxM, yM+ph-2, bwM);
    out.push(t.node);
    return { hD, hM };
  }

  if (k==='card'){
    const pad = 24, gap = 8;
    const bg = it.bg || 'rgba(16,18,43,1)';
    const innerD = wD-pad*2, innerM = wM-pad*2;
    const title = it.icon? (it.icon+'  '+(it.title||'')) : (it.title||'');
    const tSizeD = it.titleSize||19, tSizeM = Math.max(15,Math.round(tSizeD*0.9));
    const bSizeD = it.textSize||14.5, bSizeM = Math.max(13,Math.round(bSizeD*0.92));
    const thD = title? measureText(title,tSizeD,innerD):0, thM = title? measureText(title,tSizeM,innerM):0;
    const bhD = it.text? measureText(it.text,bSizeD,innerD):0, bhM = it.text? measureText(it.text,bSizeM,innerM):0;
    const cHD = pad + thD + (title&&it.text?gap:0) + bhD + pad;
    const cHM = pad + thM + (title&&it.text?gap:0) + bhM + pad;
    out.push(rectNode(bg, { radius:it.radius!=null?it.radius:16, name:'card-bg', boxShadow:it.boxShadow||'' },
      xD,yD,wD,cHD, xM,yM,wM,cHM));
    let yTD = yD+pad, yTM = yM+pad;
    if (title){
      const t = textNode(title, { sizeD:tSizeD, sizeM:tSizeM, align:it.align||'left', bold:true,
        color:it.titleColor||'rgba(232,234,246,1)', name:'card-title' }, xD+pad,yTD,innerD, xM+pad,yTM,innerM);
      out.push(t.node); yTD += thD+gap; yTM += thM+gap;
    }
    if (it.text){
      const t = textNode(it.text, { sizeD:bSizeD, sizeM:bSizeM, align:it.align||'left', bold:false,
        color:it.textColor||'rgba(154,160,181,1)', name:'card-text' }, xD+pad,yTD,innerD, xM+pad,yTM,innerM);
      out.push(t.node);
    }
    return { hD:cHD, hM:cHM };
  }

  if (k==='window'){
    const pad = 18, barH = 40, lineGap = 10;
    const bg = it.bg || 'rgba(16,18,43,1)';
    const innerD = wD-pad*2, innerM = wM-pad*2;
    const lines = it.lines || [];
    const lSizeD = 14, lSizeM = 13;
    let bodyD = 0, bodyM = 0;
    const lh = lines.map(L=>{
      const hD = measureText(L.text,lSizeD,innerD*0.9), hM = measureText(L.text,lSizeM,innerM*0.9);
      bodyD += hD+lineGap; bodyM += hM+lineGap; return {hD,hM};
    });
    const cHD = barH + pad + bodyD + pad, cHM = barH + pad + bodyM + pad;
    out.push(rectNode(bg, { radius:16, borderColor:'rgba(139,92,246,0.25)', borderWidth:1, name:'window-bg',
      boxShadow:'0px 30px 80px rgba(0,0,0,0.5)' }, xD,yD,wD,cHD, xM,yM,wM,cHM));
    const bar = textNode(it.title||'Window', { sizeD:12.5, sizeM:12, align:'left', bold:false,
      color:'rgba(154,160,181,1)', name:'window-bar' }, xD+pad+30,yD+12,innerD-30, xM+pad+30,yM+12,innerM-30);
    out.push(bar.node);
    let yLD = yD+barH+pad, yLM = yM+barH+pad;
    lines.forEach((L,i)=>{
      const you = L.who==='you';
      const t = textNode(L.text, { sizeD:lSizeD, sizeM:lSizeM, align: you?'right':'left', bold:false,
        color: you?'rgba(255,255,255,1)':'rgba(200,205,225,1)', name:'window-line' },
        xD+pad,yLD,innerD, xM+pad,yLM,innerM);
      out.push(t.node); yLD += lh[i].hD+lineGap; yLM += lh[i].hM+lineGap;
    });
    return { hD:cHD, hM:cHM };
  }

  if (k==='spacer') return { hD: it.height||40, hM: it.heightMobile||it.height||40 };

  if (k==='form') return emitForm(it, xD,yD,wD, xM,yM,wM, out);

  throw new Error('kind lạ: '+it.kind);
}

function emitForm(el, xD,yD,wD, xM,yM,wM, out){
  const fields = el.fields || [
    {name:'full_name', placeholder:'Họ và tên', type:'text', required:true},
    {name:'phone_number', placeholder:'Số điện thoại', type:'phone', required:true}
  ];
  const fieldH=50, fieldGap=14, pad=16, btnH=60;
  const formId = id(); const children=[]; let y=pad;
  const innerWD=wD-1, innerWM=wM-1;
  for (const f of fields){
    const sp = { required:f.required!==false, parentCarousel:formId, field_placeholder:f.placeholder||f.name, field_name:f.name };
    if ((f.type||'').toLowerCase()==='email'){ sp.useInputPattern=true; sp.inputPattern='[^@\\s]+@[^@\\s]+\\.[^@\\s]+'; }
    if ((f.type||'').toLowerCase()==='phone'){ sp.validate=true; sp.phone_validator='^(\\+84|84|0)(3|5|7|8|9)([0-9]{8})$'; }
    const st=(w)=>({ width:w, top:y, left:0, height:fieldH, borderWidth:'1px', borderStyle:'solid',
      borderRadius:'6px', borderColor:'rgba(147, 147, 147, 1)', background:'#fff' });
    children.push({ type:'input', specials:sp, runtime:{},
      responsive:{ mobile:{styles:st(innerWM),config:{notloaded:false}}, desktop:{styles:st(innerWD),config:{notloaded:false}} },
      properties:{ sync:true, name:'Input', movable:true, field_default:true }, id:id() });
    y += fieldH+fieldGap;
  }
  const btnTop=y+6;
  const bst=(w)=>({ width:w, top:btnTop, left:0, height:btnH, fontWeight:'bold', fontSize:'18',
    color:'rgba(255,255,255,1)', boxShadow:'0px 4px 18px rgba(139,92,246,0.35)', borderWidth:0, borderStyle:'solid',
    borderRadius:'12px', borderColor:'rgba(229,231,235,1)',
    background: el.submitBg||'linear-gradient(135deg, rgba(139,92,246,1) 0%, rgba(109,40,217,1) 100%)' });
  children.push({ type:'button', specials:{ text:String(el.submitText||'GỬI NGAY'), parentCarousel:formId, submit:true }, runtime:{},
    responsive:{ mobile:{styles:bst(innerWM),config:{notloaded:false,bgHidden:{}}}, desktop:{styles:bst(innerWD),config:{notloaded:false,bgHidden:{}}} },
    properties:{ sync:true, name:'button', movable:true }, id:id() });
  const formH = btnTop+btnH+pad;
  const fst=(w,x,y)=>({ width:w, top:Math.round(y), left:Math.round(x), height:formH, fontSize:'18', borderWidth:'1px',
    borderStyle:'solid', borderRadius:'8px', borderColor:'rgba(147, 147, 147, 1)' });
  out.push({ type:'form',
    specials:{ submit_success:el.submit||2, redirect_url:el.redirect||'', multiFormParent:'', fb_event_type:'Lead', event_name_custom:'generate_lead' },
    runtime:{},
    responsive:{ mobile:{ styles:fst(wM,xM,yM), config:{notloaded:false,borderColorHidden:{}} },
                 desktop:{ styles:fst(wD,xD,yD), config:{notloaded:false,borderColorHidden:{}} } },
    properties:{ sync:true, name:'form', movable:true }, id:formId, children });
  return { hD:formH, hM:formH };
}

/* xếp dọc 1 danh sách item, trả {hD,hM} */
function stack(items, gap, xD,yD,wD, xM,yM,wM, out){
  const gapD = gap, gapM = Math.round(gap*0.7);
  let cyD=yD, cyM=yM, first=true;
  for (const it of items){
    if (!first){ cyD+=gapD; cyM+=gapM; } first=false;
    const r = emit(it, xD,cyD,wD, xM,cyM,wM, out);
    cyD += r.hD; cyM += r.hM;
  }
  return { hD: cyD-yD, hM: cyM-yM };
}

function buildSection(sec){
  const out = [];
  const padTopD = sec.padTop!=null?sec.padTop:56, padTopM = sec.padTopMobile!=null?sec.padTopMobile:Math.round(padTopD*0.72);
  const padBot  = sec.padBottom!=null?sec.padBottom:padTopD;
  const gap = sec.gap!=null?sec.gap:18;
  const cwD = DESK_W-PADX_D*2, cwM = MOB_W-PADX_M*2;
  const r = stack(sec.elements||[], gap, PADX_D,padTopD,cwD, PADX_M,padTopM,cwM, out);
  const heightD = Math.max(sec.minHeight||0, Math.round(padTopD + r.hD + padBot));
  const heightM = Math.max(sec.minHeightMobile||0, Math.round(padTopM + r.hM + padBot));
  const secStyle = (h)=>{ const s={ position:'relative', height:h }; if (sec.background) s.background=sec.background; if (sec.fontSize) s.fontSize=String(sec.fontSize); return s; };
  return { type:'section', specials:{ imageCompression:true }, runtime:{},
    responsive:{ mobile:{ styles:secStyle(heightM), config:{ notloaded:false, bgHidden:{} } },
                 desktop:{ styles:secStyle(heightD), config:{ notloaded:false, bgHidden:{} } } },
    properties:{ sync:true, name:sec.name||'section', movable:false }, id:id(), events:[], children:out };
}

function buildPageSource(spec){
  const settings = {
    width_section:{ mobile:MOB_W, desktop:DESK_W }, title: spec.title||spec.name||'Landing Page',
    tiktok_script:'', thumbnail: spec.thumbnail||'', send_info_to_thank_page:true, keywords: spec.keywords||'',
    global_track_ids:[], fontGeneral: spec.font || 'Montserrat', fb_tracking_code:'',
    favicon: spec.favicon||'', extra_script: spec.extraScript||'', extra_css: spec.extraCss||'', description: spec.description||'',
    country:'84', bhet: spec.beforeHead||'', bbet: spec.beforeBody||'', auto_save_info_user:true, auto_save_draft:true, auto_complete_form_in_popup:true, analytic_heatmap:true
  };
  return { settings, popup:[], page:(spec.sections||[]).map(buildSection), options:{ versionID:'', mobileOnly: !!spec.mobileOnly }, cartConfigs:{} };
}
function buildEnvelope(spec){ return { source:buildPageSource(spec), owner_id:spec.owner_id||'', name:spec.name||'Landing Page', engine:2, email:{}, data_set_id:[] }; }

module.exports = { buildPageSource, buildEnvelope };

if (require.main === module){
  const [,,specPath, outPath] = process.argv;
  if (!specPath){ console.log('Cách dùng: node webcake-build.js spec.json out.pke'); process.exit(1); }
  const spec = JSON.parse(fs.readFileSync(specPath,'utf8'));
  const env = buildEnvelope(spec);
  const out = outPath || specPath.replace(/\.json$/i,'')+'.pke';
  fs.writeFileSync(out, encodeMsgpack(env).toString('base64'));
  const nEl = (spec.sections||[]).reduce((a,s)=>a+(s.elements||[]).length,0);
  console.log('OK build ->', out, '| sections:', (spec.sections||[]).length, '| top-items:', nEl);
}
