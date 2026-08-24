import { redirect } from "next/navigation";

// Raiz nao tem tela propria ainda — so as 3 rotas pedidas existem
// (login, register, dashboard). Login e o ponto de entrada natural.
export default function Home() {
  redirect("/login");
}
