{
  description = "Python SHV Tree";
  inputs = {
    pyshv.url = "git+https://gitlab.com/elektroline-predator/pyshv.git";
  };

  outputs = {
    self,
    flake-utils,
    nixpkgs,
    pyshv,
  }:
    with builtins;
    with flake-utils.lib;
    with nixpkgs.lib; let
      pyproject = trivial.importTOML ./pyproject.toml;
      list2attr = list: attr: attrValues (getAttrs list attr);

      pypy2nix_map = {
        "ruamel.yaml" = "ruamel-yaml";
      };
      pypi2nix = list: list2attr (map (n: pypy2nix_map.${n} or n) list);

      requires = pypi2nix pyproject.project.dependencies;
      requires-docs = pypi2nix pyproject.project.optional-dependencies.docs;
      requires-test = pypi2nix pyproject.project.optional-dependencies.test;
      requires-dev = p:
        pypi2nix pyproject.project.optional-dependencies.lint p
        ++ [p.build p.twine];

      pypkgs-pyshvtree = {
        buildPythonPackage,
        pythonPackages,
        sphinxHook,
        pytestCheckHook,
      }:
        buildPythonPackage {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          format = "pyproject";
          src = builtins.path {
            path = ./.;
            filter = path: type: ! hasSuffix ".nix" path;
          };
          outputs = ["out" "doc"];
          propagatedBuildInputs = requires pythonPackages;
          nativeBuildInputs = [sphinxHook] ++ requires-docs pythonPackages;
          nativeCheckInputs = [pytestCheckHook] ++ requires-test pythonPackages;
        };

      pypkgs-asyncinotify = {
        buildPythonPackage,
        fetchPypi,
        pipBuildHook,
        flit,
      }:
        buildPythonPackage rec {
          pname = "asyncinotify";
          version = "4.0.1";
          src = fetchPypi {
            inherit pname version;
            hash = "sha256-0j3/zbPw3oMm+t7QSgshm/KL4gZ7JVo3tsudXF6Xt0E=";
          };
          nativeBuildInputs = [pipBuildHook flit];
          dontUseSetuptoolsBuild = true;
          doCheck = false;
        };

      pypkg-multiversion = {
        buildPythonPackage,
        fetchFromGitHub,
        sphinx,
      }:
        buildPythonPackage {
          pname = "sphinx-multiversion";
          version = "0.2.4";
          src = fetchFromGitHub {
            owner = "Holzhaus";
            repo = "sphinx-multiversion";
            rev = "v0.2.4";
            hash = "sha256-ZFEELAeZ/m1pap1DmS4PogL3eZ3VuhTdmwDOg5rKOPA=";
          };
          propagatedBuildInputs = [sphinx];
          doCheck = false;
        };
    in
      {
        overlays = {
          pyshvtree = final: prev: {
            python3 = prev.python3.override (oldAttrs: {
              packageOverrides = composeExtensions oldAttrs.packageOverrides (
                pyfinal: pyprev: {
                  pyshvtree = pyfinal.callPackage pypkgs-pyshvtree {};
                  asyncinotify = pyfinal.callPackage pypkgs-asyncinotify {};
                  sphinx-multiversion = pyfinal.callPackage pypkg-multiversion {};
                }
              );
            });
            python3Packages = final.python3.pkgs;
          };
          default = composeManyExtensions [
            pyshv.overlays.default
            self.overlays.pyshvtree
          ];
        };
      }
      // eachDefaultSystem (system: let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
      in {
        packages = {
          inherit (pkgs.python3Packages) pyshvtree;
          default = self.packages.${system}.pyshvtree;
        };
        legacyPackages = pkgs;

        devShells = filterPackages system {
          default = pkgs.mkShell {
            packages = with pkgs; [
              editorconfig-checker
              gitlint
              (python3.withPackages (p:
                [p.sphinx-autobuild]
                ++ foldl (prev: f: prev ++ f p) [] [
                  requires
                  requires-docs
                  requires-test
                  requires-dev
                ]))
            ];
          };
        };

        checks.default = self.packages.${system}.default;

        formatter = pkgs.alejandra;
      });
}