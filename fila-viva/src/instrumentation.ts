export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { registrarAssinaturas } = await import("@/modules/registry");
    registrarAssinaturas();
  }
}
