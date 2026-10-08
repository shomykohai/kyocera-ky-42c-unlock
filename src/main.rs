/*
 * Kyocera KY-42C Unlock - Bootloader unlock for Kyocera KY-42C on firmware 1.090XX+
 * Copyright (C) 2026 Shomy
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#![feature(file_buffered)]

use std::fs::{self, File};
use std::path::PathBuf;
use std::process::exit;
use std::thread::sleep;
use std::time::Duration;

use anyhow::{Result, bail};
use clap::{CommandFactory, Parser, Subcommand};
use indicatif::{ProgressBar, ProgressStyle};
use penumbra_mtk::{DeviceBuilder, MtkPort, Partition, PlProtocol, PortBackend, PortType};

const MAX_PAYLOAD_SIZE: usize = 0x900000;
const UNLOCK_PAYLOAD: &[u8] = include_bytes!("../bin/unlock.bin");
const PATCH_PAYLOAD: &[u8] = include_bytes!("../bin/patch.bin");
const DA: &[u8] = include_bytes!("MT6761.bin");

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    #[command(about = "Unlock the device bootloader")]
    Unlock,
    #[command(about = "Disable DAA to allow using other flashing tools")]
    Patch,
    #[command(about = "Send a custom payload to the device")]
    Payload { file: PathBuf },
    #[command(about = "Dump specified partitions, comma separated, to dump/ directory", visible_aliases = &["dump", "d", "read", "r"])]
    DumpPartitions { partitions: String },
    #[command(about = "Write a partition from a file into the device", visible_aliases = &["write", "w"])]
    WritePartition { partition: String, file: PathBuf },
}

struct ProgressBarWrapper {
    pb: ProgressBar,
    done: u64,
}

impl ProgressBarWrapper {
    fn new(total: u64) -> Self {
        let pb = ProgressBar::new(total);
        pb.set_style(ProgressStyle::with_template("{spinner:.green} [{elapsed_precise}] [{wide_bar:.cyan/blue}] {bytes}/{total_bytes} ({eta}) {msg}")
               .unwrap()
               .progress_chars("#>-"));

        Self { pb, done: 0 }
    }

    fn callback(&self) -> impl FnMut(u64, u64) {
        let pb = self.pb.clone();
        let done = self.done;
        move |progress: u64, _: u64| pb.set_position(done + progress)
    }

    fn advance(&mut self, size: u64) {
        self.done += size;
        self.pb.set_position(self.done);
    }

    fn finish(&self) {
        self.pb.finish_with_message("Done");
    }

    fn set_message(&self, message: &str) {
        self.pb.set_message(message.to_owned());
    }
}

fn handle_da_cmd(port: PortType, cmd: Commands) -> Result<()> {
    let mut dev = DeviceBuilder::new(port).with_da_data(DA).build()?;

    println!("Initializing device...");
    dev.init()?;

    println!("Entering DA mode...");

    dev.enter_da_mode()?;

    match cmd {
        Commands::DumpPartitions { partitions } => {
            let parts: Vec<&str> = partitions.split(',').collect();

            let matching_parts: Vec<Partition> = dev
                .partitions_iter()
                .filter_map(|p| if parts.contains(&p.name.as_str()) { Some(p) } else { None })
                .collect();

            if matching_parts.is_empty() {
                bail!("No matching partitions found for: {}", partitions);
            }

            let dump_dir = PathBuf::from("dump");
            if !dump_dir.exists() {
                fs::create_dir_all(&dump_dir)?;
            }

            let total_size: u64 = matching_parts.iter().map(|p| p.size).sum();
            let mut pb = ProgressBarWrapper::new(total_size);

            for part in matching_parts {
                let writer = File::create_buffered(dump_dir.join(format!("{}.img", part.name)))?;

                pb.set_message(&format!("Dumping partition: {}", part.name));

                dev.read_partition(&part.name, writer, pb.callback())?;
                pb.advance(part.size);
            }

            pb.finish();
        }
        Commands::WritePartition { partition, file } => {
            if dev.get_partition(&partition).is_none() {
                bail!("Partition {} not found on device", partition);
            }

            let reader = File::open_buffered(&file)?;
            let len = reader.get_ref().metadata()?.len();

            let pb = ProgressBarWrapper::new(len);
            pb.set_message(&format!("Writing partition: {}", partition));

            dev.write_partition(&partition, len, reader, pb.callback())?;
            pb.finish();

            println!("Partition '{}' written from {}", partition, file.display());
        }
        _ => {}
    }

    Ok(())
}

fn main() {
    let args = Args::parse();

    if args.command.is_none() {
        Args::command().print_help().unwrap();
        return;
    }

    let cmd = args.command.unwrap();

    let payload = match &cmd {
        Commands::Unlock => UNLOCK_PAYLOAD.to_vec(),
        Commands::DumpPartitions { .. } | Commands::WritePartition { .. } | Commands::Patch => {
            PATCH_PAYLOAD.to_vec()
        }
        Commands::Payload { file } => {
            let payload = fs::read(&file).expect("Failed to read payload file");
            if payload.len() > MAX_PAYLOAD_SIZE {
                eprintln!("Payload size exceeds maximum allowed size of {MAX_PAYLOAD_SIZE} bytes");
                exit(1);
            }

            payload
        }
    };

    println!("-------------------------------------------");
    println!("Kyocera KY-42C Unlock");
    println!("Copyright (c) 2026 Shomy");
    println!("SPDX License-Identifier: AGPL-3.0-or-later");
    println!("-------------------------------------------");

    println!("Waiting for device to be connected...");

    let mut port = loop {
        match PortType::find_and_open(Some(0x0E8D), Some(0x2000), PortBackend::Auto) {
            Ok(Some(port)) => break port,
            Ok(None) | Err(_) => sleep(Duration::from_millis(150)),
        }
    };

    println!("Found device: {:?}", port.get_port_name());

    let mut pl = PlProtocol::new(&mut port);
    pl.handshake().expect("Failed to handshake with device");

    println!("Sending payload of size {} bytes", payload.len());

    pl.send_image("lk", &payload).expect("Failed to send payload");
    pl.boot_image("lk").expect("Failed to jump to payload");

    if matches!(&cmd, Commands::DumpPartitions { .. } | Commands::WritePartition { .. })
        && let Err(e) = handle_da_cmd(port, cmd)
    {
        eprintln!("Error: {e}");
        exit(1);
    }

    println!("Done!");
}
