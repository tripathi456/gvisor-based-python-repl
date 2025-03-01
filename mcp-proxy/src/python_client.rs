use anyhow::{Context, Result};
use bytes::{BufMut, BytesMut};
use serde::{Deserialize, Serialize};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;

// Python REPL server connection details
const PYTHON_SERVER_HOST: &str = "127.0.0.1";
const PYTHON_SERVER_PORT: u16 = 8000;

// Request to the Python REPL server
#[derive(Debug, Serialize)]
pub struct PythonRequest {
    pub code: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

// Response from the Python REPL server
#[derive(Debug, Deserialize)]
pub struct PythonResponse {
    pub status: String,
    pub output: Option<String>,
    pub error: Option<String>,
    pub session_id: String,
}

// Client for communicating with the Python REPL server
pub struct PythonClient {
    stream: TcpStream,
}

impl PythonClient {
    // Connect to the Python REPL server
    pub async fn connect() -> Result<Self> {
        let addr = format!("{}:{}", PYTHON_SERVER_HOST, PYTHON_SERVER_PORT);
        let stream = TcpStream::connect(&addr)
            .await
            .context(format!("Failed to connect to Python REPL server at {}", addr))?;

        let mut client = Self { stream };

        // Read the initial greeting message
        let _greeting = client.read_response().await?;

        Ok(client)
    }

    // Execute Python code on the server
    pub async fn execute(&mut self, code: String, session_id: Option<String>) -> Result<PythonResponse> {
        let request = PythonRequest { code, session_id };
        self.send_request(&request).await?;
        self.read_response().await
    }

    // Send a request to the Python REPL server
    async fn send_request(&mut self, request: &PythonRequest) -> Result<()> {
        // Serialize the request to JSON
        let json = serde_json::to_string(request)?;
        let json_bytes = json.as_bytes();
        
        // Create a buffer for the message
        let mut buf = BytesMut::with_capacity(4 + json_bytes.len());
        
        // Write the message length (4 bytes, big-endian)
        buf.put_u32(json_bytes.len() as u32);
        
        // Write the JSON message
        buf.put_slice(json_bytes);
        
        // Send the message
        self.stream.write_all(&buf).await?;
        
        Ok(())
    }

    // Read a response from the Python REPL server
    async fn read_response(&mut self) -> Result<PythonResponse> {
        // Read the message length (4 bytes)
        let mut length_buf = [0u8; 4];
        self.stream.read_exact(&mut length_buf).await?;
        let message_length = u32::from_be_bytes(length_buf) as usize;
        
        // Read the message content
        let mut message_buf = vec![0u8; message_length];
        self.stream.read_exact(&mut message_buf).await?;
        
        // Parse the JSON response
        let response: PythonResponse = serde_json::from_slice(&message_buf)?;
        
        Ok(response)
    }
}

// Execute code in a session
pub async fn execute_code(code: String, session_id: Option<String>) -> Result<PythonResponse> {
    let mut client = PythonClient::connect().await?;
    client.execute(code, session_id).await
}