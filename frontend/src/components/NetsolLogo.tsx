type Props = {
  size?: number;
  fill?: string;
  glyphFill?: string;
  className?: string;
};

export default function NetsolLogo({ size = 28, className }: Props) {
  return (
    <img
      src="/netbot-logo.png"
      alt=""
      width={size}
      height={size}
      className={`netbot-logo ${className ?? ""}`.trim()}
      style={{ width: size, height: size }}
      draggable={false}
    />
  );
}
