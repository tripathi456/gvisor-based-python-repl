use axum::{
    extract::Json,
    http::StatusCode,
    response::{IntoResponse, Response},
};
use serde_json::json;

use crate::{mcp, python_client};

// Health check handler
pub async fn health_check() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({"status": "ok"})))
}

// Execute code handler
pub async fn execute_code(
    Json(request): Json<mcp::McpRequest>,
) -> Result<Json<mcp::McpResponse>, AppError> {
    // Execute the code using the Python client
    let response = python_client::execute_code(request.code, request.session_id).await?;

    // Convert the Python response to an MCP response
    let mcp_response = mcp::convert_to_mcp_response(
        &response.status,
        response.output.as_deref(),
        response.error.as_deref(),
        &response.session_id,
    );

    Ok(Json(mcp_response))
}

// Application error type
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("Python client error: {0}")]
    PythonClientError(#[from] anyhow::Error),
}

// Convert AppError to an HTTP response
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_message) = match self {
            AppError::PythonClientError(err) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Failed to execute code: {}", err),
            ),
        };

        let body = Json(json!({
            "status": "error",
            "error": error_message,
        }));

        (status, body).into_response()
    }
}