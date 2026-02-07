#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
import subprocess
import urllib.parse

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_POST(self):
        if self.path == '/api/complete-task':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            project_id = data.get('projectId')
            task_id = data.get('taskId')
            
            if project_id and task_id:
                result = subprocess.run(
                    ['python3', os.path.join(DIRECTORY, 'ticktick', 'complete_task.py'), project_id, task_id],
                    capture_output=True, text=True
                )
                response = result.stdout
            else:
                response = json.dumps({"error": "Missing projectId or taskId"})
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
            
            # Refresh data after completing task
            subprocess.Popen(['python3', os.path.join(DIRECTORY, 'fetch_data.py')])
        
        elif self.path == '/api/save-moveout':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            data_path = os.path.join(DIRECTORY, 'data', 'moveout.json')
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

class ReuseAddrServer(socketserver.TCPServer):
    allow_reuse_address = True

with ReuseAddrServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Dashboard running at http://0.0.0.0:{PORT}")
    httpd.serve_forever()
