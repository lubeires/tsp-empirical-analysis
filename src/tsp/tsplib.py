"""Leitura de arquivos no formato TSPLIB (instâncias EUC_2D e rotas .tour).

Convenção do projeto: nos arquivos os vértices são numerados a partir de 1;
dentro do código, a partir de 0. A conversão acontece só neste módulo.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Instance:
    """Instância do TSP: nome e coordenadas (array n x 2 de floats)."""

    name: str
    coords: np.ndarray

    @property
    def n(self) -> int:
        return len(self.coords)


def _read_header(lines: list[str], section: str) -> tuple[dict[str, str], int]:
    """Lê as linhas 'CHAVE : valor' até encontrar `section`.

    Devolve o dicionário do cabeçalho e o índice da primeira linha de dados.
    """
    header = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(section):
            return header, i + 1
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            header[key.strip().upper()] = value.strip()
    raise ValueError(f"Seção {section} não encontrada")


def read_tsp(path: str | Path) -> Instance:
    """Lê uma instância EUC_2D. Qualquer outro tipo de distância é recusado (P2)."""
    lines = Path(path).read_text().splitlines()
    header, start = _read_header(lines, "NODE_COORD_SECTION")

    weight_type = header.get("EDGE_WEIGHT_TYPE")
    if weight_type != "EUC_2D":
        raise ValueError(f"{path}: EDGE_WEIGHT_TYPE é {weight_type}, esperado EUC_2D")

    dimension = int(header["DIMENSION"])
    coords = []
    for line in lines[start:]:
        parts = line.split()
        if not parts or parts[0] == "EOF":
            break
        # Formato da linha: <id> <x> <y>; o id é descartado (a ordem já define o índice)
        coords.append((float(parts[1]), float(parts[2])))

    if len(coords) != dimension:
        raise ValueError(f"{path}: DIMENSION={dimension}, mas foram lidos {len(coords)} pontos")

    return Instance(name=header.get("NAME", Path(path).stem), coords=np.array(coords))


def read_tour(path: str | Path) -> list[int]:
    """Lê uma rota (.tour) e devolve os vértices com índices a partir de 0."""
    lines = Path(path).read_text().splitlines()
    header, start = _read_header(lines, "TOUR_SECTION")

    tour = []
    for line in lines[start:]:
        for token in line.split():
            vertex = int(token)
            if vertex == -1:  # -1 marca o fim da rota
                break
            tour.append(vertex - 1)
        else:
            continue
        break

    dimension = int(header["DIMENSION"])
    if len(tour) != dimension:
        raise ValueError(f"{path}: DIMENSION={dimension}, mas a rota tem {len(tour)} vértices")
    return tour
