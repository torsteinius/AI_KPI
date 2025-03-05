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
            
            # CASE 1: Key only in one of them
            if valA is not None and valB is None:
                combined[key] = valA
                continue
            if valA is None and valB is not None:
                combined[key] = valB
                continue
            
            # Now both valA and valB exist. We check their types and/or equality.
            if isinstance(valA, (int, float)) and isinstance(valB, (int, float)):
                # Numeric fields
                if valA == valB:
                    # Exactly the same => just keep the value
                    combined[key] = valA
                else:
                    # Different => average and mark as "might be wrong"
                    avg_value = (valA + valB) / 2
                    # You can store as a string with a note, or store two fields, etc.
                    combined[key] = f"{avg_value} (might be wrong: avg of {valA} & {valB})"
            
            elif isinstance(valA, str) and isinstance(valB, str):
                # Text fields
                if key == "500tegnoppsummering":
                    # Combine them into one big text
                    combined[key] = valA + "\n" + valB
                else:
                    # Use the longer text
                    if len(valA) >= len(valB):
                        combined[key] = valA
                    else:
                        combined[key] = valB
                        
            else:
                # If they are the same object (or same value) in some other type
                # or both equal but not numeric or text
                if valA == valB:
                    combined[key] = valA
                else:
                    # Fallback: you might choose one or store a list.
                    combined[key] = [valA, valB]
        
        return combined
