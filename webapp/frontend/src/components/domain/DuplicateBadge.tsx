import { Badge } from "@/components/ui/badge";
import type { DuplicateInfo } from "@/types/api";

/** Segnala un'autofattura gia' presente su FiC che potrebbe coprire gli stessi addebiti. */
export function DuplicateBadge({ dup }: { dup: DuplicateInfo | null }) {
  if (!dup) return null;
  const certain = dup.level === "duplicate";
  return (
    <Badge
      variant={certain ? "red" : "amber"}
      className="whitespace-nowrap text-[10px]"
      title={dup.reason}
    >
      {certain ? "Duplicato" : "Possibile duplicato"} {dup.fic_number}
    </Badge>
  );
}
