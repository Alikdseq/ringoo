import type { DeliveryAddress, User, UserProfile } from '@/types/api';

/** ФИО из профиля: «Фамилия Имя Отчество». */
export function fullNameFromProfile(profile: UserProfile | null | undefined): string {
  if (!profile) return '';
  return [profile.last_name, profile.first_name, profile.middle_name]
    .map(s => (s ?? '').trim())
    .filter(Boolean)
    .join(' ');
}

type CheckoutContactFields = {
  fullName: string;
  phone: string;
  email: string;
  city: string;
  addressLine: string;
};

/** Подстановка контактов и адреса из профиля (только в пустые поля). */
export function mergeCheckoutFromUser<T extends CheckoutContactFields>(
  prev: T,
  user: User | null | undefined,
  defaultAddress: DeliveryAddress | undefined
): T {
  if (!user) return prev;

  const profileName = fullNameFromProfile(user.profile);
  const next: T = { ...prev };

  if (!next.fullName.trim() && profileName) next.fullName = profileName;
  if (!next.phone.trim() && user.phone?.trim()) next.phone = user.phone.trim();
  if (!next.email.trim() && user.email?.trim()) next.email = user.email.trim();

  if (defaultAddress) {
    if (!next.city.trim() && defaultAddress.city?.trim()) {
      next.city = defaultAddress.city.trim();
    }
    if (!next.addressLine.trim()) {
      const parts = [
        defaultAddress.street,
        defaultAddress.house,
        defaultAddress.apartment ? `кв. ${defaultAddress.apartment}` : null,
      ].filter(Boolean);
      if (parts.length) next.addressLine = parts.join(', ');
    }
  }

  return next;
}
