export type TokenUsage = {
  router: number;
  sql_gen: number;
  validator: number;
};

export type VizFormat =
  | "line"
  | "bar"
  | "pie"
  | "table"
  | "kpi"
  | "mixed"
  | "prose";

export type Visualization = {
  format: VizFormat;
  x_axis: string | null;
  y_axis: string | null;
  series: string | null;
  title: string;
  reasoning: string;
};

export type PlanStep = {
  step: number;
  name: string;
  natural_language: string;
  rationale: string;
};

export type Panel = {
  step: number;
  name: string;
  sql: string | null;
  rows: Record<string, unknown>[] | null;
  row_count: number;
  visualization: Visualization | null;
  error: string | null;
};

export type Trace = {
  planner_intent: string;
  planner_domains: string[];
  plan_steps: PlanStep[];
  executor_notes: string;
};

export type AskResponse = {
  intent: string;
  domains: string[];
  sql: string | null;
  rows: Record<string, unknown>[] | null;
  row_count: number;
  latency_ms: number;
  token_usage: TokenUsage;
  estimated_cost_usd: number;
  explain_ok: boolean;
  error: string | null;
  clarification_question: string | null;
  visualization: Visualization | null;
  panels: Panel[] | null;
  trace: Trace | null;
};

export type Turn = {
  id: string;
  query: string;
  response: AskResponse | null;
  error: string | null;
  ts: number;
};
