import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:8000";

const C = {
  bg:"#07090F", surface:"rgba(255,255,255,0.03)", border:"rgba(255,255,255,0.07)",
  text:"#E2E8F0", muted:"#475569", dim:"#1E293B",
  green:"#6EE7B7", blue:"#93C5FD", purple:"#C4B5FD", yellow:"#FDE68A",
  red:"#FCA5A5", orange:"#FB923C", pink:"#F9A8D4",
};

const STAGE_COLOR = {
  ENGINE:"#6EE7B7",DOM:"#93C5FD",LLM:"#C4B5FD",INTENT:"#FDE68A",
  CONTEXT:"#A5F3FC",MEMORY:"#FCA5A5",VISION:"#F9A8D4",
  DRIVER:"#67E8F9",API:"#94A3B8",JOURNEY:"#34D399",BATCH:"#FB923C",
};
const stageColor = s => STAGE_COLOR[s?.toUpperCase()] ?? "#94A3B8";

const STEP_STATUS = {
  pending:{ icon:"○", color:C.muted },
  running:{ icon:"◌", color:C.yellow, pulse:true },
  pass:   { icon:"✓", color:C.green },
  healed: { icon:"⚡", color:C.purple },
  fail:   { icon:"✕", color:C.red },
};

const STATUS_COLOR = {
  queued:"#64748B",running:C.yellow,completed:C.green,
  passed:C.green,healed:C.purple,failed:C.red,error:C.red,
};

const short = s => !s?"—":s.length<=42?s:s.slice(0,18)+"…"+s.slice(-20);
const inp = (x={}) => ({background:"rgba(255,255,255,0.05)",border:`1px solid ${C.border}`,borderRadius:8,padding:"10px 14px",color:C.text,fontFamily:"'DM Mono',monospace",fontSize:13,outline:"none",width:"100%",...x});

function useApi(key){
  return useCallback(async(method,path,body)=>{
    const r=await fetch(`${API}${path}`,{method,headers:{"Content-Type":"application/json",...(key?{Authorization:`Bearer ${key}`}:{})},...( body?{body:JSON.stringify(body)}:{})});
    return r.json();
  },[key]);
}

function StepRow({step,state}){
  const s=state||{status:"pending"};
  const cfg=STEP_STATUS[s.status]||STEP_STATUS.pending;
  const healed=s.status==="healed";
  return(
    <div style={{display:"grid",gridTemplateColumns:"28px 1fr",gap:12,padding:"10px 16px",borderBottom:`1px solid ${C.border}`,background:s.status==="running"?"rgba(253,230,138,0.03)":"transparent",animation:s.status!=="pending"?"fadeIn 0.2s ease":"none"}}>
      <div style={{width:26,height:26,borderRadius:6,flexShrink:0,marginTop:1,background:`${cfg.color}18`,border:`1px solid ${cfg.color}44`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,color:cfg.color,fontWeight:700,animation:cfg.pulse?"pulse 1.4s ease infinite":"none"}}>{cfg.icon}</div>
      <div style={{display:"flex",flexDirection:"column",gap:4,minWidth:0}}>
        <div style={{display:"flex",alignItems:"center",gap:7,flexWrap:"wrap"}}>
          <span style={{fontSize:13,fontWeight:600,color:C.text}}>{step.description}</span>
          {step.critical&&<span style={{fontSize:9,color:C.orange,border:`1px solid ${C.orange}44`,borderRadius:4,padding:"1px 5px"}}>CRITICAL</span>}
          {healed&&<span style={{fontSize:9,color:C.purple,border:`1px solid ${C.purple}44`,borderRadius:4,padding:"1px 5px"}}>⚡ AI HEALED</span>}
          {s.status==="pass"&&<span style={{fontSize:9,color:C.green,border:`1px solid ${C.green}44`,borderRadius:4,padding:"1px 5px"}}>PASSED</span>}
          {s.status==="fail"&&<span style={{fontSize:9,color:C.red,border:`1px solid ${C.red}44`,borderRadius:4,padding:"1px 5px"}}>FAILED</span>}
        </div>
        {step.selector&&<div style={{display:"flex",alignItems:"baseline",gap:6}}><span style={{fontSize:10,color:C.dim,flexShrink:0}}>selector:</span><code style={{fontSize:10,fontFamily:"'DM Mono',monospace",color:healed?"#64748B":C.muted,textDecoration:healed?"line-through":"none"}}>{short(step.selector)}</code></div>}
        {healed&&s.healed_selector&&<div style={{display:"flex",alignItems:"baseline",gap:6}}><span style={{fontSize:10,color:C.dim,flexShrink:0}}>healed →</span><code style={{fontSize:10,fontFamily:"'DM Mono',monospace",color:C.purple}}>{short(s.healed_selector)}</code></div>}
        {s.vision_verdict&&s.vision_verdict!=="unknown"&&s.vision_note&&<div style={{fontSize:10,color:s.vision_verdict==="confirmed"?C.green:C.red,opacity:0.8}}>👁 {s.vision_verdict}: {s.vision_note}</div>}
        {s.status==="fail"&&s.reason&&<div style={{fontSize:10,color:C.red}}>{s.reason}</div>}
      </div>
    </div>
  );
}

function LogRow({entry,idx}){
  if(entry.type==="step")return null;
  const lvl=entry.level||"info";
  return(
    <div style={{display:"grid",gridTemplateColumns:"60px 70px 1fr",gap:8,padding:"5px 14px",background:idx%2===0?"transparent":"rgba(255,255,255,0.01)",borderLeft:`2px solid ${stageColor(entry.stage)}`,fontFamily:"'DM Mono',monospace",fontSize:11,lineHeight:1.6}}>
      <span style={{color:"#334155"}}>{entry.time}</span>
      <span style={{color:stageColor(entry.stage),background:`${stageColor(entry.stage)}15`,borderRadius:4,padding:"0 4px",textAlign:"center",fontWeight:700,fontSize:9,letterSpacing:"0.07em"}}>{entry.stage}</span>
      <span style={{color:lvl==="error"?C.red:lvl==="warning"?C.yellow:"#64748B",wordBreak:"break-all"}}>{entry.message}</span>
    </div>
  );
}

function RegisterScreen({onSuccess}){
  const[name,setName]=useState("");
  const[email,setEmail]=useState("");
  const[tier,setTier]=useState("free");
  const[err,setErr]=useState("");
  const[loading,setLoading]=useState(false);
  const[done,setDone]=useState(null);

  const submit=async()=>{
    if(!name.trim()||!email.trim()){setErr("Name and email required");return;}
    setLoading(true);setErr("");
    try{
      const r=await fetch(`${API}/auth/register`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name.trim(),email:email.trim(),tier})});
      const d=await r.json();
      if(!r.ok){setErr(d.detail||"Registration failed");setLoading(false);return;}
      setDone(d);
    }catch{setErr("Cannot reach server — make sure the backend is running on port 8000");setLoading(false);}
  };

  if(done)return(
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",padding:24,fontFamily:"'DM Sans',sans-serif"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=DM+Mono:wght@400;600&display=swap');*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}.btn{transition:all .15s;cursor:pointer}.btn:hover{filter:brightness(1.1)}`}</style>
      <div style={{width:"100%",maxWidth:480,display:"flex",flexDirection:"column",gap:24}}>
        <div style={{textAlign:"center"}}>
          <div style={{width:56,height:56,borderRadius:14,background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:26,margin:"0 auto 16px"}}>✓</div>
          <div style={{fontWeight:700,fontSize:22,color:C.text,marginBottom:8}}>You're registered!</div>
          <div style={{fontSize:14,color:C.muted}}>Save your API key — you'll need it to connect.</div>
        </div>
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:16,padding:24,display:"flex",flexDirection:"column",gap:14}}>
          <div style={{fontSize:11,color:C.muted,textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:700}}>Your API Key</div>
          <code style={{fontSize:13,color:C.green,background:"rgba(110,231,183,0.08)",border:`1px solid ${C.green}33`,borderRadius:8,padding:"12px 16px",fontFamily:"'DM Mono',monospace",wordBreak:"break-all",display:"block"}}>{done.api_key}</code>
          <div style={{fontSize:11,color:C.muted}}>Tier: <strong style={{color:C.text}}>{done.tier}</strong> · Tenant ID: <code style={{fontFamily:"'DM Mono',monospace",color:C.blue}}>{done.tenant_id}</code></div>
        </div>
        <button className="btn" onClick={()=>onSuccess({key:done.api_key,tier:done.tier,email:email.trim()})}
          style={{background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",border:"none",borderRadius:10,padding:"14px",color:"#020C12",fontWeight:700,fontSize:14,fontFamily:"inherit"}}>
          Open Dashboard →
        </button>
      </div>
    </div>
  );

  const TIERS=[{id:"free",label:"Free",sub:"10 scripts/day"},{id:"starter",label:"Starter",sub:"100/day"},{id:"pro",label:"Pro",sub:"1,000/day"},{id:"enterprise",label:"Enterprise",sub:"Unlimited"}];

  return(
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",padding:24,fontFamily:"'DM Sans',sans-serif"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500;600&display=swap');*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}input,select{transition:border-color .15s}input:focus,select:focus{border-color:${C.green}!important;outline:none}.btn{transition:all .15s;cursor:pointer}.btn:hover:not(:disabled){filter:brightness(1.1);transform:translateY(-1px)}`}</style>
      <div style={{width:"100%",maxWidth:460,display:"flex",flexDirection:"column",gap:28}}>
        <div style={{textAlign:"center"}}>
          <div style={{display:"inline-flex",alignItems:"center",gap:12,marginBottom:14}}>
            <div style={{width:44,height:44,borderRadius:11,background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:22}}>⚡</div>
            <div style={{textAlign:"left"}}>
              <div style={{fontWeight:700,fontSize:22,color:C.text,letterSpacing:"-0.02em"}}>HealBot</div>
              <div style={{fontFamily:"'DM Mono',monospace",fontSize:10,color:C.muted,letterSpacing:"0.12em"}}>AI AUTOMATION PLATFORM</div>
            </div>
          </div>
          <p style={{fontSize:14,color:C.muted,lineHeight:1.7}}>Self-healing test automation.<br/>Your scripts fix themselves when they break.</p>
        </div>
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:16,padding:28,display:"flex",flexDirection:"column",gap:18}}>
          <div style={{fontWeight:700,fontSize:16,color:C.text}}>Create your account</div>
          {[{label:"Organisation name",value:name,set:setName,ph:"Acme Corp",type:"text"},{label:"Work email",value:email,set:setEmail,ph:"you@acme.com",type:"email"}].map(f=>(
            <div key={f.label} style={{display:"flex",flexDirection:"column",gap:6}}>
              <label style={{fontSize:11,color:C.muted,fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase"}}>{f.label}</label>
              <input type={f.type} value={f.value} onChange={e=>f.set(e.target.value)} placeholder={f.ph} onKeyDown={e=>e.key==="Enter"&&submit()} style={inp()}/>
            </div>
          ))}
          <div style={{display:"flex",flexDirection:"column",gap:6}}>
            <label style={{fontSize:11,color:C.muted,fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase"}}>Plan</label>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
              {TIERS.map(t=>(
                <div key={t.id} onClick={()=>setTier(t.id)} style={{padding:"10px 14px",borderRadius:9,cursor:"pointer",border:`1px solid ${tier===t.id?C.green+"88":C.border}`,background:tier===t.id?"rgba(110,231,183,0.08)":"transparent",transition:"all .15s"}}>
                  <div style={{fontSize:12,fontWeight:600,color:tier===t.id?C.green:C.text}}>{t.label}</div>
                  <div style={{fontFamily:"'DM Mono',monospace",fontSize:10,color:C.muted,marginTop:2}}>{t.sub}</div>
                </div>
              ))}
            </div>
          </div>
          {err&&<div style={{background:"rgba(252,165,165,0.08)",border:`1px solid ${C.red}44`,borderRadius:8,padding:"10px 14px",fontSize:12,color:C.red}}>{err}</div>}
          <button className="btn" onClick={submit} disabled={loading} style={{background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",border:"none",borderRadius:10,padding:"13px",color:"#020C12",fontWeight:700,fontSize:14,fontFamily:"inherit",opacity:loading?.7:1}}>
            {loading?"Creating account…":"Create account and get API key"}
          </button>
        </div>
        <div style={{textAlign:"center",fontSize:13,color:C.muted}}>
          Already have a key?{" "}
          <button onClick={()=>onSuccess(null)} style={{background:"none",border:"none",color:C.green,cursor:"pointer",fontFamily:"inherit",fontSize:"inherit"}}>Connect with existing key</button>
        </div>
      </div>
    </div>
  );
}

function ConnectScreen({onSuccess,onBack}){
  const[key,setKey]=useState("");
  const[err,setErr]=useState("");
  const connect=async()=>{
    if(!key.trim()){setErr("Paste your API key");return;}
    try{
      const r=await fetch(`${API}/batches`,{headers:{Authorization:`Bearer ${key.trim()}`}});
      if(!r.ok){setErr("Invalid key or server not running");return;}
      onSuccess({key:key.trim(),tier:"unknown"});
    }catch{setErr("Cannot reach server — make sure backend is running on port 8000");}
  };
  return(
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",padding:24,fontFamily:"'DM Sans',sans-serif"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=DM+Mono:wght@400;600&display=swap');*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}.btn{transition:all .15s;cursor:pointer}.btn:hover{filter:brightness(1.1)}`}</style>
      <div style={{width:"100%",maxWidth:420,display:"flex",flexDirection:"column",gap:24}}>
        <div style={{textAlign:"center"}}>
          <div style={{width:44,height:44,borderRadius:11,background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:22,margin:"0 auto 12px"}}>⚡</div>
          <div style={{fontWeight:700,fontSize:20,color:C.text}}>Connect to HealBot</div>
        </div>
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:16,padding:24,display:"flex",flexDirection:"column",gap:14}}>
          <label style={{fontSize:11,color:C.muted,fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase"}}>API Key</label>
          <input value={key} onChange={e=>setKey(e.target.value)} placeholder="hb_live_..." onKeyDown={e=>e.key==="Enter"&&connect()} style={inp({fontFamily:"'DM Mono',monospace"})}/>
          {err&&<div style={{fontSize:12,color:C.red}}>{err}</div>}
          <button className="btn" onClick={connect} style={{background:`linear-gradient(135deg,${C.green},#3B82F6)`,border:"none",borderRadius:10,padding:"12px",color:"#020C12",fontWeight:700,fontSize:14,fontFamily:"inherit"}}>Connect →</button>
        </div>
        <div style={{textAlign:"center"}}><button onClick={onBack} style={{background:"none",border:"none",color:C.muted,cursor:"pointer",fontFamily:"'DM Sans',sans-serif",fontSize:13}}>← Back to register</button></div>
      </div>
    </div>
  );
}

function AppDashboard({auth,onLogout}){
  const call=useApi(auth.key);
  const[view,setView]=useState("run");

  // ── Run tab state ──────────────────────────────────────────────────────────
  const[activeRun,setActiveRun]=useState(null);   // {run_id,batch_id,name}
  const[stepStates,setStepStates]=useState({});   // step_id → state
  const[stepOrder,setStepOrder]=useState([]);     // ordered step ids
  const[stepMeta,setStepMeta]=useState({});       // step_id → {description,selector,critical}
  const[logs,setLogs]=useState([]);
  const[metrics,setMetrics]=useState({llmCalls:0,visionCalls:0,healedSelectors:0,failures:0});
  const[runStatus,setRunStatus]=useState(null);
  const[logFilter,setLogFilter]=useState("");

  // ── Batches + Analytics state ──────────────────────────────────────────────
  const[batches,setBatches]=useState([]);
  const[analytics,setAnalytics]=useState(null);

  const esRef=useRef(null);
  const logRef=useRef(null);

  // Auto-scroll logs
  useEffect(()=>{if(logRef.current)logRef.current.scrollTop=logRef.current.scrollHeight;},[logs]);

  // ── SSE: connect to a run_id and stream all events ────────────────────────
  const connectToRun=useCallback((runId,batchId,name)=>{
    if(esRef.current)esRef.current.close();
    setActiveRun({run_id:runId,batch_id:batchId,name});
    setStepStates({});setStepOrder([]);setStepMeta({});
    setLogs([]);setMetrics({llmCalls:0,visionCalls:0,healedSelectors:0,failures:0});
    setRunStatus("running");

    const es=new EventSource(`${API}/stream/${runId}?api_key=${encodeURIComponent(auth.key)}`);
    esRef.current=es;

    es.onmessage=e=>{
      const msg=JSON.parse(e.data);

      if(msg.type==="log"){
        const entry=msg.payload;

        // Step event — update step state panel
        if(entry.type==="step"){
          const sid=entry.step_id;
          setStepStates(prev=>({...prev,[sid]:{
            status:entry.status,
            healed_selector:entry.healed_selector||entry.healed,
            original_selector:entry.original_selector,
            reason:entry.reason,
            vision_verdict:entry.vision_verdict,
            vision_note:entry.vision_note,
          }}));
          // Track order
          setStepOrder(prev=>prev.includes(sid)?prev:[...prev,sid]);
          // Store meta (description, original selector)
          if(entry.description||entry.original_selector){
            setStepMeta(prev=>({...prev,[sid]:{
              description:entry.description||sid,
              selector:entry.original_selector||"",
              critical:entry.critical||false,
            }}));
          }
        } else {
          // Regular log entry — push to pipeline log
          setLogs(prev=>[...prev,entry]);

          // Extract step description from JOURNEY log messages like "▶ [step_id] description"
          if(entry.stage==="JOURNEY"&&entry.message){
            const mRun=entry.message.match(/▶\s*\[([^\]]+)\]\s*(.*)/);
            if(mRun){
              const[,sid,desc]=mRun;
              setStepOrder(prev=>prev.includes(sid)?prev:[...prev,sid]);
              setStepMeta(prev=>({...prev,[sid]:{description:desc||sid,selector:prev[sid]?.selector||"",critical:false}}));
              setStepStates(prev=>({...prev,[sid]:{...(prev[sid]||{}),status:"running"}}));
            }
            // Step passed: "✅ [step_id] description"
            const mPass=entry.message.match(/✅\s*\[([^\]]+)\]/);
            if(mPass)setStepStates(prev=>({...prev,[mPass[1]]:{...(prev[mPass[1]]||{}),status:prev[mPass[1]]?.status==="healed"?"healed":"pass"}}));
            // Step failed: "❌ [step_id]"
            const mFail=entry.message.match(/❌\s*\[([^\]]+)\]/);
            if(mFail)setStepStates(prev=>({...prev,[mFail[1]]:{...(prev[mFail[1]]||{}),status:"fail"}}));
          }

          // Also push ENGINE/DOM/LLM/MEMORY/VISION/INTENT to pipeline logs
        }
      }

      if(msg.type==="snapshot"){
        const m=msg.payload.metrics||{};
        setMetrics(prev=>({...prev,...m}));
        setRunStatus(msg.payload.status);
      }

      if(msg.type==="done"){
        setRunStatus(msg.payload.status||"completed");
        es.close();
      }
    };
    es.onerror=()=>{setRunStatus(s=>s==="running"?"error":s);es.close();};
  },[auth.key]);

  useEffect(()=>()=>esRef.current?.close(),[]);

  // ── Auto-detect running batches and connect to them ───────────────────────
  useEffect(()=>{
    if(view!=="run")return;
    // Poll for running batches every 2s, auto-connect when one appears
    const poll=async()=>{
      const data=await call("GET","/batches").catch(()=>[]);
      if(!Array.isArray(data))return;
      const running=data.find(b=>b.status==="running");
      if(running&&(!activeRun||activeRun.batch_id!==running.id)){
        // Get the run_id for this batch
        const runs=await call("GET",`/batches/${running.id}/runs`).catch(()=>[]);
        if(runs?.length>0&&runs[0].id){
          connectToRun(runs[0].id,running.id,running.name);
        }
      }
    };
    poll();
    const t=setInterval(poll,2000);
    return()=>clearInterval(t);
  },[view,call,connectToRun,activeRun]);

  // ── Batches tab: poll every 3s ────────────────────────────────────────────
  useEffect(()=>{
    if(view!=="batches"){return;}
    call("GET","/batches").then(setBatches).catch(()=>{});
    const t=setInterval(()=>call("GET","/batches").then(setBatches).catch(()=>{}),3000);
    return()=>clearInterval(t);
  },[view,call]);

  // ── Analytics tab ─────────────────────────────────────────────────────────
  useEffect(()=>{
    if(view==="analytics")call("GET","/analytics/overview").then(setAnalytics).catch(()=>{});
  },[view,call]);

  // ── Derived counts ────────────────────────────────────────────────────────
  const passCount=Object.values(stepStates).filter(s=>s.status==="pass").length;
  const healCount=Object.values(stepStates).filter(s=>s.status==="healed").length;
  const failCount=Object.values(stepStates).filter(s=>s.status==="fail").length;
  const doneCount=passCount+healCount+failCount;
  const totalSteps=stepOrder.length;
  const visibleLogs=logFilter
    ?logs.filter(l=>l.message?.toLowerCase().includes(logFilter.toLowerCase())||l.stage?.toLowerCase().includes(logFilter.toLowerCase()))
    :logs;
  const statusColor=runStatus==="completed"||runStatus==="passed"?C.green:runStatus==="failed"?C.red:runStatus==="running"?C.yellow:C.muted;

  return(
    <div style={{minHeight:"100vh",background:C.bg,color:C.text,fontFamily:"'DM Sans',sans-serif",display:"flex",flexDirection:"column"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500;600&display=swap');*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:#1E293B;border-radius:3px}@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}.btn{transition:all .15s;cursor:pointer}.btn:hover:not(:disabled){filter:brightness(1.1);transform:translateY(-1px)}.navbtn{background:none;border:none;font-family:inherit;cursor:pointer;transition:color .15s}`}</style>

      {/* ── Header ── */}
      <header style={{height:54,borderBottom:`1px solid ${C.border}`,padding:"0 28px",display:"flex",alignItems:"center",justifyContent:"space-between",position:"sticky",top:0,zIndex:50,background:"rgba(7,9,15,0.92)",backdropFilter:"blur(14px)"}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:30,height:30,borderRadius:7,background:"linear-gradient(135deg,#6EE7B7,#3B82F6)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:15}}>⚡</div>
          <div>
            <div style={{fontWeight:700,fontSize:14,letterSpacing:"-0.02em"}}>HealBot</div>
            <div style={{fontSize:9,color:C.muted,letterSpacing:"0.1em",textTransform:"uppercase",fontFamily:"'DM Mono',monospace"}}>SaaS Platform</div>
          </div>
        </div>
        <nav style={{display:"flex",gap:4}}>
          {[{id:"run",label:"⚡ Live"},{id:"batches",label:"Batches"},{id:"analytics",label:"Analytics"}].map(n=>(
            <button key={n.id} className="navbtn" onClick={()=>setView(n.id)} style={{padding:"6px 14px",fontSize:12,fontWeight:600,borderRadius:8,color:view===n.id?C.green:C.muted,background:view===n.id?"rgba(110,231,183,0.1)":"transparent",border:view===n.id?`1px solid ${C.green}33`:"1px solid transparent"}}>{n.label}</button>
          ))}
        </nav>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <code style={{fontSize:10,color:C.dim,fontFamily:"'DM Mono',monospace"}}>{auth.key?.slice(0,20)}…</code>
          <button onClick={onLogout} className="btn" style={{fontSize:11,color:C.muted,background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"4px 10px",fontFamily:"inherit"}}>Logout</button>
        </div>
      </header>

      {/* ══ RUN TAB — Live session viewer ══════════════════════════════════════ */}
      {view==="run"&&(
        <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>

          {/* ── Top bar: metrics + status ── */}
          <div style={{padding:"12px 28px",borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
            {[{label:"Healed",value:metrics.healedSelectors||0,color:C.purple},{label:"LLM calls",value:metrics.llmCalls||0,color:C.blue},{label:"Vision",value:metrics.visionCalls||0,color:C.pink},{label:"Failures",value:metrics.failures||0,color:C.red}].map(m=>(
              <div key={m.label} style={{display:"flex",alignItems:"center",gap:7,background:C.surface,border:`1px solid ${C.border}`,borderRadius:8,padding:"6px 14px"}}>
                <span style={{fontSize:10,color:C.muted}}>{m.label}</span>
                <span style={{fontSize:16,fontWeight:700,color:m.color,fontFamily:"'DM Mono',monospace"}}>{m.value}</span>
              </div>
            ))}
            {totalSteps>0&&(
              <div style={{flex:1,minWidth:120}}>
                <div style={{height:4,background:"rgba(255,255,255,0.06)",borderRadius:2,overflow:"hidden"}}>
                  <div style={{height:"100%",borderRadius:2,transition:"width 0.4s ease",width:`${totalSteps>0?(doneCount/totalSteps)*100:0}%`,background:"linear-gradient(90deg,#6EE7B7,#3B82F6)"}}/>
                </div>
                <div style={{fontSize:10,color:C.muted,marginTop:4,fontFamily:"'DM Mono',monospace"}}>{doneCount}/{totalSteps} steps</div>
              </div>
            )}
            {runStatus&&<div style={{fontSize:11,fontWeight:700,color:statusColor,border:`1px solid ${statusColor}44`,borderRadius:999,padding:"4px 12px",fontFamily:"'DM Mono',monospace",letterSpacing:"0.08em",animation:runStatus==="running"?"pulse 1.4s ease infinite":"none"}}>{runStatus.toUpperCase()}</div>}
            {activeRun&&<div style={{fontSize:11,color:C.dim,fontFamily:"'DM Mono',monospace",marginLeft:"auto"}}>{activeRun.name}</div>}
          </div>

          {/* ── Two-column: Steps | Logs ── */}
          <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 2fr",overflow:"hidden"}}>

            {/* ── Left: Journey Steps ── */}
            <div style={{borderRight:`1px solid ${C.border}`,display:"flex",flexDirection:"column",overflow:"hidden"}}>
              <div style={{padding:"10px 16px",borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",justifyContent:"space-between"}}>
                <span style={{fontSize:11,fontWeight:700,color:C.muted,letterSpacing:"0.08em",textTransform:"uppercase"}}>Journey Steps</span>
                <div style={{display:"flex",gap:12,fontSize:11,fontFamily:"'DM Mono',monospace"}}>
                  <span style={{color:C.green}}>✓ {passCount}</span>
                  <span style={{color:C.purple}}>⚡ {healCount}</span>
                  <span style={{color:C.red}}>✕ {failCount}</span>
                </div>
              </div>
              <div style={{flex:1,overflowY:"auto"}}>
                {stepOrder.length===0?(
                  <div style={{padding:40,textAlign:"center",color:C.dim,fontSize:13}}>
                    <div style={{fontSize:28,marginBottom:12,opacity:0.4}}>⚡</div>
                    <div style={{fontWeight:600,marginBottom:6}}>Waiting for a test run</div>
                    <div style={{fontSize:12,color:C.muted}}>Run <code style={{fontFamily:"'DM Mono',monospace",color:C.green}}>pytest</code> from your qa-framework folder</div>
                    <div style={{fontSize:11,color:C.dim,marginTop:8}}>Steps appear here in real-time as they execute</div>
                  </div>
                ):stepOrder.map(sid=>{
                  const state=stepStates[sid]||{status:"pending"};
                  const meta=stepMeta[sid]||{description:sid,selector:"",critical:false};
                  const cfg=STEP_STATUS[state.status]||STEP_STATUS.pending;
                  const healed=state.status==="healed";
                  return(
                    <div key={sid} style={{display:"grid",gridTemplateColumns:"28px 1fr",gap:12,padding:"10px 16px",borderBottom:`1px solid ${C.border}`,background:state.status==="running"?"rgba(253,230,138,0.03)":"transparent",animation:state.status!=="pending"?"fadeIn 0.2s ease":"none"}}>
                      <div style={{width:26,height:26,borderRadius:6,flexShrink:0,marginTop:1,background:`${cfg.color}18`,border:`1px solid ${cfg.color}44`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,color:cfg.color,fontWeight:700,animation:cfg.pulse?"pulse 1.4s ease infinite":"none"}}>{cfg.icon}</div>
                      <div style={{display:"flex",flexDirection:"column",gap:4,minWidth:0}}>
                        <div style={{display:"flex",alignItems:"center",gap:7,flexWrap:"wrap"}}>
                          <span style={{fontSize:13,fontWeight:600,color:C.text}}>{meta.description}</span>
                          {meta.critical&&<span style={{fontSize:9,color:C.orange,border:`1px solid ${C.orange}44`,borderRadius:4,padding:"1px 5px"}}>CRITICAL</span>}
                          {healed&&<span style={{fontSize:9,color:C.purple,border:`1px solid ${C.purple}44`,borderRadius:4,padding:"1px 5px"}}>⚡ AI HEALED</span>}
                          {state.status==="pass"&&<span style={{fontSize:9,color:C.green,border:`1px solid ${C.green}44`,borderRadius:4,padding:"1px 5px"}}>PASSED</span>}
                          {state.status==="fail"&&<span style={{fontSize:9,color:C.red,border:`1px solid ${C.red}44`,borderRadius:4,padding:"1px 5px"}}>FAILED</span>}
                        </div>
                        {(meta.selector||state.original_selector)&&(
                          <div style={{display:"flex",alignItems:"baseline",gap:6}}>
                            <span style={{fontSize:10,color:C.dim,flexShrink:0}}>selector:</span>
                            <code style={{fontSize:10,fontFamily:"'DM Mono',monospace",color:healed?"#64748B":C.muted,textDecoration:healed?"line-through":"none"}}>{short(meta.selector||state.original_selector)}</code>
                          </div>
                        )}
                        {healed&&state.healed_selector&&(
                          <div style={{display:"flex",alignItems:"baseline",gap:6}}>
                            <span style={{fontSize:10,color:C.dim,flexShrink:0}}>healed →</span>
                            <code style={{fontSize:10,fontFamily:"'DM Mono',monospace",color:C.purple}}>{short(state.healed_selector)}</code>
                          </div>
                        )}
                        {state.vision_verdict&&state.vision_verdict!=="unknown"&&state.vision_note&&(
                          <div style={{fontSize:10,color:state.vision_verdict==="confirmed"?C.green:C.red,opacity:0.8}}>👁 {state.vision_verdict}: {state.vision_note}</div>
                        )}
                        {state.status==="fail"&&state.reason&&<div style={{fontSize:10,color:C.red}}>{state.reason}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
              {activeRun&&(
                <div style={{padding:"10px 16px",borderTop:`1px solid ${C.border}`,display:"flex",flexDirection:"column",gap:3}}>
                  <div style={{fontSize:11,fontWeight:600,color:C.text}}>{activeRun.name}</div>
                  <code style={{fontSize:10,color:C.dim,fontFamily:"'DM Mono',monospace"}}>batch: {activeRun.batch_id}</code>
                </div>
              )}
            </div>

            {/* ── Right: Live Pipeline Logs ── */}
            <div style={{display:"flex",flexDirection:"column",overflow:"hidden"}}>
              <div style={{padding:"10px 16px",borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",gap:10}}>
                <span style={{fontSize:11,fontWeight:700,color:C.muted,letterSpacing:"0.08em",textTransform:"uppercase"}}>Live Pipeline Logs</span>
                <span style={{fontSize:10,color:C.dim,fontFamily:"'DM Mono',monospace"}}>{visibleLogs.length}</span>
                <input value={logFilter} onChange={e=>setLogFilter(e.target.value)} placeholder="Filter…" style={{marginLeft:"auto",background:"rgba(255,255,255,0.04)",border:`1px solid ${C.border}`,borderRadius:6,padding:"4px 10px",color:C.text,fontSize:11,fontFamily:"'DM Mono',monospace",outline:"none",width:130}}/>
              </div>
              <div ref={logRef} style={{flex:1,overflowY:"auto",padding:"4px 0"}}>
                {visibleLogs.length===0?(
                  <div style={{padding:40,textAlign:"center",color:C.dim,fontSize:13}}>
                    {activeRun?<span>Waiting for log entries…</span>:<span>Logs appear here when a test run starts</span>}
                  </div>
                ):visibleLogs.map((entry,i)=>(
                  <LogRow key={i} entry={entry} idx={i}/>
                ))}
              </div>
              <div style={{padding:"8px 14px",borderTop:`1px solid ${C.border}`,display:"flex",gap:8,flexWrap:"wrap"}}>
                {Object.entries(STAGE_COLOR).map(([s,c])=>(
                  <div key={s} style={{display:"flex",alignItems:"center",gap:3}}>
                    <div style={{width:5,height:5,borderRadius:"50%",background:c}}/>
                    <span style={{fontSize:9,color:C.dim,fontFamily:"'DM Mono',monospace"}}>{s}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══ BATCHES TAB ═══════════════════════════════════════════════════════ */}
      {view==="batches"&&(
        <div style={{flex:1,padding:24,overflowY:"auto"}}>
          <div style={{maxWidth:900,margin:"0 auto",display:"flex",flexDirection:"column",gap:16}}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:4}}>
              <div style={{fontSize:16,fontWeight:700}}>Batch History</div>
              <div style={{display:"flex",alignItems:"center",gap:12}}>
                <div style={{display:"flex",alignItems:"center",gap:6,fontSize:11,color:C.green}}>
                  <div style={{width:6,height:6,borderRadius:"50%",background:C.green,animation:"pulse 1.4s ease infinite"}}/>Live
                </div>
                <button className="btn" onClick={()=>call("GET","/batches").then(setBatches).catch(()=>{})} style={{fontSize:11,color:C.muted,background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"4px 12px",fontFamily:"inherit"}}>↺ Refresh</button>
              </div>
            </div>
            <div style={{fontSize:11,color:C.dim,fontFamily:"'DM Mono',monospace",marginBottom:4}}>Active key: {auth.key?.slice(0,20)}… — pytest must use this same key</div>
            {batches.length===0?(
              <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:14,padding:48,textAlign:"center",color:C.muted,fontSize:14}}>No batches yet — run pytest with HEALBOT_API_KEY set</div>
            ):batches.map(b=>(
              <div key={b.id} style={{background:C.surface,border:`1px solid ${b.status==="running"?C.yellow:C.border}`,borderRadius:14,padding:"16px 20px",cursor:b.status==="running"?"pointer":"default",transition:"border-color 0.2s"}}
                onClick={async()=>{
                  if(b.status==="running"){
                    const runs=await call("GET",`/batches/${b.id}/runs`).catch(()=>[]);
                    if(runs?.length>0&&runs[0].id){connectToRun(runs[0].id,b.id,b.name);setView("run");}
                  }
                }}>
                <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
                  <div>
                    <div style={{fontSize:14,fontWeight:600}}>{b.name}</div>
                    <code style={{fontSize:10,color:C.muted,fontFamily:"'DM Mono',monospace"}}>{b.id}</code>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    {b.status==="running"&&<span style={{fontSize:10,color:C.yellow}}>Click to watch live →</span>}
                    <span style={{fontSize:10,fontWeight:700,color:STATUS_COLOR[b.status]||C.muted,border:`1px solid ${STATUS_COLOR[b.status]||C.muted}44`,borderRadius:999,padding:"3px 10px",fontFamily:"'DM Mono',monospace"}}>{b.status?.toUpperCase()}</span>
                  </div>
                </div>
                <div style={{display:"flex",gap:20,fontSize:12,fontFamily:"'DM Mono',monospace"}}>
                  <span>{b.total_scripts} script{b.total_scripts!==1?"s":""}</span>
                  <span style={{color:C.green}}>✓ {b.passed} passed</span>
                  <span style={{color:C.purple}}>⚡ {b.healed} healed</span>
                  <span style={{color:C.red}}>✕ {b.failed} failed</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ══ ANALYTICS TAB ═════════════════════════════════════════════════════ */}
      {view==="analytics"&&(
        <div style={{flex:1,padding:24,overflowY:"auto"}}>
          <div style={{maxWidth:900,margin:"0 auto",display:"flex",flexDirection:"column",gap:20}}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
              <div style={{fontSize:16,fontWeight:700}}>Analytics</div>
              <button className="btn" onClick={()=>call("GET","/analytics/overview").then(setAnalytics).catch(()=>{})} style={{fontSize:11,color:C.muted,background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"4px 12px",fontFamily:"inherit"}}>↺ Refresh</button>
            </div>
            {!analytics?<div style={{color:C.muted,fontSize:13}}>Loading…</div>:(
              <>
                <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
                  {[{label:"Total Scripts",value:analytics.total_scripts,color:C.green},{label:"Total Heals",value:analytics.total_heals,color:C.purple},{label:"Heal Rate",value:`${analytics.heal_rate_pct}%`,color:C.yellow},{label:"Failures",value:analytics.total_failures,color:C.red}].map(m=>(
                    <div key={m.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:14,padding:"16px 20px"}}>
                      <div style={{fontSize:10,color:C.muted,textTransform:"uppercase",letterSpacing:"0.1em",fontWeight:700,marginBottom:6}}>{m.label}</div>
                      <div style={{fontSize:30,fontWeight:700,color:m.color,fontFamily:"'DM Mono',monospace"}}>{m.value}</div>
                    </div>
                  ))}
                </div>
                {Object.keys(analytics.strategy_breakdown||{}).length>0&&(
                  <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:14,padding:"16px 20px"}}>
                    <div style={{fontSize:11,color:C.muted,textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:700,marginBottom:14}}>Healing Strategies Used</div>
                    <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
                      {Object.entries(analytics.strategy_breakdown).map(([s,n])=>(
                        <div key={s} style={{background:"rgba(255,255,255,0.04)",border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 18px"}}>
                          <div style={{fontSize:10,color:C.muted,marginBottom:4}}>{s}</div>
                          <div style={{fontSize:24,fontWeight:700,color:C.purple,fontFamily:"'DM Mono',monospace"}}>{n}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.daily_trend&&Object.keys(analytics.daily_trend).length>0&&(
                  <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:14,padding:"16px 20px"}}>
                    <div style={{fontSize:11,color:C.muted,textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:700,marginBottom:14}}>Daily Trend (last 14 days)</div>
                    <div style={{display:"flex",alignItems:"flex-end",gap:6,height:80}}>
                      {Object.entries(analytics.daily_trend).map(([day,d])=>{
                        const maxVal=Math.max(...Object.values(analytics.daily_trend).map(x=>x.runs||0),1);
                        const h=Math.max(4,((d.runs||0)/maxVal)*72);
                        const healH=Math.max(0,((d.healed||0)/maxVal)*72);
                        return(
                          <div key={day} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:2}}>
                            <div style={{width:"100%",position:"relative",height:72,display:"flex",alignItems:"flex-end"}}>
                              <div style={{width:"100%",height:h,background:"rgba(148,163,184,0.2)",borderRadius:"3px 3px 0 0",position:"relative",overflow:"hidden"}}>
                                {healH>0&&<div style={{position:"absolute",bottom:0,width:"100%",height:healH,background:C.purple,borderRadius:"3px 3px 0 0"}}/>}
                              </div>
                            </div>
                            <div style={{fontSize:9,color:C.dim,fontFamily:"'DM Mono',monospace",transform:"rotate(-45deg)",transformOrigin:"top left",marginTop:8,whiteSpace:"nowrap"}}>{day.slice(5)}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{display:"flex",gap:16,marginTop:24,fontSize:11}}>
                      <div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:10,height:10,borderRadius:2,background:"rgba(148,163,184,0.2)"}}/><span style={{color:C.muted}}>Total runs</span></div>
                      <div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:10,height:10,borderRadius:2,background:C.purple}}/><span style={{color:C.muted}}>Healed</span></div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


export default function App(){
  const[auth,setAuth]=useState(()=>{try{return JSON.parse(localStorage.getItem("hb_auth")||"null")}catch{return null}});
  const[showConnect,setShowConnect]=useState(false);
  const login=info=>{if(!info){setShowConnect(true);return;}setAuth(info);localStorage.setItem("hb_auth",JSON.stringify(info));setShowConnect(false);};
  const logout=()=>{setAuth(null);localStorage.removeItem("hb_auth");setShowConnect(false);};
  if(!auth&&showConnect)return<ConnectScreen onSuccess={login} onBack={()=>setShowConnect(false)}/>;
  if(!auth)return<RegisterScreen onSuccess={login}/>;
  return<AppDashboard auth={auth} onLogout={logout}/>;
}