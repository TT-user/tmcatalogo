"""Fase 3: baixa 2 fotos por produto (frente e costas), otimiza e gera o catálogo.

Uso:
  python scripts/baixar.py --secao brasileiros [--commit]
  python scripts/baixar.py --liga premier-league [--commit]
  python scripts/baixar.py --so-catalogo        # só regera data/catalogo.json

Frente = capa do álbum (o vendedor escolhe a frente como capa).
Costas = álbum com 2 fotos: a outra; com mais: scripts/costas.py compara miniaturas.
Retomável por state/progress.json. Com --commit, faz commit e push a cada ~300 MB.
Álbuns em "revisar" e "nao-produto" não são baixados.
"""
import argparse, io, json, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventario import pedir  # mesmos headers, pausa e retry
from costas import outra_face

RAIZ = Path(__file__).resolve().parent.parent
PROGRESSO = RAIZ / "state" / "progress.json"
CATALOGO = RAIZ / "data" / "catalogo.json"
IMAGENS = RAIZ / "imagens"
LOTE_MB = 300
SIMULTANEAS = 2
# 800 px: o site inteiro cabe no limite de 1 GB do GitHub Pages (medido: ~0,75 GB)
LARGURA, QUALIDADE = 800, 74
LARGURA_THUMB, QUALIDADE_THUMB = 400, 70
ORDEM_SECOES = ["brasileiros", "europeus", "selecoes", "retro", "sul-americanos", "norte-americanos", "outros"]

MODELO_PT = {"home": "Titular", "away": "Reserva", "third": "Terceira", "fourth": "Quarta",
             "goleiro": "Goleiro", "treino": "Treino", "especial": "Edição Especial"}
TIPO_PT = {"torcedor": "Torcedor", "jogador": "Jogador", "retro": "Retrô", "treino": "Treino",
           "agasalho": "Agasalho", "kit-infantil": "Kit Infantil", "calcao": "Calção",
           "camiseta": "Camiseta", "camisa": "Camisa", "acessorio": "Acessório"}
PUBLICO_SIGLA = {"masculino": "m", "feminino": "f", "infantil": "i"}
TAM_ADULTO = ["P", "M", "G", "GG", "2GG", "3GG", "4GG", "5GG", "6GG", "7GG"]
TAM_EN = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL", "7XL"]

_trava = threading.Lock()


def carregar():
    inv = {a["id"]: a for a in json.loads((RAIZ / "data" / "inventario.json").read_text("utf-8"))}
    cla = json.loads((RAIZ / "data" / "classificacao.json").read_text("utf-8"))
    return inv, cla


def slug(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pastas(cla):
    """Pasta de cada álbum, estável entre execuções (ordem por id)."""
    usadas, saida = set(), {}
    for r in sorted(cla, key=lambda r: int(r["id"])):
        if r["secao"] in ("revisar", "nao-produto"):
            continue
        nome = "-".join(x for x in [r["temporada"] or "sem-temporada", r["modelo"], r["tipo"], r["publico"]] if x)
        base = f"{r['secao']}/{r['liga'] or 'sem-liga'}/{r['time'] or 'sem-time'}/{slug(nome)}"
        p, n = base, 2
        while p in usadas:
            p, n = f"{base}-{n}", n + 1
        usadas.add(p)
        saida[r["id"]] = p
    return saida


def tamanhos(titulo, publico):
    t = titulo.upper().replace("XXXXL", "4XL").replace("XXXL", "3XL").replace("XXL", "2XL")
    if publico == "infantil":
        m = re.search(r"\b(\d{1,2})\s*-\s*(\d{2})\b", t)
        if m and int(m.group(1)) < int(m.group(2)) <= 40:
            return [str(x) for x in range(int(m.group(1)), int(m.group(2)) + 1, 2)]
        return None
    m = re.search(r"\b(S|M)\s*-\s*(\d?XL|L)\b", t)
    if not m:
        return None
    ini, fim = TAM_EN.index(m.group(1)), TAM_EN.index(m.group(2)) if m.group(2) in TAM_EN else None
    return TAM_ADULTO[ini:fim + 1] if fim is not None else None


def salvar(dados, destino, largura, qualidade):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(dados))).convert("RGB")
    if im.width > largura:
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
    im.save(destino, "WEBP", quality=qualidade, method=6)  # sem exif: metadados ficam de fora
    return destino.stat().st_size


def foto(url):
    """Original; se falhar ou não for imagem, a versão big."""
    for u in (url, url.rsplit("/", 1)[0] + "/big.jpg"):
        try:
            d = pedir(u).content
            Image.open(io.BytesIO(d)).verify()
            return d
        except Exception:
            continue
    raise RuntimeError(f"foto não baixou: {url}")


def processar(a, pasta):
    urls = a["urls_fotos"]
    capa = a["frente"] if a["frente"] is not None else 0
    outra = outra_face(urls, capa, lambda u: pedir(u).content)
    # com nome e número de jogador no título (#Luciano #10), a capa costuma ser a costas
    if outra is not None and re.search(r"#[A-Za-zÀ-ú.]{2,}.*#\d+", a["titulo"]):
        frente, costas = outra, capa
    else:
        frente, costas = capa, outra
    destino = IMAGENS / pasta
    destino.mkdir(parents=True, exist_ok=True)
    dados_f = foto(urls[frente])
    total = salvar(dados_f, destino / "01.webp", LARGURA, QUALIDADE)
    total += salvar(dados_f, destino / "thumb.webp", LARGURA_THUMB, QUALIDADE_THUMB)
    arquivos = ["01.webp"]
    if costas is not None:
        total += salvar(foto(urls[costas]), destino / "02.webp", LARGURA, QUALIDADE)
        arquivos.append("02.webp")
    return {"pasta": pasta, "arquivos": arquivos, "frente": frente, "costas": costas, "bytes": total}


def git(*args):
    subprocess.run(["git", *args], cwd=RAIZ, check=True)


def publicar(msg):
    gerar_catalogo()
    git("add", "imagens", "state/progress.json", "data/catalogo.json", "state/restam.txt")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RAIZ).returncode:
        git("commit", "-q", "-m", msg)
        for n in range(3):
            if subprocess.run(["git", "push", "-q"], cwd=RAIZ).returncode == 0:
                return
            subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=RAIZ)
            time.sleep(10)
        raise RuntimeError("push falhou 3 vezes")


def gerar_catalogo():
    inv, cla = carregar()
    prog = json.loads(PROGRESSO.read_text("utf-8")) if PROGRESSO.exists() else {}
    saida = []
    for r in cla:
        p = prog.get(r["id"])
        if not p:
            continue
        temp = (r["temporada"] or "").replace("-", "/")
        partes = [r["time_nome"] or "", temp, MODELO_PT.get(r["modelo"], "")]
        titulo = " ".join(x for x in partes if x).strip()
        titulo = f"{titulo} – {TIPO_PT.get(r['tipo'], r['tipo'])}" if titulo else TIPO_PT.get(r["tipo"], r["tipo"])
        if r["publico"] != "masculino" and r["tipo"] != "kit-infantil":
            titulo += " Feminina" if r["publico"] == "feminino" else " Infantil"
        base = f"imagens/{p['pasta']}"
        saida.append({
            "id": f"{r['time'] or 'item'}-{r['temporada'] or 'x'}-{r['modelo'] or 'x'}-{r['tipo']}-{PUBLICO_SIGLA[r['publico']]}-{r['id']}",
            "titulo": titulo,
            "secao": r["secao"], "liga": r["liga"], "time": r["time"], "time_nome": r["time_nome"],
            "pais": r["pais"], "publico": r["publico"], "tipo": r["tipo"],
            "temporada": r["temporada"], "modelo": r["modelo"],
            "imagens": [f"{base}/{f}" for f in p["arquivos"]],
            "thumb": f"{base}/thumb.webp",
            "preco": None,
            "tamanhos": tamanhos(r["titulo"], r["publico"]),
            "titulo_original": r["titulo"],
            "origem": inv[r["id"]]["url"],
        })
    CATALOGO.write_text(json.dumps(saida, ensure_ascii=False, indent=1), "utf-8")
    return len(saida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secao", help="uma seção ou 'todas'")
    ap.add_argument("--ate-minutos", type=float, help="para com folga antes do limite do Actions")
    ap.add_argument("--liga")
    ap.add_argument("--limite", type=int, help="processa só N álbuns (teste)")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--so-catalogo", action="store_true")
    o = ap.parse_args()
    if o.so_catalogo:
        print(f"catálogo: {gerar_catalogo()} produtos")
        return
    if not (o.secao or o.liga):
        sys.exit("informe --secao ou --liga")

    inv, cla = carregar()
    mapa = pastas(cla)
    prog = json.loads(PROGRESSO.read_text("utf-8")) if PROGRESSO.exists() else {}
    todas = o.secao == "todas"
    fila = [r for r in cla if r["id"] in mapa and r["id"] not in prog
            and (todas or not o.secao or r["secao"] == o.secao) and (not o.liga or r["liga"] == o.liga)]
    fila.sort(key=lambda r: ORDEM_SECOES.index(r["secao"]) if r["secao"] in ORDEM_SECOES else 99)
    inicio = time.time()
    pulados = 0
    (RAIZ / "state").mkdir(exist_ok=True)
    (RAIZ / "state" / "restam.txt").write_text(str(len(fila)), "utf-8")
    if o.limite:
        fila = fila[:o.limite]
    alvo = o.secao or o.liga
    print(f"{alvo}: {len(fila)} álbuns a baixar ({len(prog)} já no progress.json)", flush=True)

    lote, falhas, feitos = 0, [], 0

    def um(r):
        nonlocal lote, feitos, pulados
        if o.ate_minutos and time.time() - inicio > o.ate_minutos * 60:
            pulados += 1  # fica para a próxima execução
            return
        try:
            res = processar(inv[r["id"]], mapa[r["id"]])
        except Exception as e:
            falhas.append((r["id"], r["titulo"], str(e)))
            print(f"  FALHOU {r['titulo']}: {e}", flush=True)
            return
        with _trava:
            prog[r["id"]] = res
            PROGRESSO.parent.mkdir(exist_ok=True)
            PROGRESSO.write_text(json.dumps(prog, ensure_ascii=False), "utf-8")
            lote += res["bytes"]
            feitos += 1
            if feitos % 25 == 0:
                print(f"  {feitos}/{len(fila)}", flush=True)
            if o.commit and lote > LOTE_MB * 1024 ** 2:
                publicar(f"Imagens: {alvo}, lote até {feitos}/{len(fila)}")
                lote = 0

    with ThreadPoolExecutor(SIMULTANEAS) as ex:
        list(ex.map(um, fila))

    (RAIZ / "state").mkdir(exist_ok=True)
    (RAIZ / "state" / "restam.txt").write_text(str(pulados), "utf-8")
    n = gerar_catalogo()
    if o.commit:
        publicar(f"Imagens: {alvo} concluída ({feitos} álbuns)")
    print(f"fim: {feitos}/{len(fila)} baixados, {len(falhas)} falhas, {pulados} para a próxima; catálogo com {n} produtos", flush=True)
    for f in falhas:
        print("  falha:", *f, flush=True)


if __name__ == "__main__":
    main()
