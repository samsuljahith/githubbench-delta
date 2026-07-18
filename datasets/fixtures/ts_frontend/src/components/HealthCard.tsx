import type { Health } from '../api/client';

export function HealthCard({ item }: { item: Health }) {
  return (
    <div className="card">
      <h3>{item.service}</h3>
      <p>{item.status}</p>
    </div>
  );
}
