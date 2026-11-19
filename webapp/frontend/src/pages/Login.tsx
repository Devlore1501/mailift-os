import { useState, type FormEvent } from "react";
import { Loader2, Lock, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLogin } from "@/lib/queries";

export function Login() {
  const [password, setPassword] = useState("");
  const login = useLogin();

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password) login.mutate(password);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Receipt className="h-5 w-5" />
          </div>
          <CardTitle className="text-lg">Autofatture Mailift</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {login.error && (
              <p className="text-sm text-destructive" role="alert">
                {login.error.message}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={!password || login.isPending}>
              {login.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Lock className="h-4 w-4" />
              )}
              Accedi
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
