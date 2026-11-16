
use std::sync::OnceLock;

pub fn session() -> Option<zbus::blocking::Connection> {
    static CONN: OnceLock<Option<zbus::blocking::Connection>> = OnceLock::new();
    CONN.get_or_init(|| zbus::blocking::Connection::session().ok()).clone()
}
