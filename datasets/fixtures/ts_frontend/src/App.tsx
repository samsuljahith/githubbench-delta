import { useEffect, useState } from 'react';
import { fetchHealth, type Health } from './api/client';
import { HealthCard } from './components/HealthCard';

export function App() {
  const [items, setItems] = useState<Health[]>([]);
  useEffect(() => {
    fetchHealth('/api').then(setItems).catch(console.error);
  }, []);
  return (
    <main>
      {items.map((item) => (
        <HealthCard key={item.service} item={item} />
      ))}
    </main>
  );
}
