"""Acha a segunda foto do produto (a outra face da camisa) sem IA, comparando miniaturas.

A capa do álbum é uma das faces. Normalmente é a frente; quando o título traz
nome e número de jogador (#Luciano #10), a capa costuma ser a costas.
A outra face é a foto de "camisa inteira" que mais se parece com a capa:
fundo visível nas quatro bordas (closes de gola, barra e etiqueta enchem o
quadro), cobertura parecida com a da capa (a tabela de medidas é quase só
texto) e contorno parecido.

Uso como módulo: outra_face(urls, indice_capa, baixar) -> índice ou None
"""
import io

from PIL import Image, ImageFilter, ImageOps

LADO = 48


def _mascara(im):
    g = ImageOps.exif_transpose(im).convert("L").resize((LADO, LADO), Image.BILINEAR)
    g = g.filter(ImageFilter.GaussianBlur(1.5))
    px = list(g.getdata())
    idx_borda = sorted(set(list(range(LADO)) + list(range(LADO * (LADO - 1), LADO * LADO)) +
                           [i * LADO for i in range(LADO)] + [i * LADO + LADO - 1 for i in range(LADO)]))
    borda = [px[i] for i in idx_borda]
    fundo = sorted(borda)[len(borda) // 2]
    m = [1 if abs(p - fundo) > 28 else 0 for p in px]
    fundo_na_borda = 1 - sum(m[i] for i in idx_borda) / len(idx_borda)
    return m, px, fundo_na_borda


def _iou(a, b):
    inter = sum(1 for x, y in zip(a, b) if x and y)
    uniao = sum(1 for x, y in zip(a, b) if x or y)
    return inter / uniao if uniao else 0.0


def _espelho(m):
    return [m[r * LADO + (LADO - 1 - c)] for r in range(LADO) for c in range(LADO)]


def pontuar(imagens, capa):
    """Devolve [(índice, nota)] dos candidatos, melhor primeiro."""
    dados = [_mascara(im) for im in imagens]
    mc, pc, _ = dados[capa]
    cob_c = sum(mc) / len(mc)
    notas = []
    for i, (m, p, borda) in enumerate(dados):
        if i == capa:
            continue
        if sum(abs(x - y) for x, y in zip(p, pc)) / len(p) < 4:
            continue  # a mesma foto repetida
        cob = sum(m) / len(m)
        iou = max(_iou(m, mc), _iou(_espelho(m), mc))
        nota = borda + 0.5 * iou - abs(cob - cob_c)
        if cob < 0.12:
            nota -= 1  # quase vazia: tabela de medidas, texto
        notas.append((i, nota))
    return sorted(notas, key=lambda x: -x[1])


def outra_face(urls, capa, baixar):
    if capa is None or len(urls) < 2:
        return None
    if len(urls) == 2:
        return 1 - capa
    mini = [u.rsplit("/", 1)[0] + "/small.jpg" for u in urls]
    imagens = [Image.open(io.BytesIO(baixar(u))) for u in mini]
    notas = pontuar(imagens, capa)
    return notas[0][0] if notas else None
