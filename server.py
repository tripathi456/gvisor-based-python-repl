import socketserver
import socket
import json
import sys
import traceback
import io
import logging
import uuid
import threading
import asyncio
import websockets
from concurrent.futures import ThreadPoolExecutor

# Dictionary to store session environments
sessions = {}
sessions_lock = threading.Lock()

def process_request(code, session_id=None):
    """Process a code execution request."""
    # If no session_id provided, create a new session
    if not session_id:
        session_id = str(uuid.uuid4())
        with sessions_lock:
            sessions[session_id] = {}
        logging.info(f"Created new session: {session_id}")
    # If session_id provided but doesn't exist, return error
    elif session_id not in sessions:
        return {
            "status": "error",
            "error": f"Session {session_id} not found"
        }
    
    # Execute the code in the session's environment
    output = io.StringIO()
    try:
        old_stdout = sys.stdout
        try:
            sys.stdout = output
            with sessions_lock:
                exec(code, sessions[session_id])
        finally:
            sys.stdout = old_stdout
            
        result = output.getvalue()
        return {
            "status": "ok", 
            "output": result,
            "session_id": session_id
        }
    except Exception:
        tb = traceback.format_exc()
        return {
            "status": "error", 
            "error": tb,
            "session_id": session_id
        }

class PythonREPLHandler(socketserver.BaseRequestHandler):
    def handle(self):
        """Handle incoming TCP connections."""
        self.request.settimeout(300)  # 5-minute timeout
        logging.info(f"Connection established from {self.client_address}")
        
        try:
            # Initial greeting with protocol info
            self.send_response({
                "status": "ok", 
                "message": "Python REPL Server. Send JSON with 'code' to execute. Optional 'session_id' to continue a session."
            })
            
            while True:
                # Receive data from client
                data = self.receive_data()
                if not data:
                    break
                
                try:
                    request = json.loads(data)
                    
                    # Extract code and optional session_id
                    code = request.get('code', '')
                    session_id = request.get('session_id', None)
                    
                    # Process the request
                    response = process_request(code, session_id)
                    self.send_response(response)
                    
                except json.JSONDecodeError:
                    self.send_response({
                        "status": "error", 
                        "error": "Invalid JSON format"
                    })
                except Exception as e:
                    self.send_response({
                        "status": "error", 
                        "error": str(e)
                    })
        except socket.timeout:
            logging.info(f"Connection from {self.client_address} timed out")
        except ConnectionError:
            logging.info(f"Connection from {self.client_address} closed by client")
        except Exception as e:
            logging.error(f"Error handling connection from {self.client_address}: {str(e)}")
        finally:
            logging.info(f"Connection from {self.client_address} closed")
    
    def receive_data(self):
        """Receive data from the client."""
        try:
            # First receive the message length (4 bytes)
            length_bytes = self.request.recv(4)
            if not length_bytes:
                return None
            
            # Convert bytes to integer
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual message
            chunks = []
            bytes_received = 0
            while bytes_received < message_length:
                chunk = self.request.recv(min(4096, message_length - bytes_received))
                if not chunk:
                    raise ConnectionError("Connection closed while receiving data")
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            return b''.join(chunks).decode('utf-8')
        except Exception as e:
            logging.error(f"Error receiving data: {str(e)}")
            return None
    
    def send_response(self, response_dict):
        """Send a response to the client."""
        try:
            # Convert response to JSON string
            response_json = json.dumps(response_dict)
            response_bytes = response_json.encode('utf-8')
            
            # Send message length first (4 bytes)
            length = len(response_bytes)
            self.request.sendall(length.to_bytes(4, byteorder='big'))
            
            # Send the actual message
            self.request.sendall(response_bytes)
        except Exception as e:
            logging.error(f"Error sending response: {str(e)}")
    
# WebSocket handler
async def websocket_handler(websocket, path):
    """Handle incoming WebSocket connections."""
    client_address = websocket.remote_address
    logging.info(f"WebSocket connection established from {client_address}")
    
    try:
        # Initial greeting with protocol info
        await websocket.send(json.dumps({
            "status": "ok", 
            "message": "Python REPL Server. Send JSON with 'code' to execute. Optional 'session_id' to continue a session."
        }))
        
        async for message in websocket:
            try:
                request = json.loads(message)
                
                # Extract code and optional session_id
                code = request.get('code', '')
                session_id = request.get('session_id', None)
                
                # Process the request
                response = process_request(code, session_id)
                await websocket.send(json.dumps(response))
                
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "status": "error", 
                    "error": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send(json.dumps({
                    "status": "error", 
                    "error": str(e)
                }))
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"WebSocket connection from {client_address} closed by client")
    except Exception as e:
        logging.error(f"Error handling WebSocket connection from {client_address}: {str(e)}")
    finally:
        logging.info(f"WebSocket connection from {client_address} closed")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run_tcp_server(host, port):
    """Run the TCP server."""
    server = ThreadedTCPServer((host, port), PythonREPLHandler)
    logging.info(f"Python REPL server listening on TCP {host}:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("TCP Server is shutting down")
    finally:
        server.server_close()
        logging.info("TCP Server shut down")

async def run_websocket_server(host, port):
    """Run the WebSocket server."""
    server = await websockets.serve(websocket_handler, host, port)
    logging.info(f"Python REPL server listening on WebSocket ws://{host}:{port}")
    
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        logging.info("WebSocket Server is shutting down")
        server.close()
        await server.wait_closed()
        logging.info("WebSocket Server shut down")

def main():
    # Server configuration
    host = "0.0.0.0"  # Listen on all interfaces
    tcp_port = 8000
    ws_port = 8001
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Check if command line arguments specify the connection type
    if len(sys.argv) > 1 and sys.argv[1] == "ws-only":
        # WebSocket only mode
        asyncio.run(run_websocket_server(host, ws_port))
    elif len(sys.argv) > 1 and sys.argv[1] == "tcp-only":
        # TCP only mode
        run_tcp_server(host, tcp_port)
    else:
        # Run both TCP and WebSocket servers
        # Create a thread for the TCP server
        tcp_thread = threading.Thread(target=run_tcp_server, args=(host, tcp_port))
        tcp_thread.daemon = True
        tcp_thread.start()
        
        # Run the WebSocket server in the main thread
        try:
            asyncio.run(run_websocket_server(host, ws_port))
        except KeyboardInterrupt:
            logging.info("Servers are shutting down")
        finally:
            # TCP server will shut down automatically when the main thread exits
            # because it's a daemon thread
            logging.info("Servers shut down")

if __name__ == "__main__":
    main()