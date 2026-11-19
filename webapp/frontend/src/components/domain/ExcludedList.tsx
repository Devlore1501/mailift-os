import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { ExcludedItem, SkippedItalianItem, Transaction } from "@/types/api";

interface Props {
  excluded: ExcludedItem[];
  skippedItalian: SkippedItalianItem[];
  orphanRefunds: Transaction[];
}

/** Tutto cio' che e' uscito dal conto ma non diventa autofattura, con il motivo. */
export function ExcludedList({ excluded, skippedItalian, orphanRefunds }: Props) {
  const rows = [
    ...excluded.map((e) => ({
      date: e.date,
      label: e.description,
      reason: e.reason + (e.refund_date ? ` il ${formatDate(e.refund_date)}` : ""),
      amount: e.amount,
      currency: e.currency,
    })),
    ...skippedItalian.map((s) => ({
      date: String(s.source_transaction?.date ?? ""),
      label: s.supplier_name,
      reason: "fornitore italiano, IVA diretta",
      amount: s.amount,
      currency: "EUR",
    })),
  ].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-3">
      {orphanRefunds.length > 0 && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Rimborsi da far valutare al commercialista</AlertTitle>
          <AlertDescription>
            <p className="text-xs text-muted-foreground">
              Rimborsi senza l'addebito originale in questo estratto: se
              l'addebito era gia' stato autofatturato serve una nota di
              variazione. Non vengono compensati in automatico.
            </p>
            <ul className="mt-2 space-y-1 text-xs">
              {orphanRefunds.map((r, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span>
                    {formatDate(r.date)} · {r.description}
                  </span>
                  <span className="tabular-nums">{formatCurrency(r.amount, r.currency)}</span>
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
      {rows.length > 0 && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{rows.length} addebiti non autofatturati</AlertTitle>
          <AlertDescription>
            <Accordion type="single" collapsible className="mt-1">
              <AccordionItem value="excluded" className="border-0">
                <AccordionTrigger className="py-2 text-xs">Mostra dettagli</AccordionTrigger>
                <AccordionContent>
                  <ul className="space-y-1 text-xs">
                    {rows.map((r, i) => (
                      <li
                        key={i}
                        className="grid grid-cols-[5.5rem_1fr_auto] items-center gap-3 border-b border-border/40 py-1 sm:grid-cols-[5.5rem_1fr_14rem_auto]"
                      >
                        <span className="tabular-nums text-muted-foreground">
                          {r.date ? formatDate(r.date) : "—"}
                        </span>
                        <span className="truncate font-medium">{r.label}</span>
                        <Badge variant="zinc" className="hidden w-fit text-[10px] sm:inline-flex">
                          {r.reason}
                        </Badge>
                        <span className="tabular-nums">
                          {formatCurrency(Math.abs(r.amount), r.currency)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
