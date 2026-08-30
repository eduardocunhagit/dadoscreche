"""Extrai das bases reais da SME o universo de pessoas sobre o qual as bases
sinteticas sao construidas.

Nada aqui e inventado: sao os responsaveis, criancas, enderecos e declaracoes que
existem de fato na extracao. O CadUnico e a RAIS sinteticos sao depois construidos
POR CIMA deste universo, para que as chaves casem e as declaracoes possam ser
confrontadas com o que a base "diz".

Saidas em dados/:
    universo_familia.parquet    uma linha por (ano, responsavel)
    universo_crianca.parquet    uma linha por (ano, crianca) = uma inscricao
    declaracoes.parquet         uma linha por (inscricao, pergunta) em formato longo

Rodar com:  python -m validacao.gerador.universo
"""

from __future__ import annotations

import duckdb

from validacao.gerador.comum import DIR_BASES_SME, DIR_DADOS, RAIZ

QUERY_A = str(DIR_BASES_SME / "01_QueryA_InscricoesPorAno.csv.gz")
QUERY_B = str(DIR_BASES_SME / "02_QueryB_RespostasSocioEconomicas.csv.gz")
QUERY_C = str(DIR_BASES_SME / "03_QueryC_PerguntasComDescricao.csv")

LEITOR = "read_csv({caminho!r}, delim=';', header=true, encoding='utf-8')"


def construir(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"CREATE OR REPLACE VIEW qa AS SELECT * FROM {LEITOR.format(caminho=QUERY_A)}")
    con.execute(f"CREATE OR REPLACE VIEW qb AS SELECT * FROM {LEITOR.format(caminho=QUERY_B)}")
    con.execute(f"CREATE OR REPLACE VIEW qc AS SELECT * FROM {LEITOR.format(caminho=QUERY_C)}")

    # A QueryA tem uma linha por OPCAO de creche; a inscricao se repete. Colapsa
    # para uma linha por inscricao, guardando o desfecho mais favoravel entre as
    # opcoes -- e o que define se a crianca foi atendida naquele ano.
    con.execute("""
        CREATE OR REPLACE TABLE inscricao AS
        SELECT ano, prm_id, plm_id, ipl_id,
               any_value(aluno_anon)               AS aluno_anon,
               any_value(responsavel_anon)         AS responsavel_anon,
               any_value(sexo_crianca)             AS sexo_crianca,
               any_value(nascimento_aluno_anomes)  AS nascimento_anomes,
               any_value(CEP)                      AS cep,
               any_value(bairro)                   AS bairro,
               min(data_criacao)                   AS data_criacao,
               max(situacao IN ('Confirmado','Selecionado','Selecionado da lista','Ativo'))
                                                   AS atendida
        FROM qa
        GROUP BY ano, prm_id, plm_id, ipl_id
    """)

    # Declaracoes em formato longo, ja com o perg_id estavel do catalogo -- o
    # ich_perg_id muda a cada ano e nao serve para comparar entre edicoes.
    con.execute("""
        CREATE OR REPLACE TABLE declaracao AS
        SELECT b.ano, b.prm_id, b.plm_id, b.ipl_id,
               c.perg_id,
               b.resposta   = 'Sim' AS declarou,
               b.confirmado = 'Sim' AS confirmado_hoje
        FROM qb b
        JOIN qc c ON c.ano = b.ano AND c.ich_perg_id = b.ich_perg_id
    """)

    con.execute("""
        CREATE OR REPLACE TABLE universo_crianca AS
        SELECT i.ano, i.aluno_anon, i.responsavel_anon, i.prm_id, i.plm_id, i.ipl_id,
               i.sexo_crianca, i.nascimento_anomes, i.data_criacao, i.atendida
        FROM inscricao i
    """)

    # Uma familia pode ter mais de uma crianca inscrita no mesmo ano; endereco e
    # unico por responsavel, entao any_value basta.
    con.execute("""
        CREATE OR REPLACE TABLE universo_familia AS
        SELECT ano, responsavel_anon,
               any_value(cep)     AS cep,
               any_value(bairro)  AS bairro,
               count(DISTINCT aluno_anon) AS n_criancas,
               min(data_criacao)  AS primeira_inscricao
        FROM inscricao
        GROUP BY ano, responsavel_anon
    """)

    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    for tabela in ("universo_familia", "universo_crianca", "declaracao"):
        destino = DIR_DADOS / f"{tabela}.parquet"
        con.execute(f"COPY {tabela} TO '{destino}' (FORMAT PARQUET)")
        n = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
        print(f"  dados/{tabela}.parquet: {n:,} linhas".replace(",", "."))


def main() -> None:
    print("Extraindo universo real das bases da SME...")
    con = duckdb.connect()
    construir(con)

    resumo = con.execute("""
        SELECT ano,
               count(*)                          AS familias,
               (SELECT count(*) FROM universo_crianca c WHERE c.ano = f.ano) AS criancas
        FROM universo_familia f GROUP BY ano ORDER BY ano
    """).fetchall()
    print("\n  ano   familias  criancas")
    for ano, fam, cri in resumo:
        print(f"  {ano}  {fam:>9,}  {cri:>8,}".replace(",", "."))

    total_resp = con.execute("SELECT count(DISTINCT responsavel_anon) FROM universo_familia").fetchone()[0]
    total_alun = con.execute("SELECT count(DISTINCT aluno_anon) FROM universo_crianca").fetchone()[0]
    print(f"\n  responsaveis distintos: {total_resp:,}".replace(",", "."))
    print(f"  criancas distintas:     {total_alun:,}".replace(",", "."))
    con.close()


if __name__ == "__main__":
    main()
