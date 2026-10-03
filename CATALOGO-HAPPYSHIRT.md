# Projeto: Catálogo de Camisas (fonte: Happy Shirt / Yupoo)

> Arquivo de instruções para o Claude Code. Leia tudo antes de começar.
> Execute por fases e **pare ao fim de cada fase** para eu (Matheus) aprovar.

## Objetivo

1. Mapear **todos** os álbuns do catálogo `https://happyshirt.x.yupoo.com/` (times brasileiros, europeus, sul-americanos, norte-americanos, seleções, retrô, feminino, infantil etc.).
2. Baixar as fotos de cada álbum **sem passar pela minha máquina**: o download roda no GitHub Actions e as imagens vão direto para um repositório GitHub.
3. Organizar as imagens em pastas por seção/liga/time e gerar um `catalogo.json` que depois alimenta o site catálogo.
4. (Fase posterior) Construir o site catálogo com carrinho, personalização e envio do pedido pelo WhatsApp.

---

## Regras gerais para o Claude Code

- **Nada de download local em massa.** Localmente você só escreve código e testa com 1–2 álbuns. O download completo roda no GitHub Actions.
- **Seja educado com o servidor:** no máximo 2 requisições simultâneas, pausa de 0,5–1 s entre requisições, retry com backoff (3 tentativas) em erro 429/5xx.
- **Hotlink do Yupoo:** as imagens (`photo.yupoo.com/...`) costumam exigir o header `Referer: https://happyshirt.x.yupoo.com/` e um `User-Agent` de navegador. Sem isso voltam 403 ou uma imagem de bloqueio. Teste isso primeiro.
- **Retomável:** mantenha um `state/progress.json` com os álbuns já concluídos. Se o job cair, ele continua de onde parou.
- **Nunca** coloque tokens ou senhas em arquivos do repositório. Use os Secrets do GitHub quando precisar.
- Ao fim de cada fase, me mostre um resumo curto e espere meu OK.

---

## Pré-requisitos (eu faço)

1. Criar o repositório no GitHub: `camisas-catalogo` (pode ser **privado** enquanto organiza; para o site em GitHub Pages grátis ele precisa ser público, ou usamos Vercel/Netlify/Cloudflare Pages com repo privado).
2. Abrir o Claude Code dentro do repositório clonado (ou no Claude Code na web conectado ao repo).
3. Colocar este arquivo na raiz do repo como `CATALOGO-HAPPYSHIRT.md` e mandar: **"Leia o CATALOGO-HAPPYSHIRT.md e execute a Fase 0."**

---

## Fase 0 — Reconhecimento da estrutura (só leitura, poucas requisições)

1. Baixe o HTML da página inicial e de 1 página de categoria e 1 página de álbum.
2. Descubra e documente em `docs/estrutura-yupoo.md`:
   - URL das categorias (padrão comum: `/categories/{id}`) e se há subcategorias.
   - Listagem de álbuns e paginação (padrão comum: `/albums?tab=gallery&page=N` e `/categories/{id}?page=N`).
   - URL do álbum (padrão comum: `/albums/{id}?uid=1`).
   - Onde ficam as URLs das fotos no HTML (geralmente atributos `data-origin-src` / `data-src`, com variações `big`, `medium`, `small`, `square`). Escolha a **maior** disponível.
   - Se o título do álbum traz time/temporada/tipo (ex.: "2026/27 Flamengo Home Fan", "Women", "Kids", "Retro", "Player version").
3. Teste o download de 3 imagens com e sem `Referer` e registre o resultado.
4. **Pare e me mostre** o que encontrou.

---

## Fase 1 — Inventário + estimativa de tamanho (sem baixar imagens)

Crie `scripts/inventario.py` (Python 3, `requests` + `beautifulsoup4`) que:

1. Percorre **todas** as categorias e **todas** as páginas de álbuns. Deduplique álbuns que aparecem em mais de uma categoria.
2. Para cada álbum, salva: `id`, `titulo`, `url`, `categoria_yupoo`, `qtd_fotos`, `urls_fotos[]`.
3. Para estimar o tamanho, faz `HEAD` (ou GET com `Range: bytes=0-0`) numa **amostra** de 300 fotos aleatórias, lê o `Content-Length` e calcula:
   - tamanho médio por foto
   - **total estimado em GB = total de fotos × média**
   - total estimado **depois da otimização** (ver Fase 3: WebP 1200 px costuma ficar entre 15% e 30% do original)
4. Grava tudo em `data/inventario.json` e um resumo em `data/inventario-resumo.md` com:
   - nº de categorias, nº de álbuns, nº de fotos
   - GB estimados (original e otimizado)
   - contagem por categoria
5. Este script pode rodar localmente (é só HTML, poucos MB) **ou** como workflow do Actions (`inventario.yml`, com `workflow_dispatch`) que comita os JSONs.
6. **Pare e me mostre o resumo**, principalmente o total de GB.

### Decisão de armazenamento (com base no total otimizado)

| Total otimizado | Onde guardar as imagens |
|---|---|
| Até ~1 GB | No próprio repositório GitHub, servido pelo GitHub Pages / Vercel. |
| 1 GB a ~5 GB | Repositório GitHub ainda funciona, mas com push em lotes por pasta. Site hospedado em Cloudflare Pages ou Vercel. |
| Acima de ~5 GB | Imagens no **Cloudflare R2** (10 GB grátis, sem custo de saída). O repositório guarda só o código e o `catalogo.json` com as URLs. |

Limites do GitHub a respeitar: arquivo individual < 100 MB, cada push < 2 GB, repo idealmente < 5 GB, GitHub Pages < 1 GB por site.

---

## Fase 2 — Classificação em seções

Crie `scripts/classificar.py` que lê `data/inventario.json` e atribui a cada álbum:

- `secao` (uma): `brasileiros`, `europeus`, `sul-americanos`, `norte-americanos`, `selecoes`, `retro`, `outros`
- `liga` (quando der): `brasileirao`, `premier-league`, `la-liga`, `serie-a`, `bundesliga`, `ligue-1`, `liga-portugal`, `argentina`, `mls`, `liga-mx`, etc.
- `time` (slug, ex.: `flamengo`, `real-madrid`)
- `publico`: `masculino`, `feminino`, `infantil` (kits infantis)
- `tipo`: `torcedor`, `jogador`, `retro`, `treino`, `agasalho`, `kit-infantil`
- `temporada` (ex.: `2026-27`) e `modelo` (`home`, `away`, `third`, `goleiro`…)

Regras:
- Use primeiro a categoria do Yupoo; depois palavras-chave do título (Women/Lady → feminino; Kids/Children → infantil; Player → jogador; Retro → retro).
- Mantenha um dicionário `scripts/times.json` (time → país → liga) e amplie quando aparecer time desconhecido.
- O que não for classificado com segurança vai para `secao: "revisar"` e entra numa lista `data/revisar.md` para eu conferir.
- **Pare e me mostre** a contagem por seção/liga e a lista de "revisar".

---

## Fase 3 — Download + otimização no GitHub Actions

Crie `scripts/baixar.py` e o workflow `.github/workflows/baixar.yml`.

### O script
- Recebe a `secao` (ou `liga`) como parâmetro e processa só os álbuns dela — **pasta por pasta**.
- Para cada foto: baixa (com `Referer`), converte para **WebP**, largura máx. **1200 px**, qualidade ~80, e gera também uma miniatura de **400 px** para a grade do site. (Use `Pillow`.)
- Remove metadados (EXIF).
- Nome dos arquivos: `01.webp`, `02.webp`… e `thumb.webp` (primeira foto, 400 px).
- Atualiza `state/progress.json` a cada álbum concluído.

### Estrutura de pastas
```
imagens/
  brasileiros/
    brasileirao/
      flamengo/
        2026-27-home-torcedor-masculino/
          01.webp
          02.webp
          thumb.webp
  europeus/
    premier-league/
      arsenal/...
  feminino/   ← NÃO usar como pasta raiz; feminino/infantil ficam como campo no JSON
```
(O público feminino/infantil é filtro no site, não pasta, para evitar duplicação.)

### O workflow
- Gatilho `workflow_dispatch` com input `secao`.
- Passos: checkout → setup Python → `pip install requests beautifulsoup4 pillow` → `python scripts/baixar.py --secao X` → commit e push **a cada ~300 MB** ou ao fim de cada liga (para não estourar o limite de push).
- `timeout-minutes: 350`. Se não terminar, a próxima execução continua pelo `progress.json`.
- Se a decisão da Fase 1 foi **Cloudflare R2**: em vez de commitar as imagens, envie para o bucket com `boto3` usando os secrets `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, e comite só o `catalogo.json`. (Eu crio o bucket e os secrets; me passe o passo a passo nessa hora.)

### Ordem de execução
1. Rode primeiro com `secao=brasileiros` e **pare** para eu conferir as fotos.
2. Depois rode as outras seções uma por vez.

### Saída final
`data/catalogo.json`, uma entrada por produto:
```json
{
  "id": "flamengo-2026-27-home-torcedor-m",
  "titulo": "Flamengo 2026/27 Home – Torcedor",
  "secao": "brasileiros",
  "liga": "brasileirao",
  "time": "flamengo",
  "publico": "masculino",
  "tipo": "torcedor",
  "temporada": "2026-27",
  "imagens": ["imagens/brasileiros/brasileirao/flamengo/2026-27-home-torcedor-masculino/01.webp"],
  "thumb": "imagens/.../thumb.webp",
  "preco": null,
  "tamanhos": ["P", "M", "G", "GG", "2GG"]
}
```
`preco` fica `null`: eu vou passar a tabela de preços depois (por tipo: torcedor, jogador, retrô, feminino, kit infantil).

---

## Fase 4 — Site catálogo (só depois que as imagens estiverem prontas)

Stack sugerida: site estático (HTML/CSS/JS ou Astro), lendo o `catalogo.json`. Hospedagem: Vercel ou Cloudflare Pages.

### Navegação
- Menu por seção: Brasileiros, Europeus (com sub-filtro por liga), Sul-Americanos, Norte-Americanos, Seleções, Retrô.
- Filtros: Masculino / Feminino / Kits Infantis, tipo (torcedor/jogador), time (busca por nome).
- Grade com miniatura, nome e preço; página do produto com galeria.
- Imagens com `loading="lazy"`.

### Personalização (no produto)
- Tamanho (obrigatório) e quantidade.
- **Nome**: +R$ 20,00
- **Número**: +R$ 20,00
- **Patch**: +R$ 10,00 por patch (o cliente pode escolher mais de um)
- O preço do item atualiza na hora.

### Carrinho e pedido
- Carrinho guardado em memória/`localStorage`, com várias camisas.
- Botão "Enviar pedido pelo WhatsApp" abre `https://wa.me/55DDDNUMERO?text=...` com a mensagem pronta, por exemplo:

```
Olá! Quero fazer este pedido:

1) Flamengo 2026/27 Home – Torcedor
   Tamanho: G | Qtd: 1
   Nome: MATHEUS (+R$20) | Número: 10 (+R$20)
   Patches: Brasileirão (+R$10)
   Subtotal: R$ XXX
   Foto: https://meusite.com/p/flamengo-2026-27-home-torcedor-m

TOTAL: R$ XXX
Nome do cliente: ____  Cidade: ____
```

- **Limitação do WhatsApp:** o link `wa.me` só envia **texto**, não anexa imagem. A solução é colocar o **link da página/foto de cada produto** na mensagem — o WhatsApp mostra a prévia da imagem a partir do link. Para isso, cada página de produto precisa das tags `og:image` e `og:title`.
- O número de WhatsApp fica numa variável de configuração (`config.js`).

---

## Checklist de entrega

- [ ] Fase 0 — estrutura documentada
- [ ] Fase 1 — inventário + total de GB → decisão de armazenamento
- [ ] Fase 2 — classificação revisada
- [ ] Fase 3 — imagens no repositório/R2 + `catalogo.json`
- [ ] Preços preenchidos (eu informo)
- [ ] Fase 4 — site no ar com carrinho e WhatsApp
