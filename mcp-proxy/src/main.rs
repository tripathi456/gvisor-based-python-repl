mod python_client;
mod mcp;
mod handlers;

use axum::{
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Build our application with routes
    let app = Router::new()
        .route("/", get(handlers::health_check))
        .route("/execute", post(handlers::execute_code))
        .layer(TraceLayer::new_for_http());

    // Run the server
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    tracing::info!("MCP Proxy listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}