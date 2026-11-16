fn main() {
    let config = slint_build::CompilerConfiguration::new().with_style("fluent-dark".into());
    slint_build::compile_with_config("ui/app.slint", config).expect("Slint build failed");

    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        #[cfg(windows)]
        {
            let mut res = winresource::WindowsResource::new();
            res.set_icon("packaging/windows/icon.ico");
            res.set("ProductName", "Mukyu Launcher");
            res.set("FileDescription", "Mukyu Launcher");
            if let Err(e) = res.compile() {
                println!("cargo:warning=could not embed Windows resources: {e}");
            }
        }
    }
    println!("cargo:rerun-if-changed=packaging/windows/icon.ico");
}
