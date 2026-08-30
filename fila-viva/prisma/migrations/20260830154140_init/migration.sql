-- CreateTable
CREATE TABLE "Usuario" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "senhaHash" TEXT NOT NULL,
    "papel" TEXT NOT NULL,
    "nomeExibicao" TEXT NOT NULL,
    "responsavelId" TEXT,
    "poloId" TEXT,
    "unidadeEscCodigo" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Usuario_responsavelId_fkey" FOREIGN KEY ("responsavelId") REFERENCES "Responsavel" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Usuario_poloId_fkey" FOREIGN KEY ("poloId") REFERENCES "Polo" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Usuario_unidadeEscCodigo_fkey" FOREIGN KEY ("unidadeEscCodigo") REFERENCES "Unidade" ("escCodigo") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Responsavel" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "responsavelAnon" TEXT NOT NULL,
    "nomeExibicao" TEXT NOT NULL,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "Crianca" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "alunoAnon" TEXT NOT NULL,
    "nomeExibicao" TEXT NOT NULL,
    "sexo" TEXT NOT NULL,
    "nascimentoAnoMes" TEXT NOT NULL,
    "responsavelPrincipalId" TEXT NOT NULL,
    "semContatoAlternativoDeclarado" BOOLEAN NOT NULL DEFAULT false,
    "semContatoAlternativoDeclaradoEm" DATETIME,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Crianca_responsavelPrincipalId_fkey" FOREIGN KEY ("responsavelPrincipalId") REFERENCES "Responsavel" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Contato" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "criancaId" TEXT NOT NULL,
    "papel" TEXT NOT NULL,
    "nomeContato" TEXT,
    "parentesco" TEXT,
    "canal" TEXT NOT NULL,
    "valor" TEXT NOT NULL,
    "ordemTentativa" INTEGER NOT NULL DEFAULT 1,
    "verificadoEm" DATETIME,
    "consentimentoEm" DATETIME,
    "ativo" BOOLEAN NOT NULL DEFAULT true,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL,
    CONSTRAINT "Contato_criancaId_fkey" FOREIGN KEY ("criancaId") REFERENCES "Crianca" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ContatoHistorico" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "contatoId" TEXT NOT NULL,
    "autorUsuarioId" TEXT,
    "autorResponsavelId" TEXT,
    "autorPapel" TEXT NOT NULL,
    "campo" TEXT NOT NULL,
    "valorAntes" TEXT,
    "valorDepois" TEXT,
    "quando" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ContatoHistorico_contatoId_fkey" FOREIGN KEY ("contatoId") REFERENCES "Contato" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "ContatoHistorico_autorUsuarioId_fkey" FOREIGN KEY ("autorUsuarioId") REFERENCES "Usuario" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "ContatoHistorico_autorResponsavelId_fkey" FOREIGN KEY ("autorResponsavelId") REFERENCES "Responsavel" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Polo" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "plmId" INTEGER NOT NULL,
    "nome" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Unidade" (
    "escCodigo" TEXT NOT NULL PRIMARY KEY,
    "nome" TEXT NOT NULL,
    "tipoGestao" TEXT NOT NULL,
    "logradouro" TEXT,
    "numero" TEXT,
    "complemento" TEXT,
    "bairro" TEXT,
    "cep" TEXT
);

-- CreateTable
CREATE TABLE "Vaga" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "unidadeEscCodigo" TEXT NOT NULL,
    "ano" INTEGER NOT NULL,
    "grupamento" TEXT NOT NULL,
    "turno" TEXT NOT NULL,
    "capacidade" INTEGER NOT NULL,
    CONSTRAINT "Vaga_unidadeEscCodigo_fkey" FOREIGN KEY ("unidadeEscCodigo") REFERENCES "Unidade" ("escCodigo") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Processo" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "ano" INTEGER NOT NULL,
    "prmId" INTEGER NOT NULL,
    "nome" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Pergunta" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "processoId" TEXT NOT NULL,
    "ichPergId" INTEGER NOT NULL,
    "pergId" INTEGER NOT NULL,
    "texto" TEXT NOT NULL,
    "ordemVisualizacao" INTEGER NOT NULL,
    "pontuacao" INTEGER NOT NULL,
    "criterioDesempate" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "Pergunta_processoId_fkey" FOREIGN KEY ("processoId") REFERENCES "Processo" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Inscricao" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "processoId" TEXT NOT NULL,
    "poloId" TEXT NOT NULL,
    "iplId" INTEGER NOT NULL,
    "criancaId" TEXT NOT NULL,
    "responsavelId" TEXT NOT NULL,
    "dataCriacao" DATETIME NOT NULL,
    "cepResponsavel" TEXT,
    "bairroResponsavel" TEXT,
    CONSTRAINT "Inscricao_processoId_fkey" FOREIGN KEY ("processoId") REFERENCES "Processo" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "Inscricao_poloId_fkey" FOREIGN KEY ("poloId") REFERENCES "Polo" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "Inscricao_criancaId_fkey" FOREIGN KEY ("criancaId") REFERENCES "Crianca" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "Inscricao_responsavelId_fkey" FOREIGN KEY ("responsavelId") REFERENCES "Responsavel" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Opcao" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "inscricaoId" TEXT NOT NULL,
    "ordem" INTEGER NOT NULL,
    "unidadeEscCodigo" TEXT NOT NULL,
    "grupamento" TEXT NOT NULL,
    "turno" TEXT NOT NULL,
    "estado" TEXT NOT NULL DEFAULT 'NA_FILA',
    "situacaoOriginal" TEXT,
    "ofertaAbertaEm" DATETIME,
    "ofertaPrazo" DATETIME,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Opcao_inscricaoId_fkey" FOREIGN KEY ("inscricaoId") REFERENCES "Inscricao" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "Opcao_unidadeEscCodigo_fkey" FOREIGN KEY ("unidadeEscCodigo") REFERENCES "Unidade" ("escCodigo") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "OfertaEvento" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "opcaoId" TEXT NOT NULL,
    "estadoAnterior" TEXT NOT NULL,
    "estadoNovo" TEXT NOT NULL,
    "autorUsuarioId" TEXT,
    "autorPapel" TEXT NOT NULL,
    "canal" TEXT,
    "observacao" TEXT,
    "quando" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "OfertaEvento_opcaoId_fkey" FOREIGN KEY ("opcaoId") REFERENCES "Opcao" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "OfertaEvento_autorUsuarioId_fkey" FOREIGN KEY ("autorUsuarioId") REFERENCES "Usuario" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Resposta" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "inscricaoId" TEXT NOT NULL,
    "perguntaId" TEXT NOT NULL,
    "resposta" TEXT NOT NULL,
    "confirmado" TEXT NOT NULL,
    CONSTRAINT "Resposta_inscricaoId_fkey" FOREIGN KEY ("inscricaoId") REFERENCES "Inscricao" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "Resposta_perguntaId_fkey" FOREIGN KEY ("perguntaId") REFERENCES "Pergunta" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "Usuario_email_key" ON "Usuario"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Usuario_responsavelId_key" ON "Usuario"("responsavelId");

-- CreateIndex
CREATE UNIQUE INDEX "Responsavel_responsavelAnon_key" ON "Responsavel"("responsavelAnon");

-- CreateIndex
CREATE UNIQUE INDEX "Crianca_alunoAnon_key" ON "Crianca"("alunoAnon");

-- CreateIndex
CREATE INDEX "Crianca_responsavelPrincipalId_idx" ON "Crianca"("responsavelPrincipalId");

-- CreateIndex
CREATE INDEX "Contato_criancaId_idx" ON "Contato"("criancaId");

-- CreateIndex
CREATE INDEX "ContatoHistorico_contatoId_idx" ON "ContatoHistorico"("contatoId");

-- CreateIndex
CREATE UNIQUE INDEX "Polo_plmId_key" ON "Polo"("plmId");

-- CreateIndex
CREATE UNIQUE INDEX "Vaga_unidadeEscCodigo_ano_grupamento_turno_key" ON "Vaga"("unidadeEscCodigo", "ano", "grupamento", "turno");

-- CreateIndex
CREATE UNIQUE INDEX "Processo_ano_key" ON "Processo"("ano");

-- CreateIndex
CREATE UNIQUE INDEX "Processo_prmId_key" ON "Processo"("prmId");

-- CreateIndex
CREATE UNIQUE INDEX "Pergunta_ichPergId_key" ON "Pergunta"("ichPergId");

-- CreateIndex
CREATE INDEX "Inscricao_criancaId_idx" ON "Inscricao"("criancaId");

-- CreateIndex
CREATE INDEX "Inscricao_responsavelId_idx" ON "Inscricao"("responsavelId");

-- CreateIndex
CREATE UNIQUE INDEX "Inscricao_processoId_poloId_iplId_key" ON "Inscricao"("processoId", "poloId", "iplId");

-- CreateIndex
CREATE INDEX "Opcao_unidadeEscCodigo_grupamento_turno_idx" ON "Opcao"("unidadeEscCodigo", "grupamento", "turno");

-- CreateIndex
CREATE UNIQUE INDEX "Opcao_inscricaoId_ordem_key" ON "Opcao"("inscricaoId", "ordem");

-- CreateIndex
CREATE INDEX "OfertaEvento_opcaoId_idx" ON "OfertaEvento"("opcaoId");

-- CreateIndex
CREATE UNIQUE INDEX "Resposta_inscricaoId_perguntaId_key" ON "Resposta"("inscricaoId", "perguntaId");
