let
  inherit (import <nixpkgs> {})
    chromedriver
    chromium
    mkShell
    python3
  ;

  inherit (python3.pkgs)
    altgraph
    buildPythonPackage
    fetchPypi
    requests-toolbelt
  ;

  my-python = python3.override {
    packageOverrides = self: super: {
      beepy = buildPythonPackage rec {
        pname = "beepy";
        version = "1.0.7";
        src = fetchPypi {
          inherit pname version;
          sha256 = "0psv1na3cygarh7h42nc1zigsqmpj99c2yyys6lar6607kzlhww1";
        };
        doCheck = false;
        propagatedBuildInputs = [
          super.simpleaudio
        ];
      };

      cloudscraper = buildPythonPackage rec {
        pname = "cloudscraper";
        version = "1.2.58";
        src = fetchPypi {
          inherit pname version;
          sha256 = "1wnzv2k8cm8q1x18r4zg8pcnpm4gsdp82hywwjimp2v2qll918nx";
        };
        doCheck = false;
        propagatedBuildInputs = [
          self.pyparsing
          super.requests-toolbelt
        ];
      };

      plyer = buildPythonPackage rec {
        pname = "plyer";
        version = "2.0.0";
        src = fetchPypi {
          inherit pname version;
          sha256 = "156z58gzb3afzilhdbsm323sn0sky1n59kgaxmpg73a3phbqpqwd";
        };
        doCheck = false;
      };

      pyparsing = buildPythonPackage rec {
        pname = "pyparsing";
        version = "2.4.7";
        src = fetchPypi {
          inherit pname version;
          sha256 = "1hgc8qrbq1ymxbwfbjghv01fm3fbpjwpjwi0bcailxxzhf3yq0y2";
        };
        doCheck = false;
      };
    };
  };
in

mkShell {
  name = "vaccipy";

  buildInputs = [
    chromium
    (my-python.withPackages (p: [
      p.beepy
      p.certifi
      p.chardet
      p.cloudscraper
      p.idna
      p.plyer
      p.selenium
      p.urllib3
    ]))
  ];

  shellHook = ''
    export VACCIPY_CHROMEDRIVER=${chromedriver}/bin/chromedriver
  '';
}
