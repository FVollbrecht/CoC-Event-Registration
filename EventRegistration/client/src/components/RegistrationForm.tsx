import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { useQuery } from "@tanstack/react-query";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { InfoIcon } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

interface RegistrationFormProps {
  isVisible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

const formSchema = z.object({
  name: z.string().min(2, {
    message: "Team name must be at least 2 characters.",
  }),
  count: z.coerce.number().min(1, {
    message: "Must have at least 1 participant.",
  }).max(18, {
    message: "Cannot exceed maximum of 18 participants per registration.",
  }),
  discordUserId: z.string().default("web-user"),
  discordUsername: z.string().default("Web User"),
});

export default function RegistrationForm({ isVisible, onCancel, onSuccess }: RegistrationFormProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  
  // Aktuelle Registrierungen für den angemeldeten Benutzer abrufen
  const { data: userRegistrations = [] } = useQuery<any[]>({
    queryKey: ["/api/registrations", user?.discordUserId || ""],
    queryFn: async () => {
      if (!user) return [];
      try {
        const res = await fetch(`/api/registrations?userId=${user.discordUserId}`);
        if (!res.ok) return [];
        return await res.json();
      } catch (error) {
        return [];
      }
    },
    enabled: isVisible && !!user, // Nur laden, wenn das Formular sichtbar ist und Benutzer angemeldet ist
  });
  
  // Gesamtzahl der bereits registrierten Teilnehmer berechnen
  const totalUserParticipants = userRegistrations.reduce(
    (total: number, reg: any) => total + reg.count, 
    0
  );
  
  // Anzahl der verbleibenden Plätze berechnen (von 18)
  const remainingUserSpots = Math.max(0, 18 - totalUserParticipants);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      count: 1,
      discordUserId: user?.discordUserId || "",
      discordUsername: user?.username || "",
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      await apiRequest("POST", "/api/registrations", values);
      
      toast({
        title: "Registration successful",
        description: `Team "${values.name}" has been registered with ${values.count} participants`,
      });
      
      form.reset();
      onSuccess();
    } catch (error: any) {
      const message = error.message || "An error occurred during registration";
      
      toast({
        title: "Registration failed",
        description: message,
        variant: "destructive",
      });
    }
  }

  if (!isVisible) return null;

  return (
    <div className="mb-6 bg-[#40444b] p-4 rounded-md">
      <h3 className="text-lg font-medium mb-3">New Registration</h3>
      
      {/* Benutzer-Limit Info-Box */}
      <Alert className="mb-4 bg-[#2f3136] border-blue-600">
        <div className="flex items-center gap-2">
          <InfoIcon className="h-4 w-4 text-blue-400" />
          <AlertDescription className="flex-1">
            <span className="text-sm text-gray-200">
              Du hast bereits <span className="font-bold text-blue-400">{totalUserParticipants}</span> von maximal 18 Teilnehmern angemeldet.
              <br/>
              Noch <span className="font-bold text-blue-400">{remainingUserSpots}</span> Plätze verfügbar.
            </span>
          </AlertDescription>
        </div>
      </Alert>
      
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Team/Group Name</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="Enter name" 
                      {...field} 
                      className="bg-[#2f3136] border-gray-600 text-white"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="count"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Number of Participants</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={18}
                      placeholder="Enter count"
                      {...field}
                      className="bg-[#2f3136] border-gray-600 text-white"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
          <div className="mt-4 flex justify-end space-x-2">
            <Button 
              type="button" 
              variant="secondary" 
              onClick={onCancel}
              className="bg-gray-600 hover:bg-gray-700"
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              className="bg-[#5865F2] hover:bg-opacity-80"
            >
              Register
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
