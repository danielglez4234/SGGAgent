import json
import urllib.parse
import requests
import yaml
from flask import Flask, abort, request, jsonify, Response
# CORS
from flask_cors import CORS


def get_config(path):
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return data


config = get_config("config.yaml")['iot']
# server config variables
HOSTNAME = config['server']['hostname']
PORT = config['server']['port']
SUBSCRIPTION_TARGET = config['server']['subscription_target']
# notification config variables
COMPONENTS_PREFIX = config['notification']['component']
MAGNITUDE_PREFIX = config['notification']['magnitude']
VALUE_PREFIX = config['notification']['value']
# json model config variables
SGG_INTERNAL_NAME = config['notification']['internal_name']
SGG_TYPE = config['notification']['type']
# required headers
REQUIRED_HEADERS = config['notification']['required_headers']

# init flask app
app = Flask(__name__)


# cors = CORS(app, resources={r"/*": {"origins": "http://" + HOSTNAME + ":" + PORT}})


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
# get value label and value
#
def get_properties(value):
    if isinstance(value, int):
        return {"type_value": "Decimal", "value_label": "DecimalValue"}
    return {"type_value": "Text", "value_label": "TextValue"}


#
# create attributes data rows
# 
def get_row_model(entity, attr):
    component = entity["id"]
    magnitude = attr
    value = entity[attr]["value"]
    props = get_properties(value)
    return {
        "Row": [
            {
                "InternalName": COMPONENTS_PREFIX,
                "Type": "Text",
                "TextValue": component
            },
            {
                "InternalName": MAGNITUDE_PREFIX,
                "Type": "Text",
                "TextValue": magnitude
            },
            {
                "InternalName": VALUE_PREFIX,
                "Type": props["type_value"],
                [props["value_label"]]: value
            },
        ]
    }


def create_attr_data(notification_data):
    notification_model = {
        "PanelFields": [{
            "InternalName": SGG_INTERNAL_NAME,
            "Type": SGG_TYPE,
        }]
    }
    fields_group_values = []
    #  create arrange of components attributes
    data = notification_data["data"]
    for entity in data:
        for attribute in entity:
            if attribute == "id" or attribute == "type":
                continue
            fields_group_values.append(get_row_model(entity, attribute))

    notification_model["PanelFields"][0]["FieldsGroupValue"] = fields_group_values
    return notification_model


# 
# create new notification object if it doesn't already exist
#
# def create_httpCustom(notification):
#     return {
#         "httpCustom": {
#             "url": notification['http']['url'],
#             "headers": {
#                 "destPage": NOTIFICATION_TARGET,
#             },
#             'method': 'POST'
#         }
#     }


# 
# subscriptions POST route
# 
@app.route("/subscriptions", methods=['POST'])
def subscribe():
    data = urllib.parse.quote(request.data.decode('utf-8'), safe='\"\n\t {}:,[]\\/$%')
    json_post = json.JSONDecoder().decode(data)
    # create and assign httpCustom and destPage if not exists
    notification = json_post['notification']
    notification_attrs = list(notification)
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
    print(data)
    headers = unquote(request.headers)
    print(headers)
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


# @app.route("/subscriptions", methods=['GET'])
# def delete_with_body():
#     id = request.json['id']
#     r = requests.delete(SUBSCRIPTION_TARGET + id)
#     return r.text, r.status_code


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
