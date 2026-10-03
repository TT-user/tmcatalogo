"""Fase 1: inventário de todos os álbuns da Happy Shirt, sem baixar fotos.

Uso: python scripts/inventario.py
Retomável: cada álbum lido vai para state/inventario-cache.jsonl, e uma nova
execução pula o que já está lá.

Saídas: data/inventario.json e data/inventario-resumo.md
"""
import io, json, random, re, statistics, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://happyshirt.x.yupoo.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Referer": BASE + "/",
}
SIMULTANEAS = 2
PAUSA = 0.7          # por requisição, em cada uma das 2 linhas
AMOSTRA = 300        # fotos para estimar tamanho
AMOSTRA_WEBP = 24    # destas, quantas converter de verdade para medir a otimização

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "state" / "inventario-cache.jsonl"
SAIDA = RAIZ / "data" / "inventario.json"
RESUMO = RAIZ / "data" / "inventario-resumo.md"

# categorias que não são produto
LIXO = {"4793362", "4818484", "4792364"}  # How to order?, Menu/Catalog, Contact

_local = threading.local()
_trava = threading.Lock()


def sessao():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers.update(HEADERS)
    return _local.s


class NaoExiste(Exception):
    pass


def pedir(url, metodo="GET", **kw):
    """Requisição educada: pausa, 3 tentativas com backoff em 429/5xx/567 e erro de rede."""
    for n in range(3):
        try:
            r = sessao().request(metodo, url, timeout=40, **kw)
            time.sleep(PAUSA)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                raise NaoExiste(url)
            if r.status_code in (429, 567) or r.status_code >= 500:
                time.sleep(5 * 2 ** n)
                continue
            r.raise_for_status()
        except requests.RequestException:
            time.sleep(5 * 2 ** n)
    raise RuntimeError(f"falhou 3 vezes: {url}")


def sopa(url):
    return BeautifulSoup(pedir(url).text, "html.parser")


def n_paginas(s):
    campo = s.select_one("input[max]")
    return int(campo["max"]) if campo else 1


def listar(caminho):
    """Todas as páginas de uma listagem: [(id, título, qtd_fotos, capa)].

    A capa é a foto que o vendedor escolheu para o álbum: é a de frente,
    mesmo quando aparece por último dentro do álbum."""
    sep = "&" if "?" in caminho else "?"
    s = sopa(f"{BASE}{caminho}")
    total = n_paginas(s)
    itens = []
    for p in range(1, total + 1):
        if p > 1:
            s = sopa(f"{BASE}{caminho}{sep}page={p}")
        for a in s.select("a.album__main"):
            m = re.search(r"/albums/(\d+)", a.get("href", ""))
            if not m:
                continue
            tit = a.select_one(".album__title")
            num = a.select_one(".album__photonumber")
            img = a.select_one("img")
            src = (img.get("data-src") or img.get("src") or "") if img else ""
            capa = re.search(r"photo\.yupoo\.com/[^/]+/([0-9a-z]+)/", src)
            itens.append((m.group(1),
                          (tit.get_text(strip=True) if tit else a.get("title", "")).strip(),
                          int(num.get_text(strip=True)) if num else None,
                          capa.group(1) if capa else None))
        if total > 3:
            print(f"    {caminho} {p}/{total}", flush=True)
    return itens, total


def categorias():
    s = sopa(BASE + "/")
    cats = {}
    for a in s.select('a[href^="/categories/"]'):
        m = re.match(r"/categories/(\d+)", a["href"])
        nome = " ".join(a.get_text(" ", strip=True).split())
        if m and nome and m.group(1) not in cats:
            cats[m.group(1)] = nome
    return cats


def fotos(album_id):
    s = sopa(f"{BASE}/albums/{album_id}?uid=1")
    urls = []
    for img in s.select(".showalbum__children img"):
        u = img.get("data-origin-src") or img.get("data-src")
        if not u or "square" in u:
            continue
        u = "https:" + u if u.startswith("//") else u
        if "photo.yupoo.com" in u and u not in urls:
            urls.append(u)
    return urls


def tamanho(url):
    r = pedir(url, "HEAD")
    if r.headers.get("Content-Type", "").startswith("image") and r.headers.get("Content-Length"):
        return int(r.headers["Content-Length"])
    r = pedir(url, headers={"Range": "bytes=0-0"})
    m = re.search(r"/(\d+)$", r.headers.get("Content-Range", ""))
    return int(m.group(1)) if m else None


def otimizado(url):
    """Converte de verdade: WebP 1200 px q80 + miniatura 400 px. Devolve (original, webp, thumb)."""
    from PIL import Image
    dados = pedir(url).content
    im = Image.open(io.BytesIO(dados)).convert("RGB")
    out = []
    for larg in (1200, 400):
        x = im.copy()
        if x.width > larg:
            x = x.resize((larg, round(x.height * larg / x.width)), Image.LANCZOS)
        b = io.BytesIO()
        x.save(b, "WEBP", quality=80, method=6)
        out.append(b.tell())
    return len(dados), out[0], out[1]


def mb(b):
    return f"{b / 1024**2:,.0f} MB".replace(",", ".")


def gb(b):
    return f"{b / 1024**3:.2f} GB".replace(".", ",")


def main():
    CACHE.parent.mkdir(exist_ok=True)
    SAIDA.parent.mkdir(exist_ok=True)

    # 1. galeria completa = fonte única
    galeria, pags = listar("/albums?tab=gallery")
    albuns = {}
    for aid, tit, qtd, capa in galeria:
        albuns.setdefault(aid, {"id": aid, "titulo": tit, "url": f"{BASE}/albums/{aid}?uid=1",
                                "categoria_yupoo": [], "qtd_fotos_listagem": qtd, "capa_id": capa})
    print(f"galeria: {pags} páginas, {len(galeria)} entradas, {len(albuns)} álbuns únicos", flush=True)

    # 2. categorias viram etiquetas
    cats = categorias()
    print(f"{len(cats)} categorias", flush=True)
    por_cat = {}
    inexistentes = []
    for cid, nome in cats.items():
        try:
            itens, p = listar(f"/categories/{cid}")
        except NaoExiste:
            inexistentes.append(f"{nome} ({cid})")
            print(f"  {nome}: 404, link morto no menu", flush=True)
            continue
        por_cat[cid] = {"nome": nome, "paginas": p, "albuns": len(itens)}
        for aid, tit, qtd, capa in itens:
            a = albuns.setdefault(aid, {"id": aid, "titulo": tit, "url": f"{BASE}/albums/{aid}?uid=1",
                                        "categoria_yupoo": [], "qtd_fotos_listagem": qtd,
                                        "capa_id": capa, "fora_da_galeria": True})
            if nome not in a["categoria_yupoo"]:
                a["categoria_yupoo"].append(nome)
        print(f"  {nome}: {len(itens)} álbuns em {p} pág.", flush=True)

    # 3. fotos de cada álbum (retomável)
    feitos = {}
    if CACHE.exists():
        for linha in CACHE.read_text("utf-8").splitlines():
            if linha.strip():
                d = json.loads(linha)
                feitos[d["id"]] = d["urls_fotos"]
    faltam = [a for a in albuns if a not in feitos]
    print(f"álbuns: {len(feitos)} já lidos, {len(faltam)} faltam", flush=True)
    falhas = []

    def ler(aid):
        try:
            u = fotos(aid)
        except Exception as e:
            falhas.append({"id": aid, "erro": str(e)})
            return
        with _trava:
            feitos[aid] = u
            with CACHE.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"id": aid, "urls_fotos": u}) + "\n")
            if len(feitos) % 100 == 0:
                print(f"  {len(feitos)}/{len(albuns)} álbuns lidos", flush=True)

    with ThreadPoolExecutor(SIMULTANEAS) as ex:
        list(ex.map(ler, faltam))

    for aid, a in albuns.items():
        a["urls_fotos"] = feitos.get(aid, [])
        a["qtd_fotos"] = len(a["urls_fotos"])
        # índice da foto de frente (a capa) dentro do álbum
        ids = [u.split("/")[-2] for u in a["urls_fotos"]]
        a["frente"] = ids.index(a["capa_id"]) if a.get("capa_id") in ids else None

    # 4. amostra de tamanho
    todas = [u for a in albuns.values() for u in a["urls_fotos"]]
    random.seed(42)
    amostra = random.sample(todas, min(AMOSTRA, len(todas)))
    with ThreadPoolExecutor(SIMULTANEAS) as ex:
        tams = [t for t in ex.map(lambda u: _seguro(tamanho, u), amostra) if t]
    conv = [c for c in map(lambda u: _seguro(otimizado, u), amostra[:AMOSTRA_WEBP]) if c]
    media = statistics.mean(tams)
    r_webp = sum(c[1] for c in conv) / sum(c[0] for c in conv)
    r_thumb = sum(c[2] for c in conv) / sum(c[0] for c in conv)

    n_fotos = len(todas)
    n_albuns_com_foto = sum(1 for a in albuns.values() if a["urls_fotos"])
    n_duas = sum(min(2, a["qtd_fotos"]) for a in albuns.values())
    total_orig = n_fotos * media
    duas_webp = n_duas * media * r_webp + n_albuns_com_foto * media * r_thumb

    SAIDA.write_text(json.dumps(list(albuns.values()), ensure_ascii=False, indent=1), "utf-8")

    linhas = [
        "# Inventário da Happy Shirt (Fase 1)", "",
        f"Gerado por `scripts/inventario.py` em {time.strftime('%d/%m/%Y %H:%M')}.", "",
        "## Totais", "",
        "| | |", "|---|---|",
        f"| categorias | {len(cats)} ({len(LIXO & set(cats))} não são produto) |",
        f"| categorias com link morto (404) | {len(inexistentes)}: {', '.join(inexistentes) or 'nenhuma'} |",
        f"| páginas da galeria | {pags} |",
        f"| álbuns únicos | {len(albuns)} |",
        f"| álbuns só em categoria, fora da galeria | {sum(1 for a in albuns.values() if a.get('fora_da_galeria'))} |",
        f"| álbuns sem foto lida | {len(albuns) - n_albuns_com_foto} |",
        f"| álbuns com a capa (frente) achada entre as fotos | {sum(1 for a in albuns.values() if a['frente'] is not None)} |",
        f"| álbuns com exatamente 2 fotos | {sum(1 for a in albuns.values() if a['qtd_fotos'] == 2)} |",
        f"| fotos | {n_fotos} |",
        f"| média por álbum | {n_fotos / max(1, n_albuns_com_foto):.1f} |",
        f"| falhas de leitura | {len(falhas)} |", "",
        "## Tamanho", "",
        f"Amostra: `HEAD` em {len(tams)} fotos aleatórias (média **{media / 1024:.0f} KB**), "
        f"e {len(conv)} delas convertidas de verdade para WebP 1200 px q80 "
        f"(**{r_webp:.0%}** do original) e miniatura 400 px (**{r_thumb:.0%}**).", "",
        "| Cenário | Tamanho |", "|---|---|",
        f"| todas as fotos, originais | {gb(total_orig)} |",
        f"| todas as fotos, WebP 1200 + miniatura | {gb(n_fotos * media * r_webp + n_albuns_com_foto * media * r_thumb)} |",
        f"| **2 fotos por peça (frente e costas), WebP 1200 + miniatura** | **{gb(duas_webp)}** ({n_duas} fotos) |", "",
        "## Álbuns por categoria", "",
        "| Categoria | id | Álbuns | Páginas |", "|---|---|---|---|",
    ]
    for cid, c in sorted(por_cat.items(), key=lambda x: -x[1]["albuns"]):
        marca = " (não é produto)" if cid in LIXO else ""
        linhas.append(f"| {c['nome']}{marca} | {cid} | {c['albuns']} | {c['paginas']} |")
    if falhas:
        linhas += ["", "## Falhas", ""] + [f"- {f['id']}: {f['erro']}" for f in falhas]
    RESUMO.write_text("\n".join(linhas) + "\n", "utf-8")
    print(f"fim: {len(albuns)} álbuns, {n_fotos} fotos, 2 por peça = {gb(duas_webp)}", flush=True)


def _seguro(f, u):
    try:
        return f(u)
    except Exception:
        return None


if __name__ == "__main__":
    main()
