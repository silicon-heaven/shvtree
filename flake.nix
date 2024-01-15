{
  description = "Project template for Python";

  outputs = {
    self,
    flake-utils,
    nixpkgs,
  }:
    with builtins;
    with flake-utils.lib;
    with nixpkgs.lib; let
      pyproject = trivial.importTOML ./pyproject.toml;
      attrList = attr: list: attrValues (getAttrs list attr);

      requires = p: attrList p pyproject.project.dependencies;
      requires-docs = p: attrList p pyproject.project.optional-dependencies.docs;
      requires-test = p: attrList p pyproject.project.optional-dependencies.test;
      requires-dev = p:
        attrList p pyproject.project.optional-dependencies.lint
        ++ [p.build p.twine];

      pypkg-template-python = {
        buildPythonPackage,
        pytestCheckHook,
        pythonPackages,
        setuptools,
        sphinxHook,
      }:
        buildPythonPackage {
          pname = pyproject.project.name;
          version = fileContents ./foo/version;
          format = "pyproject";
          src = builtins.path {
            path = ./.;
            filter = path: type: ! hasSuffix ".nix" path;
          };
          outputs = ["out" "doc"];
          propagatedBuildInputs = requires pythonPackages;
          nativeBuildInputs = [setuptools sphinxHook] ++ requires-docs pythonPackages;
          nativeCheckInputs = [pytestCheckHook] ++ requires-test pythonPackages;
        };
    in
      {
        overlays = {
          pythonPackagesExtension = final: prev: {
            template-python = final.callPackage pypkg-template-python {};
          };
          noInherit = final: prev: {
            pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [self.overlays.pythonPackagesExtension];
          };
          default = composeManyExtensions [self.overlays.noInherit];
        };
      }
      // eachDefaultSystem (system: let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;
      in {
        packages.default = pkgs.python3Packages.template-python;
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

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/foo";
        };


        checks.default = self.packages.${system}.default;

        formatter = pkgs.alejandra;
      });
}
