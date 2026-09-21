import copy
import json
import re
import sys

coordinates = set()


def load_geojson(filepath: str) -> list[dict]:
    """
    Carica i feature da un file GeoJSON, supportando sia il formato standard
    (singolo JSON FeatureCollection / Feature) sia il formato GeoJSON NL (GeoJSONL).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return []

    # 1. Tenta il parsing dell'intero file come JSON unico (GeoJSON standard)
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if data.get("type") == "FeatureCollection":
                return data.get("features", [])
            elif data.get("type") == "Feature":
                return [data]
            elif "features" in data and isinstance(data["features"], list):
                return data["features"]
        elif isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Se fallisce, effettua il parsing riga per riga (GeoJSON NL / GeoJSONL / RFC 8142)
    features = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.lstrip("\x1e")  # Rimuove il Record Separator (RFC 8142) se presente
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                if item.get("type") == "FeatureCollection":
                    features.extend(item.get("features", []))
                elif item.get("type") == "Feature":
                    features.append(item)
                else:
                    features.append(item)
        except json.JSONDecodeError:
            continue

    return features


def filter_feature(filter_criteria, feature):
    output = True
    props = feature.get("properties", {})
    for criteria in filter_criteria:
        prop_val = props.get(criteria[0], "")
        if prop_val is None:
            prop_val = ""
        output = output and bool(
            re.match(criteria[1].lower(), str(prop_val).lower())
        )
    return output


def translation(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria[0], None) is not None:
        feature["properties"][criteria[1]] = feature["properties"].pop(criteria[0])


def delete(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria, None) is not None:
        feature["properties"].pop(criteria)


def soft_delete(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria, None) == "":
        feature["properties"].pop(criteria)


def case(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria, None) is not None:
        feature["properties"][criteria] = feature["properties"][criteria].title()


def lowercase(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria, None) is not None:
        feature["properties"][criteria] = feature["properties"][criteria].lower()


def concatenate(criteria, feature):
    if feature.get("properties") and (
        feature["properties"].get(criteria[0], None) is not None
        and feature["properties"].get(criteria[1], None) is not None
    ):
        feature["properties"][criteria[0]] += feature["properties"][criteria[1]]
        feature["properties"].pop(criteria[1])

def replace(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria[0], None) is not None:
        feature["properties"][criteria[0]] = feature["properties"][criteria[0]].replace(criteria[1], criteria[2])

def split_values(criteria, feature):
    if feature.get("properties") and feature["properties"].get(criteria[0], None) is not None:
        splitted = feature["properties"][criteria[0]].split(criteria[1])
        if len(splitted) > 0:
            to_return = []
            feature["properties"][criteria[0]] = splitted[0]
            for val in splitted[1:]:
                new_dict = copy.deepcopy(feature)
                new_dict["properties"][criteria[0]] = val
                to_return.append(new_dict)
            return to_return


def check_uniqueness(criteria: set, feature):
    iteration = 0
    if feature.get("geometry") is None or feature["geometry"].get("coordinates") is None:
        return
    coords = feature["geometry"]["coordinates"]
    key = f"{coords[0]}+{coords[1]}"
    while key in criteria:
        iteration += 1
        if iteration % 2:
            coords[0] += 0.000001
        else:
            coords[1] += 0.000001
        key = f"{coords[0]}+{coords[1]}"
    criteria.add(key)


def manipulate_coord(criteria, feature):
    change = float(criteria[1])
    position = 0
    if criteria[0][0] == "-":
        change *= -1
    if criteria[0][1] == "y":
        position = 1

    if feature.get("geometry") is not None and feature["geometry"].get("coordinates") is not None:
        feature["geometry"]["coordinates"][position] += change

def set_val(criteria, feature):
    if feature.get("properties") is not None and len(criteria) > 1:
        feature["properties"][criteria[0]] = criteria[1]


def conditional_operation(criteria: list[str], feature):
    criteria = copy.deepcopy(criteria)
    can_go = False
    criteria[1] = criteria[1].replace(":", "")
    for key, val in feature.get("properties", {}).items():
        if val is not None:
            can_go = True
            criteria[0] = criteria[0].replace(key, '\'' + str(val) + '\'')
    if not can_go:
        return
    try:
        if eval(criteria[0]):
            del criteria[0]
            parsed = parse_arg(criteria)
            if parsed is not None:
                fun, arg_arr = parsed
                if fun is not None:
                    fun(arg_arr, feature)
    except Exception as e:
        pass


def polish_arg(arr, stop=None):
    if stop is None:
        arr_len = len(arr)
    else:
        arr_len = stop
    counter = 0
    while counter < arr_len:
        del arr[counter]
        counter += 1
        arr_len -= 1


def parse_arg(argument: str | list):
    
    if isinstance(argument, str):
        arg = argument.split('"')
    else:
        arg = argument
    alen = len(arg)
    
    if alen > 2 and arg[2].startswith(":"):
        polish_arg(arg, 1)
        return conditional_operation, arg
    elif alen > 2 and "=" == arg[2]:
        polish_arg(arg)
        return set_val, arg
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
    elif alen > 0 and arg[0] in ["@", "§"]:
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
    if isinstance(arg, str):
        arg = arg.split('"')
    if len(arg) > 2 and arg[2] == "==":
        polish_arg(arg, 3)
        return arg
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <script.gps> oppure python main.py <input.geojson> <output.geojson> [operazioni...]")
        sys.exit(1)

    script = None
    if sys.argv[1].endswith(".gps"):
        script = sys.argv[1]

    if script:
        with open(script, "r", encoding="utf-8") as sc:
            lines = [i.strip("\n").strip() for i in sc.readlines() if i.strip()]
            database_file = lines[0]
            output_file = lines[1]
            raw_commands = lines[2:]
    else:
        database_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "output.geojson"
        raw_commands = sys.argv[3:] if len(sys.argv) > 3 else []

    filter_criteria = []
    command_list = []
    for arg in raw_commands:
        result = parse_filter(arg)
        if result is not None:
            filter_criteria.append(result)
        else:
            command_list.append(arg)

    parse_list = []
    for arg in command_list:
        parsed = parse_arg(arg)
        if parsed is not None:
            parse_list.append(parsed)

    features = load_geojson(database_file)

    coda = []
    processed_features = []

    for d in features:
        if filter_feature(filter_criteria, d):
            for function, criteria in parse_list:
                if function is not None:
                    value = function(criteria, d)
                    if isinstance(value, list):
                        for feature in value:
                            coda.append(feature)
            processed_features.append(d)

    for d in coda:
        if filter_feature(filter_criteria, d):
            for function, criteria in parse_list:
                if function is not None:
                    value = function(criteria, d)
                    if isinstance(value, list):
                        for feature in value:
                            coda.append(feature)
            processed_features.append(d)

    output_geojson = {
        "type": "FeatureCollection",
        "features": processed_features
    }

    # Scrive l'output in un file GeoJSON valido e formattato
    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(output_geojson, out, ensure_ascii=False, indent=2)