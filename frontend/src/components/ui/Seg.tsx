"use client";
/** Selettore a segmenti: chiaro quale voce è attiva (riempita) e quali no. */
export function Seg<T extends string>({ value, onChange, items, label }: { value: T; onChange: (v: T) => void; items: { v: NoInfer<T>; label: string; n?: number }[]; label?: string }) {
  return (
    <div className="seg" role="tablist" aria-label={label}>
      {items.map((i) => (
        <button key={i.v} role="tab" aria-selected={value === i.v} className={value === i.v ? "on" : ""} onClick={() => onChange(i.v)}>
          {i.label}{i.n != null && <em>{i.n}</em>}
        </button>
      ))}
    </div>
  );
}
/** Interruttore on/off con testo di stato: non resta nessun cerchio arancione a sporcare il pulsante. */
export function Switch({ on, onChange, label, state }: { on: boolean; onChange: (v: boolean) => void; label: string; state: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} className={"sw" + (on ? " on" : "")} onClick={() => onChange(!on)}>
      <span className="sw-knob" aria-hidden="true" /><span>{label}</span><em>{state}</em>
    </button>
  );
}
