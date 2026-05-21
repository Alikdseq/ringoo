interface PlaceholderBlockProps {
  title: string;
  note?: string;
  items?: string[];
}

export function PlaceholderBlock({ title, note, items = [] }: PlaceholderBlockProps) {
  return (
    <section className="rounded-xl border border-dashed border-border bg-background-alt p-4">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {note && <p className="mt-1 text-sm text-foreground-muted">{note}</p>}
      {items.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-foreground-muted">
          {items.map(item => (
            <li key={item}>- {item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
