import json
import os

DATA_DIR = "data"

def load_json(filename: str):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                return []
    return []

COLLEGES_DATA = load_json("colleges.json")
TFC_DATA = load_json("tnea_tfc.json") or load_json("tfc.json")
RULES_DATA = load_json("tnea_rules.json") or load_json("rules.json")
BROCHURE_DATA = load_json("brochure_chunks.json")

def find_colleges(district: str = None, category: str = None, autonomous: str = None):
    results = []
    target_dist = district.strip().lower() if district else ""
    target_cat = category.strip().lower() if category else ""
    target_auto = autonomous.strip().lower() if autonomous else ""

    for col in COLLEGES_DATA:
        if not isinstance(col, dict): continue
        contact = col.get("contact_details") or {}
        col_dist = (contact.get("district") or "").lower()
        if target_dist and target_dist not in col_dist: continue

        col_cat = (col.get("college_category") or "").lower()
        if target_cat and target_cat not in col_cat: continue

        gen_info = col.get("general_info") or {}
        col_auto = (gen_info.get("autonomous_status") or "").lower()
        if target_auto and target_auto != col_auto: continue

        results.append({
            "code": col.get("tnea_code"),
            "name": col.get("college_name"),
            "district": contact.get("district") or "N/A",
            "category": col.get("college_category") or "N/A",
            "autonomous": gen_info.get("autonomous_status") or "No"
        })
    return results[:10]

def get_tfc_centers(district: str):
    if not district: return []
    target = district.strip().lower()
    results = []
    for tfc in TFC_DATA:
        if not isinstance(tfc, dict): continue
        if target in (tfc.get("district") or "").lower():
            results.append(tfc)
    return results

def get_tnea_rules(query: str):
    if not query: return ["No query provided."]
    q_lower = query.strip().lower()
    results = []
    
    for rule in RULES_DATA:
        if not isinstance(rule, dict): continue
        keywords = rule.get("keywords") or []
        if any(kw.lower() in q_lower for kw in keywords if isinstance(kw, str)):
            results.append(rule.get("content"))

    if not results:
        for chunk in BROCHURE_DATA:
            if not isinstance(chunk, dict): continue
            content = chunk.get("content") or ""
            if any(term in content.lower() for term in q_lower.split()):
                results.append(content)
                if len(results) >= 3: break

    return results if results else ["Please refer to the official TNEA guidelines for details on this."]