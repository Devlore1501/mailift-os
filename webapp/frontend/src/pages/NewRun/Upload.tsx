import { useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Upload as UploadIcon, FileText } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUploadStatement, useHistory } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const ACCEPTED = [".csv", ".xlsx", ".xls", ".pdf"];

function validExt(name: string) {
  const lower = name.toLowerCase();
  return ACCEPTED.some((ext) => lower.endsWith(ext));
}

export function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const upload = useUploadStatement();
  const { data: history } = useHistory();

  const handleFile = async (file: File) => {
    if (!validExt(file.name)) {
      toast.error("Formato file non supportato", {
        description: `Ammessi: ${ACCEPTED.join(", ")}`,
      });
      return;
    }
    try {
      const res = await upload.mutateAsync(file);
      toast.success("File caricato", { description: res.filename });
      navigate(`/new/processing/${res.statement_id}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      toast.error("Upload fallito", { description: msg });
    }
  };

  const recent = (history ?? []).slice(0, 3);

  return (
    <div className="space-y-6">
      <Card
        className={cn(
          "border-2 border-dashed transition-colors",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        )}
      >
        <CardContent
          className="flex cursor-pointer flex-col items-center justify-center gap-4 px-6 py-16 text-center"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <UploadIcon className="h-7 w-7 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="text-lg font-semibold">
              Trascina qui l&apos;estratto conto
            </div>
            <div className="text-sm text-muted-foreground">
              oppure clicca per selezionare un file · {ACCEPTED.join(", ")}
            </div>
          </div>
          <Button type="button" disabled={upload.isPending}>
            {upload.isPending ? "Caricamento..." : "Seleziona file"}
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(",")}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = "";
            }}
          />
        </CardContent>
      </Card>

      {recent.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Run recenti
          </div>
          <div className="space-y-1">
            {recent.map((r) => (
              <Link
                key={r.id}
                to={`/history/${r.id}`}
                className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-2 text-sm transition-colors hover:bg-accent"
              >
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="flex-1 truncate font-mono text-xs">
                  {r.statement_id || "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(r.started_at, "short")}
                </span>
                <span className="text-xs tabular-nums">
                  {r.created_count}/{r.total_count}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
