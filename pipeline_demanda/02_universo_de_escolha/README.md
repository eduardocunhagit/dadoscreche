# Universo de escolha

## Objeto

O mercado é uma célula `ano × território de origem × grupamento`. A alternativa é `unidade × turno`.

Para cada mercado, entram todas as alternativas observadas como ativas naquele `ano × grupamento`. A primeira opção registrada vira a contagem escolhida; as demais alternativas recebem zero. Assim, o modelo não é estimado apenas sobre a lista curta submetida pela família.

## Tratamento territorial

- origem: bairro normalizado da inscrição;
- coordenada da origem: centroide mediano das unidades localizadas no bairro;
- unidade: coordenada oficial por código e, para parceiras, também por nome normalizado;
- fallback: centroide do bairro e depois centroide municipal, sempre sinalizado.

Cobertura atual: 95,6% das origens e 98,5% das células de alternativas com coordenada oficial. Entre as 350 parceiras, 93,5% têm coordenada oficial recuperada.

## Quebra de cobertura em 2024

As parceiras só aparecem na Query A a partir de 2024. Elas são tratadas como um regime de cold start, separado das unidades incumbentes. Isso evita interpretar ausência na extração de 2021–2023 como ausência de demanda.
