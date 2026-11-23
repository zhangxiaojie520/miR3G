#!/usr/bin/env python3
"""Patch EasyTier v2.6.4 source for the ultra-slim mipsel build.

Usage: python3 patch.py <source-root>

Env:
  NOWSS=1         drop wss/TLS support (rustls, tokio-rustls, webpki-roots, rcgen)
  FMTDEBUG=1      add -Z fmt-debug=none to target rustflags
  ABORT=modern    profile panic = "immediate-abort" + cargo-features opt-in
  ABORT=legacy    profile panic = "abort" only (std feature set by the workflow)

Every textual replacement is asserted: a missing pattern aborts the build.
"""
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "source")
here = pathlib.Path(__file__).resolve().parent
nowss = os.environ.get("NOWSS") == "1"
fmtdebug = os.environ.get("FMTDEBUG") == "1"
abort_mode = os.environ.get("ABORT", "0")
if abort_mode == "1":  # backwards compatibility
    abort_mode = "modern"
aborts = abort_mode in ("modern", "legacy")


def read(rel):
    return (root / rel).read_text()


def write(rel, text):
    (root / rel).write_text(text)


def sub(rel, old, new, label):
    text = read(rel)
    if old not in text:
        sys.exit(f"PATCH FAILED [{label}] in {rel}\n--- missing ---\n{old[:300]}")
    write(rel, text.replace(old, new, 1))
    print(f"patched [{label}] {rel}")


# ---------------------------------------------------------------- slim main
write("easytier/src/easytier-core.rs", (here / "slim_main.rs").read_text())
print("replaced easytier/src/easytier-core.rs with slim main")

# ---------------------------------------------------------------- no wss / TLS
if nowss:
    sub(
        "easytier/Cargo.toml",
        'websocket = [\n'
        '    "dep:tokio-websockets",\n'
        '    "dep:http",\n'
        '    "dep:forwarded-header-value",\n'
        '    "dep:tokio-rustls",\n'
        '    "dep:rustls",\n'
        '    "dep:rcgen",\n'
        ']\n',
        'websocket = [\n'
        '    "dep:tokio-websockets",\n'
        '    "dep:http",\n'
        '    "dep:forwarded-header-value",\n'
        ']\n',
        "cargo-websocket-feature",
    )

    sub(
        "easytier/Cargo.toml",
        'features = [\n    "rustls-webpki-roots",\n    "client",',
        'features = [\n    "client",',
        "cargo-tokio-websockets-features",
    )

    sub(
        "easytier/src/tunnel/mod.rs",
        '#[cfg(any(feature = "quic", feature = "websocket"))]\n'
        "pub mod insecure_tls;\n",
        '#[cfg(feature = "quic")]\npub mod insecure_tls;\n',
        "tunnel-mod-gate",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        "    common::{TunnelWrapper, wait_for_connect_futures},\n"
        "    insecure_tls::{get_insecure_tls_cert, init_crypto_provider},\n"
        "    packet_def::{ZCPacket, ZCPacketType},\n"
        "};\n"
        "use crate::tunnel::common::bind;\n"
        "use crate::{proto::common::TunnelInfo, tunnel::insecure_tls::get_insecure_tls_client_config};\n",
        "    common::{TunnelWrapper, wait_for_connect_futures},\n"
        "    packet_def::{ZCPacket, ZCPacketType},\n"
        "};\n"
        "use crate::tunnel::common::bind;\n"
        "use crate::proto::common::TunnelInfo;\n",
        "ws-imports",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        "use tokio_rustls::TlsAcceptor;\nuse tokio_util::either::Either;\n",
        "",
        "ws-tls-imports",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        '        "ws" => Ok(false),\n'
        '        "wss" => Ok(true),\n'
        "        _ => Err(TunnelError::InvalidProtocol(addr.scheme().to_string())),\n",
        '        "ws" => Ok(false),\n'
        "        _ => Err(TunnelError::InvalidProtocol(addr.scheme().to_string())),\n",
        "ws-is_wss",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        "        let stream = if is_wss(&self.addr)? {\n"
        "            init_crypto_provider();\n"
        "            let (certs, key) = get_insecure_tls_cert();\n"
        "            let config = rustls::ServerConfig::builder()\n"
        "                .with_no_client_auth()\n"
        "                .with_single_cert(certs, key)\n"
        '                .with_context(|| "Failed to create server config")?;\n'
        "\n"
        "            let stream = TlsAcceptor::from(Arc::new(config)).accept(stream).await?;\n"
        "            Either::Left(stream)\n"
        "        } else {\n"
        "            Either::Right(stream)\n"
        "        };\n",
        "        is_wss(&self.addr)?;\n",
        "ws-server-tls",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        "        let is_wss = is_wss(&addr)?;\n",
        "        is_wss(&addr)?;\n",
        "ws-client-is_wss-var",
    )

    sub(
        "easytier/src/tunnel/websocket.rs",
        "        let stream: MaybeTlsStream<TcpStream> = if is_wss {\n"
        "            init_crypto_provider();\n"
        "            let tls_conn =\n"
        "                tokio_rustls::TlsConnector::from(Arc::new(get_insecure_tls_client_config()));\n"
        '            // Modify SNI logic: use "localhost" as SNI for url without domain to avoid IP blocking.\n'
        "            let sni = match addr.domain() {\n"
        '                None => "localhost".to_string(),\n'
        "                Some(domain) => domain.to_string(),\n"
        "            };\n"
        "            let server_name = rustls::pki_types::ServerName::try_from(sni)\n"
        '                .map_err(|_| TunnelError::InvalidProtocol("Invalid SNI".to_string()))?;\n'
        "            let stream = tls_conn.connect(server_name, stream).await?;\n"
        "            MaybeTlsStream::Rustls(stream)\n"
        "        } else {\n"
        "            MaybeTlsStream::Plain(stream)\n"
        "        };\n",
        "        let stream: MaybeTlsStream<TcpStream> = MaybeTlsStream::Plain(stream);\n",
        "ws-client-tls",
    )

# ---------------------------------------------------------------- link flags
cfg = pathlib.Path(root / ".cargo/config.toml")
text = cfg.read_text()
marker = (
    '[target.mipsel-unknown-linux-musl]\n'
    'linker = "mipsel-unknown-linux-muslsf-gcc"\n'
    "rustflags = [\n"
)
if marker not in text:
    sys.exit("PATCH FAILED [cargo-config-marker]")
extra = '    "-C",\n    "link-arg=-Wl,--gc-sections",\n'
if abort_mode == "modern":
    # Rust 1.95 turned immediate-abort into a real panic strategy; rustc needs
    # -Z unstable-options present at the crate level for that value.
    extra += '    "-Z",\n    "unstable-options",\n'
if fmtdebug:
    extra += '    "-Z",\n    "fmt-debug=none",\n'
cfg.write_text(text.replace(marker, marker + extra, 1))
print(f"patched [cargo-config-rustflags] fmtdebug={fmtdebug} abort={abort_mode}")

# ---------------------------------------------------------------- mini profile
ws = pathlib.Path(root / "Cargo.toml")
wtext = ws.read_text()
if abort_mode == "modern" and "cargo-features" not in wtext:
    wtext = 'cargo-features = ["panic-immediate-abort"]\n\n' + wtext
    print("prepended cargo-features = panic-immediate-abort")
if "profile.mini" not in wtext:
    block = '\n[profile.mini]\ninherits = "release"\nopt-level = "z"\n'
    if abort_mode == "modern":
        block += 'panic = "immediate-abort"\n'
    elif abort_mode == "legacy":
        block += 'panic = "abort"\n'
    wtext = wtext + block
    print(f"added [profile.mini] abort={abort_mode}")
ws.write_text(wtext)

print("ALL PATCHES APPLIED")
