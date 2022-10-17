import json
import urllib.parse
import requests
import yaml
from flask import Flask, request, jsonify, Response

app = Flask(__name__)


def get_config(path):
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return data

config = get_config("config.yaml")['iot']

HOSTNAME = config['server']['hostname']
PORT = config['server']['port']
SUBSCRIPTION_TARGET = config['server']['subscription_target']
NOTIFICATION_TARGET = config['server']['notification_target']

COMPONENTS_PREFIX = config['notification']['component']
MAGNITUDE_PREFIX = config['notification']['magnitude']
VALUE_PREFIX = config['notification']['value']

SGG_INTERNAL_NAME = config['notification']['interna_name']
SGG_TYPE = config['notification']['type']



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
# create attributes data rows
# 
def get_row_model(entity, key):
    type = entity["type"]
    value_str = str(entity[key])
    return {
        "Row": [
            {
                "InternalName": COMPONENTS_PREFIX + key,
                "Type": type,
                "TextValue": value_str
            },
            {
                "InternalName": MAGNITUDE_PREFIX + key,
                "Type": type,
                "TextValue": value_str
            },
            {
                "InternalName": VALUE_PREFIX,
                "Type": type,
                "TextValue": value_str
            },
        ]
    }

# 
# create attributes data rows
# 
def create_fields_group_value(entity):
    rows = []
    # iterate over entity attributes 
    for key in entity:
        if key == "id" or key == "type":
            continue
        rows.append( get_row_model(entity, key) )
    return rows


def create_attr_data(notification_data):
    notification_model = {
        "InternalName": SGG_INTERNAL_NAME,
        "Type": SGG_TYPE,
    }
    print(notification_data)
    #
    #  create arrange of components attributes
    #
    data = notification_data["data"]
    for entity in data:   
        notification_model["FieldsGroupValue"] = create_fields_group_value(entity)
    return notification_model


# 
# create new notification object if it doesn't already exist
# 
def create_notification(notification):
    return {
        "httpCustom": {
            "url": NOTIFICATION_TARGET,
            "headers": {
                "desPage": notification['http']['url']
            },
            'method': 'POST'
        }
    }


# TEST
@app.route("/subscriptions", methods=['GET'])
def get_data():
    print(HOSTNAME)
    print(PORT)
    print(SUBSCRIPTION_TARGET)
    r = requests.get(SUBSCRIPTION_TARGET, headers=request.headers)
    return r.text, r.status_code


# 
# subscriptions POST route
# 
@app.route("/subscriptions", methods=['POST'])
def subscribe():
    data = urllib.parse.quote(request.data.decode('utf-8'), safe='\"\n\t {}:,[]\\/$%')

    json_post = json.JSONDecoder().decode(data)
    notification = json_post['notification']

    if 'httpCustom' in notification.keys():
        notification['httpCustom']['headers']['destPage'] = notification['httpCustom']['url']
    else:
        json_post['notification'] = create_notification(notification)

    print(json_post)
    r = requests.post(SUBSCRIPTION_TARGET, json=json_post, headers=request.headers)

    return Response(json.dumps(r.text), status=r.status_code, mimetype='application/json', headers=r.headers.items())


# 
# notification POST route
# 
@app.route("/notification", methods=['POST'])
def notify():
    print("---------------------------------------------------------")
    data = urllib.parse.unquote(request.data.decode('utf-8'))

    # required object (Destpage)
    headers = unquote(request.headers)
    dest_page = headers.pop("Destpage")
    json_post = json.JSONDecoder().decode(data)

    print("--------------------------------------------------------")
    print(json_post)
    # create response object
    json_response = create_attr_data(json_post)

    r = requests.post(dest_page, json=json_post, headers={"apikey": headers['Apikey'], "userdata": headers['Userdata']})
    return json_response, r.status_code


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
