import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import urllib.parse
import time
import requests

hostName = "161.72.123.165"
serverPort = 8080


class Middleware(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>https://pythonbasics.org</title></head>", "utf-8"))
        self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes("<p>This is an example web server.</p>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))

    def do_POST(self):
        post_data = self.rfile.read(int(self.headers['Content-Length']))
        if self.path == '/subscriber':
            data = urllib.parse.quote(post_data.decode('utf-8'), safe='\"\n\t {}:,[]\\/$%')
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

            r = requests.post('http://orm-viotserver:1026/v2/subscriptions', json=json_post, headers=self.headers)
            self.send_response(r.status_code)
            self.send_header("Content-type", "application/json")
            self.wfile.write(bytes(r.text, "utf-8"))
            self.end_headers()
        elif self.path == '/notification':
            data = urllib.parse.unquote(post_data.decode('utf-8'))
            headers = {}
            for header in self.headers.keys():
                headers[header] = urllib.parse.unquote(self.headers.get(header))
            dest_page = headers.pop("destpage")
            headers.pop("Content-Length")
            headers.pop("Host")
            headers['Content-Type'] = "application/json"
            headers['host'] = hostName
            json_post = json.JSONDecoder().decode(data)
            print(json_post['PanelFields'][1])
            r = requests.post(dest_page, json=json_post, headers={"apikey": headers['apikey'], "userdata": headers['userdata']})
            self.send_response(201)
            self.end_headers()


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), Middleware)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")