import { redirect } from "next/navigation";
import { auth } from "@/core/auth";

export default async function PaginaMapaDemanda() {
  const session = await auth();

  if (session!.user.papel !== "GESTOR_SME") redirect("/");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-serif text-2xl text-ink">Mapa de demanda</h1>
        <p className="mt-1 text-sm text-muted">
          Compare a pressão histórica, a previsão de todas as inscrições e a pressão efetiva prevista por
          creche.
        </p>
      </div>

      <iframe
        src="/mapa-creches-2025.html"
        title="Mapa de pressão por creche"
        className="h-[calc(100vh-11rem)] min-h-[680px] w-full rounded-lg border border-line bg-white shadow-sm"
      />
    </div>
  );
}
