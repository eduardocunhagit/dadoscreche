#!/usr/bin/env node
// Roda automaticamente depois de `npm install` (ver "postinstall" no
// package.json). Sem isto, criar o .env é um passo manual fácil de
// esquecer — e sem ele o login quebra com um erro genérico do Auth.js
// ("There was a problem with the server configuration") que não diz o
// que fazer. Gerar sozinho elimina essa classe inteira de problema.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const envPath = path.join(__dirname, "..", ".env");

if (fs.existsSync(envPath)) {
  console.log("[setup-env] .env já existe — nada a fazer.");
  process.exit(0);
}

const conteudo = [
  'DATABASE_URL="file:./dev.db"',
  `AUTH_SECRET="${crypto.randomBytes(32).toString("hex")}"`,
  "",
].join("\n");

fs.writeFileSync(envPath, conteudo);
console.log("[setup-env] Criado fila-viva/.env (DATABASE_URL + AUTH_SECRET gerado automaticamente).");
