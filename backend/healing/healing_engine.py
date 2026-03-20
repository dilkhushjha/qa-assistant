"""
healing_engine.py — Full self-healing pipeline with per-tenant memory.

Pipeline:
  1. Memory recall (tenant → global)
  2. DOM heuristic scoring
     score >= CONFIDENCE_THRESHOLD → trust DOM, skip LLM
     score <  CONFIDENCE_THRESHOLD → invoke LLM
  3. LLM (Ollama)
  4. Vision confirmation (llava)
  5. DOM fallback (last resort)

Returns a full result dict for audit trail persistence.
"""
# ── sys.path fix ──
from context.element_context_extractor import extract_element_context
from healing.intent_engine import infer_intent_from_selector
from healing.learning_engine import learn, recall
from healing.vision_analyzer import analyze_screenshot
from healing.vision_capture import capture_screen
from healing.llm_reasoner import ask_llm_for_element
from healing.dom_healer import dom_heal, CONFIDENCE_THRESHOLD
from core.logger import log
import sys as _sys
import os as _os
_BACKEND_DIR = _os.path.abspath(__file__)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)
# ── sys.path fix ──


def _xpath(el: dict) -> str | None:
    if not el:
        return None
    if el.get("id"):
        return f"//*[@id='{el['id']}']"
    if el.get("name"):
        return f"//*[@name='{el['name']}']"
    if el.get("data_testid"):
        return f"//*[@data-testid='{el['data_testid']}']"
    if el.get("aria_label"):
        return f"//*[@aria-label='{el['aria_label']}']"
    if el.get("placeholder"):
        return f"//*[@placeholder='{el['placeholder']}']"
    return None


def _vision_check(screenshot, intent, selector, ctx) -> dict:
    if not screenshot:
        return {"vision_verdict": "unknown", "vision_note": "no screenshot"}
    r = analyze_screenshot(screenshot, intent, selector, ctx=ctx)
    return {"vision_verdict": r["verdict"], "vision_note": r["note"]}


def heal_selector(
    old_selector:  str,
    new_html:      str,
    driver=None,
    intent:        str | None = None,
    client_id:     str | None = None,
    tenant_id:     str = "default",
    run_id:        str = "default",
    step_id:       str = "unknown",
    ctx=None,
) -> dict:
    """
    Returns:
    {
      "healed":         str | None,
      "strategy":       str | None,   # memory|dom|llm|dom_fallback
      "dom_score":      int,
      "llm_invoked":    bool,
      "dom_candidate":  str | None,
      "llm_candidate":  str | None,
      "vision_verdict": str,
      "vision_note":    str,
      "screenshot":     str | None,
    }
    """
    log("ENGINE", f"Healing: {old_selector}", ctx=ctx)

    result = {
        "healed": None, "strategy": None,
        "dom_score": 0, "llm_invoked": False,
        "dom_candidate": None, "llm_candidate": None,
        "vision_verdict": "unknown", "vision_note": "",
        "screenshot": None,
    }

    # ── 1. Memory (tenant first, then global pool) ────────────────────────
    cached = recall(old_selector, tenant_id=tenant_id)
    if cached:
        log("ENGINE", f"✅ Memory hit → {cached}", ctx=ctx)
        return {**result, "healed": cached, "strategy": "memory"}

    # ── 2. Screenshot ─────────────────────────────────────────────────────
    screenshot = capture_screen(driver, run_id=run_id, ctx=ctx)
    result["screenshot"] = screenshot

    # ── 3. Intent ─────────────────────────────────────────────────────────
    resolved_intent = intent or infer_intent_from_selector(
        old_selector, client_id or tenant_id)
    log("INTENT", f"'{resolved_intent}'", ctx=ctx)

    # ── 4. Context ────────────────────────────────────────────────────────
    context = extract_element_context(new_html, ctx=ctx)
    if not context:
        log("ENGINE", "No context — cannot heal", level="error", ctx=ctx)
        if ctx:
            ctx.increment("failures")
        return result

    # ── 5. DOM heal ───────────────────────────────────────────────────────
    dom_el, score = dom_heal(context, resolved_intent, ctx=ctx)
    result["dom_score"] = score
    result["dom_candidate"] = _xpath(dom_el)

    if dom_el and score >= CONFIDENCE_THRESHOLD:
        healed = _xpath(dom_el)
        if healed:
            vision = _vision_check(screenshot, resolved_intent, healed, ctx)
            result.update(vision)
            if vision["vision_verdict"] != "rejected":
                learn(old_selector, healed, tenant_id=tenant_id, ctx=ctx)
                if ctx:
                    ctx.increment("healedSelectors")
                log("ENGINE",
                    f"✅ DOM heal (score={score}) → {healed}", ctx=ctx)
                return {**result, "healed": healed, "strategy": "dom"}
            log("ENGINE", "DOM rejected by vision → LLM", level="warning", ctx=ctx)

    # ── 6. LLM ───────────────────────────────────────────────────────────
    log("ENGINE",
        f"DOM score {score} < {CONFIDENCE_THRESHOLD} → LLM" if score < CONFIDENCE_THRESHOLD
        else "DOM vision-rejected → LLM", ctx=ctx)
    result["llm_invoked"] = True
    llm_el = ask_llm_for_element(context, resolved_intent, ctx=ctx)
    if llm_el:
        healed = _xpath(llm_el)
        result["llm_candidate"] = healed
        if healed:
            vision = _vision_check(screenshot, resolved_intent, healed, ctx)
            result.update(vision)
            if vision["vision_verdict"] != "rejected":
                learn(old_selector, healed, tenant_id=tenant_id, ctx=ctx)
                if ctx:
                    ctx.increment("healedSelectors")
                log("ENGINE", f"✅ LLM heal → {healed}", ctx=ctx)
                return {**result, "healed": healed, "strategy": "llm"}

    # ── 7. DOM fallback ───────────────────────────────────────────────────
    if result["dom_candidate"]:
        healed = result["dom_candidate"]
        learn(old_selector, healed, tenant_id=tenant_id, ctx=ctx)
        if ctx:
            ctx.increment("healedSelectors")
        log("ENGINE", f"⚠ DOM fallback (score={score}) → {healed}", ctx=ctx)
        return {**result, "healed": healed, "strategy": "dom_fallback"}

    log("ENGINE", "All strategies exhausted", level="error", ctx=ctx)
    if ctx:
        ctx.increment("failures")
    return result
