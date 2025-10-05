import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/ask':
            # Simple test response for GET requests
            response = json.dumps({"answer": "Please send a POST request with your question"})
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            # Handle other GET requests normally
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            question = data.get('question', '').lower()
            
            # Simple answers
            if 'password' in question:
                answer = "To reset your password, go to the login page and click 'Forgot Password'"
            elif 'email' in question:
                answer = "Check your spam folder if you're not receiving emails"
            elif 'vpn' in question:
                answer = "Download the VPN client from the company website"
            else:
                answer = "I'm not sure about that. Please contact IT support."
            
            response = json.dumps({"answer": answer})
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

PORT = 8000
with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()