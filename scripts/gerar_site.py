"""Fase 4: monta o site em _site/ a partir de site/, data/catalogo.json e data/loja.json.

Uso: python scripts/gerar_site.py [--sem-imagens]

- produtos.json: catálogo enxuto que o app.js lê, já com preço e pronta entrega.
- p/<id>.html: uma página por produto com og:image e og:title, para o WhatsApp
  mostrar a foto quando o link vai na mensagem do pedido. Redireciona para o app.
- imagens/: copiadas (o Pages publica só o que está em _site/).
"""
import html, json, re, shutil, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "_site"


def main():
    arq = RAIZ / "data" / "catalogo.json"
    catalogo = json.loads(arq.read_text("utf-8")) if arq.exists() else []  # antes do 1º download
    loja = json.loads((RAIZ / "data" / "loja.json").read_text("utf-8"))
    config = (RAIZ / "site" / "config.js").read_text("utf-8")
    site_url = re.search(r'SITE_URL:\s*"([^"]+)"', config).group(1).rstrip("/") + "/"

    por_tipo = loja.get("precos_por_tipo", {})
    precos = loja.get("precos", {})
    pronta = loja.get("pronta_entrega", {})

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    shutil.copytree(RAIZ / "site", SAIDA)
    (SAIDA / ".nojekyll").write_text("")
    (SAIDA / "p").mkdir()

    enxuto = []
    for c in catalogo:
        pr = precos.get(c["id"], por_tipo.get(c["tipo"]))
        pe = pronta.get(c["id"])
        enxuto.append({
            "id": c["id"], "t": c["titulo"], "s": c["secao"], "l": c["liga"],
            "tm": c["time"], "tn": c["time_nome"], "pu": c["publico"], "ti": c["tipo"],
            "te": c["temporada"], "im": c["imagens"], "th": c["thumb"],
            "pr": pr, "tz": c["tamanhos"],
            "pe": (pe if pe else True) if pe is not None else False,
        })
        titulo = html.escape(c["titulo"])
        preco = f"R$ {pr:.2f}".replace(".", ",") if pr is not None else "Preço sob consulta"
        destino = f"../#/p/{c['id']}"
        (SAIDA / "p" / f"{c['id']}.html").write_text(f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{titulo} · TM Sports</title>
<meta property="og:type" content="product">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{preco} · TM Sports">
<meta property="og:image" content="{site_url}{c['imagens'][0]}">
<meta property="og:url" content="{site_url}p/{c['id']}.html">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={destino}">
</head><body><a href="{destino}">{titulo}</a></body></html>
""", "utf-8")

    # ordem da vitrine: brasileiros e seleções primeiro, depois o resto
    ordem = ["brasileiros", "selecoes", "europeus", "retro", "sul-americanos", "norte-americanos", "outros"]
    enxuto.sort(key=lambda p: p["te"] or "", reverse=True)  # temporada mais nova primeiro
    enxuto.sort(key=lambda p: (ordem.index(p["s"]) if p["s"] in ordem else 99, p["tn"] or "~"))
    (SAIDA / "produtos.json").write_text(json.dumps(enxuto, ensure_ascii=False, separators=(",", ":")), "utf-8")

    if "--sem-imagens" not in sys.argv and (RAIZ / "imagens").exists():
        shutil.copytree(RAIZ / "imagens", SAIDA / "imagens")

    tam = sum(f.stat().st_size for f in SAIDA.rglob("*") if f.is_file())
    print(f"site: {len(enxuto)} produtos, {tam / 1024**2:.0f} MB em {SAIDA}")
    if tam > 950 * 1024 ** 2:
        sys.exit("site passou de 950 MB: perto do limite de 1 GB do GitHub Pages")


if __name__ == "__main__":
    main()
