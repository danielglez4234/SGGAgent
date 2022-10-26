import json
import urllib.parse
import requests
import yaml
from flask import Flask, abort, request, jsonify, Response


def get_config(path):
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return data


config = get_config("config.yaml")['iot']
server = config['server']
notification = config['notification']

# server config variables
HOSTNAME = server['hostname']
PORT = server['port']
SUBSCRIPTION_TARGET = server['subscription_target']

# notification config variables
COMPONENTS_PREFIX = notification['component']
MAGNITUDE_PREFIX = notification['magnitude']
TEXT_VALUE_PREFIX = notification['text_value']
DECIMAL_VALUE_PREFIX = notification['decimal_value']
REQUIRED_HEADERS = notification['required_headers']

# json model config variables
NOTIFICATION_MODEL = {
    "PanelFields": [{
        "InternalName": notification['internal_name'],
        "Type": notification['type'],
    }]
}

#
# ---------------------------------------------------------------------
# init flask app
# ---------------------------------------------------------------------
#
app = Flask(__name__)


#
# Replace %xx escapes with their single-character equivalent.
# 
def unquote(elements):
    parse = {}
    for element in elements.keys():
        if element:
            parse[element] = urllib.parse.unquote(elements[element])
    return parse


#
# get value label and value depending on type
#
def value_model_by_type(value):
    if type(value) == str:
        return get_row_model(TEXT_VALUE_PREFIX, "Text", "TextValue", value)
    return get_row_model(DECIMAL_VALUE_PREFIX, "Decimal", "DecimalValue", value)


#
# get row element model
#
def get_row_model(name, type, label, value):
    return {
        "InternalName": name,
        "Type": type,
        label: value
    }


#
# create attributes data rows
# 
def create_row(entity, attribute):
    value = entity[attribute]["value"]
    return {
        "Row": [
            get_row_model(COMPONENTS_PREFIX, "Text", "TextValue", entity["id"]),
            get_row_model(MAGNITUDE_PREFIX, "Text", "TextValue", attribute),
            value_model_by_type(value)
        ]
    }


#
# create FieldsGroupValue data
#
def create_attr_data(notification_data):
    data = notification_data["data"]

    fields_group_values = []
    for entity in data:
        for attribute in entity:
            if attribute == "id" or attribute == "type":
                continue
            fields_group_values.append(
                create_row(entity, attribute)
            )

    NOTIFICATION_MODEL["PanelFields"][0]["FieldsGroupValue"] = fields_group_values
    return NOTIFICATION_MODEL


# 
# subscriptions POST route
# 
@app.route("/subscriptions", methods=['POST'])
def subscribe():
    data = urllib.parse.quote(request.data.decode('utf-8'), safe='\"\n\t {}:,[]\\/$%')
    json_post = json.JSONDecoder().decode(data)

    notification_ = json_post['notification']
    notification_attrs = list(notification_)

    if 'httpCustom' not in notification_attrs:
        abort(403, '{"message": "HttpCustom is a required field inside the notification object."}')

    # httpCustom_headers = list(notification['httpCustom']['headers'])
    # if all(value not in httpCustom_headers for value in REQUIRED_HEADERS):
    #     abort(403, '{"message": "Check that the headers include the following requested fields: ' + str(
    #         REQUIRED_HEADERS) + '"}')

    print(json_post)
    r = requests.post(SUBSCRIPTION_TARGET, json=json_post, headers=request.headers)
    return Response(json.dumps(r.text), status=r.status_code, mimetype='application/json', headers=r.headers.items())


#
# notification POST route
#
@app.route("/notification", methods=['POST'])
def notify():
    data = urllib.parse.unquote(request.data.decode('utf-8'))
    headers = unquote(request.headers)
    headers_keys = list(headers)
    # if "Destpage" not in headers_keys:
    if all(value not in headers_keys for value in REQUIRED_HEADERS):
        abort(403, '{"message": "Check that the headers include the following requested fields: ' + str(
            REQUIRED_HEADERS) + '"}')
    else:
        # get required headers
        dest_page = headers.pop("Destpage")
        api_key = headers.pop("Apikey")
        user_data = headers.pop("Userdata")
        # create response object
        json_decode = json.JSONDecoder().decode(data)
        json_post = create_attr_data(json_decode)
        print(json_post)
        r = requests.post(dest_page, json=json_post, headers={"apikey": api_key, "userdata": user_data})
        return r.text, r.status_code


# 
# subscriptions DELETE by id route
# 
@app.route("/subscriptions/<subscription_id>", methods=['DELETE'])
def delete(subscription_id):
    r = requests.delete(SUBSCRIPTION_TARGET + subscription_id)
    return r.text, r.status_code


# 
# subscriptions DELETE by id with body route
# 
@app.route("/subscriptions", methods=['DELETE'])
def delete_with_body():
    id = request.json['id']
    r = requests.delete(SUBSCRIPTION_TARGET + id)
    return r.text, r.status_code


# 
# test dummy
# 
@app.route("/dummy", methods=['POST'])
def dummy():
    data = urllib.parse.unquote(request.data.decode('utf-8'))
    print(data)
    return "200"


if __name__ == "__main__":
    app.run(threaded=True, host=HOSTNAME, port=PORT)
