"""Exporta a transcrição do Claude Code (.jsonl) para Markdown legível em prompts/ (T24, D16).

Uso (na raiz do projeto):
    python3 scripts/export_prompts.py <transcricao.jsonl> [<saida.md>] [--redact ARQUIVO]

`--redact`: arquivo FORA do repositório com um termo por linha (ex.: nome, domínio);
cada ocorrência, sem diferenciar maiúsculas, vira "[removido]". A lista fica fora do
repositório para que os próprios termos não sejam publicados.

O que entra: as mensagens da autora, as respostas em texto do assistente e cada uso de
ferramenta (nome e entrada resumida), com as saídas das ferramentas cortadas.
O que sai: o raciocínio interno do assistente, os lembretes injetados pelo sistema
(<system-reminder>, que trazem dados da conta, como o e-mail) e conteúdo binário.
Ao final, falha se algum endereço de e-mail sobrar no arquivo gerado.

Só usa a biblioteca padrão.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_INPUT_LIMIT = 1500   # caracteres da entrada de cada ferramenta
TOOL_OUTPUT_LIMIT = 1200  # caracteres da saída de cada ferramenta
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
NOISE = re.compile(r"<(local-command-caveat|command-name|command-message|command-args|"
                   r"local-command-stdout)>.*?</\1>", re.S)


REDACT: list[re.Pattern] = []


def clean(text: str) -> str:
    text = NOISE.sub("", REMINDER.sub("", text))
    text = EMAIL.sub("[e-mail removido]", text)
    for pattern in REDACT:
        text = pattern.sub("[removido]", text)
    return text.strip()


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… [{len(text) - limit} caracteres cortados]"


def fence(text: str) -> str:
    """Bloco de código que não quebra se o texto tiver crases."""
    ticks = "````" if "```" in text else "```"
    return f"{ticks}\n{text}\n{ticks}"


def tool_use(block: dict) -> str:
    name, args = block.get("name", "?"), block.get("input", {})
    if name == "Bash":
        body = args.get("command", "")
        title = args.get("description", "")
    elif name in ("Write", "Edit", "Read"):
        title = args.get("file_path", "")
        body = args.get("content") or args.get("new_string") or ""
    else:
        title, body = "", json.dumps(args, ensure_ascii=False, indent=1)
    head = f"**Ferramenta: {name}**" + (f" — {clean(title)}" if title else "")
    body = clean(body)
    return head + ("\n\n" + fence(cut(body, TOOL_INPUT_LIMIT)) if body else "")


def tool_result(block: dict) -> str:
    content = block.get("content", "")
    if isinstance(content, list):
        parts = []
        for c in content:
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif c.get("type") == "image":
                parts.append("[imagem]")
        content = "\n".join(parts)
    content = clean(str(content))
    return "*Resultado:*\n\n" + fence(cut(content, TOOL_OUTPUT_LIMIT)) if content else ""


def render(entry: dict) -> list[str]:
    kind = entry.get("type")
    if kind not in ("user", "assistant") or entry.get("isMeta"):
        return []
    content = entry.get("message", {}).get("content", "")
    blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
    out = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            text = clean(block.get("text", ""))
            if not text:
                continue
            if kind == "user":
                label = ("### Resumo automático do contexto"
                         if text.startswith("This session is being continued") else "### Autora")
                out.append(f"{label}\n\n{text}")
            else:
                out.append(f"### Assistente\n\n{text}")
        elif btype == "tool_use":
            out.append(tool_use(block))
        elif btype == "tool_result":
            res = tool_result(block)
            if res:
                out.append(res)
        # "thinking" e demais tipos ficam de fora
    return out


def export(src: Path, dst: Path) -> int:
    parts = [f"# Transcrição da sessão do Claude Code ({src.stem})",
             "Gerada por `scripts/export_prompts.py`: mensagens da autora, respostas do "
             "assistente e uso de ferramentas (entradas e saídas cortadas). Lembretes do "
             "sistema e raciocínio interno foram removidos."]
    with src.open() as f:
        for line in f:
            parts += render(json.loads(line))
    text = "\n\n".join(parts) + "\n"
    leftover = [m for m in EMAIL.findall(text) if "[e-mail removido]" not in m]
    leftover += [m for p in REDACT for m in p.findall(text)]
    if leftover:
        raise SystemExit(f"dado pessoal ainda presente na saída: {len(leftover)} ocorrência(s)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return len(text)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--redact" in args:
        i = args.index("--redact")
        terms = Path(args[i + 1]).read_text().split()
        REDACT += [re.compile(re.escape(t), re.I) for t in terms if t]
        del args[i:i + 2]
    src = Path(args[0])
    dst = Path(args[1]) if len(args) > 1 else ROOT / "prompts" / f"session-{src.stem[:8]}.md"
    size = export(src, dst)
    print(f"{dst.relative_to(ROOT)}: {size / 1e6:.1f} MB")
