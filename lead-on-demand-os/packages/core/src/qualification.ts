import type { QualificationCategory } from "./enums.js";

export type AnswerValue = string | number | boolean | string[] | null;
export type Answers = Record<string, AnswerValue>;

export interface QuestionOption {
  value: string;
  label: string;
  next?: string | null; // chiave della domanda successiva se questa opzione viene scelta
}

export interface Question {
  key: string;
  text: string;
  type: "single" | "multi" | "number" | "text" | "boolean";
  options?: QuestionOption[];
  next?: string | null; // default se l'opzione non specifica un salto
  required?: boolean;
  help?: string;
}

export interface QualificationTemplate {
  start: string;
  questions: Question[];
}

export function findQuestion(template: QualificationTemplate, key: string): Question | undefined {
  return template.questions.find((q) => q.key === key);
}

// Ritorna la prossima domanda non ancora risposta seguendo i salti condizionali.
export function nextQuestion(template: QualificationTemplate, answers: Answers): Question | null {
  let key: string | null | undefined = template.start;
  const visited = new Set<string>();
  while (key) {
    if (visited.has(key)) return null; // protezione contro cicli
    visited.add(key);
    const q = findQuestion(template, key);
    if (!q) return null;
    const answer = answers[q.key];
    if (answer === undefined || answer === null || answer === "") return q;
    let next: string | null | undefined = q.next;
    if (q.type === "single" && q.options) {
      const opt = q.options.find((o) => o.value === String(answer));
      if (opt && opt.next !== undefined) next = opt.next;
    }
    if (q.type === "boolean" && q.options) {
      const opt = q.options.find((o) => o.value === String(answer));
      if (opt && opt.next !== undefined) next = opt.next;
    }
    key = next;
  }
  return null;
}

export function isComplete(template: QualificationTemplate, answers: Answers): boolean {
  return nextQuestion(template, answers) === null;
}

export type CriterionOp = "eq" | "neq" | "gte" | "lte" | "in" | "truthy" | "falsy" | "contains";
export type CriterionKind = "MANDATORY" | "PREFERRED" | "EXCLUSION";

export interface Criterion {
  field: string;
  op: CriterionOp;
  value?: AnswerValue;
  kind: CriterionKind;
  label: string;
}

function toNumber(v: AnswerValue | undefined): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))) return Number(v);
  return null;
}

export function evaluateOp(op: CriterionOp, actual: AnswerValue | undefined, expected?: AnswerValue): boolean {
  switch (op) {
    case "eq":
      return actual !== undefined && actual !== null && String(actual) === String(expected);
    case "neq":
      return actual === undefined || actual === null || String(actual) !== String(expected);
    case "gte": {
      const a = toNumber(actual);
      const e = toNumber(expected);
      return a !== null && e !== null && a >= e;
    }
    case "lte": {
      const a = toNumber(actual);
      const e = toNumber(expected);
      return a !== null && e !== null && a <= e;
    }
    case "in":
      return Array.isArray(expected) && actual !== undefined && actual !== null && expected.includes(String(actual));
    case "truthy":
      return actual === true || actual === "true" || actual === "yes" || actual === "si" || actual === "sì" || actual === 1 || actual === "1";
    case "falsy":
      return !(actual === true || actual === "true" || actual === "yes" || actual === "si" || actual === "sì" || actual === 1 || actual === "1");
    case "contains":
      return Array.isArray(actual) && actual.includes(String(expected));
  }
}

export interface CriteriaEvaluation {
  passed: boolean; // tutti gli obbligatori soddisfatti e nessuna esclusione colpita
  mandatoryFailed: Criterion[];
  exclusionsHit: Criterion[];
  preferredMet: Criterion[];
  preferredMissed: Criterion[];
}

// I criteri obbligatori e di esclusione decidono. Quelli preferenziali alimentano solo lo score.
export function evaluateCriteria(criteria: readonly Criterion[], answers: Answers): CriteriaEvaluation {
  const out: CriteriaEvaluation = {
    passed: true,
    mandatoryFailed: [],
    exclusionsHit: [],
    preferredMet: [],
    preferredMissed: [],
  };
  for (const c of criteria) {
    const ok = evaluateOp(c.op, answers[c.field], c.value);
    switch (c.kind) {
      case "MANDATORY":
        if (!ok) out.mandatoryFailed.push(c);
        break;
      case "EXCLUSION":
        if (ok) out.exclusionsHit.push(c);
        break;
      case "PREFERRED":
        (ok ? out.preferredMet : out.preferredMissed).push(c);
        break;
    }
  }
  out.passed = out.mandatoryFailed.length === 0 && out.exclusionsHit.length === 0;
  return out;
}

export interface ScoreRule {
  field: string;
  op: CriterionOp;
  value?: AnswerValue;
  points: number;
  label: string;
}

export interface ScoreConfig {
  rules: ScoreRule[];
  thresholds: { hot: number; qualified: number; review: number };
}

export interface ScoreResult {
  score: number;
  maxScore: number;
  category: QualificationCategory;
  breakdown: Array<{ label: string; points: number; met: boolean }>;
}

export const DEFAULT_SCORE_THRESHOLDS = { hot: 80, qualified: 60, review: 40 };

// Lo score non sostituisce i criteri obbligatori (PRD sez. 16): se `criteriaPassed` è false
// la categoria è sempre NOT_QUALIFIED, qualunque sia il punteggio.
export function computeScore(config: ScoreConfig, answers: Answers, criteriaPassed = true): ScoreResult {
  let score = 0;
  let maxScore = 0;
  const breakdown: ScoreResult["breakdown"] = [];
  for (const r of config.rules) {
    const met = evaluateOp(r.op, answers[r.field], r.value);
    if (r.points > 0) maxScore += r.points;
    if (met) score += r.points;
    breakdown.push({ label: r.label, points: r.points, met });
  }
  const t = config.thresholds;
  let category: QualificationCategory;
  if (!criteriaPassed) category = "NOT_QUALIFIED";
  else if (score >= t.hot) category = "HOT";
  else if (score >= t.qualified) category = "QUALIFIED";
  else if (score >= t.review) category = "REVIEW";
  else category = "NOT_QUALIFIED";
  return { score, maxScore, category, breakdown };
}
