import Credentials from "next-auth/providers/credentials";
import type { NextAuthConfig } from "next-auth";
import bcrypt from "bcryptjs";
import { prisma } from "@/core/db/client";
import type { PapelUsuario } from "@/core/domain/constants";

// Config isolada de src/core/auth/index.ts porque o proxy (antigo
// middleware) só pode importar bordas "leves" — sem tocar o Prisma direto
// no runtime edge. Ver node_modules/next/dist/docs sobre proxy vs edge.
export const authConfig: NextAuthConfig = {
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "E-mail", type: "email" },
        senha: { label: "Senha", type: "password" },
      },
      async authorize(credentials) {
        const email = credentials?.email;
        const senha = credentials?.senha;
        if (typeof email !== "string" || typeof senha !== "string") return null;

        const usuario = await prisma.usuario.findUnique({ where: { email } });
        if (!usuario) return null;

        const ok = await bcrypt.compare(senha, usuario.senhaHash);
        if (!ok) return null;

        return {
          id: usuario.id,
          email: usuario.email,
          name: usuario.nomeExibicao,
          papel: usuario.papel as PapelUsuario,
          responsavelId: usuario.responsavelId,
          poloId: usuario.poloId,
          unidadeEscCodigo: usuario.unidadeEscCodigo,
        };
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.papel = user.papel;
        token.responsavelId = user.responsavelId;
        token.poloId = user.poloId;
        token.unidadeEscCodigo = user.unidadeEscCodigo;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
        session.user.papel = token.papel as PapelUsuario;
        session.user.responsavelId = (token.responsavelId as string | null) ?? null;
        session.user.poloId = (token.poloId as string | null) ?? null;
        session.user.unidadeEscCodigo = (token.unidadeEscCodigo as string | null) ?? null;
      }
      return session;
    },
  },
};
