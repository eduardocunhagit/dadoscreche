# Fila Viva

Ferramenta que auxilia a Secretaria da Educação na gestão das matrículas de creches e educação infantil.

## Para abrir a ferramenta no seu computador

Clonar o repositório no GitHub:

```
git clone https://github.com/eduardocunhagit/dadoscreche.git
cd dadoscreche/fila-viva
```

Para abrir o site é necessário ter Node.js versão 20 ou mais nova.

Caso você não tenha, baixe em **nodejs.org** (botão da versão LTS) — ou, no Windows, digite `winget install OpenJS.NodeJS.LTS` no Prompt de Comando e feche/abra o terminal de novo depois.

Após isso, rode esses 3 comandos no terminal (CMD, PowerShell ou Terminal):

```
npm install
npm run setup
npm run dev
```

Depois disso, é só abrir o site digitando http://localhost:3000/login no seu navegador.

Contas de demonstração (senha `demo1234` para todas):

| E-mail | Papel | Escopo |
| --- | --- | --- |
| `gestor@filaviva.rio` | Gestor SME | Rede inteira |
| `cre1@filaviva.rio` | Servidor da CRE | Polo 1 (CRE 1) |
| `unidade@filaviva.rio` | Servidor da unidade | Uma unidade específica |
| `responsavel@filaviva.rio` | Responsável | As próprias crianças |

## Quer adicionar uma funcionalidade?

Leia o `EXTENDING.md` antes de mexer no código — é o guia de como acrescentar algo sem esbarrar no que já está pronto.
