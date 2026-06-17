import { useTheme } from "@/lib/theme";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

/**
 * App-wide toast container. Mount once in main.tsx.
 * Sonner "sonner-richColors" variants are used via utility re-exports.
 */
const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useTheme();
  const effective: ToasterProps["theme"] =
    theme === "system" ? "system" : (theme as "dark" | "light");

  return (
    <Sonner
      theme={effective}
      className="toaster group"
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
export { toast } from "sonner";
