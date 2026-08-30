-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Processo" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "ano" INTEGER NOT NULL,
    "prmId" INTEGER NOT NULL,
    "nome" TEXT NOT NULL,
    "liberacaoEmCascata" BOOLEAN NOT NULL DEFAULT false,
    "aceiteCondicional" BOOLEAN NOT NULL DEFAULT false,
    "janelaCondicionalDias" INTEGER NOT NULL DEFAULT 30
);
INSERT INTO "new_Processo" ("ano", "id", "nome", "prmId") SELECT "ano", "id", "nome", "prmId" FROM "Processo";
DROP TABLE "Processo";
ALTER TABLE "new_Processo" RENAME TO "Processo";
CREATE UNIQUE INDEX "Processo_ano_key" ON "Processo"("ano");
CREATE UNIQUE INDEX "Processo_prmId_key" ON "Processo"("prmId");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
