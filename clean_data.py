import json  
colleges = json.load(open('data/colleges.json'))  
for c in colleges:  
    if type(c) == dict and c.get('tnea_code') in [1414, 1442, 1509]:  
        if c.get('general_info'): c['general_info']['placement_percentage'] = None  
json.dump(colleges, open('data/colleges.json', 'w'), indent=2)  
tnea = json.load(open('data/tnea_data.json'))  
for d in tnea:  
    if any(f\"({code})\" in str(d.get('college')) for code in [1414, 1442, 1509]):  
        for k in d.get('cutoffs', {}):  
            if type(d['cutoffs'][k]) in [float, int] and d['cutoffs'][k] > 165:  
                d['cutoffs'][k] -= 35.0  # Bring it down to a realistic tier range  
json.dump(tnea, open('data/tnea_data.json', 'w'), indent=2)  
