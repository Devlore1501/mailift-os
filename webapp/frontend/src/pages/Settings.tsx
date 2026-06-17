import { useState } from "react";
import { Plus, Trash2, FileText, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/domain/EmptyState";
import {
  useConfig,
  useDeleteOverride,
  useHealth,
  useOverrides,
  useSaveOverride,
  useVerifyRejects,
} from "@/lib/queries";
import { ApiError, rejectPdfUrl } from "@/lib/api";
import type { SupplierOverridePayload } from "@/types/api";
import { formatDate } from "@/lib/utils";

function OverrideDialog({
  open,
  onOpenChange,
  initial,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial?: SupplierOverridePayload | null;
}) {
  const save = useSaveOverride();
  const [form, setForm] = useState({
    supplier_key: initial?.supplier_key ?? "",
    supplier_name_display: initial?.supplier_name_display ?? "",
    country_iso: initial?.country_iso ?? "",
    vat_number: initial?.vat_number ?? "",
    vat_id: initial?.vat_id ?? 0,
    note: initial?.note ?? "",
  });

  const handleSave = async () => {
    try {
      await save.mutateAsync(form);
      toast.success("Override salvato");
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      toast.error("Salvataggio fallito", { description: msg });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {initial ? "Modifica override" : "Nuovo override"}
          </DialogTitle>
          <DialogDescription>
            Forza country, P.IVA o vat_id per un fornitore.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-3">
          <div>
            <Label htmlFor="sk">Supplier key</Label>
            <Input
              id="sk"
              value={form.supplier_key}
              onChange={(e) =>
                setForm((f) => ({ ...f, supplier_key: e.target.value }))
              }
              placeholder="es. higgsfield"
            />
          </div>
          <div>
            <Label htmlFor="nd">Nome display</Label>
            <Input
              id="nd"
              value={form.supplier_name_display}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  supplier_name_display: e.target.value,
                }))
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="ci">Country ISO</Label>
              <Input
                id="ci"
                value={form.country_iso}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    country_iso: e.target.value.toUpperCase(),
                  }))
                }
                maxLength={2}
                placeholder="US"
              />
            </div>
            <div>
              <Label htmlFor="vi">vat_id</Label>
              <Input
                id="vi"
                type="number"
                value={form.vat_id}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    vat_id: parseInt(e.target.value) || 0,
                  }))
                }
              />
            </div>
          </div>
          <div>
            <Label htmlFor="vn">P.IVA</Label>
            <Input
              id="vn"
              value={form.vat_number}
              onChange={(e) =>
                setForm((f) => ({ ...f, vat_number: e.target.value }))
              }
            />
          </div>
          <div>
            <Label htmlFor="no">Note</Label>
            <Input
              id="no"
              value={form.note}
              onChange={(e) =>
                setForm((f) => ({ ...f, note: e.target.value }))
              }
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Annulla
          </Button>
          <Button onClick={handleSave} disabled={save.isPending}>
            {save.isPending ? "Salvataggio..." : "Salva"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function OverridesTab() {
  const { data, isLoading } = useOverrides();
  const del = useDeleteOverride();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SupplierOverridePayload | null>(null);

  const handleDelete = async (id: number) => {
    if (!confirm("Eliminare questo override?")) return;
    try {
      await del.mutateAsync(id);
      toast.success("Override eliminato");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      toast.error("Eliminazione fallita", { description: msg });
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">Override fornitori</CardTitle>
          <CardDescription>
            Regole persistenti per normalizzare country/P.IVA dei fornitori
          </CardDescription>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setDialogOpen(true);
          }}
        >
          <Plus className="h-4 w-4" />
          Nuovo
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : !data || data.length === 0 ? (
          <EmptyState
            title="Nessun override"
            description="Aggiungi una regola per forzare country/vat_id di un fornitore."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Country</TableHead>
                <TableHead>P.IVA</TableHead>
                <TableHead>vat_id</TableHead>
                <TableHead>Note</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((o) => (
                <TableRow key={o.id}>
                  <TableCell className="font-mono text-xs">
                    {o.supplier_key}
                  </TableCell>
                  <TableCell>{o.supplier_name_display}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{o.country_iso || "—"}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {o.vat_number || "—"}
                  </TableCell>
                  <TableCell className="tabular-nums">{o.vat_id}</TableCell>
                  <TableCell className="max-w-[180px] truncate text-xs text-muted-foreground">
                    {o.note}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditing(o);
                          setDialogOpen(true);
                        }}
                      >
                        Modifica
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(o.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
      {dialogOpen && (
        <OverrideDialog
          key={editing?.id ?? "new"}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          initial={editing}
        />
      )}
    </Card>
  );
}

function SystemTab() {
  const { data: health } = useHealth();
  const { data: config } = useConfig();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configurazione</CardTitle>
        </CardHeader>
        <CardContent>
          {!config ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted-foreground">Company ID</dt>
                <dd className="font-mono">{config.company_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Company</dt>
                <dd>{config.company_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Numerazione</dt>
                <dd>{config.numeration}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Metodo pagamento
                </dt>
                <dd>{config.payment_method}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Account hint
                </dt>
                <dd>{config.payment_account_hint}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Blacklist fornitori IT
                </dt>
                <dd>{config.blacklist_count}</dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stato servizi</CardTitle>
        </CardHeader>
        <CardContent>
          {!health ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <ul className="space-y-1 text-sm">
              <li className="flex justify-between">
                <span>Fatture in Cloud</span>
                <Badge variant={health.fic_token_valid ? "success" : "destructive"}>
                  {health.fic_token_valid ? "OK" : "Down"}
                </Badge>
              </li>
              <li className="flex justify-between">
                <span>Database</span>
                <Badge variant={health.db_ok ? "success" : "destructive"}>
                  {health.db_ok ? "OK" : "Down"}
                </Badge>
              </li>
              <li className="flex justify-between">
                <span>Gmail personale</span>
                <Badge
                  variant={
                    health.gmail_tokens_ok?.personal ? "success" : "destructive"
                  }
                >
                  {health.gmail_tokens_ok?.personal ? "OK" : "Down"}
                </Badge>
              </li>
              <li className="flex justify-between">
                <span>Gmail business</span>
                <Badge
                  variant={
                    health.gmail_tokens_ok?.business ? "success" : "destructive"
                  }
                >
                  {health.gmail_tokens_ok?.business ? "OK" : "Down"}
                </Badge>
              </li>
              <li className="flex justify-between">
                <span>Anthropic API</span>
                <Badge variant={health.anthropic_api_ok ? "success" : "warning"}>
                  {health.anthropic_api_ok ? "OK" : "Unavailable"}
                </Badge>
              </li>
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RejectsTab() {
  const { data, isLoading } = useVerifyRejects();

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  if (!data || data.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="Nessuna quarantena"
        description="Tutti i PDF verificati hanno passato i controlli bill-to."
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Quarantena verifica</CardTitle>
        <CardDescription>
          PDF scaricati ma scartati perche&apos; bill-to non coincide con Mailift
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Supplier</TableHead>
              <TableHead>File</TableHead>
              <TableHead className="text-right">Size</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((r) => (
              <TableRow key={r.path}>
                <TableCell className="font-mono text-xs">
                  {r.supplier_key}
                </TableCell>
                <TableCell className="max-w-[280px] truncate text-xs">
                  {r.filename}
                </TableCell>
                <TableCell className="text-right tabular-nums text-xs">
                  {(r.size_bytes / 1024).toFixed(1)} KB
                </TableCell>
                <TableCell>
                  <Button asChild size="sm" variant="ghost">
                    <a
                      href={rejectPdfUrl(r.path)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Apri <ExternalLink className="h-3 w-3" />
                    </a>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function Settings() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Impostazioni</h1>
        <p className="text-sm text-muted-foreground">
          Override fornitori, info sistema e quarantena
        </p>
      </div>

      <Tabs defaultValue="overrides">
        <TabsList>
          <TabsTrigger value="overrides">Override fornitori</TabsTrigger>
          <TabsTrigger value="system">Info sistema</TabsTrigger>
          <TabsTrigger value="rejects">Quarantena</TabsTrigger>
        </TabsList>
        <TabsContent value="overrides" className="mt-4">
          <OverridesTab />
        </TabsContent>
        <TabsContent value="system" className="mt-4">
          <SystemTab />
        </TabsContent>
        <TabsContent value="rejects" className="mt-4">
          <RejectsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
