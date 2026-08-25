import { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

type ContactFormProps = {
  name: string;
  setName: (v: string) => void;
  phone: string;
  setPhone: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  tags: string;
  setTags: (v: string) => void;
  saving: boolean;
  error: string | null;
  onSubmit: (e: FormEvent) => void;
};

/** Formulário de criação de cliente — usado na tela de Clientes. Só
 * name/phone/email/tags nesta fase (ver docs/features/CLIENTES_ESTAGIOS.md,
 * "sem campos extras"). */
export function ContactForm({
  name,
  setName,
  phone,
  setPhone,
  email,
  setEmail,
  tags,
  setTags,
  saving,
  error,
  onSubmit,
}: ContactFormProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-xl border border-border-light bg-card-bg p-4"
    >
      <Input id="name" label="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
      <Input id="phone" label="Telefone" value={phone} onChange={(e) => setPhone(e.target.value)} required />
      <Input id="email" label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input
        id="tags"
        label="Tags (separadas por vírgula)"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
      />
      <ErrorMessage>{error}</ErrorMessage>
      <Button type="submit" loading={saving} loadingText="Salvando...">
        Salvar cliente
      </Button>
    </form>
  );
}
