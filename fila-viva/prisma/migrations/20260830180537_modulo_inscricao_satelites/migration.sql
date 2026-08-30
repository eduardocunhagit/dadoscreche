-- CreateTable
CREATE TABLE "InscPerfilInscricao" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "inscricaoId" TEXT NOT NULL,
    "cpfCrianca" TEXT NOT NULL,
    "cpfResponsavel" TEXT NOT NULL,
    "cepResidencia" TEXT NOT NULL,
    "logradouroResidencia" TEXT,
    "bairroResidencia" TEXT,
    "latResidencia" REAL,
    "lonResidencia" REAL,
    "origemGeoResidencia" TEXT NOT NULL,
    "cepTrabalho" TEXT,
    "logradouroTrabalho" TEXT,
    "bairroTrabalho" TEXT,
    "latTrabalho" REAL,
    "lonTrabalho" REAL,
    "origemGeoTrabalho" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "InscPerfilInscricao_inscricaoId_fkey" FOREIGN KEY ("inscricaoId") REFERENCES "Inscricao" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "InscContextoSeguranca" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "inscricaoId" TEXT NOT NULL,
    "areaSobInfluencia" BOOLEAN NOT NULL,
    "faccaoRelatada" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "InscContextoSeguranca_inscricaoId_fkey" FOREIGN KEY ("inscricaoId") REFERENCES "Inscricao" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "InscUnidadeGeo" (
    "unidadeEscCodigo" TEXT NOT NULL PRIMARY KEY,
    "latitude" REAL NOT NULL,
    "longitude" REAL NOT NULL,
    "plmId" INTEGER,
    "origem" TEXT NOT NULL,
    "atualizadoEm" DATETIME NOT NULL,
    CONSTRAINT "InscUnidadeGeo_unidadeEscCodigo_fkey" FOREIGN KEY ("unidadeEscCodigo") REFERENCES "Unidade" ("escCodigo") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "InscDemandaPrevista" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "unidadeEscCodigo" TEXT NOT NULL,
    "ano" INTEGER NOT NULL,
    "fonte" TEXT NOT NULL,
    "classe" TEXT NOT NULL,
    "valor" REAL,
    "importadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "InscDemandaPrevista_unidadeEscCodigo_fkey" FOREIGN KEY ("unidadeEscCodigo") REFERENCES "Unidade" ("escCodigo") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "InscPerfilInscricao_inscricaoId_key" ON "InscPerfilInscricao"("inscricaoId");

-- CreateIndex
CREATE UNIQUE INDEX "InscContextoSeguranca_inscricaoId_key" ON "InscContextoSeguranca"("inscricaoId");

-- CreateIndex
CREATE UNIQUE INDEX "InscDemandaPrevista_unidadeEscCodigo_ano_fonte_key" ON "InscDemandaPrevista"("unidadeEscCodigo", "ano", "fonte");
