"""Baixa da TSPLIB as instâncias usadas no trabalho e confere os checksums.

Uso (na raiz do projeto):
    .venv/bin/python -m experiments.fetch_tsplib

Os arquivos baixados também ficam versionados em data/tsplib/; este script
existe para que o download possa ser refeito e verificado (constituição, P5).
"""

import csv
import gzip
import hashlib
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ARCHIVE_URL = "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/ALL_tsp.tar.gz"
OPTIMA_SOURCE = "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/TSP-BEST.html"

# Raiz do projeto = duas pastas acima de src/experiments/
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "tsplib"

# SHA-256 dos arquivos já descompactados (calculados no download de 20/11/2026)
CHECKSUMS = {
    # Faixa limite: instâncias completas (D1)
    "eil51.tsp": "66c05ad077ffd64d5778e358bbd16be049f8c8ae880cbd24f034487331d1ccce",
    "berlin52.tsp": "8496a5838133e3c3eb25a9fa8893b1ac302593fc8dc325350643a0cabd8abadc",
    "st70.tsp": "60c09e8886609bf22d6dc699fe7d7aa1924207d084578aad1a377ec65cf15b1b",
    # Origens das sub-instâncias (D6): uniformes
    "kroA100.tsp": "e103100c1cf31dfc06be95a9d04011b5a8753bb65a3339594ca34404e574bdf5",
    "rd100.tsp": "6f62863c4f5d9fe1d7226077923716b8d0ba76d58bae7eb65fdaff127c5cdf5c",
    # Origens das sub-instâncias (D6): estruturadas / com clusters
    "pr76.tsp": "5746518c9358041835e887663ad6c8b65432ff4b21eabf69e46417b4324ddcec",
    "lin105.tsp": "8d34cafef4279bf6ab077a5c5c75bc4757a509f9cbbfd42f7e3170a5e280e1cb",
    "pr107.tsp": "e0d774d2e853fbb1a507f06e8aa83e625690edc29866268e970471ea6febf65b",
    "d198.tsp": "d4383f7a91eabb83f8b1be9b4b7bf98bf15f8c87851ad99e6aa6719046d414df",
    # Rota ótima oficial, usada no teste da T03
    "berlin52.opt.tour": "8f3915f397dcdbf9f07bd570fc41faa7e9b3d27391537f048164b2f937d1ccc9",
}

# Ótimos publicados (fonte: OPTIMA_SOURCE, consultada em 20/11/2026)
OPTIMA = {
    "eil51": 426,
    "berlin52": 7542,
    "st70": 675,
    "kroA100": 21282,
    "rd100": 7910,
    "pr76": 108159,
    "lin105": 14379,
    "pr107": 44303,
    "d198": 15780,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "ALL_tsp.tar.gz"
        print(f"Baixando {ARCHIVE_URL} ...")
        urllib.request.urlretrieve(ARCHIVE_URL, archive_path)

        with tarfile.open(archive_path, "r:gz") as tar:
            for name, expected in CHECKSUMS.items():
                # Lê só o membro pedido (sem extractall), evitando gravar
                # caminhos arbitrários vindos do arquivo compactado.
                member = tar.extractfile(f"{name}.gz")
                if member is None:
                    raise FileNotFoundError(f"{name}.gz não está no pacote")
                data = gzip.decompress(member.read())

                actual = sha256(data)
                if actual != expected:
                    raise ValueError(f"Checksum diferente para {name}: {actual}")

                (DATA_DIR / name).write_bytes(data)
                print(f"  ok  {name}")

    optima_path = DATA_DIR / "optima.csv"
    with optima_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["instance", "optimum"])
        for instance, value in OPTIMA.items():
            writer.writerow([instance, value])
    print(f"  ok  {optima_path.name}")


if __name__ == "__main__":
    main()
