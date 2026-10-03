import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Briefcase,
  Building2,
  Check,
  ChevronRight,
  Clock,
  FileCheck,
  GraduationCap,
  House,
  IdCard,
  MapPin,
  MessageSquare,
  Pin,
  PinOff,
  Plane,
  Plus,
  Search,
  Sparkles,
  Stethoscope,
  Trash2,
  Wallet,
} from "lucide-react";

// One registry for every icon in the app: change a glyph here and it changes everywhere.
const ICONS = {
  // brand + assistant
  logo: FileCheck,
  spark: Sparkles,
  // categories (match `icon` in the categories list)
  education: GraduationCap,
  health: Stethoscope,
  travel: Plane,
  public: IdCard,
  career: Briefcase,
  business: Building2,
  daily: House,
  // actions + navigation
  search: Search,
  send: ArrowUp,
  go: ArrowRight,
  back: ArrowLeft,
  next: ChevronRight,
  plus: Plus,
  check: Check,
  pin: Pin,
  unpin: PinOff,
  trash: Trash2,
  chat: MessageSquare,
  // details
  location: MapPin,
  cost: Wallet,
  time: Clock,
};

// Shared defaults keep size and stroke consistent; override `size` per spot when needed.
export function Icon({ name, size = 18, strokeWidth = 2, className = "", ...props }) {
  const Glyph = ICONS[name];
  if (!Glyph) return null;
  return (
    <Glyph
      size={size}
      strokeWidth={strokeWidth}
      className={`icon ${className}`.trim()}
      aria-hidden="true"
      focusable="false"
      {...props}
    />
  );
}
