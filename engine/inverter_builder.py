import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/inverter-cable-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7").strip()
CUSTOM_INVERTER = os.environ.get("CUSTOM_INVERTER", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_inverters.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Inverter Model / Setup Name, Continuous Watts, Surge Watts, System DC Volts, Efficiency, Rec Battery Ah)
SEED_INVERTERS = [
    ("Victron MultiPlus-II 12/3000/120-50 2x120V Inverter/Charger", 2400, 5500, 12, 0.93, 400),
    ("Victron MultiPlus 24/3000/70-50 Pure Sine Inverter/Charger", 2400, 6000, 24, 0.94, 200),
    ("Victron Quattro 48/5000/70-100 Off-Grid Inverter/Charger", 4000, 10000, 48, 0.95, 200),
    ("Victron Phoenix 12/1200 VE.Direct Pure Sine Wave Inverter", 1000, 2200, 12, 0.92, 200),
    ("Renogy 2000W 12V Pure Sine Wave Inverter w/ UPS Transfer", 2000, 4000, 12, 0.90, 200),
    ("Renogy 3000W 12V Pure Sine Wave Heavy-Duty RV Inverter", 3000, 6000, 12, 0.90, 400),
    ("Renogy 1000W 12V Pure Sine Wave Camper & Van Inverter", 1000, 2000, 12, 0.90, 100),
    ("Giandel 2200W 12V Pure Sine Wave Heavy-Duty Inverter", 2200, 4400, 12, 0.90, 200),
    ("Giandel 4000W 12V/24V Pure Sine Wave High-Output Inverter", 4000, 8000, 24, 0.91, 200),
    ("Giandel 1200W 12V Pure Sine Wave Truck & Camping Inverter", 1200, 2400, 12, 0.90, 100),
    ("Xantrex Freedom XC PRO 3000 (3000W / 150A) Inverter/Charger", 3000, 6000, 12, 0.91, 400),
    ("Xantrex Freedom XC 2000 (2000W / 80A) RV Inverter/Charger", 2000, 4000, 12, 0.91, 200),
    ("Xantrex PROwatt SW 2000 True Sine Wave 12V Inverter", 1800, 3000, 12, 0.90, 200),
    ("AIMS Power 3000W 12V Low-Frequency Pure Sine Inverter/Charger", 3000, 9000, 12, 0.90, 400),
    ("AIMS Power 4000W 24V Pure Sine Inverter/Charger (120V/240V)", 4000, 12000, 24, 0.91, 200),
    ("AIMS Power 6000W 48V Split-Phase Pure Sine Inverter", 6000, 18000, 48, 0.92, 200),
    ("Magnum Energy MS2012 (2000W 12V) Pure Sine Inverter/Charger", 2000, 3900, 12, 0.90, 300),
    ("Magnum Energy MS4024PAE (4000W 24V) Split-Phase Inverter", 4000, 5800, 24, 0.93, 200),
    ("Samlex Evolution EVO-2212 (2200W 12V) Marine Grade Inverter", 2200, 6600, 12, 0.91, 300),
    ("Samlex PST-1500-12 & PST-2000-12 Pure Sine Inverter", 2000, 4000, 12, 0.90, 200),
    ("Go Power! GP-ISW2000-12 & GP-IC-3000 RV Inverter Setup", 2000, 4000, 12, 0.90, 200),
    (" Krieger & BESTEK 2000W 12V Semi-Truck Sleeper Inverter", 2000, 4000, 12, 0.89, 200),
    ("WZRELB Reliable 3000W 24V/48V Pure Sine Wave Off-Grid", 3000, 6000, 24, 0.91, 200),
    ("Sungoldpower 4000W 24V / 6000W 48V Low-Frequency Inverter", 4000, 12000, 24, 0.91, 200),
    ("1000W 12V Pure Sine Wave Inverter Wire & Fuse Sizing", 1000, 2000, 12, 0.90, 100),
    ("1500W 12V Pure Sine Wave Inverter Wire & Fuse Sizing", 1500, 3000, 12, 0.90, 200),
    ("2000W 12V Pure Sine Wave Inverter Wire & Fuse Sizing", 2000, 4000, 12, 0.90, 200),
    ("3000W 12V vs 24V Pure Sine Inverter Wire & Fuse Sizing", 3000, 6000, 12, 0.90, 400),
    ("4000W 24V vs 48V Pure Sine Inverter Wire & Fuse Sizing", 4000, 8000, 24, 0.92, 200),
    ("5000W 48V Whole-Cabin Off-Grid Inverter Wire & Fuse Sizing", 5000, 10000, 48, 0.94, 200)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=2000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_inverter_queries():
    discovered = []
    seeds = [
        "what size wire for inverter ",
        "what size fuse for inverter ",
        "victron multiplus ",
        "renogy pure sine wave inverter "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|wire|fuse|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        w_m = re.search(r"(\d{4})\s*w", cleaned)
                        w_v = int(w_m.group(1)) if w_m else 2000
                        v_sys = 24 if ("24v" in cleaned or w_v >= 3500) else (48 if "48v" in cleaned else 12)
                        discovered.append((cleaned.title(), w_v, w_v * 2, v_sys, 0.90, 200))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_inverter_data(inv_tuple):
    """Mesin Fisika Inverter DC-ke-AC, ABYC E-11 Ampacity & Class-T Fuse (100% bebas gagal)."""
    model_name, cont_w, surge_w, dc_volts, eff, rec_ah = inv_tuple

    # Rumus Arus DC Kontinu Maksimum (saat baterai turun ke batas bawah 12.0V / 24.0V / 48.0V):
    # Max Continuous DC Amps = Continuous Watts / (DC Volts * Efficiency)
    cont_dc_amps = int(round(cont_w / (float(dc_volts) * eff)))
    surge_dc_amps = int(round(surge_w / (float(dc_volts) * eff)))

    # Aturan Sekring ABYC E-11 & NEC (1.25x dari Arus Kontinu Maksimum, dibulatkan ke ukuran standar Class-T / ANL)
    raw_fuse = cont_dc_amps * 1.25
    if raw_fuse <= 110:
        fuse_amps = 110
        cable_awg = "4 AWG 100% OFC Welding/Marine Copper"
    elif raw_fuse <= 150:
        fuse_amps = 150
        cable_awg = "2 AWG 100% OFC Welding/Marine Copper"
    elif raw_fuse <= 200:
        fuse_amps = 200
        cable_awg = "1/0 AWG 100% OFC Welding/Marine Copper"
    elif raw_fuse <= 250:
        fuse_amps = 250
        cable_awg = "2/0 AWG 100% OFC Welding/Marine Copper"
    elif raw_fuse <= 325:
        fuse_amps = 300
        cable_awg = "4/0 AWG 100% OFC Welding/Marine Copper"
    else:
        fuse_amps = 400
        cable_awg = "4/0 AWG (or Dual 2/0 AWG) 100% OFC Copper"

    # Runtime pada beban rumah tangga/RV rata-rata 50% (cont_w * 0.50):
    half_load_w = int(round(cont_w * 0.50))
    half_load_amps = round(cont_dc_amps * 0.50, 1)
    # LiFePO4 (90% usable DoD) vs Lead-Acid AGM (50% usable DoD + Peukert loss = ~42% efektif pada beban tinggi)
    lifepo4_hrs = round((rec_ah * 0.90) / max(5.0, half_load_amps), 1)
    agm_hrs = round((rec_ah * 0.42) / max(5.0, half_load_amps), 1)

    return {
        "inverter_name": model_name,
        "seo_title": f"{model_name} Wire Size (AWG), Fuse & Battery Runtime Calculator (2026)",
        "meta_description": f"Calculate exact DC amp draw ({cont_dc_amps}A continuous / {surge_dc_amps}A surge), ABYC copper cable size ({cable_awg}), {fuse_amps}A Class-T fuse, and {rec_ah}Ah LiFePO4 runtime ({lifepo4_hrs} hrs) for {model_name}.",
        "specs": {
            "continuous_watts": cont_w,
            "surge_watts": surge_w,
            "system_dc_volts": dc_volts,
            "inverter_efficiency": eff,
            "continuous_dc_amps": cont_dc_amps,
            "surge_dc_amps": surge_dc_amps,
            "recommended_fuse_amps": fuse_amps,
            "recommended_cable_awg": cable_awg,
            "recommended_battery_ah": rec_ah,
            "lifepo4_50pct_runtime_hrs": lifepo4_hrs,
            "agm_50pct_runtime_hrs": agm_hrs
        },
        "abyc_verdict": f"Delivering {cont_w:,}W continuous AC power ({surge_w:,}W peak surge) from a {dc_volts}V DC battery bank at {int(eff*100)}% conversion efficiency, the {model_name} draws up to {cont_dc_amps} Amps DC continuously ({surge_dc_amps}A instantaneous surge). Per ABYC E-11 and NEC 125% overcurrent rules ( keeping voltage drop under 3% over a 5-foot cable run), wire this inverter with {cable_awg} protected by a {fuse_amps}-Amp Class-T Fuse within 7 inches of the positive battery terminal. On a {dc_volts}V {rec_ah}Ah LiFePO4 battery bank at a 50% load ({half_load_w:,}W), expect ~{lifepo4_hrs} hours of runtime (vs. just {agm_hrs} hours on lead-acid AGM).",
        "hardware_bundle": [
            {
                "badge": f"{cont_w:,}W / {dc_volts}V Inverter",
                "title": f"{model_name} Pure Sine Wave Power System",
                "price_range": "$189 - $1,399",
                "amazon_query": f"{model_name} Pure Sine Wave Inverter",
                "inv_note": f"Produces grid-grade <3% THD pure sine wave AC power for sensitive induction cooktops, microwaves, and CPAPs."
            },
            {
                "badge": f"{fuse_amps}A Class-T Fuse & Block",
                "title": f"Blue Sea / Littelfuse {fuse_amps}-Amp Class-T Fuse Block (20,000A AIC) + 300A Copper BusBars",
                "price_range": "$54 - $129",
                "amazon_query": f"{fuse_amps} Amp Class T Fuse Block Holder High Interrupt LiFePO4",
                "inv_note": f"LiFePO4 batteries can dump 3,000+ Amps during a dead short; a 20,000A AIC Class-T fuse extinguishes DC arcs without exploding."
            },
            {
                "badge": f"{cable_awg.split()[0]} AWG OFC Cable Kit",
                "title": f"Ultra-Flexible {cable_awg} Battery Inverter Cables (Red/Black) + Tinned Copper 3/8\" Lugs",
                "price_range": "$59 - $169",
                "amazon_query": f"{cable_awg.split()[0]} AWG Pure Copper Battery Inverter Cables 3/8 Lugs",
                "inv_note": f"Fine-stranded 100% Oxygen-Free Copper handles {cont_dc_amps}A continuous draw without melting insulation or causing low-voltage inverter shutdowns."
            },
            {
                "badge": f"{dc_volts}V {rec_ah}Ah LiFePO4 Bank",
                "title": f"{dc_volts}V {rec_ah}Ah Deep-Cycle LiFePO4 Lithium Battery Bank (200A+ BMS Discharge)",
                "price_range": "$329 - $1,199",
                "amazon_query": f"{dc_volts}V {rec_ah}Ah LiFePO4 Lithium Battery 200A BMS",
                "inv_note": f"Maintains flat {dc_volts + 1.2}V+ voltage under heavy {cont_dc_amps}A inverter loads with zero Peukert capacity loss."
            }
        ],
        "wiring_checklist": [
            f"Keep DC battery-to-inverter cables as short as possible (ideally 3 to 6 feet one-way) using {cable_awg}; DC voltage drop scales with round-trip wire length (Positive + Negative).",
            f"Install a {fuse_amps}-Amp Class-T Fuse (not a cheap plastic audio circuit breaker!) within 7 inches of the battery positive post; cheap resettable breakers weld shut or cause 0.8V voltage drops at {cont_dc_amps}A.",
            "Pre-charge the inverter's internal capacitors using a 25W 10-Ohm resistor (or pre-charge bulb) across the disconnect switch for 5 seconds before closing the main battery switch to prevent a violent spark that trips your LiFePO4 BMS.",
            "Bond the inverter chassis grounding lug directly to your vehicle frame or boat negative DC grounding busbar using an 8 AWG or 6 AWG bare/green copper conductor."
        ],
        "faqs": [
            {
                "q": f"What size wire and fuse do I need for the {model_name} ({cont_w:,}W at {dc_volts}V)?",
                "a": f"Divide {cont_w:,}W by ({dc_volts}V × {eff} efficiency) to get {cont_dc_amps} Amps continuous DC draw. Multiplying by the 1.25x NEC/ABYC safety factor requires a {fuse_amps}-Amp Class-T or ANL fuse and {cable_awg} cables (for runs up to 6 feet)."
            },
            {
                "q": f"How long will a {rec_ah}Ah battery run a {cont_w:,}W ({dc_volts}V) inverter?",
                "a": f"At full {cont_w:,}W continuous output ({cont_dc_amps}A), a {dc_volts}V {rec_ah}Ah LiFePO4 battery runs for {round((rec_ah * 0.90) / max(5.0, cont_dc_amps), 1)} hours. At a realistic 50% load ({half_load_w:,}W / {half_load_amps}A), a LiFePO4 bank runs for {lifepo4_hrs} hours, whereas a {rec_ah}Ah Lead-Acid AGM battery lasts only {agm_hrs} hours due to Peukert voltage sag."
            },
            {
                "q": f"Why does my {cont_w:,}W inverter beep and shut off with a 'Low Voltage' alarm when my battery is at 70%?",
                "a": f"Undersized cables (or cheap Copper-Clad Aluminum CCA wires) and loose crimps create a 1.5V to 2.5V voltage drop when you pull {cont_dc_amps} Amps, causing the inverter terminals to drop below 10.5V even when the battery itself is full. Upgrading to {cable_awg} solves this immediately."
            }
        ]
    }


def generate_inverter_data(inv_tuple):
    if not GEMINI_API_KEY:
        return build_deterministic_inverter_data(inv_tuple)

    model_name, cont_w, surge_w, dc_volts, eff, rec_ah = inv_tuple
    det_fallback = build_deterministic_inverter_data(inv_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are an ABYC Certified Master Marine/RV Electrical Engineer & Off-Grid Power Systems Architect. Create an accurate 2026 DC amp draw, welding-grade AWG battery cable, Class-T fuse, and LiFePO4 battery runtime guide for: "{model_name}".
Baseline specs: Continuous Power={cont_w}W, Surge={surge_w}W, System Voltage={dc_volts}V DC, Efficiency={int(eff*100)}%, Max Continuous DC Current={sp['continuous_dc_amps']}A (Surge {sp['surge_dc_amps']}A), Fuse={sp['recommended_fuse_amps']}A Class-T, Cable={sp['recommended_cable_awg']}, Battery Bank={dc_volts}V {rec_ah}Ah ({sp['lifepo4_50pct_runtime_hrs']} hrs @ 50% load).
Return ONLY a valid JSON object matching this exact schema:
{{
  "inverter_name": "{model_name}",
  "seo_title": "{model_name} Wire Size (AWG), Fuse & Battery Runtime Calculator (2026)",
  "meta_description": "Calculate exact DC amp draw, ABYC copper battery cable gauge (AWG), Class-T fuse rating, and LiFePO4 runtime for {model_name}.",
  "specs": {{
    "continuous_watts": {cont_w},
    "surge_watts": {surge_w},
    "system_dc_volts": {dc_volts},
    "inverter_efficiency": {eff},
    "continuous_dc_amps": {sp['continuous_dc_amps']},
    "surge_dc_amps": {sp['surge_dc_amps']},
    "recommended_fuse_amps": {sp['recommended_fuse_amps']},
    "recommended_cable_awg": "{sp['recommended_cable_awg']}",
    "recommended_battery_ah": {rec_ah},
    "lifepo4_50pct_runtime_hrs": {sp['lifepo4_50pct_runtime_hrs']},
    "agm_50pct_runtime_hrs": {sp['agm_50pct_runtime_hrs']}
  }},
  "abyc_verdict": "3-sentence technical summary stating continuous DC amps, 1.25x Class-T fuse rating, required OFC copper cable gauge, and 50%-load runtime on LiFePO4 vs AGM.",
  "hardware_bundle": [
    {{
      "badge": "{cont_w}W / {dc_volts}V Inverter",
      "title": "{model_name}",
      "price_range": "$189 - $1,399",
      "amazon_query": "{model_name} Pure Sine Wave Inverter",
      "inv_note": "1-sentence pure sine THD and surge capacity note"
    }},
    {{
      "badge": "{sp['recommended_fuse_amps']}A Class-T Fuse Kit",
      "title": "{sp['recommended_fuse_amps']}-Amp Class-T Fuse Block (20,000A AIC) + 300A Copper BusBars",
      "price_range": "$54 - $129",
      "amazon_query": "{sp['recommended_fuse_amps']} Amp Class T Fuse Block Holder LiFePO4",
      "inv_note": "1-sentence LiFePO4 short-circuit AIC protection note"
    }},
    {{
      "badge": "{sp['recommended_cable_awg'].split()[0]} AWG OFC Cable",
      "title": "Ultra-Flexible {sp['recommended_cable_awg']} Inverter Cables + Tinned Copper Lugs",
      "price_range": "$59 - $169",
      "amazon_query": "{sp['recommended_cable_awg'].split()[0]} AWG Pure Copper Battery Inverter Cables",
      "inv_note": "1-sentence <3% voltage drop prevention note"
    }},
    {{
      "badge": "{dc_volts}V {rec_ah}Ah LiFePO4",
      "title": "{dc_volts}V {rec_ah}Ah Deep-Cycle LiFePO4 Battery Bank (200A+ BMS)",
      "price_range": "$329 - $1,199",
      "amazon_query": "{dc_volts}V {rec_ah}Ah LiFePO4 Lithium Battery",
      "inv_note": "1-sentence flat discharge curve and runtime note"
    }}
  ],
  "wiring_checklist": [
    "Step 1 regarding keeping DC cable runs under 6 feet with 100% OFC copper",
    "Step 2 regarding 20,000A AIC Class-T fuse placement within 7 inches of battery",
    "Step 3 regarding capacitor pre-charge resistor to prevent BMS trip spark",
    "Step 4 regarding chassis ground bonding and hydraulic lug crimping"
  ],
  "faqs": [
    {{"q": "What size wire and fuse do I need for the {model_name}?", "a": "Exact DC amps formula, 1.25x fuse rating, and AWG cable gauge."}},
    {{"q": "How long will a {rec_ah}Ah battery run the {model_name}?", "a": "Exact runtime hours at 100% load and 50% load comparing LiFePO4 vs AGM."}},
    {{"q": "Should I build a 12V, 24V, or 48V battery bank for {cont_w}W?", "a": "Direct electrical comparison showing how doubling voltage halves DC current and wire size."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")

    return det_fallback


def build_inverter_html_page(data, slug, mon_cfg):
    inv_name = data.get("inverter_name", "Pure Sine Wave Inverter")
    sp = data.get("specs", {})
    cont_w = int(safe_float(sp.get("continuous_watts", 2000), 2000))
    surge_w = int(safe_float(sp.get("surge_watts", 4000), 4000))
    dc_v = int(safe_float(sp.get("system_dc_volts", 12), 12))
    cont_a = int(safe_float(sp.get("continuous_dc_amps", 185), 185))
    fuse_a = int(safe_float(sp.get("recommended_fuse_amps", 250), 250))
    cable_awg = sp.get("recommended_cable_awg", "2/0 AWG 100% OFC Copper")
    rec_ah = int(safe_float(sp.get("recommended_battery_ah", 200), 200))
    life_hrs = round(safe_float(sp.get("lifepo4_50pct_runtime_hrs", 1.9), 1.9), 1)
    agm_hrs = round(safe_float(sp.get("agm_50pct_runtime_hrs", 0.9), 0.9), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pure+Sine+Wave+Power+Inverter+Class+T+Fuse"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{inv_name} Wire Gauge, Fuse & Battery Runtime Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Pure Sine Wave Inverter")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-emerald-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'DC Power Gear')}</span>
              <span class="text-sm font-bold text-amber-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🔋 {item.get('inv_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build 12V vs 24V vs 48V Inverter Wire & Fuse Reference Matrix Table
    inv_tiers = [
        ("1,000W Continuous (12V)", "93 Amps DC", "4 AWG OFC Copper", "125A ANL / Class-T", "12V 100Ah LiFePO4"),
        ("1,500W Continuous (12V)", "139 Amps DC", "2 AWG OFC Copper", "175A Class-T Fuse", "12V 200Ah LiFePO4"),
        ("2,000W Continuous (12V)", "185 Amps DC", "2/0 AWG OFC Copper", "250A Class-T Fuse", "12V 200Ah–300Ah"),
        ("3,000W Continuous (12V)", "278 Amps DC", "4/0 AWG OFC Copper", "350A–400A Class-T", "12V 400Ah (2x 200Ah)"),
        ("3,000W Continuous (24V)", "139 Amps DC", "2 AWG / 1/0 AWG OFC", "175A–200A Class-T", "24V 200Ah LiFePO4"),
        ("5,000W Continuous (48V)", "116 Amps DC", "2 AWG OFC Copper", "150A Class-T Fuse", "48V 100Ah–200Ah Rack")
    ]
    matrix_rows_html = ""
    for w_lbl, a_lbl, c_lbl, f_lbl, b_lbl in inv_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{w_lbl}</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{a_lbl}</td>
          <td class="py-3 px-4 text-amber-400 font-semibold">{c_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{f_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{b_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("wiring_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-emerald-500 rounded cursor-pointer inv-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>ABYC Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', inv_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', inv_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">INVERTER</span>CableIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Inverters & Class-T Fuses →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-emerald-500 text-slate-950 px-3 py-1 rounded-full">{cont_w:,}W ({dc_v}V DC) | {cont_a}A Draw</span>
        <span class="text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 px-3 py-1 rounded-full">Wire: {cable_awg.split()[0]} AWG | {fuse_a}A Class-T Fuse</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{rec_ah}Ah LiFePO4 (50% Load): ~{life_hrs} hrs</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', inv_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-emerald-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ABYC E-11 & LiFePO4 Engineering Verdict:</strong> {data.get('abyc_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE DC AMP DRAW, AWG CABLE GAUGE, CLASS-T FUSE & RUNTIME CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {inv_name} Cable, Fuse & Runtime Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your inverter continuous wattage, battery system voltage (12V/24V/48V), one-way cable length, and battery bank Ah capacity to compute exact DC amps, AWG wire gauge, Class-T fuse rating, and LiFePO4 runtime.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="wattSlider" class="text-slate-300">Inverter Continuous AC Load (Watts)</label>
              <span class="text-emerald-400 font-bold"><span id="wattVal">{cont_w:,}</span> Watts</span>
            </div>
            <input id="wattSlider" type="range" min="500" max="6000" step="100" value="{cont_w}" class="w-full accent-emerald-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="voltSelect" class="block text-xs font-medium text-slate-400 mb-1">Battery Bank Voltage</label>
              <select id="voltSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="12" {"selected" if dc_v == 12 else ""}>12V DC System</option>
                <option value="24" {"selected" if dc_v == 24 else ""}>24V DC System</option>
                <option value="48" {"selected" if dc_v == 48 else ""}>48V DC System</option>
              </select>
            </div>
            <div>
              <label for="lenSelect" class="block text-xs font-medium text-slate-400 mb-1">One-Way Cable Distance</label>
              <select id="lenSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="3">3 Feet (6 ft Round-Trip)</option>
                <option value="5" selected>5 Feet (10 ft Round-Trip)</option>
                <option value="8">8 Feet (16 ft Round-Trip)</option>
                <option value="12">12 Feet (24 ft Round-Trip)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="ahSlider" class="text-slate-300">Battery Bank Total Capacity (Amp-Hours @ {dc_v}V)</label>
              <span class="text-emerald-400 font-bold"><span id="ahVal">{rec_ah}</span> Ah</span>
            </div>
            <input id="ahSlider" type="range" min="100" max="800" step="50" value="{rec_ah}" class="w-full accent-emerald-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Cable & Class-T Fuse</span>
            <div id="cableOut" class="text-xl sm:text-2xl font-black text-white mt-1">{cable_awg.split()[0]} AWG</div>
            <p id="fuseOut" class="text-xs text-emerald-400 font-semibold mt-1">{cont_a}A Draw → {fuse_a}A Fuse</p>
          </div>

          <div class="bg-slate-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">LiFePO4 Runtime</span>
            <div class="text-xl sm:text-2xl font-black text-amber-400 mt-1">~<span id="runtimeOut">{life_hrs}</span> <span class="text-xs font-normal text-slate-400">hrs</span></div>
            <p id="agmNoteOut" class="text-xs text-slate-300 font-semibold mt-1">Full Load (vs {agm_hrs}h AGM)</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="invAdviceBanner" class="text-sm text-emerald-100 font-medium"></div>
        <a id="dynamicInvBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Cables & Class-T Fuse on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {inv_name} Cable, Fuse & LiFePO4 Hardware Bundle</h2>
        <span class="text-xs text-slate-400">ABYC E-11 & 20,000A AIC Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- INVERTER WIRING MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Inverter Wattage, DC Amp Draw, AWG Copper Wire & Class-T Fuse Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Inverter Size & Voltage</th>
              <th class="py-3.5 px-4 text-emerald-400">Max Continuous DC Amps</th>
              <th class="py-3.5 px-4 text-amber-400">Minimum OFC Cable (≤6 ft)</th>
              <th class="py-3.5 px-4">Class-T / ANL Fuse</th>
              <th class="py-3.5 px-4">Min LiFePO4 Bank</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- WIRING CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ABYC Marine & RV Inverter Pre-Charge & Fuse Safety Checklist</h2>
        <span id="invBadge" class="text-xs font-bold bg-slate-800 text-emerald-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({inv_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} InverterCableIndex. Independent DC-to-AC Power Inverter & ABYC Cable Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const wattSlider = document.getElementById('wattSlider');
    const voltSelect = document.getElementById('voltSelect');
    const lenSelect = document.getElementById('lenSelect');
    const ahSlider = document.getElementById('ahSlider');
    const wattVal = document.getElementById('wattVal');
    const ahVal = document.getElementById('ahVal');
    const cableOut = document.getElementById('cableOut');
    const fuseOut = document.getElementById('fuseOut');
    const runtimeOut = document.getElementById('runtimeOut');
    const agmNoteOut = document.getElementById('agmNoteOut');
    const invAdviceBanner = document.getElementById('invAdviceBanner');
    const dynamicInvBtn = document.getElementById('dynamicInvBtn');

    function recalculateInverter() {{
      const watts = parseInt(wattSlider.value, 10);
      const volts = parseInt(voltSelect.value, 10);
      const oneWayFt = parseInt(lenSelect.value, 10);
      const bankAh = parseInt(ahSlider.value, 10);

      wattVal.textContent = watts.toLocaleString();
      ahVal.textContent = bankAh;

      const dcAmps = Math.round(watts / (volts * 0.90));
      const reqFuseRaw = dcAmps * 1.25;

      let stdFuse = 100;
      if (reqFuseRaw <= 110) stdFuse = 110;
      else if (reqFuseRaw <= 150) stdFuse = 150;
      else if (reqFuseRaw <= 200) stdFuse = 200;
      else if (reqFuseRaw <= 250) stdFuse = 250;
      else if (reqFuseRaw <= 300) stdFuse = 300;
      else if (reqFuseRaw <= 350) stdFuse = 350;
      else stdFuse = 400;

      // Upsize cable if one-way distance > 6 ft
      const effAmpsForDrop = oneWayFt > 6 ? dcAmps * 1.25 : dcAmps;
      let awgLabel = "2/0 AWG";
      if (effAmpsForDrop <= 85) awgLabel = "4 AWG";
      else if (effAmpsForDrop <= 125) awgLabel = "2 AWG";
      else if (effAmpsForDrop <= 165) awgLabel = "1/0 AWG";
      else if (effAmpsForDrop <= 215) awgLabel = "2/0 AWG";
      else if (effAmpsForDrop <= 300) awgLabel = "4/0 AWG";
      else awgLabel = "Dual 2/0 AWG";

      const fullLoadLifeHrs = ((bankAh * 0.90) / Math.max(5.0, dcAmps)).toFixed(1);
      const halfLoadLifeHrs = ((bankAh * 0.90) / Math.max(5.0, dcAmps * 0.50)).toFixed(1);
      const fullLoadAgmHrs = ((bankAh * 0.42) / Math.max(5.0, dcAmps)).toFixed(1);

      cableOut.textContent = `${{awgLabel}} OFC`;
      fuseOut.textContent = `${{dcAmps}}A Draw → ${{stdFuse}}A Class-T`;
      runtimeOut.textContent = fullLoadLifeHrs;
      agmNoteOut.textContent = `50% Load: ${{halfLoadLifeHrs}}h (AGM: ${{fullLoadAgmHrs}}h)`;

      invAdviceBanner.innerHTML = `🔋 <strong>ABYC E-11 Spec:</strong> Pulling <strong>${{watts.toLocaleString()}}W at ${{volts}}V DC</strong> draws <strong>${{dcAmps}} Amps</strong>. Wire with <strong>${{awgLabel}} 100% OFC Welding/Marine Cable</strong> and a <strong>${{stdFuse}}-Amp Class-T Fuse</strong> within 7" of your ${{volts}}V ${{bankAh}}Ah LiFePO4 bank.`;
      dynamicInvBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(awgLabel)}}+Pure+Copper+Battery+Inverter+Cable+${{stdFuse}}+Amp+Class+T+Fuse+Block&tag=${{amzTag}}`;
    }}

    wattSlider.addEventListener('input', recalculateInverter);
    voltSelect.addEventListener('change', recalculateInverter);
    lenSelect.addEventListener('change', recalculateInverter);
    ahSlider.addEventListener('input', recalculateInverter);
    recalculateInverter();

    const checks = document.querySelectorAll('.inv-check');
    const badge = document.getElementById('invBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pure+Sine+Wave+Power+Inverter+Class+T+Fuse"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-emerald-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-emerald-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('watts', 2000):,}W ({item.get('volts', 12)}V)</span>
            <span class="text-xs text-slate-400">{item.get('dc_amps', 185)}A | {item.get('fuse_a', 250)}A Fuse</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-emerald-400 transition">{item['inverter_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-emerald-400">Calculate Wire AWG, Fuse & Runtime →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InverterCableIndex — 12V/24V/48V Power Inverter Wire Size, Fuse & Battery Calculator (2026)</title>
  <meta name="description" content="Calculate exact DC amp draw, 4/0 to 4 AWG welding-grade copper battery cable size, Class-T fuse ratings, and LiFePO4 runtime for Victron MultiPlus, Renogy, Giandel, Xantrex, and AIMS pure sine wave inverters.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="InverterCableIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">INVERTER</span>CableIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Inverters & Class-T Fuses →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Power Inverter Wire Size (AWG), Class-T Fuse & Battery Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your 12V, 24V, or 48V pure sine wave inverter below to calculate continuous DC amp draw, ABYC copper battery cable gauge, 20,000A AIC Class-T fuse size, and LiFePO4 runtime.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search inverter model or wattage (e.g. Victron MultiPlus 3000, Renogy 2000W, Giandel, Xantrex, 12V, 24V...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-emerald-500">
      </div>
    </div>

    <div id="invGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} InverterCableIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('invGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>InverterCableIndex Power Inverter & Battery Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive 12V/24V/48V Power Inverter Wire Gauge, Class-T Fuse & LiFePO4 Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_INVERTER:
        candidates.append((CUSTOM_INVERTER.strip(), 2000, 4000, 12, 0.90, 200))
    candidates.extend(SEED_INVERTERS)
    candidates.extend(discover_google_inverter_queries())

    new_urls = []
    count = 0

    for inv_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        i_name = inv_tuple[0]
        slug = slugify(f"{i_name}-wire-fuse-battery-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating power inverter wire & fuse calculator for: {i_name}...")
        try:
            data = generate_inverter_data(inv_tuple)
            build_inverter_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "inverter_name": data.get("inverter_name", i_name),
                "slug": slug,
                "title": data.get("seo_title", f"{i_name} Wire & Fuse Calculator"),
                "description": data.get("meta_description", ""),
                "watts": int(safe_float(sp.get("continuous_watts", inv_tuple[1]), inv_tuple[1])),
                "volts": int(safe_float(sp.get("system_dc_volts", inv_tuple[3]), inv_tuple[3])),
                "dc_amps": int(safe_float(sp.get("continuous_dc_amps", 185), 185)),
                "fuse_a": int(safe_float(sp.get("recommended_fuse_amps", 250), 250)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {i_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new power inverter wire & fuse calculator pages.")


if __name__ == "__main__":
    main()
