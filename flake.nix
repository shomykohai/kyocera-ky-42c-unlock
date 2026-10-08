{
  description = "Bootloader unlock for the Kyocera DIGNO Keitai 4 (KY-42C)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    rust-overlay,
  }: let
    inherit (nixpkgs) lib;

    systems = ["x86_64-linux" "aarch64-linux"];

    forAllSystems = fn:
      lib.genAttrs systems (
        system:
          fn (import nixpkgs {
            inherit system;
            overlays = [rust-overlay.overlays.default];
          })
      );

    source = lib.cleanSourceWith {
      src = lib.cleanSource ./.;
      filter = path: _type:
        !(builtins.elem (baseNameOf path) ["target" "build" "out" "dump" "__pycache__"]);
    };

    rustToolchain = pkgs: pkgs.rust-bin.fromRustupToolchainFile ./rust-toolchain.toml;
  in {
    packages = forAllSystems (pkgs: let
      toolchain = rustToolchain pkgs;

      rustPlatform = pkgs.makeRustPlatform {
        cargo = toolchain;
        rustc = toolchain;
      };
    in rec {
      kyocera-ky-42c-unlock = rustPlatform.buildRustPackage {
        pname = "kyocera-ky-42c-unlock";
        version = "0.1.0";

        src = source;
        cargoHash = "sha256-BS4MHU5BM6QNkNLAmfJrM4P0iY/VbgJxapU9TTVuGUo=";

        nativeBuildInputs = [pkgs.gcc-arm-embedded pkgs.gnumake pkgs.pkg-config];
        buildInputs = [pkgs.udev];

        meta = {
          description = "Bootloader unlock for the Kyocera DIGNO Keitai 4 (KY-42C)";
          homepage = "https://github.com/shomykohai/kyocera-ky-42c-unlock";
          license = lib.licenses.agpl3Plus;
          mainProgram = "kyocera-ky-42c-unlock";
          platforms = systems;
        };
      };

      default = kyocera-ky-42c-unlock;
    });

    apps = forAllSystems (pkgs: let
      package = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
    in rec {
      kyocera-ky-42c-unlock = {
        type = "app";
        program = "${package}/bin/kyocera-ky-42c-unlock";
      };

      default = kyocera-ky-42c-unlock;
    });

    overlays.default = _final: prev: {
      kyocera-ky-42c-unlock = self.packages.${prev.stdenv.hostPlatform.system}.default;
    };

    devShells = forAllSystems (pkgs: {
      default = pkgs.mkShell {
        packages = [
          (rustToolchain pkgs)
          pkgs.rust-analyzer
          pkgs.gcc-arm-embedded
          pkgs.gnumake
          pkgs.git
          pkgs.python3
          pkgs.clang
          pkgs.llvm
          pkgs.lld
          pkgs.cmake
        ];

        nativeBuildInputs = [pkgs.pkg-config];
        buildInputs = [pkgs.udev];

        shellHook = ''
          export CROSS_COMPILE=arm-none-eabi-
        '';
      };
    });
  };
}
