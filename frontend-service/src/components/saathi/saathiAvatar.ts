/**
 * Utility for generating reliable, vibrant customer avatars in Saathi.
 * Uses inline CSS linear-gradients to prevent Tailwind dynamic class purging.
 */

export interface CustomerAvatarMeta {
  initials: string;
  gradient: string;
  ring: string;
  accentDot: string;
}

export function getCustomerAvatar(customer: {
  id?: string;
  name: string;
  tier?: string;
}): CustomerAvatarMeta {
  if (!customer || !customer.name) {
    return {
      initials: 'CU',
      gradient: 'linear-gradient(135deg, #64748b 0%, #1e293b 100%)',
      ring: 'ring-slate-500/20',
      accentDot: '#94a3b8',
    };
  }

  // Strip academic / formal titles for intuitive initials
  const cleanName = customer.name.replace(/^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.)\s+/i, '').trim();
  const words = cleanName.split(/\s+/).filter(Boolean);
  const initials = words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase()
    : cleanName.slice(0, 2).toUpperCase();

  const id = customer.id || '';
  const tier = customer.tier || '';
  const lower = cleanName.toLowerCase();

  // Customer 1: Rahul Sharma (NRI Elite) -> Warm Amber & Crimson Gold
  if (id === 'customer-1' || tier === 'NRI Elite' || lower.includes('rahul')) {
    return {
      initials,
      gradient: 'linear-gradient(135deg, #d97706 0%, #e11d48 100%)',
      ring: 'ring-amber-500/25',
      accentDot: '#f59e0b',
    };
  }

  // Customer 2: Dr. Ananya Sen (Burgundy Private) -> Signature Burgundy & Deep Violet
  if (id === 'customer-2' || tier === 'Burgundy Private' || lower.includes('ananya')) {
    return {
      initials,
      gradient: 'linear-gradient(135deg, #97144d 0%, #581c87 100%)',
      ring: 'ring-rose-500/25',
      accentDot: '#be185d',
    };
  }

  // Customer 3: Vikramaditya Malhotra (Private Wealth) -> Dark Emerald/Teal & Midnight Slate
  if (id === 'customer-3' || tier === 'Private Wealth' || lower.includes('vikram')) {
    return {
      initials,
      gradient: 'linear-gradient(135deg, #0d9488 0%, #0f172a 100%)',
      ring: 'ring-teal-500/25',
      accentDot: '#14b8a6',
    };
  }

  // Fallback for custom / new clients
  return {
    initials,
    gradient: 'linear-gradient(135deg, #6366f1 0%, #1e1b4b 100%)',
    ring: 'ring-indigo-500/25',
    accentDot: '#818cf8',
  };
}
