mod format;
mod unused;

fn main() {
    let msg = format::render("deploy", "ok");
    println!("{msg}");
}
