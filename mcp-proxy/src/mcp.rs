use serde::{Deserialize, Serialize};

// MCP Request structure
#[derive(Debug, Deserialize)]
pub struct McpRequest {
    pub code: String,
    #[serde(default)]
    pub session_id: Option<String>,
}

// MCP Response structure
#[derive(Debug, Serialize)]
pub struct McpResponse {
    pub status: String,
    pub content: McpContent,
    pub session_id: String,
}

// MCP Content structure
#[derive(Debug, Serialize)]
#[serde(tag = "type")]
pub enum McpContent {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "error")]
    Error { error: String },
}

impl McpResponse {
    // Create a successful response
    pub fn success(output: String, session_id: String) -> Self {
        Self {
            status: "success".to_string(),
            content: McpContent::Text { text: output },
            session_id,
        }
    }

    // Create an error response
    pub fn error(error_message: String, session_id: String) -> Self {
        Self {
            status: "error".to_string(),
            content: McpContent::Error { error: error_message },
            session_id,
        }
    }
}

// Convert from Python response to MCP response
pub fn convert_to_mcp_response(
    python_status: &str,
    python_output: Option<&str>,
    python_error: Option<&str>,
    session_id: &str,
) -> McpResponse {
    match python_status {
        "ok" => {
            let output = python_output.unwrap_or("").to_string();
            McpResponse::success(output, session_id.to_string())
        }
        _ => {
            let error = python_error.unwrap_or("Unknown error").to_string();
            McpResponse::error(error, session_id.to_string())
        }
    }
}