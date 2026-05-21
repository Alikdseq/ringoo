import type { Metadata } from 'next';
import { ProfileContent } from '@/app/profile/ProfileContent';

export const metadata: Metadata = {
  title: 'Личный кабинет Ringoo — мои заказы, бонусы, избранное',
  description:
    'Управляйте заказами, отслеживайте бонусы, оценивайте менеджеров. Быстрый доступ к адресам доставки и настройкам.',
  robots: {
    index: false,
    follow: true,
  },
};

export default function ProfilePage() {
  return <ProfileContent />;
}
