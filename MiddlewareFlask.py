import json
import urllib.parse
import requests
import os
from flask import Flask, request, jsonify, Response


hostName = "161.72.123.165"
serverPort = 8080

app = Flask(__name__)


@app.route("/subscriptions", methods=['POST'])
def subscribe():
    data = urllib.parse.quote(request.data.decode('utf-8'), safe='\"\n\t {}:,[]\\/$%')
    json_post = json.JSONDecoder().decode(data)
    notification = json_post['notification']
    if 'httpCustom' in notification.keys():
        if 'headers' in notification['httpCustom']:
            notification['httpCustom']['headers']['destPage'] = notification['httpCustom']['url']
        else:
            notification['httpCustom']['headers']['destPage'] = notification['httpCustom']['url']
    else:
        new_notification = {"httpCustom": {
            "url": notification['http']['url'],
            "headers": {
                "desPage": notification['http']['url']
            },
            'method': 'POST'
        }}
        json_post['notification'] = new_notification

    notification['httpCustom']['url'] = "http://%s:%s/notification" % (hostName, serverPort)
    print(json_post)
    r = requests.post('http://orm-viotserver:1026/v2/subscriptions', json=json_post, headers=request.headers)
    resp = Response("Example")
    resp.headers = r.headers.items()
    resp.status_code = r.status_code
    resp.da = r.text
    return Response(json.dumps(r.text), status=r.status_code, mimetype='application/json', headers=r.headers.items())


@app.route("/notification", methods=['POST'])
def notify():
    data = urllib.parse.unquote(request.data.decode('utf-8'))
    headers = {}
    for header in request.headers.keys():
        headers[header] = urllib.parse.unquote(request.headers[header])
    print(headers)
    dest_page = headers.pop("Destpage")
    json_post = json.JSONDecoder().decode(data)
    print(json_post['PanelFields'][1])
    r = requests.post(dest_page, json=json_post, headers={"apikey": headers['Apikey'], "userdata": headers['Userdata']})
    return "200"


@app.route("/subscriptions/<subscription_id>", methods=['DELETE'])
def delete(subscription_id):
    r = requests.delete('http://orm-viotserver:1026/v2/subscriptions/'+subscription_id)
    return r.text, r.status_code


@app.route("/subscriptions", methods=['DELETE'])
def delete_with_body():
    id = request.json['id']
    r = requests.delete('http://orm-viotserver:1026/v2/subscriptions/'+id)
    return r.text, r.status_code


@app.route("/dummy", methods=['POST'])
def dummy():
    data = urllib.parse.unquote(request.data.decode('utf-8'))
    print(data)
    return "200"


if __name__ == "__main__":
    app.run(threaded=True, host=hostName, port=serverPort)