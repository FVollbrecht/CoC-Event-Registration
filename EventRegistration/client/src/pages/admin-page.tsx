import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Loader2, UserCheck, UserX } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

type User = {
  id: number;
  username: string;
  discordUserId: string;
  isAdmin: boolean;
  lastLogin: string;
};

export default function AdminPage() {
  const [confirmDialog, setConfirmDialog] = useState<{ isOpen: boolean; user: User | null; action: "grant" | "revoke" }>({
    isOpen: false,
    user: null,
    action: "grant"
  });
  const { toast } = useToast();
  const { isAdmin } = useAuth();

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ["/api/auth/users"],
    queryFn: async () => {
      const res = await fetch("/api/auth/users");
      if (!res.ok) throw new Error("Failed to fetch users");
      return res.json();
    },
  });

  const updateAdminStatus = useMutation({
    mutationFn: async ({ userId, isAdmin }: { userId: number; isAdmin: boolean }) => {
      const res = await apiRequest("PATCH", `/api/auth/admin/${userId}`, { isAdmin });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/auth/users"] });
      setConfirmDialog({ isOpen: false, user: null, action: "grant" });
      toast({
        title: "Administratorrechte aktualisiert",
        description: "Die Benutzerrechte wurden erfolgreich aktualisiert.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Aktualisierung fehlgeschlagen",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  function handleAdminAction(user: User, action: "grant" | "revoke") {
    setConfirmDialog({
      isOpen: true,
      user,
      action
    });
  }

  function confirmAdminAction() {
    if (!confirmDialog.user) return;
    updateAdminStatus.mutate({ 
      userId: confirmDialog.user.id, 
      isAdmin: confirmDialog.action === "grant" 
    });
  }

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Zugriff verweigert</CardTitle>
            <CardDescription>
              Du benötigst Administrator-Rechte, um auf diese Seite zuzugreifen.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container py-10">
      <h1 className="text-3xl font-bold mb-6">Admin-Dashboard</h1>
      
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Benutzerverwaltung</CardTitle>
          <CardDescription>
            Verwalte Benutzer und ihre Administratorrechte
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : !users || users.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">
              Keine Benutzer gefunden
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Benutzername</TableHead>
                  <TableHead>Discord-ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Letzte Anmeldung</TableHead>
                  <TableHead className="text-right">Aktionen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{user.discordUserId}</TableCell>
                    <TableCell>
                      {user.isAdmin ? (
                        <Badge variant="default" className="bg-green-600">Administrator</Badge>
                      ) : (
                        <Badge variant="outline">Benutzer</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.lastLogin ? new Date(user.lastLogin).toLocaleString() : "Nie"}
                    </TableCell>
                    <TableCell className="text-right">
                      {user.isAdmin ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAdminAction(user, "revoke")}
                          className="text-red-500 border-red-200 hover:bg-red-50"
                        >
                          <UserX className="h-4 w-4 mr-1" />
                          Admin-Rechte entziehen
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAdminAction(user, "grant")}
                          className="text-green-500 border-green-200 hover:bg-green-50"
                        >
                          <UserCheck className="h-4 w-4 mr-1" />
                          Admin-Rechte gewähren
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog 
        open={confirmDialog.isOpen} 
        onOpenChange={(open) => setConfirmDialog(prev => ({ ...prev, isOpen: open }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {confirmDialog.action === "grant" 
                ? "Admin-Rechte gewähren" 
                : "Admin-Rechte entziehen"}
            </DialogTitle>
            <DialogDescription>
              {confirmDialog.action === "grant"
                ? `Möchtest du ${confirmDialog.user?.username} wirklich Administratorrechte gewähren?`
                : `Möchtest du ${confirmDialog.user?.username} wirklich die Administratorrechte entziehen?`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
            >
              Abbrechen
            </Button>
            <Button 
              variant={confirmDialog.action === "grant" ? "default" : "destructive"}
              onClick={confirmAdminAction}
              disabled={updateAdminStatus.isPending}
            >
              {updateAdminStatus.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Bestätigen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}