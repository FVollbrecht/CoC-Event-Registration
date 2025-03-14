import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { z } from "zod";
import { insertRegistrationSchema, insertActivityLogSchema } from "@shared/schema";
import { initializeBot } from "./discord/bot";
import { setupAuth, requireAuth, requireAdmin, requireOwnership } from "./auth";
import crypto from "crypto";

// Aktive Sicherheits-Tokens für API-Zugriff speichern (Memory Store in Produktion durch Redis ersetzen)
const validSecurityTokens = new Set<string>();

// Middleware zum Überprüfen des Sicherheits-Tokens bei Schreiboperationen
function validateSecurityToken(req: Request, res: Response, next: NextFunction) {
  // GET-Anfragen benötigen keine Token-Validierung
  if (req.method === 'GET') {
    return next();
  }
  
  const token = req.headers['x-security-token'] as string;
  const clientVersion = req.headers['x-client-version'] as string;
  
  // Prüflogik für API-Token
  if (!token) {
    return res.status(403).json({ message: "Security token missing" });
  }
  
  // Speichern des Tokens wenn es das erste Mal gesehen wird
  // In einer Produktions-App wäre hier eine striktere Validierung mit Server-generierten Tokens
  if (!validSecurityTokens.has(token)) {
    // Maximal 1000 Tokens speichern, um Speicherprobleme zu vermeiden
    if (validSecurityTokens.size >= 1000) {
      const oldestToken = Array.from(validSecurityTokens)[0];
      validSecurityTokens.delete(oldestToken);
    }
    validSecurityTokens.add(token);
  }
  
  // Überprüfen der Client-Version (optional)
  if (!clientVersion || clientVersion !== "1.0.0") {
    console.warn(`Outdated client version detected: ${clientVersion}`);
    // In der Produktion könnte man hier alte Clients ablehnen
  }
  
  // Token ist gültig, Anfrage fortsetzen
  next();
}

export async function registerRoutes(app: Express): Promise<Server> {
  // Authentifizierung einrichten
  setupAuth(app);
  
  // Sicherheits-Middleware für alle API-Routen registrieren
  app.use('/api', validateSecurityToken);
  
  // Start the Discord bot
  await initializeBot(storage);

  // API Endpoint: Get event config
  app.get("/api/config", async (req, res) => {
    const config = await storage.getEventConfig();
    res.json(config);
  });

  // API Endpoint: Update event config (nur für Admins)
  app.patch("/api/config", requireAdmin, async (req, res) => {
    const config = await storage.updateEventConfig(req.body);
    res.json(config);
  });

  // API Endpoint: Get all registrations
  app.get("/api/registrations", async (req, res) => {
    // Filteroption für Benutzer-ID hinzufügen
    const userId = req.query.userId as string;
    
    if (userId) {
      const userRegistrations = await storage.getRegistrationsByDiscordUserId(userId);
      return res.json(userRegistrations);
    }
    
    const registrations = await storage.getRegistrations();
    res.json(registrations);
  });

  // API Endpoint: Create a new registration (angemeldete Benutzer)
  app.post("/api/registrations", requireAuth, async (req, res) => {
    try {
      const validatedData = insertRegistrationSchema.parse(req.body);
      
      // Prüfe ob die Anzahl das Limit pro Benutzer überschreitet
      if (validatedData.count > 18) {
        return res.status(400).json({
          message: "Maximum 18 participants per registration allowed"
        });
      }
      
      // Check if there's an existing registration with the same name
      const existingRegistration = await storage.getRegistrationByName(validatedData.name);
      if (existingRegistration) {
        return res.status(400).json({ 
          message: "A registration with this name already exists" 
        });
      }
      
      // Prüfe ob der Benutzer bereits ein Team hat (wenn er nicht Admin ist)
      const user = await storage.getUserByDiscordId(validatedData.discordUserId);
      if (user && !user.isAdmin) {
        const userRegistrations = await storage.getRegistrationsByDiscordUserId(validatedData.discordUserId);
        if (userRegistrations.length >= 1) {
          return res.status(400).json({
            message: "Non-admin users can only register one team"
          });
        }
      }
      
      // Prüfe ob Benutzer das Gesamtlimit überschreitet (18 Teilnehmer total)
      const userRegistrations = await storage.getRegistrationsByDiscordUserId(validatedData.discordUserId);
      const currentUserTotal = userRegistrations.reduce((total, reg) => total + reg.count, 0);
      
      if (currentUserTotal + validatedData.count > 18) {
        return res.status(400).json({
          message: `User already has ${currentUserTotal} participants registered. Cannot exceed the maximum of 18 participants per user.`
        });
      }
      
      // Check if adding this registration would exceed capacity
      const currentCount = await storage.getCurrentRegistrationCount();
      const config = await storage.getEventConfig();
      
      if (currentCount + validatedData.count > config.maxCapacity) {
        return res.status(400).json({ 
          message: `Cannot register ${validatedData.count} participants. Only ${config.maxCapacity - currentCount} spots available.` 
        });
      }
      
      const registration = await storage.createRegistration(validatedData);
      res.status(201).json(registration);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: error.errors[0].message });
      } else {
        res.status(500).json({ message: "An unexpected error occurred" });
      }
    }
  });

  // API Endpoint: Update an existing registration (nur Eigentümer oder Admins)
  app.patch("/api/registrations/:id", requireOwnership, async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid ID format" });
      }
      
      const { count } = req.body;
      if (typeof count !== "number" || count < 1) {
        return res.status(400).json({ message: "Invalid count value" });
      }
      
      // Prüfe ob die Anzahl das Limit pro Benutzer überschreitet
      if (count > 18) {
        return res.status(400).json({
          message: "Maximum 18 participants per registration allowed"
        });
      }
      
      // Check if the registration exists
      const existingRegistration = await storage.getRegistration(id);
      if (!existingRegistration) {
        return res.status(404).json({ message: "Registration not found" });
      }
      
      // Prüfe, ob das Benutzer-Gesamtlimit überschritten wird (18 Teilnehmer total)
      const userRegistrations = await storage.getRegistrationsByDiscordUserId(existingRegistration.discordUserId);
      const currentUserTotal = userRegistrations.reduce((total, reg) => total + reg.count, 0);
      const adjustedUserTotal = currentUserTotal - existingRegistration.count; // Alte Anzahl abziehen
      
      if (adjustedUserTotal + count > 18) {
        return res.status(400).json({
          message: `User already has ${adjustedUserTotal} participants registered in other teams. Cannot exceed the maximum of 18 participants per user.`
        });
      }
      
      // Check if updating would exceed capacity
      const currentCount = await storage.getCurrentRegistrationCount();
      const config = await storage.getEventConfig();
      const difference = count - existingRegistration.count;
      
      if (currentCount + difference > config.maxCapacity) {
        return res.status(400).json({ 
          message: `Cannot update to ${count} participants. Only ${config.maxCapacity - currentCount + existingRegistration.count} spots available.` 
        });
      }
      
      const updatedRegistration = await storage.updateRegistration(id, count);
      res.json(updatedRegistration);
    } catch (error) {
      res.status(500).json({ message: "An unexpected error occurred" });
    }
  });

  // API Endpoint: Delete a registration (nur Eigentümer oder Admins)
  app.delete("/api/registrations/:id", requireOwnership, async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid ID format" });
      }
      
      const success = await storage.deleteRegistration(id);
      if (!success) {
        return res.status(404).json({ message: "Registration not found" });
      }
      
      res.status(204).end();
    } catch (error) {
      res.status(500).json({ message: "An unexpected error occurred" });
    }
  });

  // API Endpoint: Get activity logs
  app.get("/api/activity", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 10;
      const logs = await storage.getActivityLogs(limit);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ message: "An unexpected error occurred" });
    }
  });

  // API Endpoint: Get stats
  app.get("/api/stats", async (req, res) => {
    try {
      const config = await storage.getEventConfig();
      const currentCount = await storage.getCurrentRegistrationCount();
      const registrations = await storage.getRegistrations();
      
      res.json({
        totalRegistrations: registrations.length,
        currentCount,
        availableSpots: config.maxCapacity - currentCount,
        maxCapacity: config.maxCapacity
      });
    } catch (error) {
      res.status(500).json({ message: "An unexpected error occurred" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
