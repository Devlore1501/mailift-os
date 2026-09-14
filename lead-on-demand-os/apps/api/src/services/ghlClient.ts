// Client minimale per l'API LeadConnector v2 (GoHighLevel).
// L'interfaccia permette di sostituirlo con un fake nei test.

export interface GhlAuth {
  apiKey: string;
  locationId: string;
}

export interface GhlContactInput {
  firstName?: string | null;
  lastName?: string | null;
  phone?: string | null;
  email?: string | null;
  address1?: string | null;
  city?: string | null;
  postalCode?: string | null;
  state?: string | null;
  source?: string | null;
  tags?: string[];
  customFields?: Array<{ id: string; value: unknown }>;
}

export interface GhlOpportunityInput {
  pipelineId: string;
  pipelineStageId?: string | null;
  name: string;
  contactId: string;
  monetaryValue?: number | null;
  status?: "open" | "won" | "lost" | "abandoned";
}

export interface GhlClient {
  upsertContact(auth: GhlAuth, input: GhlContactInput): Promise<{ contactId: string }>;
  createOpportunity(auth: GhlAuth, input: GhlOpportunityInput): Promise<{ opportunityId: string }>;
  addTags(auth: GhlAuth, contactId: string, tags: string[]): Promise<void>;
  addNote(auth: GhlAuth, contactId: string, body: string): Promise<void>;
}

export class GhlHttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "GhlHttpError";
  }
}

export class HttpGhlClient implements GhlClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiVersion: string,
    private readonly fetchImpl: typeof fetch = fetch,
  ) {}

  private async request<T>(auth: GhlAuth, method: string, path: string, body?: unknown): Promise<T> {
    const res = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${auth.apiKey}`,
        Version: this.apiVersion,
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) throw new GhlHttpError(res.status, `GHL ${method} ${path} -> ${res.status}: ${text.slice(0, 500)}`);
    return (text ? JSON.parse(text) : {}) as T;
  }

  async upsertContact(auth: GhlAuth, input: GhlContactInput): Promise<{ contactId: string }> {
    const data = await this.request<{ contact?: { id: string }; id?: string }>(auth, "POST", "/contacts/upsert", {
      locationId: auth.locationId,
      ...input,
    });
    const id = data.contact?.id ?? data.id;
    if (!id) throw new GhlHttpError(502, "GHL upsert contact: id mancante nella risposta");
    return { contactId: id };
  }

  async createOpportunity(auth: GhlAuth, input: GhlOpportunityInput): Promise<{ opportunityId: string }> {
    const data = await this.request<{ opportunity?: { id: string }; id?: string }>(auth, "POST", "/opportunities/", {
      locationId: auth.locationId,
      pipelineId: input.pipelineId,
      pipelineStageId: input.pipelineStageId ?? undefined,
      name: input.name,
      contactId: input.contactId,
      monetaryValue: input.monetaryValue ?? undefined,
      status: input.status ?? "open",
    });
    const id = data.opportunity?.id ?? data.id;
    if (!id) throw new GhlHttpError(502, "GHL create opportunity: id mancante nella risposta");
    return { opportunityId: id };
  }

  async addTags(auth: GhlAuth, contactId: string, tags: string[]): Promise<void> {
    if (tags.length === 0) return;
    await this.request(auth, "POST", `/contacts/${contactId}/tags`, { tags });
  }

  async addNote(auth: GhlAuth, contactId: string, body: string): Promise<void> {
    await this.request(auth, "POST", `/contacts/${contactId}/notes`, { body });
  }
}

// Fake in memoria per test e ambiente demo (nessuna chiamata di rete).
export class FakeGhlClient implements GhlClient {
  public contacts: Array<{ auth: GhlAuth; input: GhlContactInput; id: string }> = [];
  public opportunities: Array<{ auth: GhlAuth; input: GhlOpportunityInput; id: string }> = [];
  public tags: Array<{ contactId: string; tags: string[] }> = [];
  public notes: Array<{ contactId: string; body: string }> = [];
  public failNext = 0; // numero di chiamate da far fallire (simula errori API)

  private maybeFail() {
    if (this.failNext > 0) {
      this.failNext -= 1;
      throw new GhlHttpError(503, "GHL simulato non disponibile");
    }
  }
  async upsertContact(auth: GhlAuth, input: GhlContactInput) {
    this.maybeFail();
    const id = `ghl_c_${this.contacts.length + 1}`;
    this.contacts.push({ auth, input, id });
    return { contactId: id };
  }
  async createOpportunity(auth: GhlAuth, input: GhlOpportunityInput) {
    this.maybeFail();
    const id = `ghl_o_${this.opportunities.length + 1}`;
    this.opportunities.push({ auth, input, id });
    return { opportunityId: id };
  }
  async addTags(_auth: GhlAuth, contactId: string, tags: string[]) {
    this.maybeFail();
    this.tags.push({ contactId, tags });
  }
  async addNote(_auth: GhlAuth, contactId: string, body: string) {
    this.maybeFail();
    this.notes.push({ contactId, body });
  }
}
