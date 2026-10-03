(() => {
  "use strict";
  const C = window.TM_CONFIG;
  const $ = (s) => document.querySelector(s);
  const POR_PAGINA = 48;

  const SECOES = [
    ["", "Todas"], ["brasileiros", "Brasileiros"], ["europeus", "Europeus"],
    ["selecoes", "Seleções"], ["retro", "Retrô"], ["sul-americanos", "Sul-Americanos"],
    ["norte-americanos", "Norte-Americanos"], ["outros", "Outros esportes"],
  ];
  const LIGAS = {
    "brasileirao": "Brasileirão", "premier-league": "Premier League", "la-liga": "La Liga",
    "serie-a": "Serie A", "bundesliga": "Bundesliga", "ligue-1": "Ligue 1",
    "liga-portugal": "Liga Portugal", "scottish-premiership": "Escócia", "eredivisie": "Holanda",
    "super-lig": "Turquia", "outros-europa": "Outros da Europa", "argentina": "Argentina",
    "chile": "Chile", "colombia": "Colômbia", "mls": "MLS", "liga-mx": "Liga MX",
    "selecoes": "Seleções", "saudi": "Arábia Saudita", "j-league": "Japão", "nba": "NBA",
    "nrl": "Rugby (NRL)", "nhl": "Hóquei (NHL)", "mlb": "Beisebol (MLB)", "f1": "Fórmula 1",
  };
  const TIPOS = {
    "torcedor": "Torcedor", "jogador": "Jogador", "retro": "Retrô", "treino": "Treino",
    "kit-infantil": "Kit infantil", "agasalho": "Agasalho / jaqueta", "calcao": "Calção",
    "camiseta": "Camiseta", "camisa": "Camisa (outros esportes)", "acessorio": "Acessório",
  };
  const PUBLICOS = [["", "Todos"], ["masculino", "Masculino"], ["feminino", "Feminino"], ["infantil", "Infantil"]];

  const brl = (v) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const semAcento = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  // ---------- estado ----------
  let produtos = [];
  let porId = new Map();
  const filtro = { secao: "", liga: "", time: "", tipo: "", publico: "", pronta: false, busca: "" };
  let visiveis = [];
  let mostrados = 0;

  const guardar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const ler = (k, padrao) => { try { return JSON.parse(localStorage.getItem(k)) ?? padrao; } catch (e) { return padrao; } };
  let carrinho = ler("tm-carrinho", []);

  // ---------- vitrine ----------
  function aplicarFiltros() {
    const termos = semAcento(filtro.busca).split(/\s+/).filter(Boolean);
    visiveis = produtos.filter((p) =>
      (!filtro.secao || p.s === filtro.secao) &&
      (!filtro.liga || p.l === filtro.liga) &&
      (!filtro.time || p.tm === filtro.time) &&
      (!filtro.tipo || p.ti === filtro.tipo) &&
      (!filtro.publico || p.pu === filtro.publico) &&
      (!filtro.pronta || p.pe) &&
      termos.every((t) => p._busca.includes(t))
    );
    // pronta entrega primeiro
    visiveis.sort((a, b) => (b.pe ? 1 : 0) - (a.pe ? 1 : 0));
    mostrados = 0;
    $("#grade").innerHTML = "";
    renderMais();
    $("#contagem").textContent = `${visiveis.length.toLocaleString("pt-BR")} ${visiveis.length === 1 ? "produto" : "produtos"}`;
  }

  function card(p) {
    const preco = p.pr != null
      ? `<span class="card__preco">${brl(p.pr)}</span>`
      : `<span class="card__preco card__preco--consulta">Preço sob consulta</span>`;
    return `<a class="card" href="#/p/${p.id}">
      ${p.pe ? '<span class="selo">Pronta entrega</span>' : ""}
      <span class="card__foto"><img src="${esc(p.th)}" alt="${esc(p.t)}" loading="lazy" width="400" height="400"></span>
      <span class="card__corpo"><span class="card__titulo">${esc(p.t)}</span>${preco}</span>
    </a>`;
  }

  function renderMais() {
    const lote = visiveis.slice(mostrados, mostrados + POR_PAGINA);
    if (!mostrados && !lote.length) {
      $("#grade").innerHTML = '<p class="vazio-grade">Nenhuma camisa com esses filtros.</p>';
    } else {
      $("#grade").insertAdjacentHTML("beforeend", lote.map(card).join(""));
    }
    mostrados += lote.length;
    $("#carregar-mais").hidden = mostrados >= visiveis.length;
  }

  function opcoes(sel, pares, valor) {
    sel.innerHTML = pares.map(([v, r]) => `<option value="${esc(v)}"${v === valor ? " selected" : ""}>${esc(r)}</option>`).join("");
  }

  function atualizarSelects() {
    const daSecao = produtos.filter((p) => !filtro.secao || p.s === filtro.secao);
    const ligas = [...new Set(daSecao.map((p) => p.l).filter(Boolean))]
      .sort((a, b) => (LIGAS[a] || a).localeCompare(LIGAS[b] || b, "pt-BR"));
    if (filtro.liga && !ligas.includes(filtro.liga)) filtro.liga = "";
    opcoes($("#f-liga"), [["", "Todas as ligas"], ...ligas.map((l) => [l, LIGAS[l] || l])], filtro.liga);
    $("#f-liga").closest(".campo").hidden = ligas.length < 2;

    const daLiga = daSecao.filter((p) => !filtro.liga || p.l === filtro.liga);
    const times = new Map();
    daLiga.forEach((p) => p.tm && times.set(p.tm, p.tn));
    if (filtro.time && !times.has(filtro.time)) filtro.time = "";
    opcoes($("#f-time"), [["", "Todos os times"], ...[...times].sort((a, b) => a[1].localeCompare(b[1], "pt-BR"))], filtro.time);

    const tipos = [...new Set(daLiga.map((p) => p.ti))];
    if (filtro.tipo && !tipos.includes(filtro.tipo)) filtro.tipo = "";
    opcoes($("#f-tipo"), [["", "Todos os tipos"], ...Object.keys(TIPOS).filter((t) => tipos.includes(t)).map((t) => [t, TIPOS[t]])], filtro.tipo);
  }

  function montarControles() {
    $("#secoes").innerHTML = SECOES.map(([v, r]) =>
      `<button type="button" data-secao="${v}" aria-pressed="${v === filtro.secao}">${r}</button>`).join("");
    $("#secoes").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-secao]");
      if (!b) return;
      filtro.secao = b.dataset.secao;
      filtro.liga = filtro.time = "";
      $("#secoes").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      atualizarSelects(); aplicarFiltros();
      if (location.hash.startsWith("#/p/")) location.hash = "#/";
    });

    $("#f-publico").innerHTML = PUBLICOS.map(([v, r]) =>
      `<button type="button" data-publico="${v}" aria-pressed="${v === filtro.publico}">${r}</button>`).join("");
    $("#f-publico").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-publico]");
      if (!b) return;
      filtro.publico = b.dataset.publico;
      $("#f-publico").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      aplicarFiltros();
    });

    $("#f-liga").addEventListener("change", (e) => { filtro.liga = e.target.value; filtro.time = ""; atualizarSelects(); aplicarFiltros(); });
    $("#f-time").addEventListener("change", (e) => { filtro.time = e.target.value; aplicarFiltros(); });
    $("#f-tipo").addEventListener("change", (e) => { filtro.tipo = e.target.value; aplicarFiltros(); });
    $("#f-pronta").addEventListener("change", (e) => { filtro.pronta = e.target.checked; aplicarFiltros(); });
    let t;
    $("#busca").addEventListener("input", (e) => {
      clearTimeout(t);
      t = setTimeout(() => { filtro.busca = e.target.value; aplicarFiltros(); }, 180);
    });
    $("#carregar-mais").addEventListener("click", renderMais);
    // carrega mais ao chegar perto do fim
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((es) => { if (es[0].isIntersecting && mostrados < visiveis.length) renderMais(); },
        { rootMargin: "600px" }).observe($("#carregar-mais"));
    }
  }

  // ---------- produto ----------
  let atual = null;
  const escolha = { tamanho: "", qtd: 1 };

  function tamanhosDe(p) {
    return p.tz || (p.pu === "infantil" ? C.TAMANHOS_INFANTIL_PADRAO : C.TAMANHOS_PADRAO);
  }

  function precoUnit(p, pers) {
    if (p.pr == null) return null;
    return p.pr + extras(pers);
  }
  function extras(pers) {
    return (pers.nome ? C.PRECO_NOME : 0) + (pers.numero ? C.PRECO_NUMERO : 0) + pers.patches.length * C.PRECO_PATCH;
  }

  function personalizacao() {
    return {
      nome: $("#p-nome-on").checked ? $("#p-nome").value.trim().toUpperCase() : "",
      numero: $("#p-numero-on").checked ? $("#p-numero").value.trim() : "",
      patches: [...document.querySelectorAll("#p-patches input:checked")].map((i) => i.value),
    };
  }

  function atualizarTotal() {
    const pers = personalizacao();
    const ex = extras(pers);
    const u = precoUnit(atual, pers);
    $("#p-total").textContent = u != null
      ? `Total: ${brl(u * escolha.qtd)}${escolha.qtd > 1 ? ` (${escolha.qtd} × ${brl(u)})` : ""}`
      : ex ? `Personalização: + ${brl(ex * escolha.qtd)} · valor da camisa sob consulta` : "";
  }

  function abrirProduto(id) {
    const p = porId.get(id);
    if (!p) { location.hash = "#/"; return; }
    atual = p;
    escolha.tamanho = ""; escolha.qtd = 1;
    $("#p-titulo").textContent = p.t;
    $("#p-selo").textContent = p.pe ? "Pronta entrega" : "";
    $("#p-preco").textContent = p.pr != null ? brl(p.pr) : "Preço sob consulta";
    const fotos = p.im;
    $("#p-foto").src = fotos[0]; $("#p-foto").alt = `${p.t}, frente`;
    $("#p-miniaturas").innerHTML = fotos.map((f, i) =>
      `<button type="button" data-foto="${i}" aria-pressed="${i === 0}"><img src="${esc(f)}" alt=""><span>${i === 0 ? "Frente" : "Costas"}</span></button>`).join("");
    const emEstoque = Array.isArray(p.pe) ? p.pe : [];
    $("#p-tamanhos").innerHTML = tamanhosDe(p).map((t) =>
      `<button type="button" data-tam="${esc(t)}" aria-pressed="false">${esc(t)}${emEstoque.includes(t) ? '<span class="ok">pronta</span>' : ""}</button>`).join("");
    $("#p-preco-nome").textContent = `+ ${brl(C.PRECO_NOME)}`;
    $("#p-preco-numero").textContent = `+ ${brl(C.PRECO_NUMERO)}`;
    $("#p-preco-patch").textContent = `+ ${brl(C.PRECO_PATCH)} cada`;
    $("#p-patches").innerHTML = C.PATCHES.map((n) => `<label><input type="checkbox" value="${esc(n)}"> ${esc(n)}</label>`).join("");
    ["#p-nome-on", "#p-numero-on"].forEach((s) => ($(s).checked = false));
    ["#p-nome", "#p-numero"].forEach((s) => { $(s).value = ""; $(s).hidden = true; });
    $("#p-qtd").textContent = "1";
    $("#p-aviso").textContent = "";
    atualizarTotal();
    abrir("#produto");
    document.title = `${p.t} · TM Sports`;
  }

  function montarProduto() {
    $("#p-miniaturas").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-foto]");
      if (!b) return;
      const i = +b.dataset.foto;
      $("#p-foto").src = atual.im[i];
      $("#p-foto").alt = `${atual.t}, ${i === 0 ? "frente" : "costas"}`;
      $("#p-miniaturas").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    });
    $("#p-tamanhos").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-tam]");
      if (!b) return;
      escolha.tamanho = b.dataset.tam;
      $("#p-tamanhos").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      $("#p-aviso").textContent = "";
    });
    [["#p-nome-on", "#p-nome"], ["#p-numero-on", "#p-numero"]].forEach(([c, i]) => {
      $(c).addEventListener("change", () => { $(i).hidden = !$(c).checked; if ($(c).checked) $(i).focus(); atualizarTotal(); });
    });
    $("#p-numero").addEventListener("input", (e) => { e.target.value = e.target.value.replace(/\D/g, "").slice(0, 2); });
    $("#p-patches").addEventListener("change", atualizarTotal);
    $("#p-menos").addEventListener("click", () => { escolha.qtd = Math.max(1, escolha.qtd - 1); $("#p-qtd").textContent = escolha.qtd; atualizarTotal(); });
    $("#p-mais").addEventListener("click", () => { escolha.qtd = Math.min(20, escolha.qtd + 1); $("#p-qtd").textContent = escolha.qtd; atualizarTotal(); });
    $("#p-adicionar").addEventListener("click", () => {
      const pers = personalizacao();
      if (!escolha.tamanho) { $("#p-aviso").textContent = "Escolha o tamanho."; return; }
      if ($("#p-nome-on").checked && !pers.nome) { $("#p-aviso").textContent = "Digite o nome ou desmarque a opção."; return; }
      if ($("#p-numero-on").checked && !pers.numero) { $("#p-aviso").textContent = "Digite o número ou desmarque a opção."; return; }
      carrinho.push({ id: atual.id, tamanho: escolha.tamanho, qtd: escolha.qtd, ...pers });
      guardar("tm-carrinho", carrinho);
      atualizarContador();
      location.hash = "#/";
      abrirCarrinho();
    });
  }

  // ---------- carrinho ----------
  function atualizarContador() {
    $("#qtd-carrinho").textContent = carrinho.reduce((s, i) => s + i.qtd, 0);
  }

  function linhaItem(it, i) {
    const p = porId.get(it.id);
    if (!p) return "";
    const u = precoUnit(p, it);
    const det = [`Tamanho ${it.tamanho}`];
    if (it.nome) det.push(`Nome: ${it.nome}`);
    if (it.numero) det.push(`Número: ${it.numero}`);
    if (it.patches.length) det.push(`Patches: ${it.patches.join(", ")}`);
    return `<li class="item">
      <img src="${esc(p.th)}" alt="">
      <div><div class="item__nome">${esc(p.t)}</div><div class="item__det">${esc(det.join(" · "))}</div></div>
      <div class="item__lado">
        <span class="item__valor">${u != null ? brl(u * it.qtd) : "a confirmar"}</span>
        <div class="qtd"><button type="button" data-menos="${i}" aria-label="Diminuir">−</button><output>${it.qtd}</output><button type="button" data-mais="${i}" aria-label="Aumentar">+</button></div>
        <button type="button" class="item__remover" data-remover="${i}">Remover</button>
      </div>
    </li>`;
  }

  function totais() {
    let total = 0, aConfirmar = 0;
    carrinho.forEach((it) => {
      const p = porId.get(it.id);
      const u = p && precoUnit(p, it);
      if (u != null) total += u * it.qtd; else aConfirmar += it.qtd;
    });
    return { total, aConfirmar };
  }

  function renderCarrinho() {
    carrinho = carrinho.filter((it) => porId.has(it.id));
    $("#c-itens").innerHTML = carrinho.map(linhaItem).join("");
    const vazio = !carrinho.length;
    $("#c-vazio").hidden = !vazio;
    $("#c-rodape").hidden = vazio;
    const { total, aConfirmar } = totais();
    $("#c-total").textContent = aConfirmar && !total ? "a confirmar" : brl(total) + (aConfirmar ? " + a confirmar" : "");
    $("#c-nota").textContent = aConfirmar
      ? `${aConfirmar} ${aConfirmar === 1 ? "peça está" : "peças estão"} com preço sob consulta; a loja confirma o valor no WhatsApp.`
      : "";
    atualizarContador();
  }

  function abrirCarrinho() {
    renderCarrinho();
    $("#c-cliente").value = ler("tm-cliente", "");
    $("#c-cidade").value = ler("tm-cidade", "");
    abrir("#carrinho");
  }

  function mensagem() {
    const linhas = ["Olá! Quero fazer este pedido:", ""];
    carrinho.forEach((it, i) => {
      const p = porId.get(it.id);
      const u = precoUnit(p, it);
      linhas.push(`${i + 1}) ${p.t}`);
      linhas.push(`   Tamanho: ${it.tamanho} | Qtd: ${it.qtd}`);
      const pers = [];
      if (it.nome) pers.push(`Nome: ${it.nome} (+${brl(C.PRECO_NOME)})`);
      if (it.numero) pers.push(`Número: ${it.numero} (+${brl(C.PRECO_NUMERO)})`);
      if (pers.length) linhas.push(`   ${pers.join(" | ")}`);
      if (it.patches.length) linhas.push(`   Patches: ${it.patches.join(", ")} (+${brl(C.PRECO_PATCH * it.patches.length)})`);
      linhas.push(`   Subtotal: ${u != null ? brl(u * it.qtd) : "a confirmar"}`);
      linhas.push(`   Foto: ${C.SITE_URL}p/${p.id}.html`);
      linhas.push("");
    });
    const { total, aConfirmar } = totais();
    linhas.push(`TOTAL: ${aConfirmar && !total ? "a confirmar" : brl(total) + (aConfirmar ? " + itens a confirmar" : "")}`);
    linhas.push(`Nome do cliente: ${$("#c-cliente").value.trim() || "____"}  Cidade: ${$("#c-cidade").value.trim() || "____"}`);
    return linhas.join("\n");
  }

  function montarCarrinho() {
    $("#abrir-carrinho").addEventListener("click", abrirCarrinho);
    $("#c-itens").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.remover != null) carrinho.splice(+b.dataset.remover, 1);
      if (b.dataset.menos != null) { const it = carrinho[+b.dataset.menos]; it.qtd = Math.max(1, it.qtd - 1); }
      if (b.dataset.mais != null) { const it = carrinho[+b.dataset.mais]; it.qtd = Math.min(20, it.qtd + 1); }
      guardar("tm-carrinho", carrinho);
      renderCarrinho();
    });
    $("#c-cliente").addEventListener("change", (e) => guardar("tm-cliente", e.target.value));
    $("#c-cidade").addEventListener("change", (e) => guardar("tm-cidade", e.target.value));
    $("#c-enviar").addEventListener("click", () => {
      if (!carrinho.length) return;
      const url = `https://wa.me/${C.WHATSAPP || ""}?text=${encodeURIComponent(mensagem())}`;
      window.open(url, "_blank", "noopener");
    });
  }

  // ---------- painéis e rotas ----------
  let ultimoFoco = null;
  function abrir(sel) {
    ultimoFoco = document.activeElement;
    $(sel).hidden = false;
    document.body.style.overflow = "hidden";
    $(sel).querySelector(".fechar").focus();
  }
  function fechar(sel) {
    $(sel).hidden = true;
    if ($("#produto").hidden && $("#carrinho").hidden) document.body.style.overflow = "";
    if (ultimoFoco) ultimoFoco.focus?.();
  }
  document.addEventListener("click", (e) => {
    const f = e.target.closest("[data-fechar]");
    if (!f) return;
    const painel = f.closest(".painel");
    if (painel.id === "produto") location.hash = "#/"; else fechar("#carrinho");
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#carrinho").hidden) fechar("#carrinho");
    else if (!$("#produto").hidden) location.hash = "#/";
  });

  function rota() {
    const m = location.hash.match(/^#\/p\/(.+)$/);
    if (m) abrirProduto(decodeURIComponent(m[1]));
    else if (!$("#produto").hidden) { fechar("#produto"); document.title = "TM Sports · Camisas de times"; }
  }
  window.addEventListener("hashchange", rota);

  // ---------- início ----------
  montarControles();
  montarProduto();
  montarCarrinho();
  atualizarContador();
  $("#contagem").textContent = "Carregando catálogo…";
  fetch("produtos.json")
    .then((r) => r.json())
    .then((dados) => {
      produtos = dados;
      produtos.forEach((p) => { p._busca = semAcento(`${p.t} ${p.tn || ""} ${LIGAS[p.l] || ""} ${TIPOS[p.ti] || ""}`); });
      porId = new Map(produtos.map((p) => [p.id, p]));
      atualizarSelects();
      aplicarFiltros();
      rota();
    })
    .catch(() => { $("#contagem").textContent = "Não foi possível carregar o catálogo. Recarregue a página."; });
})();
