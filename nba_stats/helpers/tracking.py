import logging
log = logging.getLogger('stats')


def convert_shot_type_dict_to_apex(data):
    converted_data = {'SHOT_TYPE': data['PT_MEASURE_TYPE']}
    for key in data:
        new_key = key.replace("CATCH_", "").replace("PULL_UP_", "")
        converted_data[new_key] = data[key]
    return converted_data


def convert_touch_dict_to_apex(data):
    converted_data = {'TOUCH_TYPE': data['PT_MEASURE_TYPE']}
    for key in data:
        if key == "DRIVES":
            new_key = "TOUCHES"
        else:
            remove = ["DRIVE", "ELBOW", "POST", "PAINT", "_TOUCH_"]
            new_key = key
            for bad in remove:
                new_key = new_key.replace(bad, "")

            new_key = new_key.replace("PF", "FOULS")
        converted_data[new_key] = data[key]
    return converted_data
"xl".lstrip()