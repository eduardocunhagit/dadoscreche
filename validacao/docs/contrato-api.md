# Contrato da API de validação de critérios

Acordo entre o **site** (parte 1) e o **motor de validação** (parte 2): qual pergunta o
site manda, qual resposta o motor devolve.

O contrato existe em duas formas que devem andar juntas: este documento e
[`validacao/motor/modelos.py`](../motor/modelos.py), que é a definição executável.
Em caso de divergência, o código manda.

**Estado atual:** o mock já responde neste formato. Pode desenvolver contra ele hoje.

```bash
pip install fastapi uvicorn pydantic pyyaml
uvicorn validacao.api.mock:app --reload --port 8000
```

Documentação interativa (Swagger) em `http://localhost:8000/docs`.

---

## Duas decisões que o contrato carrega

Antes dos campos, o que eles significam em termos de política pública:

**1. A validação automática nunca nega um critério.** Se a família declara que está no
CadÚnico e a base não confirma, o resultado é `divergente` → revisão humana, e a
declaração continua valendo. Não existe status que reprove alguém. Extrato pode estar
velho, incompleto ou com o nome grafado diferente — nada disso pode custar a vaga de uma
criança. O ganho da automação é tirar trabalho de quem já está provado, não criar uma
nova forma de indeferir.

**2. Toda validação diz de onde veio.** Todo critério que consultou uma base volta com
`fonte`: qual base, qual campo, a data do extrato e a versão da regra. É o que permite
explicar a decisão à família e atender ao direito de revisão de decisão automatizada
(LGPD art. 20). Se o site mostrar "✅ confirmado", precisa poder responder "confirmado
onde?".

---

## Endpoints

### `POST /v1/validacao`

**Requisição**

```json
{
  "responsavel": "responsavel_0001234",
  "ano_processo": 2025,
  "criancas": [
    { "aluno": "aluno_0007890", "declaracoes": { "28": true, "25": true, "17": true } }
  ]
}
```

| Campo | Tipo | Observação |
|---|---|---|
| `responsavel` | string | Chave do responsável. Hoje `responsavel_anon`; em produção, CPF |
| `ano_processo` | int | Define qual régua aplicar. A régua muda todo ano |
| `criancas[].aluno` | string | Chave da criança. Hoje `aluno_anon`; em produção, CPF ou DNV |
| `criancas[].declaracoes` | `{perg_id: bool}` | O que a família já respondeu. **Opcional** — mande `{}` na primeira chamada |

Sobre `declaracoes`: mande vazio antes do preenchimento e o motor devolve o que consegue
provar sozinho — é o que permite **pré-preencher o formulário**. Depois de a família
responder, mande as respostas e o motor passa a detectar divergência.

**Resposta** (trechos; exemplo real do mock)

```json
{
  "responsavel": "responsavel_0001234",
  "ano_processo": 2025,
  "versao_regras": "v1",
  "gerado_em": "2026-08-30T16:00:45Z",
  "trace_id": "mock-4c5490d9a49b",
  "inscricoes": [
    {
      "crianca": "aluno_0007890",
      "criterios": [
        {
          "perg_id": 28,
          "texto": "Criança cuja família seja inscrita no CadÚnico...?",
          "pontos": 51,
          "desempate": false,
          "sujeito": "familia",
          "status": "validado",
          "valor": true,
          "declarado": true,
          "fonte": {
            "base": "CADUNICO", "campo": "COD_EST_CADASTRAL_FAM",
            "extracao": "2025-11-30", "regra": "cadunico_inscrita", "versao_regras": "v1"
          },
          "explicacao": "Confirmado automaticamente em CADUNICO. Não é preciso anexar documento.",
          "acao_necessaria": "nenhuma"
        },
        {
          "perg_id": 25,
          "texto": "Candidato tem pais ou responsáveis deficientes ?",
          "pontos": 3,
          "status": "divergente",
          "valor": false,
          "declarado": true,
          "fonte": { "base": "CADUNICO", "campo": "COD_DEFICIENCIA_MEMB", "...": "..." },
          "explicacao": "Você declarou que atende, mas não localizamos confirmação na base. Sua declaração foi mantida e será analisada por uma pessoa — você não perde a pontuação por causa disto.",
          "acao_necessaria": "revisao_manual"
        },
        {
          "perg_id": 17,
          "texto": "A criança e/ou familiar do seu convívio diário é vitima de violência doméstica?",
          "pontos": 4,
          "status": "sem_fonte",
          "valor": null,
          "fonte": null,
          "explicacao": "Não existe base pública que comprove este critério. A comprovação segue manual.",
          "acao_necessaria": "anexar_documento"
        }
      ],
      "pontuacao": {
        "validada": 57, "pendente_comprovacao": 4,
        "potencial": 61, "maxima_regua": 100
      }
    }
  ]
}
```

### `GET /v1/regua/{ano}`

A régua do ano com a cobertura de cada critério. Serve para o site montar a tela de
critérios sem chamar a validação. Cada critério traz um campo `nota` explicando, quando
não há cobertura, **por quê** — texto aproveitável direto na interface.

### `GET /health`

Estado do serviço e anos disponíveis.

---

## Os cinco status

`status` é o contrato de UI. O site decide o que renderizar a partir dele:

| status | significa | o que o site faz |
|---|---|---|
| `validado` | Confirmado em base oficial | ✅ marca como provado, **não pede documento** |
| `nao_encontrado` | Base consultada, família não atende | Fluxo normal de declaração |
| `divergente` | Família declarou, base não confirma | Avisa que vai a revisão humana; **mantém a declaração** |
| `sem_fonte` | Nenhuma base responde isso | Pede documento, como hoje |
| `fonte_indisponivel` | A fonte falhou nesta consulta | Pede documento; o motor tenta de novo depois |

E `acao_necessaria` diz o que pedir: `nenhuma`, `anexar_documento` ou `revisao_manual`.

Se o site precisar de uma regra só: **peça documento sempre que `acao_necessaria` não for
`nenhuma`.** O resto é refinamento de texto na tela.

## Pontuação

| Campo | O que é |
|---|---|
| `validada` | Pontos já provados por cruzamento |
| `pendente_comprovacao` | Pontos que a família declarou e ainda dependem de documento |
| `potencial` | `validada + pendente_comprovacao` |
| `maxima_regua` | Teto do ano (100 em 2024 e 2025) |

`validada` é a barra que interessa mostrar em destaque: é o que a família já tem garantido
sem fazer mais nada.

---

## Cenários de teste no mock

Chaves reservadas que forçam cada caminho da tela, sem depender de sorteio:

| `responsavel` | O que devolve |
|---|---|
| `responsavel_TESTE_TUDO` | Todos os cobertos `validado` — 60 pontos |
| `responsavel_TESTE_NADA` | Todos os cobertos `nao_encontrado` — 0 pontos |
| `responsavel_TESTE_DIVERGE` | Todos os cobertos `divergente` — tela de revisão manual |
| `responsavel_TESTE_FORA` | CadÚnico em `fonte_indisponivel` — tela de degradação |

Qualquer outra chave cai no modo determinístico: a mesma chave devolve sempre a mesma
resposta, então dá para guardar um caso e voltar nele.

## Cobertura hoje

Dos 100 pontos da régua de 2025, o cruzamento com CadÚnico, RAIS e o histórico da própria
SME resolve **60**, distribuídos em 6 dos 13 critérios. O detalhamento e o motivo de cada
lacuna estão em [`cobertura-criterios.md`](cobertura-criterios.md).

O maior deles sozinho — inscrição no CadÚnico, 51 pontos — é hoje o que mais se perde:
das 35.141 inscrições que o declararam em 2025, apenas 6,8% conseguiram comprová-lo.

## Estabilidade

Os nomes dos campos e os valores de `status` e `acao_necessaria` estão congelados. Mudança
incompatível sobe a versão do caminho (`/v2/`), não altera `/v1/` em silêncio. Campos novos
podem aparecer em `/v1/` — trate a resposta como aberta e ignore o que não conhecer.
