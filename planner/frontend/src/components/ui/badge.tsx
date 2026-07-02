import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        success:
          "border-transparent bg-success text-success-foreground hover:bg-success/80",
        warning:
          "border-transparent bg-warning text-warning-foreground hover:bg-warning/80",
        outline: "text-foreground",
        // semantic color-coded variants for domain badges
        blue: "border-blue-500/30 bg-blue-500/10 text-blue-400 dark:text-blue-300",
        purple:
          "border-purple-500/30 bg-purple-500/10 text-purple-400 dark:text-purple-300",
        amber:
          "border-amber-500/30 bg-amber-500/10 text-amber-500 dark:text-amber-300",
        red: "border-red-500/30 bg-red-500/10 text-red-500 dark:text-red-300",
        zinc: "border-zinc-500/30 bg-zinc-500/10 text-zinc-500 dark:text-zinc-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
