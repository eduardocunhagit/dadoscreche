"""Chave de pessoa, num lugar so.

Na extracao anonimizada do hackathon a pessoa e identificada por `responsavel_anon`
e a crianca por `aluno_anon`. Sao codigos gerados por ROW_NUMBER() sobre uma chave
natural (CPF -> DNV -> NIS -> nome+nascimento), estaveis por pessoa entre as cinco
edicoes do processo -- que e exatamente a propriedade que um CPF teria.

Em producao a SME e as bases externas estao ambas identificadas e o join e por CPF.
Trocar significa mudar as duas constantes abaixo; nenhuma outra parte do codigo
escreve o nome da coluna literalmente.
"""

CHAVE_RESPONSAVEL = "responsavel_anon"
CHAVE_CRIANCA = "aluno_anon"

# Em producao:
#   CHAVE_RESPONSAVEL = "NUM_CPF_PESSOA"     # CadUnico bloco 5 / RAIS enc_cpf_worker
#   CHAVE_CRIANCA     = "NUM_CPF_PESSOA"     # ou DNV, quando a crianca nao tem CPF

#: Chave de junção de uma inscrição na extração da SME (QueryA <-> QueryB).
CHAVE_INSCRICAO = ("prm_id", "plm_id", "ipl_id")
