import { useEffect, useState } from "react";
import { FileText, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

interface PdfItem {
  filename: string;
  url: string;
}

interface PdfPreviewDialogProps {
  supplierKey: string;
  supplierName?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Fetches the list of verified invoice PDFs for a supplier and previews the
 * selected one in an iframe. Parent controls open state.
 */
export function PdfPreviewDialog({
  supplierKey,
  supplierName,
  open,
  onOpenChange,
}: PdfPreviewDialogProps) {
  const [items, setItems] = useState<PdfItem[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !supplierKey) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setItems(null);
    setSelected(null);

    fetch(`/api/suppliers/invoices/${encodeURIComponent(supplierKey)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { items?: PdfItem[] }) => {
        if (cancelled) return;
        const list = Array.isArray(data.items) ? data.items : [];
        setItems(list);
        setSelected(list[0]?.filename ?? null);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e?.message ?? e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, supplierKey]);

  const current = items?.find((it) => it.filename === selected) ?? null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            {supplierName || supplierKey}
          </DialogTitle>
          <DialogDescription>
            Fatture scaricate dalla casella email di Mailift.
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-[480px] w-full" />
          </div>
        )}

        {!loading && error && (
          <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Errore nel caricamento dei PDF: {error}</span>
          </div>
        )}

        {!loading && !error && items && items.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed p-10 text-center text-sm text-muted-foreground">
            <FileText className="h-6 w-6" />
            <span>Nessun PDF trovato per questo fornitore.</span>
          </div>
        )}

        {!loading && !error && items && items.length > 0 && (
          <div className="space-y-3">
            {items.length > 1 && (
              <Select
                value={selected ?? undefined}
                onValueChange={(v) => setSelected(v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleziona PDF" />
                </SelectTrigger>
                <SelectContent>
                  {items.map((it) => (
                    <SelectItem key={it.filename} value={it.filename}>
                      {it.filename}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {current && (
              <iframe
                key={current.url}
                src={current.url}
                title={current.filename}
                className="h-[60vh] w-full rounded-md border bg-muted"
              />
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
