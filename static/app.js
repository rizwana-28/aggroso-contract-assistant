const $ = (s) => document.querySelector(s);
const notice = (message, kind = "ok") => { const el=$("#notice"); el.textContent=message; el.className=`notice ${kind}`; window.scrollTo({top:0,behavior:"smooth"}); };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(url, options={}) {
  const res = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  const body = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
  return body;
}
async function load() {
  try {
    const [contracts, obligations] = await Promise.all([api("/api/contracts"), api("/api/obligations")]);
    $("#contractCount").textContent=contracts.length;
    $("#reviewCount").textContent=obligations.filter(o=>o.status==="Needs review").length;
    $("#approvedCount").textContent=obligations.filter(o=>o.status==="Approved").length;
    const filter=$("#filter").value;
    const visible=obligations.filter(o=>filter==="all"||o.status===filter);
    if(!visible.length){$("#obligationList").innerHTML='<div class="empty">Nothing matches this filter yet.</div>';return;}
    $("#obligationList").innerHTML=visible.map(o=>`
      <article class="ob-card" data-id="${o.id}">
        <div class="ob-top"><div class="ob-title">${esc(o.contract_title)} · ${esc(o.category)}</div><span class="tag ${o.status==="Approved"?"approved":o.status==="Rejected"?"rejected":"review"}">${esc(o.status)}</span></div>
        <div class="ob-meta">Counterparty: ${esc(o.counterparty||"Not specified")} · Suggestion confidence: ${Math.round(Number(o.confidence)*100)}% (estimate)</div>
        <label class="small-label">Obligation / reviewer correction</label>
        <textarea class="description" maxlength="280">${esc(o.description)}</textarea>
        <label class="small-label">Due date (optional)</label>
        <input class="due-date" type="date" value="${esc(o.due_date)}">
        <label class="small-label">Reviewer note</label>
        <input class="reviewer-note" maxlength="1000" value="${esc(o.reviewer_note)}" placeholder="Why you approved/rejected or what needs checking">
        <div class="ob-actions">
          <button class="save" data-action="Needs review">Save / needs review</button>
          <button class="approve" data-action="Approved">Approve</button>
          <button class="reject" data-action="Rejected">Reject</button>
        </div>
      </article>`).join("");
  } catch(e) { notice(e.message,"error"); }
}
$("#contractForm").addEventListener("submit", async e=>{
  e.preventDefault();
  const btn=$("#analyzeBtn"); btn.disabled=true; btn.textContent="Analyzing…";
  try {
    const result=await api("/api/contracts",{method:"POST",body:JSON.stringify({
      title:$("#title").value, counterparty:$("#counterparty").value, contract_text:$("#contractText").value
    })});
    $("#contractForm").reset();
    notice(`Contract saved. ${result.suggestions_created} review item(s) created. Verify every suggestion against the original document.`);
    await load();
  } catch(err) { notice(err.message,"error"); }
  finally {btn.disabled=false;btn.innerHTML='Analyze contract <span>→</span>';}
});
$("#obligationList").addEventListener("click", async e=>{
  const btn=e.target.closest("button[data-action]"); if(!btn)return;
  const card=btn.closest(".ob-card"); const id=card.dataset.id;
  btn.disabled=true;
  try {
    await api(`/api/obligations/${id}`,{method:"PATCH",body:JSON.stringify({
      status:btn.dataset.action, description:card.querySelector(".description").value,
      due_date:card.querySelector(".due-date").value,
      reviewer_note:card.querySelector(".reviewer-note").value
    })});
    notice("Review decision saved.");
    await load();
  } catch(err) {notice(err.message,"error");}
  finally {btn.disabled=false;}
});
$("#filter").addEventListener("change",load);
$("#refreshBtn").addEventListener("click",load);
load();
