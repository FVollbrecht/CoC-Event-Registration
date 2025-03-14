import { useState } from "react";
import { Redirect } from "wouter";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/hooks/use-auth";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";

const loginSchema = z.object({
  username: z.string().min(3, { message: "Benutzername muss mindestens 3 Zeichen lang sein" }),
  password: z.string().min(6, { message: "Passwort muss mindestens 6 Zeichen lang sein" }),
});

const registerSchema = loginSchema.extend({
  discordUserId: z.string().min(1, { message: "Discord-ID ist erforderlich" }),
  confirmPassword: z.string().min(6, { message: "Passwort muss mindestens 6 Zeichen lang sein" }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwörter stimmen nicht überein",
  path: ["confirmPassword"],
});

type LoginFormValues = z.infer<typeof loginSchema>;
type RegisterFormValues = z.infer<typeof registerSchema>;

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const { user, loginMutation, registerMutation } = useAuth();

  const loginForm = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const registerForm = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: "",
      password: "",
      confirmPassword: "",
      discordUserId: "",
    },
  });

  function onLoginSubmit(data: LoginFormValues) {
    loginMutation.mutate(data);
  }

  function onRegisterSubmit(data: RegisterFormValues) {
    const { confirmPassword, ...registerData } = data;
    registerMutation.mutate(registerData);
  }

  // Wenn der Benutzer bereits angemeldet ist, zur Hauptseite weiterleiten
  if (user) {
    return <Redirect to="/" />;
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Linke Spalte mit Formularen */}
      <div className="flex flex-col justify-center flex-1 px-4 py-12 sm:px-6 lg:px-20 xl:px-24">
        <div className="w-full max-w-md mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              Discord Event Manager
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Registriere oder melde dich an, um deine Veranstaltungen zu verwalten
            </p>
          </div>

          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "login" | "register")}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">Anmelden</TabsTrigger>
              <TabsTrigger value="register">Registrieren</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <Card>
                <CardHeader>
                  <CardTitle>Anmelden</CardTitle>
                  <CardDescription>
                    Melde dich mit deinem Benutzerkonto an
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Form {...loginForm}>
                    <form 
                      onSubmit={loginForm.handleSubmit(onLoginSubmit)} 
                      className="space-y-4"
                    >
                      <FormField
                        control={loginForm.control}
                        name="username"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Benutzername</FormLabel>
                            <FormControl>
                              <Input placeholder="Benutzername" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={loginForm.control}
                        name="password"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Passwort</FormLabel>
                            <FormControl>
                              <Input type="password" placeholder="Passwort" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <Button 
                        type="submit" 
                        className="w-full"
                        disabled={loginMutation.isPending}
                      >
                        {loginMutation.isPending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 
                            Anmelden...
                          </>
                        ) : (
                          "Anmelden"
                        )}
                      </Button>
                    </form>
                  </Form>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="register">
              <Card>
                <CardHeader>
                  <CardTitle>Konto erstellen</CardTitle>
                  <CardDescription>
                    Erstelle ein neues Konto mit deiner Discord-ID
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Form {...registerForm}>
                    <form 
                      onSubmit={registerForm.handleSubmit(onRegisterSubmit)} 
                      className="space-y-4"
                    >
                      <FormField
                        control={registerForm.control}
                        name="username"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Benutzername</FormLabel>
                            <FormControl>
                              <Input placeholder="Benutzername" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="discordUserId"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Discord-ID</FormLabel>
                            <FormControl>
                              <Input placeholder="Deine Discord-ID" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="password"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Passwort</FormLabel>
                            <FormControl>
                              <Input type="password" placeholder="Passwort" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={registerForm.control}
                        name="confirmPassword"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Passwort bestätigen</FormLabel>
                            <FormControl>
                              <Input type="password" placeholder="Passwort bestätigen" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <Button 
                        type="submit" 
                        className="w-full"
                        disabled={registerMutation.isPending}
                      >
                        {registerMutation.isPending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 
                            Registrieren...
                          </>
                        ) : (
                          "Registrieren"
                        )}
                      </Button>
                    </form>
                  </Form>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Rechte Spalte mit Hintergrundbild und Informationen */}
      <div className="relative hidden lg:block lg:w-1/2">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600">
          <div className="absolute inset-0 bg-black opacity-20"></div>
          <div className="relative flex flex-col items-center justify-center h-full px-16 text-white">
            <h1 className="text-4xl font-extrabold tracking-tight mb-4">
              Discord Event Manager
            </h1>
            <p className="text-xl mb-8">
              Verwalte deine Gaming-Events und Teilnehmer mit unserer leistungsstarken Plattform
            </p>
            <ul className="space-y-4 text-lg">
              <li className="flex items-center">
                <span className="mr-2">✓</span>
                Verfolge bis zu 96 Teilnehmer pro Event
              </li>
              <li className="flex items-center">
                <span className="mr-2">✓</span>
                Verwalte Teams mit bis zu 18 Teilnehmern
              </li>
              <li className="flex items-center">
                <span className="mr-2">✓</span>
                Integration mit Discord für nahtlose Kommunikation
              </li>
              <li className="flex items-center">
                <span className="mr-2">✓</span>
                Sichere Benutzerauthentifizierung und Datenverwaltung
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}