{
  description = "Python SHV Tree";
  inputs.pyshv.url = "github:silicon-heaven/pyshv";

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
      src = builtins.path {
        path = ./.;
        filter = path: type: ! hasSuffix ".nix" path;
      };

      pypy2nix_map = {
        "ruamel.yaml" = "ruamel-yaml";
      };
      list2attr = list: attr: attrValues (getAttrs list attr);
      pypi2nix = list:
        list2attr (map (n: let
          nn = elemAt (match "([^ ]*).*" n) 0;
        in
          pypy2nix_map.${nn} or nn)
        list);

      requires = pypi2nix pyproject.project.dependencies;
      requires-docs = pypi2nix pyproject.project.optional-dependencies.docs;
      requires-test = pypi2nix pyproject.project.optional-dependencies.test;
      requires-dev = p:
        pypi2nix pyproject.project.optional-dependencies.lint p
        ++ [p.build p.twine];

      pypkg-shvtree = {
        buildPythonPackage,
        pytestCheckHook,
        pythonPackages,
        setuptools,
        sphinxHook,
      }:
        buildPythonPackage {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          format = "pyproject";
          inherit src;
          outputs = ["out" "doc"];
          propagatedBuildInputs = requires pythonPackages;
          nativeBuildInputs = [setuptools sphinxHook] ++ requires-docs pythonPackages;
          nativeCheckInputs = [pytestCheckHook] ++ requires-test pythonPackages;
        };

      pypkg-asyncinotify = {
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
          pythonPackagesExtension = final: prev: {
            shvtree = final.callPackage pypkg-shvtree {};
            asyncinotify = final.callPackage pypkg-asyncinotify {};
            sphinx-multiversion = final.callPackage pypkg-multiversion {};
          };
          noInherit = final: prev: {
            pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [self.overlays.pythonPackagesExtension];
          };
          default = composeManyExtensions [
            pyshv.overlays.default
            self.overlays.noInherit
          ];
        };
      }
      // eachDefaultSystem (system: let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
      in {
        packages = {
          inherit (pkgs.python3Packages) shvtree;
          default = pkgs.python3Packages.shvtree;
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
