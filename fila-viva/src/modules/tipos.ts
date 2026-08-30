import type { ComponentType } from "react";
import type { PapelUsuario } from "@/core/domain/constants";
import type { EventoDoBarramento, NomeEvento } from "@/core/events/bus";

// O Next.js App Router resolve rotas por arquivo, não em runtime — então um
// módulo cria sua própria página de verdade em
// src/app/(painel)/<sua-rota>/page.tsx. O que o manifesto centraliza é tudo
// que PRECISARIA editar um arquivo do núcleo se não existisse aqui: item de
// menu, widget num slot do dashboard, e assinatura de evento. Ver
// EXTENDING.md para o passo a passo com o módulo de exemplo.

export interface ItemDeMenu {
  href: string;
  label: string;
  papeis: PapelUsuario[];
}

export interface WidgetDoModulo {
  slot: string;
  component: ComponentType;
}

export interface Modulo {
  id: string;
  nome: string;
  menu?: ItemDeMenu[];
  widgets?: WidgetDoModulo[];
  assina?: Partial<{ [K in NomeEvento]: (payload: EventoDoBarramento[K]) => void | Promise<void> }>;
}
