import type { SVGProps } from "react";

const base = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

export const PlusIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    <path d="M8 3v10M3 8h10" />
  </svg>
);

export const CloseIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    <path d="m4 4 8 8M12 4l-8 8" />
  </svg>
);

export const SendIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    <path d="M2.5 8 13.5 2.5 10 13.5 7.5 9 2.5 8Z" />
    <path d="m7.5 9 3-3" />
  </svg>
);

export const LogOutIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    <path d="M6.5 2.5h-3v11h3M10 5l3 3-3 3M13 8H6.5" />
  </svg>
);

export const SparkIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    <path d="M8 2v3M8 11v3M2 8h3M11 8h3M4.2 4.2l1.6 1.6M10.2 10.2l1.6 1.6M11.8 4.2l-1.6 1.6M5.8 10.2l-1.6 1.6" />
  </svg>
);

export const BoardMark = (props: SVGProps<SVGSVGElement>) => (
  <svg
    width={28}
    height={28}
    viewBox="0 0 28 28"
    fill="none"
    aria-hidden
    {...props}
  >
    <rect width="28" height="28" rx="7" fill="var(--accent)" />
    <rect x="6" y="7" width="4.5" height="14" rx="1.5" fill="#fff" />
    <rect x="11.75" y="7" width="4.5" height="9" rx="1.5" fill="#fff" fillOpacity=".85" />
    <rect x="17.5" y="7" width="4.5" height="11.5" rx="1.5" fill="#fff" fillOpacity=".7" />
  </svg>
);
