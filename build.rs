use std::env;
use std::path::Path;
use std::process::Command;

const WATCH: &[&str] = &[
    "Makefile",
    "payload/config.mk",
    "payload/payload.mk",
    "payload/include",
    "payload/src",
    "bin/unlock.bin",
    "bin/patch.bin",
];

const PAYLOADS: &[&str] = &["bin/unlock.bin", "bin/patch.bin"];

fn main() {
    for path in WATCH {
        println!("cargo::rerun-if-changed={path}");
    }

    let root = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR is not set");
    let root = Path::new(&root);
    let jobs = env::var("NUM_JOBS").unwrap_or_else(|_| String::from("1"));

    let built = Command::new("make").current_dir(root).arg(format!("-j{jobs}")).status().is_ok_and(
        |status| {
            println!("Make result: {}", status.success());
            status.success()
        },
    );

    if built {
        return;
    }

    for payload in PAYLOADS {
        assert!(
            root.join(payload).exists(),
            "failed to build the payloads and {payload} is missing, run make first"
        );
    }

    println!("cargo::warning=failed to build the payloads, using the ones already in bin/");
}
