"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useAuth } from "@/contexts/AuthContext";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import {
  Sessao,
  Mensagem,
  listSessoes,
  getMensagens,
  responder,
  encerrarAtendimento,
  whatsappWsUrl,
  ApiError,
} from "@/lib/whatsapp";

export default function AtendimentosPage() {
  const ready = useRequireAuth();
  const { user } = useAuth();
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  async function refreshSessoes() {
    if (!user) return;
    try {
      const list = await listSessoes(user.access_token);
      setSessoes(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao carregar atendimentos.");
    }
  }

  useEffect(() => {
    if (!ready || !user) return;
    refreshSessoes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (!selected || !user) return;
    getMensagens(user.access_token, selected)
      .then((list) => setMensagens(list.slice().reverse()))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar mensagens."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // WS nao passa pelo gateway (proxy do gateway e HTTP puro) — conecta
  // direto no whatsapp-service. Ver services/gateway/main.py e
  // docs/features/WHATSAPP_SERVICE.md.
  useEffect(() => {
    if (!ready || !user) return;

    const url = whatsappWsUrl(user.tenant_id, user.access_token);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "message") {
          const msg: Mensagem = payload.message;
          setSessoes((prev) => {
            const idx = prev.findIndex((s) => s.id === payload.session_id);
            if (idx === -1) {
              refreshSessoes();
              return prev;
            }
            const updated = { ...prev[idx], last_activity: msg.created_at };
            const rest = prev.filter((_, i) => i !== idx);
            return [updated, ...rest];
          });
          setMensagens((prev) =>
            payload.session_id === selected ? [...prev, msg] : prev
          );
        }
      } catch {
        // mensagem WS mal formada — ignora
      }
    };

    return () => {
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selected]);

  async function handleSend() {
    if (!user || !selected || !content.trim()) return;
    setSending(true);
    setError(null);
    try {
      const msg = await responder(user.access_token, selected, content.trim());
      setMensagens((prev) => [...prev, msg]);
      setContent("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao enviar resposta.");
    } finally {
      setSending(false);
    }
  }

  async function handleEncerrar() {
    if (!user || !selected) return;
    try {
      await encerrarAtendimento(user.access_token, selected);
      await refreshSessoes();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao encerrar atendimento.");
    }
  }

  if (!ready) return null;

  const selectedSessao = sessoes.find((s) => s.id === selected) || null;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-8">
      <div>
        <Link href="/dashboard" className="text-sm text-accent-blue hover:underline">
          ← Dashboard
        </Link>
        <h1 className="font-heading text-2xl font-bold text-text-dark">Atendimentos</h1>
      </div>

      <ErrorMessage>{error}</ErrorMessage>

      <div className="flex min-h-[60vh] gap-4">
        <div className="w-64 shrink-0 overflow-hidden rounded-xl border border-border-light bg-card-bg">
          {sessoes.length === 0 ? (
            <p className="p-4 text-sm text-text-muted">Nenhuma conversa ainda.</p>
          ) : (
            <ul>
              {sessoes.map((s) => (
                <li key={s.id}>
                  <button
                    onClick={() => setSelected(s.id)}
                    className={`w-full border-b border-border-light px-4 py-3 text-left text-sm hover:bg-page-bg ${
                      selected === s.id ? "bg-page-bg" : ""
                    }`}
                  >
                    <p className="font-medium text-text-dark">{s.contact_name || s.phone}</p>
                    <p className="text-text-muted">{s.phone}</p>
                    {!s.is_open && <p className="text-xs text-text-muted">Encerrado</p>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-1 flex-col rounded-xl border border-border-light bg-card-bg">
          {!selectedSessao ? (
            <p className="p-4 text-sm text-text-muted">Selecione uma conversa.</p>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-border-light px-4 py-3">
                <div>
                  <p className="font-medium text-text-dark">
                    {selectedSessao.contact_name || selectedSessao.phone}
                  </p>
                  <p className="text-xs text-text-muted">{selectedSessao.phone}</p>
                </div>
                {selectedSessao.is_open && (
                  <button
                    onClick={handleEncerrar}
                    className="text-sm text-red-600 hover:underline"
                  >
                    Encerrar atendimento
                  </button>
                )}
              </div>

              <div className="flex-1 space-y-2 overflow-y-auto p-4">
                {mensagens.map((m) => (
                  <div
                    key={m.id}
                    className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                      m.role === "attendant"
                        ? "ml-auto bg-accent-blue text-white"
                        : "bg-page-bg text-text-dark"
                    }`}
                  >
                    {m.content}
                  </div>
                ))}
              </div>

              <div className="flex gap-2 border-t border-border-light p-3">
                <input
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  disabled={!selectedSessao.is_open}
                  placeholder={selectedSessao.is_open ? "Digite uma resposta..." : "Atendimento encerrado"}
                  className="flex-1 rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue disabled:opacity-60"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !selectedSessao.is_open || !content.trim()}
                  className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
                >
                  Enviar
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
