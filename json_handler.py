from settings import *
import json



class Json_Handler:
    def __init__(self):
        self.json = None

    def load_json(self, json_file):
        with open(json_file, 'r') as file:
            self.json = json.load(file)

    def get_json(self):
        return self.json

    def get_json_value(self, key):
        return self.json[key]

    def get_json_keys(self):
        return self.json.keys()

    def get_json_values(self):
        return self.json.values()

    def get_json_items(self):
        return self.json.items()
    
    def combine_same_quarter(jsonA, jsonB) -> dict:
        """
        Combine two JSON dicts from the same quarter/year/company
        into a single dict, using the logic:
        - If key only in one, use that.
        - If key in both:
            - If numeric and identical, keep it.
            - If numeric and different, use average, mark as might be wrong.
            - If text and the key is 500tegnoppsummering, combine them.
            - If text (non-summary), use the longer one.
        """
        combined = {}
        all_keys = set(jsonA.keys()) | set(jsonB.keys())
        
        for key in all_keys:
            valA = jsonA.get(key)
            valB = jsonB.get(key)
            
            # 1) If only one has the key, take that.
            if valA is None and valB is not None:
                combined[key] = valB
                continue
            if valB is None and valA is not None:
                combined[key] = valA
                continue
            
            # 2) Both have the key
            if isinstance(valA, (int, float)) and isinstance(valB, (int, float)):
                # Numeric fields
                if valA == valB:
                    combined[key] = valA  # identical => keep
                else:
                    # average them (and flag it)
                    avg_val = (valA + valB) / 2
                    combined[key] = f"{avg_val} (might be wrong: avg of {valA} & {valB})"
            
            elif isinstance(valA, str) and isinstance(valB, str):
                # Text fields
                if key == "500tegnoppsummering":
                    # Combine them so nothing is lost
                    combined[key] = valA + "\n" + valB
                else:
                    # Use the longer text
                    if len(valA) >= len(valB):
                        combined[key] = valA
                    else:
                        combined[key] = valB
            
            else:
                # They might both be None, or differ in some other type. 
                # If identical, keep as-is:
                if valA == valB:
                    combined[key] = valA
                else:
                    # fallback if somehow we have different non-numeric, non-string
                    combined[key] = [valA, valB]
        
        return combined
