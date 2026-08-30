-- CreateTable
CREATE TABLE "msg_conversa" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "criancaId" TEXT NOT NULL,
    "contatoId" TEXT NOT NULL,
    "nomeContato" TEXT NOT NULL,
    "telefone" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'ENVIADA',
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "msg_mensagem" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "conversaId" TEXT NOT NULL,
    "direcao" TEXT NOT NULL,
    "conteudo" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "autorUsuarioId" TEXT,
    "classificacao" TEXT,
    "sugestaoResposta" TEXT,
    "criadaEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "msg_mensagem_conversaId_fkey" FOREIGN KEY ("conversaId") REFERENCES "msg_conversa" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "msg_conversa_criancaId_idx" ON "msg_conversa"("criancaId");

-- CreateIndex
CREATE UNIQUE INDEX "msg_conversa_criancaId_contatoId_key" ON "msg_conversa"("criancaId", "contatoId");

-- CreateIndex
CREATE INDEX "msg_mensagem_conversaId_criadaEm_idx" ON "msg_mensagem"("conversaId", "criadaEm");
