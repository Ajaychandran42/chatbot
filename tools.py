import json
import os
import re
from typing import Optional, List, Dict, Any

DATA_DIR = "data"

def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        path = filename  # Fallback to root directory
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return []
    return []

# Pre-load datasets into memory for fast tool lookups
COLLEGES = _load_json("colleges.json")
SEAT_MATRIX = _load_json("seat_matrix_2026.json")
TNEA_DATA = _load_json("tnea_data.json")
TNEA_5YRS = _load_json("tnea_5yrs.json")
TFC_CENTERS = _load_json("tnea_tfc.json")
TNEA_RULES = _load_json("tnea_rules.json")
BROCHURE_CHUNKS = _load_json("brochure_chunks.json")

# Extract 5-year historical datasets
COMPARE_CUTOFFS: List[Dict[str, Any]] = []
COMPARE_RANKS: List[Dict[str, Any]] = []
if isinstance(TNEA_5YRS, dict):
    datasets = TNEA_5YRS.get("datasets", {})
    COMPARE_CUTOFFS = datasets.get("compare", {}).get("cutoff", {}).get("data", [])
    COMPARE_RANKS = datasets.get("compare", {}).get("rank", {}).get("data", [])

# Fast index for rank data: (college_code, branch_code) -> rank item
RANK_MAP: Dict[str, Dict[str, Any]] = {}
for r_item in COMPARE_RANKS:
    c_code = str(r_item.get("college_code", "")).strip()
    b_code = str(r_item.get("branch_code", "")).strip().upper()
    if c_code and b_code:
        RANK_MAP[f"{c_code}_{b_code}"] = r_item

BRANCH_MAPPINGS = {
    "CSE": {"codes": ["CS", "CM", "CG", "AM", "SC", "CB", "CD", "CI"], "keywords": ["computer science", "computing"]},
    "CS": {"codes": ["CS", "CM", "CG", "AM", "SC", "CB", "CD", "CI"], "keywords": ["computer science", "computing"]},
    "COMPUTER SCIENCE": {"codes": ["CS", "CM", "CG", "AM", "SC", "CB", "CD", "CI"], "keywords": ["computer science", "computing"]},
    "IT": {"codes": ["IT", "IM", "IF", "IS"], "keywords": ["information technology"]},
    "INFORMATION TECHNOLOGY": {"codes": ["IT", "IM", "IF", "IS"], "keywords": ["information technology"]},
    "ECE": {"codes": ["EC", "EM", "EA", "ET", "EV", "CO"], "keywords": ["electronics and communication", "electronics & communication"]},
    "EC": {"codes": ["EC", "EM", "EA", "ET", "EV", "CO"], "keywords": ["electronics and communication", "electronics & communication"]},
    "ELECTRONICS": {"codes": ["EC", "EM", "EA", "ET", "EV", "EE", "EY", "ES"], "keywords": ["electronics"]},
    "EEE": {"codes": ["EE", "EY", "ES", "EL"], "keywords": ["electrical and electronics", "electrical & electronics"]},
    "EE": {"codes": ["EE", "EY", "ES", "EL"], "keywords": ["electrical and electronics", "electrical & electronics"]},
    "ELECTRICAL": {"codes": ["EE", "EY", "ES", "EL"], "keywords": ["electrical"]},
    "MECH": {"codes": ["ME", "MF", "MS"], "keywords": ["mechanical"]},
    "ME": {"codes": ["ME", "MF", "MS"], "keywords": ["mechanical"]},
    "MECHANICAL": {"codes": ["ME", "MF", "MS"], "keywords": ["mechanical"]},
    "CIVIL": {"codes": ["CE", "CN"], "keywords": ["civil"]},
    "CE": {"codes": ["CE", "CN"], "keywords": ["civil"]},
    "AIDS": {"codes": ["AD", "AM", "CG", "AL", "AI"], "keywords": ["artificial intelligence", "data science"]},
    "AI": {"codes": ["AD", "AM", "CG", "AL", "AI"], "keywords": ["artificial intelligence", "data science"]},
    "AD": {"codes": ["AD", "AM", "CG", "AL", "AI"], "keywords": ["artificial intelligence", "data science"]},
    "AIML": {"codes": ["AM", "CG", "AL"], "keywords": ["artificial intelligence and machine learning", "ai & ml", "ai and ml"]},
    "CYBER": {"codes": ["SC", "CY"], "keywords": ["cyber security", "cyber"]},
    "BME": {"codes": ["BM", "BY"], "keywords": ["bio medical", "biomedical"]},
    "BM": {"codes": ["BM", "BY"], "keywords": ["bio medical", "biomedical"]},
    "BT": {"codes": ["BT", "BS"], "keywords": ["bio technology", "biotechnology"]},
    "BS": {"codes": ["BT", "BS"], "keywords": ["bio technology", "biotechnology"]},
    "BIOTECH": {"codes": ["BT", "BS"], "keywords": ["bio technology", "biotechnology"]},
    "BIOMEDICAL": {"codes": ["BM", "BY"], "keywords": ["bio medical", "biomedical"]},
    "CHEM": {"codes": ["CH", "CL"], "keywords": ["chemical"]},
    "CHEMICAL": {"codes": ["CH", "CL"], "keywords": ["chemical"]},
    "AERO": {"codes": ["AE", "AO"], "keywords": ["aeronautical", "aerospace"]},
    "AERONAUTICAL": {"codes": ["AE", "AO"], "keywords": ["aeronautical", "aerospace"]},
    "AUTO": {"codes": ["AS", "AU"], "keywords": ["automobile"]},
    "AUTOMOBILE": {"codes": ["AS", "AU"], "keywords": ["automobile"]},
    "ROBOTICS": {"codes": ["RA", "RO", "RM"], "keywords": ["robotics"]},
    "PROD": {"codes": ["PR", "PN", "PS"], "keywords": ["production"]},
    "PRODUCTION": {"codes": ["PR", "PN", "PS"], "keywords": ["production"]},
    "TX": {"codes": ["TX", "TT"], "keywords": ["textile"]},
    "TEXTILE": {"codes": ["TX", "TT"], "keywords": ["textile"]},
    "FT": {"codes": ["FY", "FT"], "keywords": ["fashion"]},
    "FASHION": {"codes": ["FY", "FT"], "keywords": ["fashion"]},
    "METALLURGY": {"codes": ["MT", "MY"], "keywords": ["metallurg"]},
    "MT": {"codes": ["MT", "MY"], "keywords": ["metallurg"]},
}

TOP_COLLEGES = [
    {"rank": 1, "tnea_code": 1,    "short_name": "CEG",  "college_name": "College of Engineering, Guindy (CEG)", "district": "Chennai", "type": "Government / CEG Dept"},
    {"rank": 2, "tnea_code": 4,    "short_name": "MIT",  "college_name": "Madras Institute of Technology (MIT Campus)", "district": "Chengalpattu", "type": "Government / CEG Dept"},
    {"rank": 3, "tnea_code": 2006, "short_name": "PSG Tech", "college_name": "PSG College of Technology (Autonomous)", "district": "Coimbatore", "type": "Government Aided"},
    {"rank": 4, "tnea_code": 2007, "short_name": "CIT",  "college_name": "Coimbatore Institute of Technology (Autonomous)", "district": "Coimbatore", "type": "Government Aided"},
    {"rank": 5, "tnea_code": 2005, "short_name": "GCT",  "college_name": "Government College of Technology (Autonomous)", "district": "Coimbatore", "type": "Government"},
    {"rank": 6, "tnea_code": 5008, "short_name": "TCE",  "college_name": "Thiagarajar College of Engineering (Autonomous)", "district": "Madurai", "type": "Government Aided"},
    {"rank": 7, "tnea_code": 1315, "short_name": "SSN",  "college_name": "Sri Sivasubramaniya Nadar College of Engineering (Autonomous)", "district": "Kanchipuram", "type": "Self-Financing Tier 1"},
    {"rank": 8, "tnea_code": 2615, "short_name": "GCE Salem", "college_name": "Government College of Engineering (Autonomous), Salem", "district": "Salem", "type": "Government"},
    {"rank": 9, "tnea_code": 4974, "short_name": "GCE Tirunelveli", "college_name": "Government College of Engineering, Tirunelveli", "district": "Tirunelveli", "type": "Government"},
    {"rank": 10, "tnea_code": 2712, "short_name": "KCT", "college_name": "Kumaraguru College of Technology (Autonomous)", "district": "Coimbatore", "type": "Self-Financing Tier 1"},
]


COLLEGE_ALIASES = {
    "psg tech": ["2006", "psg college of technology"],
    "psg": ["2006", "2377", "psg"],
    "cit": ["1399", "2007", "chennai institute of technology", "coimbatore institute of technology"],
    "chennai institute of technology": ["1399"],
    "coimbatore institute of technology": ["2007"],
    "ceg": ["1", "ceg campus", "college of engineering guindy"],
    "mit": ["4", "madras institute of technology"],
    "act": ["2", "act campus", "alagappa chettiar"],
    "ssn": ["1315", "sri sivasubramaniya nadar"],
    "gct": ["2005", "government college of technology"],
    "tce": ["5008", "thiagarajar"],
    "skcet": ["2718", "sri krishna college of engineering and technology"],
    "svce": ["1219", "sri venkateswara"],
    "rec": ["1211", "rajalakshmi engineering"],
    "licet": ["1128", "loyola"],
    "kct": ["2712", "kumaraguru"],
    "rmk": ["1113", "r.m.k."],
    "rmd": ["1112", "r.m.d."],
    "saveetha": ["2127", "1216", "saveetha"],
    "valliammai": ["1422", "srm valliammai"],
    "srm": ["1422", "1321", "srm"],
    "loyola": ["1128", "loyola"],
    "thiagarajar": ["5008", "thiagarajar"],
}

def match_college(query: str, college_field: str, code_field: str = "") -> bool:
    q = query.strip().lower()
    c_text = college_field.lower()
    c_code = str(code_field).strip()

    if not q:
        return True

    digits = re.findall(r'\b\d{1,4}\b', q)
    for d in digits:
        if d == c_code or f"({d})" in c_text or f" {d} " in f" {c_text} " or c_text.endswith(f" {d}"):
            return True

    for alias_key, targets in COLLEGE_ALIASES.items():
        if alias_key in q or q in alias_key:
            for t in targets:
                if t.isdigit():
                    # Numeric alias targets are college codes: match the passed
                    # code or the trailing "(code)" in the college text — never a
                    # bare substring (avoids matching "1" inside postcodes).
                    if c_code and t == c_code:
                        return True
                    m = re.search(r'\((\d{1,4})\)\s*$', c_text)
                    if m and m.group(1) == t:
                        return True
                elif t == c_code or t in c_text:
                    return True
            # The query is an exact known alias (e.g. "MIT", "CEG") but none of
            # its alias targets matched — the alias is authoritative, so stop
            # here rather than false-matching a short token inside place names.
            if q == alias_key:
                return False

    # If the entire query is an exact alias key (e.g. "MIT", "CEG", "PSG"),
    # the alias branch above is authoritative — do NOT fall through to generic
    # word-substring matching, which can false-match short tokens inside place
    # names (e.g. "mit" inside "kumittipathy").
    if q not in COLLEGE_ALIASES:
        q_words = [w for w in re.split(r'[\s,.-]+', q) if len(w) > 1 and w not in ["college", "of", "engineering", "tech", "technology", "inst", "institute"]]
        if q_words and all(w in c_text for w in q_words):
            return True

    # Final fallback. Avoid bare substring matching for pure-numeric queries,
    # otherwise a code like "1" matches the "1" inside any postcode/address.
    if q.isdigit():
        m = re.search(r'\((\d{1,4})\)\s*$', c_text)
        return bool(m and m.group(1) == q)

    return q in c_text

def match_branch(branch_query: str, branch_code: str, branch_name: str) -> bool:
    if not branch_query:
        return True
    bq = branch_query.strip().upper()
    bc = branch_code.strip().upper()
    bn = branch_name.strip().upper()

    if bq == bc:
        return True

    if bq in BRANCH_MAPPINGS:
        mapping = BRANCH_MAPPINGS[bq]
        if bc in mapping["codes"]:
            return True
        for kw in mapping["keywords"]:
            if kw.upper() in bn:
                return True

    if bq in bc or bq in bn or bn in bq:
        return True

    return False


def search_colleges(query: str = "", district: str = "", autonomous: Optional[bool] = None) -> str:
    q = (query or "").strip().lower()
    dist = (district or "").strip().lower()
    
    matches = []
    for col in COLLEGES:
        if not isinstance(col, dict):
            continue
        c_name = str(col.get("college_name", ""))
        c_code = str(col.get("tnea_code", ""))
        c_dist = str(col.get("contact_details", {}).get("district", "")).lower()
        c_auto = str(col.get("general_info", {}).get("autonomous_status", "")).lower() == "yes"

        if q and not match_college(q, c_name, c_code):
            continue
        if dist and dist not in c_dist:
            continue
        if autonomous is not None and c_auto != autonomous:
            continue

        branches_summary = [
            f"{b.get('branch_code')} - {b.get('branch_name')}" 
            for b in col.get("branches", [])[:10] if isinstance(b, dict)
        ]
        
        matches.append({
            "code": col.get("tnea_code"),
            "name": col.get("college_name"),
            "district": col.get("contact_details", {}).get("district", "N/A"),
            "autonomous": "Yes" if c_auto else "No",
            "placement_rate": col.get("general_info", {}).get("placement_percentage", "N/A"),
            "sample_branches": branches_summary,
            "hostel_mess_fee_per_annum": col.get("hostel_facilities", {}).get("boys", {}).get("mess_bill_per_annum", "N/A")
        })
        if len(matches) >= 8:
            break
            
    return json.dumps(matches if matches else {"message": "No matching colleges found."})


def get_college_cutoffs(college_code_or_name: str, branch_code: str = "") -> str:
    target = str(college_code_or_name).strip()
    target_branch = str(branch_code).strip()

    results = []
    for item in TNEA_DATA:
        if not isinstance(item, dict):
            continue
        col_text = item.get("college", "")
        branch_text = item.get("branch", "")
        
        b_code_match = re.search(r'\(([A-Z0-9]+)\)$', branch_text.strip())
        b_code = b_code_match.group(1) if b_code_match else ""

        if match_college(target, col_text):
            if target_branch and not match_branch(target_branch, b_code, branch_text):
                continue
            results.append({
                "college": item.get("college"),
                "branch": item.get("branch"),
                "cutoffs": item.get("cutoffs", {}),
                "ranks": item.get("ranks", {})
            })
            if len(results) >= 8:
                break

    if not results and COMPARE_CUTOFFS:
        for item in COMPARE_CUTOFFS:
            c_name = item.get("college_name", "")
            c_code = str(item.get("college_code", ""))
            b_code = item.get("branch_code", "")
            b_name = item.get("branch_name", "")

            if match_college(target, c_name, c_code):
                if target_branch and not match_branch(target_branch, b_code, b_name):
                    continue
                values = item.get("values", {})
                latest_year = max(values.keys()) if values else "2025"
                latest_cutoffs = values.get(latest_year, {})

                rank_entry = RANK_MAP.get(f"{c_code}_{b_code.upper()}", {})
                rank_values = rank_entry.get("values", {})
                latest_ranks = rank_values.get(latest_year, {})

                results.append({
                    "college": f"{c_name} ({c_code})",
                    "branch": f"{b_name} ({b_code})",
                    "cutoffs": {k.upper(): v for k, v in latest_cutoffs.items()},
                    "ranks": {k.upper(): v for k, v in latest_ranks.items()}
                })
                if len(results) >= 8:
                    break

    return json.dumps(results if results else {"message": f"No cutoff records found for '{college_code_or_name}' and branch '{branch_code}'."})

def get_historical_cutoffs(college_code_or_name: str, branch_code: str = "", community: str = "") -> str:
    """Retrieve 5-year (2021-2025) cutoff marks and closing ranks for a college and branch."""
    target = str(college_code_or_name).strip()
    target_branch = str(branch_code).strip()
    comm = community.strip().lower() if community else ""

    results = []
    for item in COMPARE_CUTOFFS:
        if not isinstance(item, dict):
            continue
        c_name = item.get("college_name", "")
        c_code = str(item.get("college_code", ""))
        b_code = item.get("branch_code", "")
        b_name = item.get("branch_name", "")

        if not match_college(target, c_name, c_code):
            continue
        if target_branch and not match_branch(target_branch, b_code, b_name):
            continue

        rank_entry = RANK_MAP.get(f"{c_code}_{b_code.upper()}", {})
        rank_values = rank_entry.get("values", {})
        cutoff_values = item.get("values", {})

        history = {}
        for yr in ["2021", "2022", "2023", "2024", "2025"]:
            yr_cutoffs = cutoff_values.get(yr, {})
            yr_ranks = rank_values.get(yr, {})
            if not yr_cutoffs and not yr_ranks:
                continue

            if comm:
                history[yr] = {
                    f"{comm.upper()}_cutoff": yr_cutoffs.get(comm),
                    f"{comm.upper()}_closing_rank": yr_ranks.get(comm)
                }
            else:
                history[yr] = {
                    "cutoffs": {k.upper(): v for k, v in yr_cutoffs.items() if v is not None},
                    "ranks": {k.upper(): v for k, v in yr_ranks.items() if v is not None}
                }

        results.append({
            "college_code": item.get("college_code"),
            "college_name": c_name,
            "district": item.get("district"),
            "branch_code": b_code,
            "branch_name": b_name,
            "five_year_trends": history
        })
        if len(results) >= 6:
            break

    if not results:
        return json.dumps({"message": f"No 5-year historical cutoff records found for college '{college_code_or_name}' and branch '{branch_code}'."})

    return json.dumps(results)


def predict_colleges(cutoff: float, community: str = "OC", branch: str = "", district: str = "") -> str:
    """Predicts colleges based on cutoff, community, branch, and multiple districts."""
    # ── Guard: validate cutoff range ───────────────────────────────────
    try:
        cutoff = float(cutoff)
    except (ValueError, TypeError):
        return json.dumps({"message": "Please provide a valid numeric cutoff mark."})
    if cutoff < 0 or cutoff > 200:
        return json.dumps({"message": f"Cutoff {cutoff} is outside the valid range (0-200). Please check your marks."})
    
    target_branch = branch.strip()
    target_districts = [d.strip().lower() for d in district.split(',')] if district else []
    comm = community.strip().upper() if community else "OC"
    
    if comm not in ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]:
        comm = "OC"
        
    matches = []
    for item in TNEA_DATA:
        if not isinstance(item, dict):
            continue
            
        c_college = str(item.get("college", ""))
        c_branch = str(item.get("branch", ""))
        
        b_code_match = re.search(r'\(([A-Z0-9]+)\)$', c_branch.strip())
        b_code = b_code_match.group(1) if b_code_match else ""

        if target_districts and not any(d in c_college.lower() for d in target_districts):
            continue
            
        if target_branch and not match_branch(target_branch, b_code, c_branch):
            continue
            
        cutoffs = item.get("cutoffs", {})
        c_cutoff = cutoffs.get(comm)
        
        if c_cutoff is not None:
            try:
                c_cutoff_val = float(c_cutoff)
                if (cutoff - 15) <= c_cutoff_val <= (cutoff + 2.5):
                    matches.append({
                        "college": item.get("college"),
                        "branch": item.get("branch"),
                        f"{comm}_cutoff": c_cutoff_val
                    })
            except (ValueError, TypeError):
                pass
                
    matches = sorted(matches, key=lambda x: x[f"{comm}_cutoff"], reverse=True)
    top_matches = matches[:6] 
    
    if not top_matches:
        return json.dumps({"message": f"No colleges found matching cutoff {cutoff} for {comm} community."})
        
    return json.dumps(top_matches)

def get_seat_matrix(college_code, branch_code: str = "") -> str:
    # ── Guard: coerce to int safely ────────────────────────────────────
    try:
        college_code = int(college_code)
    except (ValueError, TypeError):
        return json.dumps({"message": f"Invalid college code '{college_code}'. Please provide a numeric code."})
    results = []
    target_branch = branch_code.strip().upper() if branch_code else ""

    for item in SEAT_MATRIX:
        if not isinstance(item, dict):
            continue
        c_code = str(item.get("college_code", ""))
        if c_code == str(college_code):
            b_code = str(item.get("branch_code", "")).upper()
            b_name = str(item.get("branch_name", ""))
            if target_branch and not match_branch(target_branch, b_code, b_name):
                continue
            results.append(item)

    return json.dumps(results if results else {"message": f"No seat matrix entries found for college code {college_code}."})


def get_tfc_centers(district_or_city: str) -> str:
    if not district_or_city or not district_or_city.strip():
        return json.dumps({"message": "Please provide a district or city name to search for TFC centers."})
    dist = district_or_city.strip().lower()
    matches = [
        c for c in TFC_CENTERS
        if isinstance(c, dict) and dist in c.get("district", "").lower()
    ]
    return json.dumps(matches if matches else {"message": f"No TFC centers listed for '{district_or_city}'."})

def get_top_colleges(branch: str = "", district: str = "") -> str:
    """Returns the top-ranked engineering colleges in Tamil Nadu with verified TNEA codes.
    Use this whenever the user asks for top/best colleges in TN."""
    target_branch = branch.strip().upper()
    target_district = district.strip().lower()
    
    results = []
    for college in TOP_COLLEGES:
        if target_district and target_district not in college["district"].lower():
            continue
        
        entry = {
            "rank": college["rank"],
            "tnea_code": college["tnea_code"],
            "short_name": college["short_name"],
            "college_name": college["college_name"],
            "district": college["district"],
            "type": college["type"]
        }
        
        # If a branch is requested, also fetch its latest OC cutoff from dataset
        if target_branch:
            best_oc = None
            for item in TNEA_DATA:
                br_text = (item.get("branch") or "").upper()
                col_text = item.get("college", "")
                if not col_text.strip().endswith(f"({college['tnea_code']})"):
                    continue
                if not match_branch(target_branch, re.search(r'\(([A-Z0-9]+)\)$', br_text.strip()).group(1) if re.search(r'\(([A-Z0-9]+)\)$', br_text.strip()) else "", br_text):
                    continue
                oc = (item.get("cutoffs") or {}).get("OC")
                if oc:
                    try:
                        val = float(oc)
                        if best_oc is None or val > best_oc:
                            best_oc = val
                    except (ValueError, TypeError):
                        pass
            if best_oc is not None:
                entry["oc_cutoff_2025"] = best_oc
        
        results.append(entry)
    
    return json.dumps(results)


def get_tnea_guidelines(query: str) -> str:
    if not query or not query.strip():
        return json.dumps({"message": "Please provide a topic to search for TNEA guidelines."})
    q = query.strip().lower()
    matched = []

    for rule in TNEA_RULES:
        if not isinstance(rule, dict):
            continue
        keywords = rule.get("keywords", [])
        if any(kw in q for kw in keywords):
            matched.append(rule.get("content"))

    if not matched:
        for chunk in BROCHURE_CHUNKS:
            content = chunk.get("content", "")
            if any(word in content.lower() for word in q.split() if len(word) > 3):
                matched.append(content)
                if len(matched) >= 3:
                    break

    return json.dumps(matched if matched else {"message": "Please consult official TNEA notification guidelines."})

AVAILABLE_TOOLS = {
    "search_colleges": search_colleges,
    "get_college_cutoffs": get_college_cutoffs,
    "get_historical_cutoffs": get_historical_cutoffs,
    "predict_colleges": predict_colleges,
    "get_seat_matrix": get_seat_matrix,
    "get_tfc_centers": get_tfc_centers,
    "get_tnea_guidelines": get_tnea_guidelines,
    "get_top_colleges": get_top_colleges,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_colleges",
            "description": "Look up college details, TNEA codes, facilities, sample branches, and autonomous status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "College name keyword or code (e.g., 'PSG Tech', 'CIT', '2006', '1399')"},
                    "district": {"type": "string", "description": "District name (e.g., 'Chennai', 'Coimbatore')"},
                    "autonomous": {"type": "boolean", "description": "True for autonomous only"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_college_cutoffs",
            "description": "Retrieve latest official TNEA cutoff marks and closing ranks for a specific college and branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_code_or_name": {"type": "string", "description": "College code or name (e.g., '2006', 'PSG Tech', '1399', 'CIT', 'CEG')"},
                    "branch_code": {"type": "string", "description": "Branch code or keyword such as CS, CSE, CM, EC, ECE, ME, AIDS"}
                },
                "required": ["college_code_or_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_cutoffs",
            "description": "Retrieve complete 5-year historical cutoff marks and closing ranks (from 2021 to 2025) for a college and branch. Use this whenever the user asks for multi-year trends, 5-year cutoffs, or historical cutoff comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_code_or_name": {"type": "string", "description": "College code or name (e.g., '2006', 'PSG Tech', '1399', 'CIT', 'CEG')"},
                    "branch_code": {"type": "string", "description": "Branch code or keyword such as CS, CSE, CM, EC, ECE, ME, AIDS"},
                    "community": {"type": "string", "description": "Optional community filter (e.g. OC, BC, BCM, MBC, SC, SCA, ST)"}
                },
                "required": ["college_code_or_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "predict_colleges",
            "description": "Recommends a list of colleges based on the user's cutoff marks, community, branch, and district.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cutoff": {"type": "number", "description": "The student's TNEA cutoff mark (e.g., 178)"},
                    "community": {"type": "string", "description": "Community category: OC, BC, BCM, MBC, SC, SCA, ST. Defaults to OC."},
                    "branch": {"type": "string", "description": "Branch keyword or code (e.g., 'CSE', 'ECE', 'Mechanical', 'Civil')."},
                    "district": {"type": "string", "description": "District name or comma-separated districts (e.g., 'Chennai, Coimbatore')."}
                },
                "required": ["cutoff"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_seat_matrix",
            "description": "Check the exact TNEA 2026 seat distribution for a specific college.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_code": {"type": "integer", "description": "4-digit or 1-digit TNEA College Code (e.g. 2006, 1399, 1)"},
                    "branch_code": {"type": "string", "description": "Optional branch code or name (e.g. CS, CSE, CM, EC)"}
                },
                "required": ["college_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tfc_centers",
            "description": "Get TNEA Facilitation Centers (TFC) and phone numbers by district.",
            "parameters": {
                "type": "object",
                "properties": {
                    "district_or_city": {"type": "string", "description": "Tamil Nadu District"}
                },
                "required": ["district_or_city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tnea_guidelines",
            "description": "Get eligibility, reservation rules, or counseling stages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic such as '7.5 quota'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_colleges",
            "description": "Returns the top-ranked engineering colleges in Tamil Nadu with verified TNEA college codes. MUST be called whenever the user asks about top/best colleges in TN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string", "description": "Optional branch to show OC cutoff for (e.g., 'CSE', 'ECE')."},
                    "district": {"type": "string", "description": "Optional district filter (e.g., 'Chennai', 'Coimbatore')."}
                }
            }
        }
    }
]
