export interface EstadoAcaoMensagens {
  ok: boolean;
  mensagem: string;
}

export const ESTADO_INICIAL_MENSAGENS: EstadoAcaoMensagens = {
  ok: false,
  mensagem: "",
};
