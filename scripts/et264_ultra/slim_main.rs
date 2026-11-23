// Ultra-slim entrypoint: no clap, no RPC portal, no config-server, no service manager.
use easytier::common::config::{ConfigFileControl, TomlConfigLoader};
use easytier::instance_manager::NetworkInstanceManager;
use std::path::PathBuf;
use std::sync::Arc;

#[tokio::main(flavor = "current_thread")]
async fn main() -> std::process::ExitCode {
    let _ = tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .try_init();

    let path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "/tmp/easytier.toml".to_string());
    let cfg = match TomlConfigLoader::new(&PathBuf::from(&path)) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("easytier-slim: load config {} failed: {:#}", path, e);
            return std::process::ExitCode::FAILURE;
        }
    };

    let manager = Arc::new(NetworkInstanceManager::new().with_config_path(None));
    if let Err(e) = manager.run_network_instance(cfg, true, ConfigFileControl::STATIC_CONFIG) {
        eprintln!("easytier-slim: start instance failed: {:#}", e);
        return std::process::ExitCode::FAILURE;
    }
    eprintln!("easytier-slim: instance started, config={}", path);

    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut term = match signal(SignalKind::terminate()) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("easytier-slim: signal handler failed: {:#}", e);
                return std::process::ExitCode::FAILURE;
            }
        };
        tokio::select! {
            _ = tokio::signal::ctrl_c() => {}
            _ = term.recv() => {}
            _ = manager.wait() => {}
        }
    }
    #[cfg(not(unix))]
    {
        manager.wait().await;
    }

    std::process::ExitCode::SUCCESS
}
