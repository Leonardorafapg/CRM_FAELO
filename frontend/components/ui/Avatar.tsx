// Mesmo padrao dos projetos de referencia (Foodapp/Simbora): a foto do
// contato do WhatsApp e uma URL externa da Evolution/WhatsApp CDN, usada
// direto num <img> — sem proxy do backend, sem <Image> do Next (URL
// arbitraria, sem loader configurado), sem onError (se a URL expirar/quebrar,
// so fica um ícone quebrado; aceitavel pro escopo atual).
export function Avatar({
  name,
  photoUrl,
  size = 40,
}: {
  name: string;
  photoUrl?: string | null;
  size?: number;
}) {
  if (photoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={photoUrl}
        alt={name}
        width={size}
        height={size}
        style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
      />
    );
  }

  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <div
      className="flex items-center justify-center rounded-full bg-accent-blue/15 font-medium text-accent-blue"
      style={{ width: size, height: size, flexShrink: 0, fontSize: size * 0.4 }}
    >
      {initial}
    </div>
  );
}
