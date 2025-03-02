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
    
    def compine_quarter_json(files_to_one, output_file):
        """
        1) if wame quarter, the best value is used;
           a) if one exist, the other not, the one that exist is used
           b) if both exist, the one with the longest text is used
           c) if a value in both, the average is used, but marked as might be wrong
        2) if different quarters, all values are kept, but they are in seperate lists marked with the quarter
        3) if the same value is in both, tis value is used
        """
        data = {}
        for file in files_to_one:
            with open(file, 'r') as f:
                data.update(json.load(f))
        with open(output_file, 'w') as f:
            json.dump(data, f)