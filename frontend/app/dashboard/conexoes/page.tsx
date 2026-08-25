"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import {
  Connection,
  listConnections,
  createConnection,
  deleteConnection,
  ApiError,
} from "@/lib/whatsapp";

// Sem helper pronto de "e admin/owner?" no projeto — replica aqui a mesma
// checagem simples usada em outras telas restritas.
function isAdminOrOwner(user: { role: string; is_admin: boolean } | null): boolean {
  if (!user) return false;
  return user.is_admin || user.role === "owner" || user.role === "admin";
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
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 px-4 py-8">
        <Link href="/dashboard" className="text-sm text-accent-blue hover:underline">
          ← Dashboard
        </Link>
        <p className="text-text-muted">Apenas administradores podem gerenciar conexões.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard" className="text-sm text-accent-blue hover:underline">
            ← Dashboard
          </Link>
          <h1 className="font-heading text-2xl font-bold text-text-dark">Conexões</h1>
        </div>
        <Button onClick={handleConnect} loading={creating} loadingText="Gerando QR code...">
          Conectar
        </Button>
      </div>

      <ErrorMessage>{error}</ErrorMessage>

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

      {loading ? (
        <p className="text-text-muted">Carregando...</p>
      ) : connections.length === 0 ? (
        <p className="text-text-muted">Nenhuma conexão cadastrada ainda.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border-light bg-card-bg">
          <table className="w-full text-left text-sm">
            <thead className="bg-page-bg text-text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Instância</th>
                <th className="px-4 py-2 font-medium">Telefone</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {connections.map((c) => (
                <tr key={c.id} className="border-t border-border-light">
                  <td className="px-4 py-2 text-text-dark">{c.instance_name}</td>
                  <td className="px-4 py-2 text-text-muted">{c.phone || "—"}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

function StatusBadge({ status }: { status: Connection["status"] }) {
  const labels: Record<Connection["status"], string> = {
    connecting: "Conectando",
    connected: "Conectado",
    disconnected: "Desconectado",
  };
  const colors: Record<Connection["status"], string> = {
    connecting: "text-amber-600",
    connected: "text-green-600",
    disconnected: "text-text-muted",
  };
  return <span className={colors[status]}>{labels[status]}</span>;
}
