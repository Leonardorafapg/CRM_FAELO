// Barrel: mantem "@/lib/api" como o import unico usado pelo resto do
// frontend, mesmo com o cliente dividido em client/auth/crm por dominio.
export * from "./client";
export * from "./auth";
export * from "./crm";
