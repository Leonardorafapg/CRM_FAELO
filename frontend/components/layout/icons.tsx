import { SVGProps } from "react";

/** Ícones de linha simples (sem lib externa) — mesmo estilo outline usado
 * na referência de sidebar (stroke fino, sem preenchimento). */
function Icon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      width={18}
      height={18}
      {...props}
    />
  );
}

export function IconDashboard(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h5v-6h4v6h5V9.5" />
    </Icon>
  );
}

export function IconUsers(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M2 21v-1c0-2.8 3.1-5 7-5s7 2.2 7 5v1" />
      <path d="M16 5.2a3 3 0 0 1 0 5.6" />
      <path d="M22 21v-1c0-2.1-1.7-4-4.3-4.7" />
    </Icon>
  );
}

export function IconKanban(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <rect x="3" y="4" width="5.5" height="16" rx="1" />
      <rect x="9.5" y="4" width="5.5" height="10" rx="1" />
      <rect x="16" y="4" width="5" height="7" rx="1" />
    </Icon>
  );
}

export function IconPlug(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M9 2v6" />
      <path d="M15 2v6" />
      <path d="M6 8h12l-.7 4.7a4.5 4.5 0 0 1-4.4 3.8h-1.8a4.5 4.5 0 0 1-4.4-3.8z" />
      <path d="M12 16.5V21" />
    </Icon>
  );
}

export function IconChat(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M21 11.5a8.4 8.4 0 0 1-4.6 7.6 8.4 8.4 0 0 1-8.2-.2L3 21l1.9-5.2A8.4 8.4 0 1 1 21 11.5z" />
    </Icon>
  );
}

export function IconSun(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Icon>
  );
}

export function IconMoon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </Icon>
  );
}

export function IconLogout(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </Icon>
  );
}
