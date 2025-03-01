import http.server
import socketserver
import socket
import json
import sys
import traceback
import io
import logging
from urllib.parse import urlparse

class ExecHandler(http.server.BaseHTTPRequestHandler):
    # Persistent execution namespace.
    exec_env = {}
    
    def do_POST(self):
        if urlparse(self.path).path != "/exec":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
            
        code = self.rfile.read(content_length).decode("utf-8")
        output = io.StringIO()
        
        try:
            old_stdout = sys.stdout
            try:
                sys.stdout = output
                exec(code, ExecHandler.exec_env)
            finally:
                sys.stdout = old_stdout
                
            result = output.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "ok", "output": result}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        except Exception:
            tb = traceback.format_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "error", "error": tb}
            self.wfile.write(json.dumps(response).encode("utf-8"))
    
    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s",
                     self.client_address,
                     self.log_date_time_string(),
                     format % args)

def main():
    # Use TCP configuration
    host = "0.0.0.0"  # Listen on all interfaces
    port = 8000
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Use threading server for handling multiple connections
    server = http.server.ThreadingHTTPServer((host, port), ExecHandler)
    
    logging.info("Python REPL server listening on TCP %s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server is shutting down")
    finally:
        server.server_close()
        logging.info("Server shut down")

if __name__ == "__main__":
    main()
