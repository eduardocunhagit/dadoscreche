"use client";

import { useState } from "react";
import { Botao } from "@/core/ui/Button";
import { Campo, CampoSelect, Rotulo } from "@/core/ui/Input";
import { Cartao, CartaoCorpo } from "@/core/ui/Card";
import { cpfValido } from "@/modules/inscricao/dominio/cpf";
import type { EnderecoGeocodificado } from "@/modules/inscricao";
import { actionGeocodificarCep } from "./actions";

interface BuscaEnderecoProps {
  titulo: string;
  obrigatorio: boolean;
  endereco: EnderecoGeocodificado | null;
  onEnderecoChange: (endereco: EnderecoGeocodificado | null) => void;
  bairros: { bairro: string; latitude: number; longitude: number }[];
}

function BuscaEndereco({ titulo, obrigatorio, endereco, onEnderecoChange, bairros }: BuscaEnderecoProps) {
  const [cepTexto, setCepTexto] = useState(endereco?.cep ?? "");
  const [buscando, setBuscando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const precisaEscolherBairro =
    endereco !== null && (endereco.origem === "INDISPONIVEL" || endereco.latitude === undefined);

  async function buscar() {
    const cepLimpo = cepTexto.replace(/\D/g, "");
    if (cepLimpo.length !== 8) {
      setErro("CEP inválido — precisa ter 8 dígitos.");
      return;
    }
    setBuscando(true);
    setErro(null);
    try {
      const resultado = await actionGeocodificarCep(cepLimpo);
      onEnderecoChange(resultado);
    } catch {
      setErro("Não foi possível consultar o CEP agora. Tente novamente.");
    } finally {
      setBuscando(false);
    }
  }

  function escolherBairro(nomeBairro: string) {
    const encontrado = bairros.find((b) => b.bairro === nomeBairro);
    if (!encontrado) return;
    onEnderecoChange({
      cep: endereco?.cep ?? cepTexto.replace(/\D/g, ""),
      bairro: encontrado.bairro,
      latitude: encontrado.latitude,
      longitude: encontrado.longitude,
      origem: "CENTROIDE_BAIRRO",
    });
  }

  return (
    <div className="space-y-2">
      <Rotulo>
        {titulo}
        {obrigatorio ? "" : " (opcional)"}
        <span className="ml-1 font-normal normal-case tracking-normal text-faint">
          (após digitar o CEP, clique em Buscar)
        </span>
      </Rotulo>
      <div className="flex gap-2">
        <Campo
          value={cepTexto}
          onChange={(e) => setCepTexto(e.target.value)}
          placeholder="00000-000"
          className="max-w-[160px]"
        />
        <Botao type="button" variante="secundaria" onClick={buscar} disabled={buscando}>
          {buscando ? "Buscando..." : "Buscar"}
        </Botao>
      </div>
      {erro && <p className="text-sm text-bad">{erro}</p>}
      {endereco && !precisaEscolherBairro && (
        <p className="text-sm text-muted">
          {[endereco.logradouro, endereco.bairro].filter(Boolean).join(", ") || "Endereço localizado."}
        </p>
      )}
      {precisaEscolherBairro && (
        <div>
          <p className="text-sm text-warn">
            Não foi possível localizar automaticamente pelo CEP. Selecione o bairro mais próximo:
          </p>
          <CampoSelect className="mt-1" defaultValue="" onChange={(e) => escolherBairro(e.target.value)}>
            <option value="" disabled>
              Selecione um bairro
            </option>
            {bairros.map((b) => (
              <option key={b.bairro} value={b.bairro}>
                {b.bairro}
              </option>
            ))}
          </CampoSelect>
        </div>
      )}
    </div>
  );
}

interface PassoIdentificacaoProps {
  cpfCrianca: string;
  onCpfCriancaChange: (valor: string) => void;
  cpfResponsavel: string;
  onCpfResponsavelChange: (valor: string) => void;
  enderecoResidencia: EnderecoGeocodificado | null;
  onEnderecoResidenciaChange: (endereco: EnderecoGeocodificado | null) => void;
  enderecoTrabalho: EnderecoGeocodificado | null;
  onEnderecoTrabalhoChange: (endereco: EnderecoGeocodificado | null) => void;
  areaSobInfluencia: boolean | null;
  onAreaSobInfluenciaChange: (valor: boolean) => void;
  faccaoRelatada: string;
  onFaccaoRelatadaChange: (valor: string) => void;
  bairros: { bairro: string; latitude: number; longitude: number }[];
}

export function PassoIdentificacao({
  cpfCrianca,
  onCpfCriancaChange,
  cpfResponsavel,
  onCpfResponsavelChange,
  enderecoResidencia,
  onEnderecoResidenciaChange,
  enderecoTrabalho,
  onEnderecoTrabalhoChange,
  areaSobInfluencia,
  onAreaSobInfluenciaChange,
  faccaoRelatada,
  onFaccaoRelatadaChange,
  bairros,
}: PassoIdentificacaoProps) {
  const [erroCpfCrianca, setErroCpfCrianca] = useState(false);
  const [erroCpfResponsavel, setErroCpfResponsavel] = useState(false);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Rotulo htmlFor="cpfCrianca">CPF da criança</Rotulo>
          <Campo
            id="cpfCrianca"
            value={cpfCrianca}
            onChange={(e) => onCpfCriancaChange(e.target.value)}
            onBlur={() => setErroCpfCrianca(cpfCrianca.length > 0 && !cpfValido(cpfCrianca))}
            placeholder="000.000.000-00"
          />
          {erroCpfCrianca && <p className="mt-1 text-sm text-bad">CPF inválido.</p>}
        </div>
        <div>
          <Rotulo htmlFor="cpfResponsavel">CPF do responsável</Rotulo>
          <Campo
            id="cpfResponsavel"
            value={cpfResponsavel}
            onChange={(e) => onCpfResponsavelChange(e.target.value)}
            onBlur={() => setErroCpfResponsavel(cpfResponsavel.length > 0 && !cpfValido(cpfResponsavel))}
            placeholder="000.000.000-00"
          />
          {erroCpfResponsavel && <p className="mt-1 text-sm text-bad">CPF inválido.</p>}
        </div>
      </div>

      <BuscaEndereco
        titulo="CEP de residência"
        obrigatorio
        endereco={enderecoResidencia}
        onEnderecoChange={onEnderecoResidenciaChange}
        bairros={bairros}
      />

      <BuscaEndereco
        titulo="CEP de trabalho"
        obrigatorio={false}
        endereco={enderecoTrabalho}
        onEnderecoChange={onEnderecoTrabalhoChange}
        bairros={bairros}
      />

      <Cartao className="border-warn/40">
        <CartaoCorpo className="space-y-3">
          <p className="text-sm font-medium text-ink">
            Você vive em área sob influência ou controle de crime organizado?
          </p>
          <div className="flex gap-4 text-sm text-ink-2">
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="area-influencia"
                checked={areaSobInfluencia === true}
                onChange={() => onAreaSobInfluenciaChange(true)}
              />
              Sim
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="area-influencia"
                checked={areaSobInfluencia === false}
                onChange={() => onAreaSobInfluenciaChange(false)}
              />
              Não
            </label>
          </div>

          {areaSobInfluencia === true && (
            <div className="space-y-2">
              <div>
                <Rotulo htmlFor="faccaoRelatada">Se se sentir confortável, qual facção/grupo? (opcional)</Rotulo>
                <Campo
                  id="faccaoRelatada"
                  value={faccaoRelatada}
                  onChange={(e) => onFaccaoRelatadaChange(e.target.value)}
                />
              </div>
              <div className="rounded-md bg-warn-soft p-3 text-xs text-ink-2">
                Esta informação é confidencial: nunca será divulgada nem compartilhada. É usada apenas
                como referência para orientar a escolha de creches mais convenientes e seguras para a
                sua família.
              </div>
            </div>
          )}
        </CartaoCorpo>
      </Cartao>
    </div>
  );
}
