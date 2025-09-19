import copy
import json
import re
import sys

coordinates = set()

def filter_feature(filter_criteria, feature):
    output = True
    for criteria in filter_criteria:
        output = output and re.match(
            criteria[1].lower(), feature["properties"][criteria[0]].lower()
        )
    return output

def translation(criteria, feature):
    if feature["properties"].get(criteria[0], None):
        feature["properties"][criteria[1]] = feature["properties"].pop(criteria[0])

def delete(criteria, feature):
    if feature["properties"].get(criteria, None):
        feature["properties"].pop(criteria)
    
def soft_delete(criteria, feature):
    if feature["properties"].get(criteria, None) == "":
        feature["properties"].pop(criteria)
        
def case(criteria, feature):
    if feature["properties"].get(criteria, None):
        feature["properties"][criteria] = feature["properties"][criteria].title()

def lowercase(criteria, feature):
    if feature["properties"].get(criteria, None):
        feature["properties"][criteria] = feature["properties"][criteria].lower()

def concatenate(criteria, feature):
    if feature["properties"].get(criteria[0], None) and feature["properties"].get(criteria[1], None):
        feature["properties"][criteria[0]] += feature["properties"][criteria[1]]
        feature["properties"].pop(criteria[1])

def split_values(criteria, feature):
    if feature["properties"].get(criteria[0], None):
        splitted = feature["properties"][criteria[0]].split(criteria[1])
        if len(splitted) != 0:
            to_return = []
            feature["properties"][criteria[0]] = splitted[0]
            del splitted[0]
            for val in splitted:
                new_dict = feature.copy()
                new_dict["properties"][criteria[0]] = val
                to_return.append(new_dict)

def check_uniqueness(criteria: set, feature):
    iteration = 0
    if feature["geometry"] is None or feature["geometry"]["coordinates"] is None:
        return
    while f"{feature["geometry"]["coordinates"][0]}+{feature["geometry"]["coordinates"][1]}" in criteria:
        iteration = iteration + 1
        if iteration % 2:
            feature["geometry"]["coordinates"][0] += 0.000001
        else:
            feature["geometry"]["coordinates"][1] += 0.000001
    criteria.add(f"{feature["geometry"]["coordinates"][0]}+{feature["geometry"]["coordinates"][1]}")

def manipulate_coord(criteria, feature):
    change = float(criteria[1])
    position = 0
    if criteria[0][0] == "-":
        change *= -1
    if criteria[0][1] == "y":
        position = 1

    if feature["geometry"] is not None:
        feature["geometry"]["coordinates"][position] += change

def conditional_operation(criteria: list[str], feature):
    criteria = copy.deepcopy(criteria)
    criteria[1] = criteria[1].replace(":", "")
    for key, val in feature["properties"].items():
        criteria[0] = criteria[0].replace(key, val)
    if eval(criteria[0]):
        del criteria[0]
        fun, arg_arr = parse_arg(criteria)
        fun(arg_arr, feature)

def polish_arg(arr, stop = None):
    if stop is None:
        arr_len = len(arr)
    else:
        arr_len = stop
    counter = 0
    while counter < arr_len:
        del arr[counter]
        counter += 1
        arr_len -= 1



def parse_arg(argument: str|list):
    if type(argument) is str:
        arg = argument.split("\"")
    else:
        arg = argument
    alen = len(arg)
    if alen > 2 and arg[2].startswith(":"):
        polish_arg(arg, 1)
        return conditional_operation, arg
    elif alen > 2 and "^" == arg[2]:
        polish_arg(arg)
        return translation, arg
    elif alen > 0 and "-" == arg[0]:
        polish_arg(arg)
        return delete, arg[0]
    elif alen > 0 and "~" == arg[0]:
        polish_arg(arg, 2)
        return soft_delete, arg[0]
    elif alen > 0 and "_" == arg[0]:
        polish_arg(arg, 2)
        return lowercase, arg[0]
    elif alen > 0 and "§" == arg[0]:
        polish_arg(arg, 2)
        return case, arg[0]
    elif alen > 0 and arg[0] in ["+x", "-x", "+y", "-y"]:
        return manipulate_coord, arg
    elif alen > 2 and "+" == arg[2]:
        polish_arg(arg, 3)
        return concatenate, arg
    elif alen > 2 and "[" in arg[2] and arg[2].endswith("]"):
        polish_arg(arg, 3)
        arg[2] = arg[2].strip("[")
        arg[2] = arg[2].strip("]")
        return split_values, arg
    elif alen > 0 and arg[0] == "#":
        return check_uniqueness, coordinates

    return None

def parse_filter(arg):
    arg = arg.split("\"")
    if len(arg) > 2 and arg[2] == "=":
        polish_arg(arg, 3)
        return arg
    return None

if __name__ == "__main__":
    script = None
    if sys.argv[1].endswith(".gps"):
        script = sys.argv[1]
    if script:
        with open(script, "r") as sc:
            database_file = sc.readline().strip()
            output_file = sc.readline().strip()
    else:
        if not sys.argv[1].endswith(".geojson"):
            print("No input file, or file not in valid geojson")
        database_file = sys.argv[1]
        if not sys.argv[2].endswith(".geojson"):
            print("No output file, or file not in valid geojson")
        output_file = sys.argv[2]

    with open(database_file, "r") as f:
        with open(output_file, "w") as out:
            command_list = []
            if script:
                with open(script, "r") as sc:
                    command_list = [i.strip("\n").strip() for i in sc.readlines()]
                    del command_list[0]
                    del command_list[0]
            else:
                command_list = sys.argv
                del command_list[0]
            parse_list = []
            filter_criteria = []
            count = 0
            for arg in command_list:
                result = parse_filter(arg)
                if result is not None:
                    filter_criteria.append(result)
                    del command_list[count]
                count += 1
            for arg in command_list:
                parse_list.append(parse_arg(arg))
            out.write('{"type": "FeatureCollection","features": [')
            coda = []
            for line in f:
                line = line.strip()
                d: dict = json.loads(line)

                if filter_feature(filter_criteria, d):
                    for function, criteria in parse_list:
                        value = function(criteria, d)
                        if type(value) is list:
                            for feature in value:
                                coda.append(feature)
                    out.write(f"{json.dumps(d)},")
            for d in coda:
                if filter_feature(filter_criteria, d):
                    for function, criteria in parse_list:
                        value = function(criteria, d)
                        if type(value) is list:
                            for feature in value:
                                coda.append(feature)
                    out.write(f"{json.dumps(d)},")
        with open(output_file, "rb+") as out:
            out.seek(-1, 2)
            out.truncate()
            out.write(b"]}")