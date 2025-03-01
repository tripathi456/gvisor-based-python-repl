import http.server
import socketserver
import socket
import json
import sys
import traceback
import io
import logging
import asyncio
import websockets
import argparse
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

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

# Function to execute code and return the result
def execute_code(code, exec_env):
    output = io.StringIO()
    try:
        old_stdout = sys.stdout
        try:
            sys.stdout = output
            exec(code, exec_env)
        finally:
            sys.stdout = old_stdout
            
        result = output.getvalue()
        return {"status": "ok", "output": result}
    except Exception:
        tb = traceback.format_exc()
        return {"status": "error", "error": tb}

# Websocket handler
async def websocket_handler(websocket, path):
    try:
        async for message in websocket:
            # Execute the code
            result = execute_code(message, ExecHandler.exec_env)
            # Send the result back
            await websocket.send(json.dumps(result))
            logging.info("Websocket executed code: %s", message[:50] + ("..." if len(message) > 50 else ""))
    except websockets.exceptions.ConnectionClosed:
        logging.info("Websocket connection closed")
    except Exception as e:
        logging.error("Error in websocket handler: %s", str(e))
        traceback.print_exc()

# Function to run the HTTP server
def run_http_server(host, port):
    server = http.server.ThreadingHTTPServer((host, port), ExecHandler)
    logging.info("Python REPL server listening on TCP %s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("HTTP server shut down")

# Function to run the websocket server
async def run_websocket_server(host, port):
    async with websockets.serve(websocket_handler, host, port):
        logging.info("Python REPL server listening on WebSocket %s:%d", host, port)
        await asyncio.Future()  # Run forever

# Main function to parse arguments and start servers
def main():
    parser = argparse.ArgumentParser(description="Python REPL server with TCP and WebSocket support")
    parser.add_argument("--tcp", action="store_true", help="Enable TCP server")
    parser.add_argument("--ws", action="store_true", help="Enable WebSocket server")
    parser.add_argument("--tcp-port", type=int, default=8000, help="TCP server port (default: 8000)")
    parser.add_argument("--ws-port", type=int, default=8001, help="WebSocket server port (default: 8001)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    # If neither --tcp nor --ws is specified, enable both
    if not args.tcp and not args.ws:
        args.tcp = True
        args.ws = True
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Start the servers based on the arguments
    if args.tcp and args.ws:
        # Run both servers concurrently
        logging.info("Starting both TCP and WebSocket servers")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run HTTP server in a separate thread
        executor = ThreadPoolExecutor(max_workers=1)
        http_future = executor.submit(run_http_server, args.host, args.tcp_port)
        
        # Run WebSocket server in the main thread
        try:
            loop.run_until_complete(run_websocket_server(args.host, args.ws_port))
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, shutting down servers")
        finally:
            loop.close()
            executor.shutdown(wait=False)
    elif args.tcp:
        # Run only HTTP server
        run_http_server(args.host, args.tcp_port)
    elif args.ws:
        # Run only WebSocket server
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_websocket_server(args.host, args.ws_port))
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, shutting down server")
        finally:
            loop.close()

if __name__ == "__main__":
    main()