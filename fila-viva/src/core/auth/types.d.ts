import type { PapelUsuario } from "@/core/domain/constants";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      papel: PapelUsuario;
      responsavelId: string | null;
      poloId: string | null;
      unidadeEscCodigo: string | null;
      name?: string | null;
      email?: string | null;
    };
  }

  interface User {
    papel: PapelUsuario;
    responsavelId: string | null;
    poloId: string | null;
    unidadeEscCodigo: string | null;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    papel?: PapelUsuario;
    responsavelId?: string | null;
    poloId?: string | null;
    unidadeEscCodigo?: string | null;
  }
}
