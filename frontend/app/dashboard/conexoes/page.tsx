"use client";

import { useEffect, useRef, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { isAdminOrOwner, useAuth } from "@/contexts/AuthContext";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { IconDevice } from "@/components/layout/icons";
import {
  Connection,
  listConnections,
  createConnection,
  deleteConnection,
  ApiError,
} from "@/lib/whatsapp";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function ConexoesPage() {
  const ready = useRequireAuth();
  const { user } = useAuth();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [qrcode, setQrcode] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const authorized = isAdminOrOwner(user ?? null);

  async function refresh() {
    if (!user) return;
    try {
      const list = await listConnections(user.access_token);
      setConnections(list);
      return list;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao carregar conexões.");
    }
  }

  useEffect(() => {
    if (!ready || !authorized || !user) return;
    setLoading(true);
    refresh().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authorized]);

  // Polling em GET /connections a cada ~3s enquanto houver alguma conexao
  // "connecting" — para automaticamente quando todas ficarem connected.
  useEffect(() => {
    if (!ready || !authorized || !user) return;

    const hasConnecting = connections.some((c) => c.status === "connecting");
    if (!hasConnecting) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    pollRef.current = setInterval(async () => {
      const list = await refresh();
      if (list && !list.some((c) => c.status === "connecting")) {
        setQrcode(null);
      }
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connections, ready, authorized]);

  async function handleConnect() {
    if (!user) return;
    setCreating(true);
    setError(null);
    try {
      const result = await createConnection(user.access_token);
      setQrcode(result.qrcode_base64);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao criar conexão.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!user) return;
    try {
      await deleteConnection(user.access_token, id);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao excluir conexão.");
    }
  }

  if (!ready) return null;

  if (!authorized) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-8">
        <p className="text-text-muted">Apenas administradores podem gerenciar conexões.</p>
      </main>
    );
  }

  const connected = connections.filter((c) => c.status === "connected").length;
  const connecting = connections.filter((c) => c.status === "connecting").length;
  const disconnected = connections.filter((c) => c.status === "disconnected").length;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-dark">Conexões</h1>
          <p className="mt-1 text-sm text-text-muted">Gerencie suas conexões de WhatsApp</p>
        </div>
        <button
          type="button"
          onClick={handleConnect}
          disabled={creating}
          className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {creating ? "Gerando QR code..." : "+ Nova Conexão"}
        </button>
      </div>

      <ErrorMessage>{error}</ErrorMessage>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Conectadas" value={connected} dotColor="bg-green-500" />
        <StatCard label="Conectando" value={connecting} dotColor="bg-amber-500" />
        <StatCard label="Desconectadas" value={disconnected} dotColor="bg-red-500" />
      </div>

      {qrcode && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-border-light bg-card-bg p-6">
          <p className="text-sm text-text-muted">
            Escaneie o QR code no WhatsApp (Aparelhos conectados → Conectar aparelho).
          </p>
          <img
            src={qrcode}
            alt="QR code de conexão do WhatsApp"
            className="h-64 w-64 rounded-lg border border-border-light"
          />
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-border-light bg-card-bg">
        <table className="w-full text-left text-sm">
          <thead className="text-[11px] uppercase tracking-wide text-text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Conexão</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Criada em</th>
              <th className="px-4 py-3 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-text-muted">
                  Carregando...
                </td>
              </tr>
            ) : connections.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-14">
                  <div className="flex flex-col items-center gap-3 text-center">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border-light text-text-muted">
                      <IconDevice width={20} height={20} />
                    </span>
                    <div>
                      <p className="font-medium text-text-dark">Nenhuma conexão encontrada</p>
                      <p className="text-sm text-text-muted">Clique em + Nova Conexão para começar</p>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              connections.map((c) => (
                <tr key={c.id} className="border-t border-border-light">
                  <td className="px-4 py-3">
                    <p className="text-text-dark">{c.instance_name}</p>
                    <p className="text-xs text-text-muted">{c.phone || "Aguardando conexão"}</p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-text-muted">{formatDate(c.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function StatCard({ label, value, dotColor }: { label: string; value: number; dotColor: string }) {
  return (
    <div className="rounded-xl border border-border-light bg-card-bg p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-muted">{label}</p>
        <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} />
      </div>
      <p className="mt-2 text-3xl font-bold text-text-dark">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: Connection["status"] }) {
  const labels: Record<Connection["status"], string> = {
    connecting: "Conectando",
    connected: "Conectado",
    disconnected: "Desconectado",
  };
  const styles: Record<Connection["status"], string> = {
    connecting: "bg-amber-100 text-amber-700",
    connected: "bg-green-100 text-green-700",
    disconnected: "bg-red-100 text-red-700",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[status]}`}>{labels[status]}</span>
  );
}
