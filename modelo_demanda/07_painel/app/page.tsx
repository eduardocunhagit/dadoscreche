'use client';

import { useEffect, useState } from 'react';

type Group = { grupamento_norm:string; demanda_2026_ppml:number; demanda_2026_persistencia:number };
type Unit = { codigo_unidade:string; nome_unidade_norm:string; demanda_2026_ppml:number; demanda_2026_persistencia:number; interesse_bruto_2025:number|string; bairro:string };
type Results = {
  projection:{ total_ppml:number; total_persistence:number; markets:number; alternatives:number; units:number; origin_geo_coverage:number; unit_context_coverage:number };
  groups:Group[];
  top_units:Unit[];
  audit:{ n_choice_episodes:number; n_panel_rows:number };
};

const integer = (x:number) => new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(x);
const pct = (x:number) => new Intl.NumberFormat('pt-BR',{style:'percent',maximumFractionDigits:1}).format(x);

export default function Home() {
  const [results,setResults] = useState<Results|null>(null);
  useEffect(() => { fetch('/results.json').then(r=>r.json()).then(setResults); }, []);
  const p = results?.projection;

  return <main>
    <nav className="nav shell">
      <a className="brand" href="#top"><span>MD</span>Modelo de demanda</a>
      <div className="navLinks"><a href="#projecao">Projeção</a><a href="#unidades">Creches</a><a href="#metodo">Método</a></div>
      <small className="status">● projeção 2026 concluída</small>
    </nav>

    <section className="hero shell" id="top">
      <div className="eyebrow">SME Rio · planejamento de creches</div>
      <div className="heroGrid">
        <div>
          <h1>Quantas crianças devem procurar cada creche em 2026?</h1>
          <p className="lede">O modelo combina população elegível, histórico de inscrições, distância, atributos das unidades e concorrência para prever demanda de primeira opção por creche e turno.</p>
          <div className="actions"><a className="primary" href="#projecao">Ver projeção ↓</a><a href="#metodo">Entender o modelo</a></div>
        </div>
        <div className="visual">
          <div className="origin"><b>bairro × idade</b><span>crianças previstas</span></div>
          <div className="routes"><i/><i/><i/></div>
          <div className="schools"><div><b>p₁</b><span>creche A</span></div><div><b>p₂</b><span>creche B</span></div><div><b>p₃</b><span>creche C</span></div></div>
          <small>As participações somam 1 e preservam o total previsto em cada território.</small>
        </div>
      </div>
      <div className="audit">
        <article><strong>{p?integer(p.total_ppml):'—'}</strong><b>crianças</b><small>cenário principal de 2026</small></article>
        <article><strong>{p?integer(p.total_persistence):'—'}</strong><b>crianças</b><small>cenário de persistência</small></article>
        <article><strong>{p?integer(p.units):'—'}</strong><b>creches</b><small>{p?integer(p.alternatives):'—'} alternativas com turno</small></article>
        <article><strong>{p?pct(p.unit_context_coverage):'—'}</strong><b>cadastros unidos</b><small>geografia e contexto das unidades</small></article>
      </div>
    </section>

    <section className="section dark" id="projecao"><div className="shell">
      <header className="sectionHead"><div><span>Projeção integrada</span><h2>Demanda prevista por grupamento.</h2></div><p>O cenário principal usa PPML-FE territorial e o logit completo de escolha. Persistência permanece como cenário comparável.</p></header>
      <div className="metrics">
        {(results?.groups ?? []).map(g=><span key={g.grupamento_norm}>{g.grupamento_norm}<b>{integer(g.demanda_2026_ppml)} principal · {integer(g.demanda_2026_persistencia)} persistência</b></span>)}
      </div>
    </div></section>

    <section className="section shell" id="unidades">
      <header className="sectionHead"><div><span>Distribuição entre unidades</span><h2>Creches com maior demanda prevista.</h2></div><p>O interesse bruto de 2025 conta todas as unidades selecionadas pela criança; a previsão de 2026 representa primeira opção.</p></header>
      <div className="modelTable">
        <header><span>Creche</span><span>Principal</span><span>Persistência</span></header>
        {(results?.top_units ?? []).map(u=><article key={u.codigo_unidade}><div><b>{u.nome_unidade_norm}</b><small>{u.bairro || 'contexto geográfico ausente'} · código {u.codigo_unidade}</small></div><span>{integer(u.demanda_2026_ppml)}</span><em>{integer(u.demanda_2026_persistencia)}</em></article>)}
      </div>
    </section>

    <section className="section shell" id="metodo">
      <header className="sectionHead"><div><span>Arquitetura econômica</span><h2>Uma previsão, duas equações conectadas.</h2></div><p>O modelo estima o total territorial e, depois, a probabilidade de escolha de cada creche e turno.</p></header>
      <div className="pipeline">
        <article><div><span>01</span><i>→</i></div><h3>Demanda potencial</h3><p>Nascimentos, coortes elegíveis, histórico e tendência territorial.</p></article>
        <article><div><span>02</span><i>→</i></div><h3>Conjunto de escolha</h3><p>Alternativas ativas por grupamento, unidade e turno.</p></article>
        <article><div><span>03</span><i>→</i></div><h3>Preferências</h3><p>Distância, mesmo bairro, atributos e concorrência por co-seleção.</p></article>
        <article><div><span>04</span></div><h3>Demanda por creche</h3><p>Total territorial multiplicado pela participação prevista.</p></article>
      </div>
      <div className="formula"><div><span>Estimando final</span><b>D̂<sub>agt</sub> = Σ<sub>m</sub> Â<sub>mgt</sub> × ŝ<sub>amgt</sub></b></div><p>Treino de 2021–2025, {results?.audit?integer(results.audit.n_choice_episodes):'—'} crianças-ano e {p?integer(p.markets):'—'} mercados previstos para 2026.</p></div>
    </section>

    <section className="decision shell"><div><span>Reproduzível</span><h2>Modelo explicável, com cenários e IC95.</h2></div><p>Rode <code>python modelo_demanda/05_projecao_2026/prever_demanda_2026.py</code>. Resultados e manifesto ficam em <code>modelo_demanda/06_resultados</code>.</p></section>
    <footer className="shell"><span>Modelo de demanda por creche · projeção 2026</span><span>Dados históricos anonimizados · alocação legal fora do modelo</span></footer>
  </main>;
}