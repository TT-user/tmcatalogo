# Estrutura do Yupoo da Happy Shirt (Fase 0)

Levantado em 03/10/2026 com ~15 requisições, sem baixar catálogo.
Loja: https://happyshirt.x.yupoo.com/

## Headers que funcionam

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36
Referer: https://happyshirt.x.yupoo.com/
```

As páginas HTML abrem com ou sem `Referer`. As fotos não (ver teste abaixo).

## URLs

| O quê | Padrão | Observação |
|---|---|---|
| Galeria completa | `/albums?tab=gallery&page=N` | 120 álbuns por página, **38 páginas**, a última com 79. Total **4.519 álbuns**, o mesmo número que o site exibe. |
| Categoria | `/categories/{id}?page=N` | 120 por página. Número de páginas no atributo `max="N"` do campo de pular página (também aparece como `共N页`). |
| Álbum | `/albums/{id}?uid=1` | Todas as fotos numa página só. O maior álbum testado (12 fotos) não teve paginação. |

### Categorias

A home lista **109 categorias** (`href="/categories/{id}"`). Elas **se sobrepõem**:

- Há categorias-mãe que agregam as filhas: `Collection` (5198563, 4 páginas), `Best` (5198561), `NBA` (5100375, 2 páginas, com uma categoria por time), `La Liga` (5027675, com uma por time), `FIFA 2026` (5075595, 5 páginas, com uma por seleção).
- E categorias transversais: `Player version` (4792917), `Women` (4791266, 1 página), `Kids kit` (4791583), `Retro Collection` (4785256), `Retro` (856604), `Retro Kids Kit` (5072569), `Baby Kit` (5187658).

Consequência: **o mesmo álbum aparece em várias categorias.** A fonte única do inventário deve ser a galeria (`tab=gallery`, 4.519 álbuns). As categorias servem só como **etiquetas** de cada álbum (lista de `categoria_yupoo`), coletadas percorrendo cada categoria e anotando os ids.

Categorias de futebol por região (as que mais servem à classificação):

| Seção | Categorias Yupoo |
|---|---|
| brasileiros | Brazil 4786095 (3 páginas, 342 álbuns) |
| europeus | Premier League 4786236, La Liga 5027675, Serie A 4786100, Bundesliga 4786294, Ligue 1 4786290, Liga Portugal 5151026, Scottish Premiership 5151048 |
| sul-americanos | liga argentina 4793247, Chilean League 4786087 |
| norte-americanos | MLS 4791037, Liga MX 4833172 |
| seleções | National team shirt 4790853, FIFA 2026 5075595 (+ 28 filhas por país) |
| outros futebol | Saudi League 4793263, Japan League 4791042, Other clubs 5108376 |
| retrô | Retro Collection 4785256, Retro 856604, Retro Kids Kit 5072569 |

**Fora de futebol** (decidir se entra): NBA (+ 30 times), NRL, NHL, MLB, F1, Windbreaker, Shorts, T shirts, Keychains, Fan World.
**Lixo** (não são produtos): `How to order?` 4793362, `Menu/Catalog` 4818484, `Contact` 4792364, `未分类` (sem categoria) 4785253.

## Onde estão as fotos no HTML do álbum

Dentro de `.showalbum__children`, cada foto é um `<img>` com:

| Atributo | Exemplo | Tamanho |
|---|---|---|
| `data-origin-src` | `https://photo.yupoo.com/happyshirt/1de81e5e2d/6631ecd3.jpeg` | **original, 1280 px** (o maior) |
| `data-src` | `.../1de81e5e2d/big.jpeg` | 1080 px |
| `src` | `.../medium.jpeg`, `.../small.jpeg` | miniaturas |
| `data-src` em `square.jpeg` | | recorte quadrado da capa, ignorar |

Algumas URLs começam com `//` e recebem `https:` na frente. A extensão varia (`.jpg`, `.jpeg`); `big.jpg` e `big.jpeg` respondem igual.
**Usar `data-origin-src`, com `data-src` (big) como reserva.**

A contagem de fotos de cada álbum aparece na listagem em `.album__photonumber`, o que permite somar fotos sem abrir os álbuns.

## Teste de download (3 fotos do álbum 253367253)

| Foto | Com Referer | Sem Referer |
|---|---|---|
| original 1 | 200, `image/jpg`, 291 KB, 1280×1280 | **567**, `text/html`, 7 KB |
| big 1 | 200, `image/jpeg`, 226 KB, 1080×1080 | **567**, `text/html`, 7 KB |
| original 2 | 200, 210 KB, 1280×1280 | **567**, `text/html`, 7 KB |
| big 2 | 200, 165 KB, 1080×1080 | **567**, `text/html`, 7 KB |
| original 3 | 200, 182 KB, 1280×1280 | **567**, `text/html`, 7 KB |
| big 3 | 200, 145 KB, 1080×1080 | **567**, `text/html`, 7 KB |

Sem `Referer` o servidor devolve **HTTP 567** com uma página HTML de bloqueio. O script deve tratar como falha qualquer resposta que não seja `image/*` ou que o Pillow não abra.

## Títulos

Os títulos são em inglês, sem padrão fixo, mas trazem quase sempre:

- temporada: `26/27`, `2026/27`, `2627`, `26-27`, `2026`, `87/90` (retrô dos anos 80/90 vem com dois dígitos)
- time: `Flamengo`, `PSG Paris Saint-Germain`, `Al Nassr`, `River Plate`
- modelo: `Home`, `Away`, `Third`, `GK`/`Goalkeeper`, `Training`, `Pre-match`, `Special Edition`
- versão e público: `Player`/`#Player`, `Fan`, `Women`, `Kids Kit 16-28`, `Baby 9-12`, `Retro`/`#Retro`, `Long Sleeved`
- jogador e número por hashtag: `#Ronaldo #7`, `#NaymarJr #10` (com erros de digitação)
- tamanhos: `S-4XL`, `S-XXL`, `S-3XL`, `16-28`

Exemplos: `2627 River Plate Away Long Sleeved Player S-4XL`, `26/27 Al Nassr Home #Player #Ronaldo #7`, `2025-26 NBA Dallas Mavericks 11#IRVING`.
Há títulos repetidos (o mesmo produto cadastrado duas vezes, com ids diferentes).

## Primeira estimativa de volume (a Fase 1 mede direito)

- Página 1 da galeria: 120 álbuns, 1.052 fotos, **média de 8,8 fotos por álbum**.
- 4.519 álbuns × 8,8 ≈ **40 mil fotos**.
- Originais de ~180–290 KB → **~9 GB** brutos; em WebP 1200 px, provavelmente entre **1,4 e 2,7 GB**.
