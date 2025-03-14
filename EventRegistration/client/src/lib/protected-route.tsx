import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";
import { Redirect, Route, RouteComponentProps } from "wouter";
import type { ComponentType } from "react";

interface ProtectedRouteProps {
  path: string;
  component: ComponentType<any>;
  requireAdmin?: boolean;
}

export function ProtectedRoute({
  path,
  component: Component,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const { user, isLoading, isAdmin } = useAuth();

  if (isLoading) {
    return (
      <Route path={path}>
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </Route>
    );
  }

  if (!user) {
    return (
      <Route path={path}>
        <Redirect to="/auth" />
      </Route>
    );
  }

  if (requireAdmin && !isAdmin) {
    return (
      <Route path={path}>
        <div className="flex flex-col items-center justify-center min-h-screen p-4 text-center">
          <h1 className="text-2xl font-bold mb-4">Zugriff verweigert</h1>
          <p className="mb-6">Du benötigst Administrator-Rechte, um auf diese Seite zuzugreifen.</p>
          <Redirect to="/" />
        </div>
      </Route>
    );
  }

  return (
    <Route path={path}>
      <Component />
    </Route>
  );
}