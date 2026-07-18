import type { ReactNode } from 'react';
export function MetricCard({label,value,unit,accent}:{label:string;value:string|number;unit:string;accent?:ReactNode}) { return <article className="card metric"><span>{label}</span><strong>{value}</strong><small>{unit}</small>{accent}</article> }
