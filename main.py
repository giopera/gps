import json
import re
import sys

if __name__ == "__main__":
    if not sys.argv[1].endswith(".geojson"):
        print("No input file, or file not in valid geojson")
    database_file = sys.argv[1]
    if not sys.argv[2].endswith(".geojson"):
        print("No output file, or file not in valid geojson")
    output_file = sys.argv[2]
    with open(database_file, "r") as f:
        with open(output_file, "w") as out:
            out.write('{"type": "FeatureCollection","features": [')
            out.flush()
            filter_criteria = []
            translation = []
            delete_criteria = []
            soft_delete_criteria = []
            all_lowercase_criteria = []
            case_criteria = []
            for arg in sys.argv:
                if "=" in arg:
                    filter_criteria.append(arg.split("="))
                elif "^" in arg:
                    translation.append(arg.split("^"))
                elif arg.startswith("-"):
                    delete_criteria.append(arg.lstrip("-"))
                elif arg.startswith("~"):
                    soft_delete_criteria.append(arg.lstrip("~"))
                elif arg.startswith("_"):
                    all_lowercase_criteria.append(arg.lstrip("_"))
                elif arg.startswith("§"):
                    case_criteria.append(arg.lstrip("§"))
            check = len(filter_criteria) != 0
            translate = len(translation) != 0
            delete = len(delete_criteria) != 0
            soft_delete = len(soft_delete_criteria) != 0
            all_lowercase = len(all_lowercase_criteria) != 0
            case = len(case_criteria) != 0
            for line in f:
                output = True
                line = line.strip()
                d: dict = json.loads(line)
                if check:
                    for criteria in filter_criteria:
                        output = output and re.match(
                            criteria[1].lower(), d["properties"][criteria[0]].lower()
                        )
                if output:
                    if delete:
                        for criteria in delete_criteria:
                            d["properties"].pop(criteria)
                    if soft_delete:
                        for criteria in soft_delete_criteria:
                            if d["properties"].get(criteria, "") == "":
                                d["properties"].pop(criteria)
                    if case:
                        for criteria in case_criteria:
                            d["properties"][criteria] = d["properties"][criteria].title()
                    if all_lowercase:
                        for criteria in all_lowercase_criteria:
                            d["properties"][criteria] = d["properties"][criteria].lower()
                    if translate:
                        for criteria in translation:
                            if d["properties"].get(criteria[0], None) is not None:
                                d["properties"][criteria[1]] = d["properties"].pop(
                                    criteria[0]
                                )
                        out.write(f"{json.dumps(d)},")
                    else:
                        line = line.replace("\n", "")
                        line += ","
                        out.write(line)
        with open(output_file, "rb+") as out:
            out.seek(-1, 2)
            out.truncate()
            out.write(b"]}")
