import { describe, expect, it } from "vitest";
import {
  PV_RESIDENTIAL_CRITERIA,
  PV_RESIDENTIAL_SCORE,
  PV_RESIDENTIAL_TEMPLATE,
  assertTransition,
  canTransition,
  checkReplacementSla,
  computeBalance,
  computeScore,
  derivePackageStatus,
  detectTerritoryConflict,
  evaluateCriteria,
  evaluateDuplicate,
  evaluateRouting,
  nextQuestion,
  normalizePhone,
  signedQuantity,
  type RoutingCandidate,
  type RoutingLead,
} from "../src/index.js";

describe("state machine", () => {
  it("accetta il percorso principale del PRD", () => {
    const path = ["NEW", "VALIDATING", "TO_CONTACT", "ATTEMPT_1", "CONTACTED", "QUALIFYING", "QUALIFIED", "ASSIGNED", "DELIVERED", "REPLACEMENT_REQUESTED", "REPLACEMENT_APPROVED"] as const;
    for (let i = 0; i < path.length - 1; i++) expect(canTransition(path[i]!, path[i + 1]!)).toBe(true);
  });
  it("rifiuta i salti non ammessi", () => {
    expect(canTransition("NEW", "DELIVERED")).toBe(false);
    expect(() => assertTransition("DELIVERED", "NEW")).toThrow(/non ammessa/);
  });
});

describe("ledger", () => {
  it("calcola il saldo come somma delle transazioni", () => {
    const entries = [
      { type: "PURCHASE" as const, quantity: signedQuantity("PURCHASE", 20) },
      { type: "DELIVERY" as const, quantity: signedQuantity("DELIVERY", 1) },
      { type: "REPLACEMENT" as const, quantity: signedQuantity("REPLACEMENT", 1) },
      { type: "DELIVERY" as const, quantity: signedQuantity("DELIVERY", 1) },
    ];
    expect(computeBalance(entries)).toBe(19);
  });
  it("deriva lo stato pacchetto dalle soglie", () => {
    expect(derivePackageStatus("ACTIVE", 20)).toBe("ACTIVE");
    expect(derivePackageStatus("ACTIVE", 5)).toBe("LOW_BALANCE");
    expect(derivePackageStatus("LOW_BALANCE", 0)).toBe("COMPLETED");
    expect(derivePackageStatus("COMPLETED", 1)).toBe("LOW_BALANCE");
    expect(derivePackageStatus("PAUSED", 0)).toBe("PAUSED");
  });
});

describe("normalizzazione e duplicati", () => {
  it("normalizza i telefoni italiani", () => {
    expect(normalizePhone("340 123 4567")).toBe("+393401234567");
    expect(normalizePhone("+39 340-123-4567")).toBe("+393401234567");
    expect(normalizePhone("0039 3401234567")).toBe("+393401234567");
    expect(normalizePhone("abc")).toBeNull();
  });
  it("rileva duplicati per telefono nella finestra e ignora fuori finestra", () => {
    const now = new Date("2026-09-14T10:00:00Z");
    const existing = [
      { id: "old", phoneNormalized: "+393401234567", emailNormalized: null, addressLastnameKey: null, createdAt: new Date("2026-01-01") },
      { id: "recent", phoneNormalized: "+393401234567", emailNormalized: null, addressLastnameKey: null, createdAt: new Date("2026-09-01") },
    ];
    const r = evaluateDuplicate({ phone: "3401234567" }, existing, 90, now);
    expect(r.result).toBe("DUPLICATE");
    expect(r.matchedLeadId).toBe("recent");
    const r2 = evaluateDuplicate({ phone: "3401234567" }, [existing[0]!], 90, now);
    expect(r2.result).toBe("UNIQUE");
  });
  it("segnala possibile duplicato su indirizzo + cognome", () => {
    const r = evaluateDuplicate(
      { phone: "3331112222", lastName: "Rossi", address: "Via Roma 1" },
      [{ id: "x", phoneNormalized: "+390000000000", emailNormalized: null, addressLastnameKey: "rossi|via roma 1", createdAt: new Date() }],
    );
    expect(r.result).toBe("POSSIBLE_DUPLICATE");
  });
});

describe("qualificazione", () => {
  it("segue i salti condizionali dello script", () => {
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, {})?.key).toBe("interested");
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, { interested: "false" })).toBeNull();
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, { interested: "true" })?.key).toBe("owner");
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, { interested: "true", owner: "false" })?.key).toBe("decision_maker");
  });
  it("criteri obbligatori e score come nell'esempio del PRD", () => {
    const answers = {
      interested: "true",
      owner: "true",
      property_type: "villa",
      roof_available: "true",
      monthly_bill: 180,
      timeline: "lt3m",
      decision_maker: "true",
      storage: "true",
      phone_verified: "true",
    };
    const crit = evaluateCriteria(PV_RESIDENTIAL_CRITERIA, answers);
    expect(crit.passed).toBe(true);
    const score = computeScore(PV_RESIDENTIAL_SCORE, answers, crit.passed);
    expect(score.score).toBe(100);
    expect(score.category).toBe("HOT");
  });
  it("lo score non supera i criteri obbligatori", () => {
    const answers = { interested: "true", owner: "false", monthly_bill: 300, timeline: "lt3m", decision_maker: "true", roof_available: "true", storage: "true", phone_verified: "true" };
    const crit = evaluateCriteria(PV_RESIDENTIAL_CRITERIA, answers);
    expect(crit.passed).toBe(false);
    expect(crit.mandatoryFailed.map((c) => c.field)).toEqual(["owner"]);
    expect(computeScore(PV_RESIDENTIAL_SCORE, answers, crit.passed).category).toBe("NOT_QUALIFIED");
  });
  it("le esclusioni bloccano", () => {
    const crit = evaluateCriteria(PV_RESIDENTIAL_CRITERIA, { interested: "true", owner: "true", roof_available: "true", property_type: "condo" });
    expect(crit.passed).toBe(false);
    expect(crit.exclusionsHit).toHaveLength(1);
  });
});

function candidate(over: Partial<RoutingCandidate>): RoutingCandidate {
  return {
    clientId: "c1",
    clientName: "Rossi Impianti",
    clientStatus: "ACTIVE",
    clientType: "RESIDENTIAL",
    vertical: "photovoltaic",
    packages: [{ id: "p1", status: "ACTIVE", balance: 7, createdAt: new Date("2026-01-01") }],
    territories: [{ clientId: "c1", level: "PROVINCE", value: "VI", exclusive: false }],
    caps: {},
    deliveredCounts: { day: 0, week: 0, month: 0 },
    ...over,
  };
}
const lead: RoutingLead = {
  id: "l1",
  vertical: "photovoltaic",
  leadType: "RESIDENTIAL",
  location: { region: "VENETO", province: "VI", municipality: "VICENZA", postalCode: "36100" },
  qualificationPassed: true,
};

describe("routing engine", () => {
  it("assegna al cliente compatibile con credito", () => {
    const d = evaluateRouting(lead, [candidate({})]);
    expect(d.outcome).toBe("ASSIGNED");
    if (d.outcome === "ASSIGNED") expect(d.packageId).toBe("p1");
  });
  it("mette in coda con motivazione quando nessun cliente è disponibile", () => {
    const d = evaluateRouting(lead, [candidate({ packages: [{ id: "p1", status: "COMPLETED", balance: 0, createdAt: new Date() }] })]);
    expect(d.outcome).toBe("WAITING_ASSIGNMENT");
    if (d.outcome === "WAITING_ASSIGNMENT") expect(d.summary).toContain("NO_CREDIT");
  });
  it("rispetta il cap giornaliero", () => {
    const d = evaluateRouting(lead, [candidate({ caps: { daily: 3 }, deliveredCounts: { day: 3, week: 3, month: 3 } })]);
    expect(d.outcome).toBe("WAITING_ASSIGNMENT");
    if (d.outcome === "WAITING_ASSIGNMENT") expect(d.summary).toContain("CAP_DAILY_REACHED");
  });
  it("l'esclusiva blocca gli altri clienti anche se il titolare non ha credito", () => {
    const holder = candidate({
      clientId: "A",
      clientName: "A",
      territories: [{ clientId: "A", level: "PROVINCE", value: "VI", exclusive: true }],
      packages: [],
    });
    const other = candidate({ clientId: "B", clientName: "B" });
    const d = evaluateRouting(lead, [holder, other]);
    expect(d.outcome).toBe("WAITING_ASSIGNMENT");
    if (d.outcome === "WAITING_ASSIGNMENT") {
      expect(d.summary).toContain("EXCLUSIVE_HOLDER_UNAVAILABLE");
      expect(d.evaluations.find((e) => e.clientId === "B")?.reasons).toContain("EXCLUSIVITY_OF_OTHER_CLIENT");
    }
  });
  it("preferisce il territorio più specifico e poi il round robin", () => {
    const prov = candidate({ clientId: "P", clientName: "P", deliveredCounts: { day: 0, week: 0, month: 0 } });
    const cap = candidate({ clientId: "C", clientName: "C", territories: [{ clientId: "C", level: "POSTAL_CODE", value: "36100", exclusive: false }], deliveredCounts: { day: 0, week: 0, month: 9 } });
    const d = evaluateRouting(lead, [prov, cap]);
    expect(d.outcome === "ASSIGNED" && d.clientId).toBe("C");
    const p2 = candidate({ clientId: "P2", clientName: "P2", deliveredCounts: { day: 0, week: 0, month: 2 } });
    const d2 = evaluateRouting(lead, [prov, p2]);
    expect(d2.outcome === "ASSIGNED" && d2.clientId).toBe("P");
  });
  it("consuma prima il pacchetto più vecchio", () => {
    const d = evaluateRouting(lead, [
      candidate({
        packages: [
          { id: "new", status: "ACTIVE", balance: 20, createdAt: new Date("2026-05-01") },
          { id: "old", status: "LOW_BALANCE", balance: 2, createdAt: new Date("2026-01-01") },
        ],
      }),
    ]);
    expect(d.outcome === "ASSIGNED" && d.packageId).toBe("old");
  });
});

describe("territori e replacement", () => {
  it("rileva il conflitto di esclusiva", () => {
    const conflict = detectTerritoryConflict(
      { clientId: "B", level: "PROVINCE", value: "VI", exclusive: false },
      [{ clientId: "A", level: "PROVINCE", value: "VI", exclusive: true }],
      { A: "Cliente A", B: "Cliente B" },
    );
    expect(conflict?.message).toBe("Impossibile assegnare VI a Cliente B. Il territorio è attualmente assegnato in esclusiva a Cliente A.");
  });
  it("rileva il conflitto gerarchico comune dentro provincia esclusiva", () => {
    const conflict = detectTerritoryConflict(
      { clientId: "B", level: "MUNICIPALITY", value: "VICENZA", province: "VI", exclusive: false },
      [{ clientId: "A", level: "PROVINCE", value: "VI", exclusive: true }],
    );
    expect(conflict).not.toBeNull();
    const ok = detectTerritoryConflict(
      { clientId: "B", level: "PROVINCE", value: "PD", exclusive: false },
      [{ clientId: "A", level: "PROVINCE", value: "VI", exclusive: true }],
    );
    expect(ok).toBeNull();
  });
  it("applica lo SLA replacement", () => {
    const delivered = new Date("2026-09-10T10:00:00Z");
    expect(checkReplacementSla(delivered, 72, new Date("2026-09-12T10:00:00Z")).allowed).toBe(true);
    const late = checkReplacementSla(delivered, 72, new Date("2026-09-14T10:00:00Z"));
    expect(late.allowed).toBe(false);
    expect(late.message).toMatch(/terminato/);
  });
});

describe("domande facoltative", () => {
  it("una domanda facoltativa saltata non viene riproposta", () => {
    const answers = { interested: "true", owner: "true", property_type: "villa", roof_available: "true", monthly_bill: 120, annual_kwh: "" };
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, answers)?.key).toBe("household_size");
    const mandatoryEmpty = { interested: "true", owner: "true", property_type: "villa", roof_available: "true", monthly_bill: "" };
    expect(nextQuestion(PV_RESIDENTIAL_TEMPLATE, mandatoryEmpty)?.key).toBe("monthly_bill");
  });
});
