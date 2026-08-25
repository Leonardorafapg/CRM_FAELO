"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useAuth } from "@/contexts/AuthContext";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Avatar } from "@/components/ui/Avatar";
import { BackLink } from "@/components/ui/BackLink";
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

// Distancia (em px) do fundo da thread pra considerar "perto o suficiente" e
// auto-rolar quando chega mensagem nova — mesmo padrao do WhatsappChat.tsx
// de referencia (Foodapp/slzfood). Se o atendente rolou pra cima pra ler
// mensagem antiga, uma mensagem nova nao deve arrastar a tela sozinha.
const SCROLL_BOTTOM_THRESHOLD = 150;

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
  const threadRef = useRef<HTMLDivElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const pertoDoFundoRef = useRef(true);

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
    pertoDoFundoRef.current = true;
    getMensagens(user.access_token, selected)
      .then((list) => setMensagens(list.slice().reverse()))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar mensagens."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // Auto-scroll so quando o atendente ja estava perto do fim — mesmo
  // motivo do threshold acima.
  useEffect(() => {
    if (pertoDoFundoRef.current) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [mensagens]);

  const handleScrollThread = useCallback(() => {
    const el = threadRef.current;
    if (!el) return;
    const distanciaDoFim = el.scrollHeight - el.scrollTop - el.clientHeight;
    pertoDoFundoRef.current = distanciaDoFim < SCROLL_BOTTOM_THRESHOLD;
  }, []);

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
          if (payload.session_id === selected) {
            pertoDoFundoRef.current = true; // mensagem na conversa aberta sempre desce
            setMensagens((prev) => [...prev, msg]);
          }
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
      pertoDoFundoRef.current = true;
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
    <div className="flex h-full flex-col overflow-hidden">
      {error && (
        <div className="shrink-0 px-4 pt-3">
          <ErrorMessage>{error}</ErrorMessage>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Lista de conversas — coluna fixa, com scroll proprio */}
        <div className="flex w-72 shrink-0 flex-col overflow-hidden border-r border-border-light bg-card-bg">
          <div className="shrink-0 border-b border-border-light px-4 py-3">
            <BackLink href="/dashboard">← Dashboard</BackLink>
            <h1 className="mt-1 font-heading text-lg font-bold text-text-dark">Atendimentos</h1>
          </div>

          <div className="flex-1 overflow-y-auto">
            {sessoes.length === 0 ? (
              <p className="p-4 text-sm text-text-muted">Nenhuma conversa ainda.</p>
            ) : (
              <ul>
                {sessoes.map((s) => (
                  <li key={s.id}>
                    <button
                      onClick={() => setSelected(s.id)}
                      className={`flex w-full items-center gap-3 border-b border-border-light px-4 py-3 text-left text-sm hover:bg-page-bg ${
                        selected === s.id ? "bg-page-bg" : ""
                      }`}
                    >
                      <Avatar name={s.contact_name || s.phone} photoUrl={s.foto_url} size={36} />
                      <div className="min-w-0">
                        <p className="truncate font-medium text-text-dark">{s.contact_name || s.phone}</p>
                        <p className="truncate text-text-muted">{s.phone}</p>
                        {!s.is_open && <p className="text-xs text-text-muted">Encerrado</p>}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Thread — coluna flexivel: header e campo de envio fixos, so as
            mensagens rolam. */}
        <div className="flex flex-1 flex-col overflow-hidden bg-page-bg">
          {!selectedSessao ? (
            <div className="flex flex-1 items-center justify-center text-sm text-text-muted">
              Selecione uma conversa.
            </div>
          ) : (
            <>
              <div className="flex shrink-0 items-center justify-between border-b border-border-light bg-card-bg px-4 py-3">
                <div className="flex items-center gap-3">
                  <Avatar
                    name={selectedSessao.contact_name || selectedSessao.phone}
                    photoUrl={selectedSessao.foto_url}
                    size={36}
                  />
                  <div>
                    <p className="font-medium text-text-dark">
                      {selectedSessao.contact_name || selectedSessao.phone}
                    </p>
                    <p className="text-xs text-text-muted">{selectedSessao.phone}</p>
                  </div>
                </div>
                {selectedSessao.is_open && (
                  <button onClick={handleEncerrar} className="text-sm text-red-600 hover:underline">
                    Encerrar atendimento
                  </button>
                )}
              </div>

              <div
                ref={threadRef}
                onScroll={handleScrollThread}
                className="flex-1 space-y-2 overflow-y-auto p-4"
              >
                {mensagens.map((m) => (
                  <div
                    key={m.id}
                    className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                      m.role === "attendant"
                        ? "ml-auto bg-accent-blue text-white"
                        : "bg-card-bg text-text-dark"
                    }`}
                  >
                    {m.content}
                  </div>
                ))}
                <div ref={endRef} />
              </div>

              <div className="flex shrink-0 gap-2 border-t border-border-light bg-card-bg p-3">
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
    </div>
  );
}
