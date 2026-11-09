import type { Metadata } from 'next';
import { ProfileContent } from '@/app/profile/ProfileContent';

export const metadata: Metadata = {
  title: 'Личный кабинет Ringoo — мои заказы и избранное',
  description:
    'Управляйте заказами, избранным и адресами доставки. Оценивайте менеджеров и следите за статусами.',
  robots: {
    index: false,
    follow: true,
  },
};

export default function ProfilePage() {
  return <ProfileContent />;
}
