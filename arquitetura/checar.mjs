// Confere o mapa sem navegador: sintaxe, ids, referências entre cards e limites das zonas.
// Uso: node docs/arquitetura/checar.mjs   (sai com código 1 se houver erro)
// O que depende da altura real dos cards (cards encostados, setas atravessando) só aparece
// no navegador: abra index.html?checar.
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('index.html', import.meta.url), 'utf8');
const ini = html.indexOf('/* ===== DADOS DO MAPA'), fim = html.indexOf('/* ===== FIM DOS DADOS');
if (ini < 0 || fim < 0) { console.error('Marcadores DADOS DO MAPA / FIM DOS DADOS não encontrados.'); process.exit(1); }

const erros = [], avisos = [];
try { new Function(html.slice(html.indexOf('<script>') + 8, html.lastIndexOf('</script>'))); }
catch (e) { console.error('Erro de sintaxe no script:', e.message); process.exit(1); }

const ctx = {};
vm.runInNewContext(html.slice(ini, fim) + '\n;globalThis.M = {ZONES, ST, CARDS, EDGES, TOURS, DEC, EDGE_KINDS, I, W, H};', ctx);
const {ZONES, ST, CARDS, EDGES, TOURS, DEC, EDGE_KINDS, I, W, H} = ctx.M;

const ids = new Set();
for (const c of CARDS) {
  const nome = c.id || JSON.stringify(c).slice(0, 40);
  for (const f of ['id', 'k', 'z', 'x', 'y', 'w', 'eb', 't']) if (c[f] === undefined) erros.push(`card ${nome}: falta o campo ${f}`);
  if (ids.has(c.id)) erros.push(`id repetido: ${c.id}`);
  ids.add(c.id);
  if (!(c.k in I)) erros.push(`card ${nome}: tipo k='${c.k}' não existe (use ${Object.keys(I).join(', ')})`);
  if (c.k === 'etapa' && !c.n) erros.push(`card ${nome}: etapa sem número n`);
  if (c.st && !(c.st in ST)) erros.push(`card ${nome}: situação st='${c.st}' não existe (use ${Object.keys(ST).join(', ')})`);
  const z = ZONES[c.z];
  if (!z) { erros.push(`card ${nome}: zona '${c.z}' não existe`); continue; }
  if (c.x < z.x || c.x + c.w > z.x + z.w) erros.push(`card ${nome}: sai da zona ${c.z} na horizontal`);
  if (c.y < z.y + 40 || c.y > z.y + z.h - 100) avisos.push(`card ${nome}: perto da borda de cima ou de baixo da zona ${c.z}`);
  if (c.k === 'etapa' && c.tx && c.tx.length > 115) avisos.push(`etapa ${nome}: texto com ${c.tx.length} caracteres (o espaço comporta uns 115)`);
}
for (const [id, z] of Object.entries(ZONES)) if (z.x + z.w > W || z.y + z.h > H) erros.push(`zona ${id} passa do canvas: aumente W ou H`);

// Cards da mesma coluna muito próximos: a altura real só se sabe no navegador
for (const a of CARDS) for (const b of CARDS) {
  if (a === b || a.z !== b.z || b.y <= a.y) continue;
  if (a.x < b.x + b.w && b.x < a.x + a.w && b.y - a.y < (a.k === 'etapa' ? 125 : 150)) avisos.push(`${a.id} e ${b.id} estão a ${b.y - a.y}px: confira com ?checar`);
}

const tipos = new Set(EDGE_KINDS.map(k => k[0]));
for (const e of EDGES) {
  const nome = `seta ${e.a} → ${e.b}`;
  if (!ids.has(e.a)) erros.push(`${nome}: origem '${e.a}' não existe`);
  if (!ids.has(e.b)) erros.push(`${nome}: destino '${e.b}' não existe`);
  if (!tipos.has(e.k)) erros.push(`${nome}: tipo k='${e.k}' não existe`);
  if (e.via && (e.s === undefined || e.t === undefined)) erros.push(`${nome}: seta com via precisa de s e t`);
}
TOURS.forEach(t => t.steps.forEach((s, i) => s.c.forEach(id => { if (!ids.has(id)) erros.push(`fluxo "${t.t}", passo ${i + 1}: card '${id}' não existe`); })));
DEC.forEach(d => {
  for (const f of ['g', 't', 's', 'tx']) if (!d[f]) erros.push(`decisão "${d.t}": falta o campo ${f}`);
  (d.c || []).forEach(id => { if (!ids.has(id)) erros.push(`decisão "${d.t}": card '${id}' não existe`); });
});

for (const a of avisos) console.log('aviso:', a);
for (const e of erros) console.error('erro:', e);
console.log(`${CARDS.length} cards, ${EDGES.length} setas, ${TOURS.length} fluxos, ${DEC.length} decisões: ${erros.length} erro(s), ${avisos.length} aviso(s).`);
process.exit(erros.length ? 1 : 0);
