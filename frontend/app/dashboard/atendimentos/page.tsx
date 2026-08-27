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
import { getCachedSessoes } from "@/lib/sessoesCache";

// Distancia (em px) do fundo da thread pra considerar "perto o suficiente" e
// auto-rolar quando chega mensagem nova — mesmo padrao do WhatsappChat.tsx
// de referencia (Foodapp/slzfood). Se o atendente rolou pra cima pra ler
// mensagem antiga, uma mensagem nova nao deve arrastar a tela sozinha.
const SCROLL_BOTTOM_THRESHOLD = 150;

function mesmoDia(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function formatHora(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// Mesmo padrao do WhatsApp: "Hoje"/"Ontem" pros dias recentes, data por
// extenso pros demais — separador exibido entre mensagens de dias diferentes.
function formatDiaSeparador(iso: string | null): string {
  if (!iso) return "";
  const data = new Date(iso);
  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(hoje.getDate() - 1);
  if (mesmoDia(data, hoje)) return "Hoje";
  if (mesmoDia(data, ontem)) return "Ontem";
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
}

// Versao curta pra lista de conversas (mesmo padrao do WhatsApp: hora se foi
// hoje, "Ontem" se foi ontem, data curta caso contrario).
function formatListaHorario(iso: string | null): string {
  if (!iso) return "";
  const data = new Date(iso);
  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(hoje.getDate() - 1);
  if (mesmoDia(data, hoje)) return formatHora(iso);
  if (mesmoDia(data, ontem)) return "Ontem";
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

export default function AtendimentosPage() {
  const ready = useRequireAuth();
  const { user } = useAuth();
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [mobileShowThread, setMobileShowThread] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
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
    // Pinta com o que o AuthContext ja deixou em voo/pronto no login (ver
    // lib/sessoesCache.ts) pra evitar tela vazia esperando uma chamada nova
    // — e sempre revalida com refreshSessoes logo em seguida.
    const cached = getCachedSessoes(user.tenant_id);
    if (cached) {
      cached.then(setSessoes).catch(() => {});
    }
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
      inputRef.current?.focus();
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
        {/* Lista de conversas — coluna fixa, com scroll proprio. Em telas
            pequenas ocupa a tela toda e some quando uma conversa e aberta
            (padrao mobile do WhatsApp: uma coluna por vez). */}
        <div
          className={`flex w-full shrink-0 flex-col overflow-hidden border-r border-border-light bg-card-bg sm:w-72 ${
            mobileShowThread ? "hidden sm:flex" : "flex"
          }`}
        >
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
                      onClick={() => {
                        setSelected(s.id);
                        setMobileShowThread(true);
                      }}
                      className={`flex w-full items-center gap-3 border-b border-border-light px-4 py-3 text-left text-sm hover:bg-page-bg ${
                        selected === s.id ? "bg-page-bg" : ""
                      }`}
                    >
                      <Avatar name={s.contact_name || s.phone} photoUrl={s.foto_url} size={40} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-text-dark">{s.contact_name || s.phone}</p>
                        {s.contact_name && <p className="truncate text-xs text-text-muted">{s.phone}</p>}
                        {!s.is_open && <p className="text-xs text-text-muted">Encerrado</p>}
                      </div>
                      <span className="shrink-0 self-start whitespace-nowrap text-xs text-text-muted">
                        {formatListaHorario(s.last_activity)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Thread — coluna flexivel: header e campo de envio fixos, so as
            mensagens rolam. Em telas pequenas so aparece depois que uma
            conversa e selecionada (ver mobileShowThread acima). */}
        <div
          className={`flex-1 flex-col overflow-hidden bg-page-bg ${
            mobileShowThread ? "flex" : "hidden sm:flex"
          }`}
        >
          {!selectedSessao ? (
            <div className="flex flex-1 items-center justify-center text-sm text-text-muted">
              Selecione uma conversa.
            </div>
          ) : (
            <>
              <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border-light bg-card-bg px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <button
                    onClick={() => setMobileShowThread(false)}
                    className="shrink-0 text-text-muted hover:text-text-dark sm:hidden"
                    aria-label="Voltar para a lista"
                  >
                    ←
                  </button>
                  <Avatar
                    name={selectedSessao.contact_name || selectedSessao.phone}
                    photoUrl={selectedSessao.foto_url}
                    size={40}
                  />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text-dark">
                      {selectedSessao.contact_name || selectedSessao.phone}
                    </p>
                    {selectedSessao.contact_name && (
                      <p className="truncate text-xs text-text-muted">{selectedSessao.phone}</p>
                    )}
                  </div>
                </div>
                {selectedSessao.is_open && (
                  <button
                    onClick={handleEncerrar}
                    className="shrink-0 text-sm text-red-600 hover:underline"
                  >
                    Encerrar atendimento
                  </button>
                )}
              </div>

              <div
                ref={threadRef}
                onScroll={handleScrollThread}
                className="flex-1 space-y-1.5 overflow-y-auto overflow-x-hidden p-3 sm:p-4"
              >
                {mensagens.map((m, i) => {
                  const anterior = mensagens[i - 1];
                  const mostraSeparador =
                    m.created_at &&
                    (!anterior?.created_at || !mesmoDia(new Date(m.created_at), new Date(anterior.created_at)));

                  return (
                    <div key={m.id}>
                      {mostraSeparador && (
                        <div className="my-3 flex justify-center">
                          <span className="rounded-full bg-card-bg px-3 py-1 text-xs text-text-muted shadow-sm">
                            {formatDiaSeparador(m.created_at)}
                          </span>
                        </div>
                      )}
                      <div
                        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed sm:max-w-[70%] ${
                          m.role === "attendant"
                            ? "ml-auto bg-accent-blue text-white"
                            : "bg-card-bg text-text-dark"
                        }`}
                      >
                        <p className="whitespace-pre-wrap break-words">{m.content}</p>
                        <p
                          className={`mt-1 text-right text-[10px] ${
                            m.role === "attendant" ? "text-white/70" : "text-text-muted"
                          }`}
                        >
                          {formatHora(m.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={endRef} />
              </div>

              <div className="flex shrink-0 gap-2 border-t border-border-light bg-card-bg p-2.5 sm:p-3">
                <input
                  ref={inputRef}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  disabled={!selectedSessao.is_open}
                  placeholder={selectedSessao.is_open ? "Digite uma resposta..." : "Atendimento encerrado"}
                  className="min-w-0 flex-1 rounded-lg border border-border-light bg-page-bg px-3 py-2 text-sm text-text-dark outline-none focus:border-accent-blue disabled:opacity-60"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !selectedSessao.is_open || !content.trim()}
                  className="shrink-0 rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
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
