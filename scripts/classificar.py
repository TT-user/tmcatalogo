"""Fase 2: classifica cada álbum do inventário em seção, liga, time, público, tipo,
temporada e modelo.

Uso: python scripts/classificar.py
Lê data/inventario.json e scripts/times.json.
Grava data/classificacao.json, data/classificacao-resumo.md e data/revisar.md.

Ordem de decisão: primeiro a categoria do Yupoo, depois palavras do título.
Time desconhecido ou em conflito com a categoria vai para secao "revisar".
"""
import collections, json, re, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INVENTARIO = RAIZ / "data" / "inventario.json"
TIMES = RAIZ / "scripts" / "times.json"

# categoria do Yupoo (trecho do nome) -> liga
CAT_LIGA = {
    "Brazil (巴西）": "brasileirao", "Premier League": "premier-league", "La Liga": "la-liga",
    "Serie A": "serie-a", "Bundesliga": "bundesliga", "Ligue 1": "ligue-1",
    "Liga Portugal": "liga-portugal", "Scottish": "scottish-premiership",
    "liga argentina": "argentina", "Chilean": "chile", "MLS": "mls", "Liga MX": "liga-mx",
    "Japan League": "j-league", "Saudi League": "saudi",
    "National team": "selecoes", "FIFA 2026": "selecoes",
    "NBA": "nba", "NRL": "nrl", "NHL": "nhl", "MLB": "mlb", "F1": "f1",
}
LIGA_SECAO = {
    "brasileirao": "brasileiros",
    "premier-league": "europeus", "la-liga": "europeus", "serie-a": "europeus",
    "bundesliga": "europeus", "ligue-1": "europeus", "liga-portugal": "europeus",
    "scottish-premiership": "europeus", "eredivisie": "europeus", "super-lig": "europeus",
    "outros-europa": "europeus",
    "argentina": "sul-americanos", "chile": "sul-americanos", "colombia": "sul-americanos",
    "mls": "norte-americanos", "liga-mx": "norte-americanos",
    "selecoes": "selecoes",
    "saudi": "outros", "j-league": "outros",
    "nba": "outros", "nrl": "outros", "nhl": "outros", "mlb": "outros", "f1": "outros",
}
FORA_DO_FUTEBOL = {"nba", "nrl", "nhl", "mlb", "f1"}
CAT_NAO_PRODUTO = ("How to order", "Contact", "Menu/Catalog")
NAO_PRODUTO = r"whatsapp|telegram|instagram|youtube|tiktok|about us|about shipping|feedback|q a|service center|how to order|australian sizes|^code$|^product$|^national teams$"

ACESSORIO = r"keychains?|chaveiro|socks|scarf|caps|gloves|necklace|belts|bags|underwear|patches"
AGASALHO = r"jacket|jcket|windbreaker|tracksuits?|track|hoodie|sweatshirt|coat|anthem|pants|weather|half zip|full|cny tang"
CALCAO = r"shorts?(?! sleeve)"
CAMISETA = r"t shirts?|tshirt|tee|cotton|casual|terrace icons|leisure"
RETRO = r"retro|retr0|retor|retrro|rerro|vintage|retrô"
GENERICO = r"three stripes|threestripes|originals classic|originalsclassic|originals x|cny tang|oasis"
FEMININO = r"women|womens|woman|lady|ladies|female|cropped|crop top|girl"
INFANTIL = r"kids?|children|child|baby|youth|infant|16 28|9 12|size 16"


def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode() \
        if t.isascii() else "".join(c for c in unicodedata.normalize("NFKD", t)
                                    if not unicodedata.combining(c))
    t = t.lower().replace("_", " ")
    t = re.sub(r"(\d)([a-z])|([a-z])(\d)", lambda m: " ".join(x for x in m.groups() if x), t)
    t = re.sub(r"(?<=[^\x00-\x7f])(?=\d)", " ", t)  # CJK colado em número
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


_rx = {}


def rx(padrao):
    if padrao not in _rx:
        _rx[padrao] = re.compile(rf"(?<![a-z0-9])(?:{padrao})(?![a-z0-9])")
    return _rx[padrao]


def tem(padrao, texto):
    return rx(padrao).search(texto) is not None


def temporada(titulo):
    t = titulo.replace("_", " ")
    t = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", t)
    m = re.search(r"\b(19|20)(\d{2})\s*[/-]\s*(\d{2})\b", t)
    if m:
        return f"{m.group(1)}{m.group(2)}-{m.group(3)}"
    m = re.search(r"\b(\d{2})\s*/\s*(\d{2})\b", t)
    if m:
        a = m.group(1)
        return f"{'19' if int(a) >= 50 else '20'}{a}-{m.group(2)}"
    for m in re.finditer(r"\b(\d{2})(?:\s*-\s*|\s+)?(\d{2})\b", t):
        a, b = int(m.group(1)), int(m.group(2))
        if b - a in (1, 2) or (a == 99 and b == 0):
            return f"{'19' if a >= 50 else '20'}{m.group(1)}-{m.group(2)}"
    m = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", t)
    return m.group(1) if m else None


def modelo(n):
    if tem(r"goalkeeper|goalkeep|gk|keeper", n):
        return "goleiro"
    if tem(r"training|train|traning|pre match|pre game|pre race|warm up", n):
        return "treino"
    if tem(r"third|tercera|iii|3rd", n):
        return "third"
    if tem(r"fourth|4th|fifth", n):
        return "fourth"
    if tem(r"away|guest|second|ii", n):
        return "away"
    if tem(r"home|main|i", n):
        return "home"
    if tem(r"special|edition|anniversary|commemorative|concept|limited|centennial|centenary|signature|\d+th", n):
        return "especial"
    return None


def main():
    albuns = json.loads(INVENTARIO.read_text("utf-8"))
    times = {k: v for k, v in json.loads(TIMES.read_text("utf-8")).items() if not k.startswith("_")}
    apelidos = [(rx(re.escape(norm(a)).replace(r"\ ", r"\s+")), len(norm(a)), slug)
                for slug, t in times.items() for a in t["apelidos"] if norm(a)]

    saida, revisar = [], []
    for a in albuns:
        titulo, cats = a["titulo"], a["categoria_yupoo"]
        n = norm(re.sub(r"#[^\s，,]+", " ", titulo))  # hashtags: código, jogador, número
        nh = norm(titulo)  # com as hashtags (#Player, #Retro)
        ncat = norm(" ".join(cats))
        ligas_cat = {liga for trecho, liga in CAT_LIGA.items() if any(trecho in c for c in cats)}

        r = {"id": a["id"], "titulo": titulo, "secao": None, "liga": None, "time": None,
             "time_nome": None, "pais": None, "publico": "masculino", "tipo": "torcedor",
             "temporada": temporada(titulo), "modelo": modelo(n)}

        # não é produto
        if any(c.startswith(p) or p in c for c in cats for p in CAT_NAO_PRODUTO) or tem(NAO_PRODUTO, n) or not n:
            r["secao"] = "nao-produto"
            saida.append(r)
            continue

        # time: candidatos por apelido; a categoria desempata; depois o mais longo
        cands = {}
        for padrao, tam, slug in apelidos:
            if padrao.search(n):
                cands[slug] = max(cands.get(slug, 0), tam)
        if cands:
            na_cat = {s: l for s, l in cands.items() if times[s]["liga"] in ligas_cat
                      or ("brasileirao" in ligas_cat and times[s]["liga"] == "selecoes" and s == "brasil")}
            escolha = max(na_cat or cands, key=lambda s: (na_cat.get(s, cands[s]), -len(s)))
            t = times[escolha]
            r.update(time=escolha, time_nome=t["nome"], pais=t["pais"], liga=t["liga"])

        # público
        if tem(FEMININO, n) or "Women" in ncat.title() or "women" in ncat:
            r["publico"] = "feminino"
        elif tem(INFANTIL, n) or tem(r"kids|baby", ncat):
            r["publico"] = "infantil"

        # tipo
        if tem(ACESSORIO, n) or tem(r"keychains|fan world", ncat):
            r["tipo"] = "acessorio"
        elif tem(AGASALHO, n) or tem(r"windbreaker", ncat):
            r["tipo"] = "agasalho"
        elif tem(CALCAO, n) or tem(r"shorts", ncat):
            r["tipo"] = "calcao"
        elif tem(CAMISETA, n) or tem(r"t shirts", ncat):
            r["tipo"] = "camiseta"
        elif r["publico"] == "infantil":
            r["tipo"] = "kit-infantil"
        elif tem(RETRO, nh) or tem(r"retro", ncat):
            r["tipo"] = "retro"
        elif r["modelo"] == "treino":
            r["tipo"] = "treino"
        elif tem(r"player|players", nh):
            r["tipo"] = "jogador"
        elif r["liga"] in FORA_DO_FUTEBOL or ligas_cat & FORA_DO_FUTEBOL:
            r["tipo"] = "camisa"
        e_retro = tem(RETRO, nh) or tem(r"retro", ncat)

        # seção
        motivo = None
        if not r["time"]:
            if r["tipo"] == "acessorio" or tem(GENERICO, n) or (r["tipo"] in ("agasalho", "camiseta") and not ligas_cat - FORA_DO_FUTEBOL):
                r["secao"] = "outros"
            elif ligas_cat & FORA_DO_FUTEBOL:
                liga = next(iter(ligas_cat & FORA_DO_FUTEBOL))
                r.update(secao="outros", liga=liga)
            else:
                motivo = "time não reconhecido"
        else:
            # categoria e título discordam: o título vence (a categoria do Yupoo é mal cadastrada)
            if ligas_cat and r["liga"] not in ligas_cat and not (r["time"] == "brasil" and "brasileirao" in ligas_cat):
                r["obs"] = f"categoria Yupoo diz {'/'.join(sorted(ligas_cat))}; ficou o time do título"
            if e_retro and r["liga"] not in FORA_DO_FUTEBOL:
                r["secao"] = "retro"
            else:
                r["secao"] = LIGA_SECAO.get(r["liga"], "outros")
        if motivo:
            r["secao"] = "revisar"
            r["motivo"] = motivo
            revisar.append(r)
        saida.append(r)

    (RAIZ / "data" / "classificacao.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), "utf-8")

    # resumo
    sec = collections.Counter(r["secao"] for r in saida)
    lig = collections.Counter((r["secao"], r["liga"]) for r in saida)
    pub = collections.Counter(r["publico"] for r in saida if r["secao"] != "nao-produto")
    tip = collections.Counter(r["tipo"] for r in saida if r["secao"] != "nao-produto")
    sem_temp = sum(1 for r in saida if r["secao"] not in ("nao-produto",) and not r["temporada"])
    L = ["# Classificação (Fase 2)", "", f"{len(saida)} álbuns.", "", "## Por seção", "",
         "| Seção | Álbuns |", "|---|---|"]
    L += [f"| {s} | {c} |" for s, c in sec.most_common()]
    L += ["", "## Por seção e liga", "", "| Seção | Liga | Álbuns |", "|---|---|---|"]
    L += [f"| {s} | {l or '—'} | {c} |" for (s, l), c in sorted(lig.items(), key=lambda x: (x[0][0] or "", -x[1]))]
    L += ["", "## Público", "", "| Público | Álbuns |", "|---|---|"] + [f"| {p} | {c} |" for p, c in pub.most_common()]
    L += ["", "## Tipo", "", "| Tipo | Álbuns |", "|---|---|"] + [f"| {p} | {c} |" for p, c in tip.most_common()]
    L += ["", f"Produtos sem temporada no título: {sem_temp}."]
    (RAIZ / "data" / "classificacao-resumo.md").write_text("\n".join(L) + "\n", "utf-8")

    R = ["# Para revisar", "",
         "Álbuns que o script não classificou com segurança. Para corrigir: acrescente o time ",
         "(ou o apelido) em `scripts/times.json` e rode `python scripts/classificar.py` de novo.", "",
         f"Total: {len(revisar)}", ""]
    por_motivo = collections.defaultdict(list)
    for r in revisar:
        por_motivo[r["motivo"].split(",")[0]].append(r)
    for m, rs in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
        R += [f"## {m} ({len(rs)})", ""]
        R += [f"- [{r['titulo']}](https://happyshirt.x.yupoo.com/albums/{r['id']}?uid=1)"
              + (f" · {r['motivo']}" if "," in r["motivo"] else "") for r in rs]
        R.append("")
    conf = [r for r in saida if r.get("obs")]
    R += [f"## Categoria e título discordavam: ficou o título ({len(conf)}), para conferir", ""]
    R += [f"- [{r['titulo']}](https://happyshirt.x.yupoo.com/albums/{r['id']}?uid=1) → {r['time_nome']} · {r['obs']}" for r in conf]
    R.append("")
    nao = [r for r in saida if r["secao"] == "nao-produto"]
    R += [f"## Marcados como não-produto ({len(nao)}), para conferir", ""]
    R += [f"- [{r['titulo']}](https://happyshirt.x.yupoo.com/albums/{r['id']}?uid=1)" for r in nao]
    (RAIZ / "data" / "revisar.md").write_text("\n".join(R) + "\n", "utf-8")

    print(dict(sec.most_common()))


if __name__ == "__main__":
    main()
