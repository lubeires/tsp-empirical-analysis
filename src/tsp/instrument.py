"""Instrumentação por sub-rotina: tempo (padrão) ou pico de memória (modo memória).

Uso dentro de um algoritmo (o profiler é passado como parâmetro, D11 / T05 opção (a)):

    def algoritmo(dist, prof=None):
        prof = prof or Profiler()
        with prof.timed("mst"):
            ...

Observação: trechos podem ser aninhados (ex.: "mst" dentro de "christofides").
O tempo do trecho de dentro também está contido no de fora, então os tempos
não se somam entre níveis diferentes.
"""

import gc
import time
import tracemalloc
from dataclasses import dataclass


@dataclass
class _Stats:
    calls: int = 0
    time_s: float = 0.0
    peak_bytes: int = 0


def _gc_collections() -> int:
    """Total de coletas de lixo já feitas pelo Python (somando as 3 gerações)."""
    return sum(gen["collections"] for gen in gc.get_stats())


class Profiler:
    """Acumula chamadas, tempo e (no modo memória) pico de memória por nome de trecho."""

    def __init__(self, memory: bool = False):
        self.memory = memory
        self._stats: dict[str, _Stats] = {}
        # Pilha dos trechos abertos no modo memória.
        # Cada item: [memória em uso ao entrar, maior pico absoluto já visto no trecho]
        self._stack: list[list[int]] = []
        self._gc_start = _gc_collections()
        self._started_tracing = False
        if memory and not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracing = True

    # Permite `with Profiler(memory=True) as prof:` para desligar o tracemalloc no fim
    def __enter__(self) -> "Profiler":
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def stop(self) -> None:
        """Desliga o tracemalloc, se foi este profiler que o ligou."""
        if self._started_tracing:
            tracemalloc.stop()
            self._started_tracing = False

    def timed(self, name: str) -> "_Timer":
        """Devolve um gerenciador de contexto que mede o trecho `name`."""
        # Não usar setdefault(name, _Stats()): o argumento _Stats() seria criado
        # (e descartado) a cada chamada, custando ~0,4 µs (medido na T05).
        stats = self._stats.get(name)
        if stats is None:
            stats = self._stats[name] = _Stats()
        return _Timer(self, stats)

    def _enter_memory(self) -> None:
        current, peak = tracemalloc.get_traced_memory()
        if self._stack:
            # O pico do tracemalloc é único para o programa todo. Antes de zerá-lo,
            # repassa ao trecho de fora o pico que ele já tinha atingido.
            self._stack[-1][1] = max(self._stack[-1][1], peak)
        tracemalloc.reset_peak()
        self._stack.append([current, current])

    def _exit_memory(self) -> int:
        """Fecha o trecho atual e devolve o pico alocado dentro dele (em bytes)."""
        start, seen_peak = self._stack.pop()
        _, peak = tracemalloc.get_traced_memory()
        absolute_peak = max(peak, seen_peak)
        if self._stack:
            # O trecho de fora também "viu" este pico
            self._stack[-1][1] = max(self._stack[-1][1], absolute_peak)
        return absolute_peak - start

    def gc_collections(self) -> int:
        """Coletas de lixo feitas desde a criação do profiler."""
        return _gc_collections() - self._gc_start

    def records(self) -> list[dict]:
        """Uma linha por trecho, no formato do profile.csv."""
        return [
            {
                "subroutine": name,
                "calls": s.calls,
                "time_s": s.time_s,
                "peak_bytes": s.peak_bytes if self.memory else None,
            }
            for name, s in self._stats.items()
        ]


class _Timer:
    """Gerenciador de contexto devolvido por Profiler.timed.

    É uma classe (e não um @contextmanager) por desempenho: o @contextmanager
    cria um gerador a cada uso. Medido na T05, o custo de `with prof.timed(...)`
    caiu de ~2,1 µs para ~1,05 µs (junto com a troca do setdefault em timed).
    Importa no B&B, que mede o limite inferior em cada nó (D19).
    """

    __slots__ = ("prof", "stats", "start")  # evita criar um __dict__ por objeto

    def __init__(self, prof: Profiler, stats: _Stats):
        self.prof = prof
        self.stats = stats

    def __enter__(self) -> None:
        if self.prof.memory:
            self.prof._enter_memory()
        self.start = time.perf_counter()

    def __exit__(self, *exc) -> bool:
        # Executado mesmo se o trecho terminar com exceção (ex.: timeout do B&B)
        self.stats.time_s += time.perf_counter() - self.start
        self.stats.calls += 1
        if self.prof.memory:
            self.stats.peak_bytes = max(self.stats.peak_bytes, self.prof._exit_memory())
        return False  # não engole a exceção
