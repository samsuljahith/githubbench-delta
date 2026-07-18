pub fn render(kind: &str, status: &str) -> String {
    format!("{kind}:{status}")
}

pub fn render_json(kind: &str, status: &str) -> String {
    let kind = kind.replace('"', "\\\"");
    let status = status.replace('"', "\\\"");
    format!(r#"{{"kind":"{kind}","status":"{status}"}}"#)
}
