"use server";

import { signOut } from "@/core/auth";

export async function sair() {
  await signOut({ redirectTo: "/login" });
}
