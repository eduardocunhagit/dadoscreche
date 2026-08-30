'use client';

import { useEffect, useMemo, useState } from 'react';

type Fold = '2024' | '2025';
type Metric = { fold:string; model:string; log_loss:number; top1:number; demand_mae:number; demand_wape:number };
type Results = {
  audit:{ n_choice_episodes:number; n_markets:number; n_active_alternative_cells:number; n_panel_rows:number; origin_geo_coverage:number; unit_geo_official_share:number };
  metrics:Metric[];
  selected_by_log_loss:{fold:string;model:string;log_loss:number}[];
};

const foldInfo = {
  '2024': { train:'2021–2023', note:'Grande entrada de unidades novas. Distância é o melhor modelo por log loss.' },
  '2025': { train:'2021–2024', note:'Rede mais estável. Histórico vence em log loss; o modelo completo vence em erro de demanda.' },
};
const modelInfo = [
  ['historical_share','Participação histórica','benchmark'],
  ['nearest_unit','Mais próxima','benchmark'],
  ['conditional_logit_distance','Logit · distância','M1'],
  ['conditional_logit_attributes','Logit · atributos','M2'],
  ['conditional_logit_full','Atributos + concorrência','M3'],
];

const pct = (x:number) => (100*x).toFixed(1).replace('.',',') + '%';
const num = (x:number,d=2) => x.toFixed(d).replace('.',',');
const integer = (x:number) => new Intl.NumberFormat('pt-BR').format(x);

export default function Home() {
  const [fold,setFold] = useState<Fold>('2024');
  const [results,setResults] = useState<Results|null>(null);
  useEffect(() => { fetch('/results.json').then(r=>r.json()).then(setResults); }, []);
  const metrics = useMemo(() => results?.metrics.filter(m=>m.fold==='oos_'+fold) ?? [],[results,fold]);
  const winner = metrics.length ? [...metrics].sort((a,b)=>a.log_loss-b.log_loss)[0].model : undefined;
  const audit = results?.audit;

  return <main>
    <nav className="nav shell">
      <a className="brand" href="#top"><span>F2</span>Mapa de demanda</a>
      <div className="navLinks"><a href="#resultados">Resultados</a><a href="#modelo">Modelo</a><a href="#contrato">Contrato</a></div>
      <small className="status">● modelos rodados</small>
    </nav>

    <section className="hero shell" id="top">
      <div className="eyebrow">SME Rio · Frente 2</div>
      <div className="heroGrid">
        <div>
          <h1>Para onde vai a demanda por creche?</h1>
          <p className="lede">Escolha entre todas as alternativas unidade × turno ativas no ano, com distância, atributos, concorrência e validação fora da amostra.</p>
          <div className="actions"><a className="primary" href="#resultados">Ver resultados OOS ↓</a><a href="#modelo">Ver arquitetura</a></div>
        </div>
        <div className="visual">
          <div className="origin"><b>m × g × t</b><span>entrada prevista</span></div>
          <div className="routes"><i/><i/><i/></div>
          <div className="schools"><div><b>p₁</b><span>unidade A</span></div><div><b>p₂</b><span>unidade B</span></div><div><b>p₃</b><span>unidade C</span></div></div>
          <small>As probabilidades somam 1 dentro de cada origem × grupamento × ano.</small>
        </div>
      </div>
      <div className="audit">
        <article><strong>{audit?integer(audit.n_choice_episodes):'—'}</strong><b>episódios</b><small>primeiras opções</small></article>
        <article><strong>{audit?integer(audit.n_active_alternative_cells):'—'}</strong><b>células ativas</b><small>ano × grupo × alternativa</small></article>
        <article><strong>{audit?integer(audit.n_panel_rows):'—'}</strong><b>linhas no painel</b><small>conjunto completo</small></article>
        <article><strong>{audit?pct(audit.origin_geo_coverage):'—'}</strong><b>origens cobertas</b><small>proxy territorial</small></article>
      </div>
    </section>

    <section className="section dark" id="resultados"><div className="shell">
      <header className="sectionHead"><div><span>Resultados reais</span><h2>Dois testes temporais. Cinco modelos.</h2></div><p>Log loss mede a previsão individual. WAPE e MAE medem o erro agregado por alternativa.</p></header>
      <div className="foldButtons">{(['2024','2025'] as Fold[]).map(y=><button key={y} className={fold===y?'active':''} onClick={()=>setFold(y)}>OOS {y}</button>)}</div>
      <div className="eval">
        <aside><small>Treino</small><strong>{foldInfo[fold].train}</strong><small>Teste</small><strong>{fold}</strong><small>Universo</small><strong>{audit?integer(audit.n_markets):'—'} mercados</strong><p>{foldInfo[fold].note}</p></aside>
        <div className="modelTable">
          <header><span>Modelo</span><span>Log loss</span><span>WAPE</span></header>
          {modelInfo.map(([id,label,role])=>{
            const m=metrics.find(x=>x.model===id);
            return <article key={id} className={winner===id?'winner':''}><div><b>{label}</b><small>{role}{winner===id?' · melhor log loss':''}</small></div><span>{m?num(m.log_loss,3):'—'}</span><em>{m?pct(m.demand_wape):'—'}</em></article>;
          })}
        </div>
      </div>
      <div className="metrics">
        <span>2024 · amostra completa <b>logit de distância</b></span>
        <span>2024 · incumbentes <b>participação histórica</b></span>
        <span>2024 · parceiras <b>modelo completo em log loss</b></span>
        <span>2025 · amostra completa <b>histórico em log loss · completo em WAPE</b></span>
      </div>
    </div></section>

    <section className="section shell" id="modelo">
      <header className="sectionHead"><div><span>Arquitetura econômica</span><h2>O universo deixou de ser a lista observada.</h2></div><p>Cada mercado recebe todas as alternativas observadas como ativas naquele ano e grupamento. A escolha registrada vira contagem dentro desse universo.</p></header>
      <div className="pipeline">
        <article><div><span>01</span><i>→</i></div><h3>Mercado</h3><p>Origem territorial × grupamento × ano.</p></article>
        <article><div><span>02</span><i>→</i></div><h3>Alternativas</h3><p>Todas as unidades × turnos ativos.</p></article>
        <article><div><span>03</span><i>→</i></div><h3>Escolha</h3><p>Softmax linear, coeficientes expostos.</p></article>
        <article><div><span>04</span></div><h3>Demanda</h3><p>Total da Frente 1 × participação prevista.</p></article>
      </div>
      <div className="formula"><div><span>Integração</span><b>D̂<sub>agt</sub> = Σ<sub>m</sub> Â<sub>mgt</sub> × ŝ<sub>amgt</sub></b></div><p>O total territorial é conservado. A Frente 2 distribui a entrada prevista; não classifica crianças.</p></div>
    </section>

    <section className="section shell" id="contrato">
      <header className="sectionHead"><div><span>Leitura econômica</span><h2>Distância domina; histórico ajuda quando a rede estabiliza.</h2></div><p>Em 2024, o share passado quebra com a expansão da rede. Em 2025, ele volta a ser forte; concorrência melhora a previsão agregada.</p></header>
      <div className="cards">
        <article><i>+</i><h3>Modelo completo</h3><ul><li>distância e mesmo bairro;</li><li>turno e tipo da unidade;</li><li>demanda e pressão de lista defasadas;</li><li>concorrência geográfica e co-listagem.</li></ul></article>
        <article><i>✓</i><h3>Teste operacional</h3><ul><li>treino termina antes do teste;</li><li>probabilidades somam 1;</li><li>demanda total é conservada;</li><li>unidades novas são avaliadas separadamente.</li></ul></article>
        <article className="competition"><span>Resultado</span><h3>Não há campeão universal.</h3><div className="network"><i/><i/><i/><i/></div><p>Produção deve usar seleção temporal: distância para mudanças grandes de rede; histórico ou modelo completo quando a rede está estável.</p></article>
      </div>
    </section>

    <section className="decision shell"><div><span>Versão testável</span><h2>Pipeline real, reproduzível e sem caixa-preta.</h2></div><p>Os arquivos agregados e o manifesto estão em <code>frente2/06_resultados/arquivos_gerados</code>. Rode <code>python frente2/executar_frente2.py</code> para reproduzir.</p></section>
    <footer className="shell"><span>Frente 2 · demanda condicionada à inscrição</span><span>Dados históricos anonimizados · OOS 2024–2025</span></footer>
  </main>;
}
