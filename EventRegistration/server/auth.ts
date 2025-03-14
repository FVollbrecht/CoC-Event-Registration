import passport from "passport";
import { Strategy as LocalStrategy } from "passport-local";
import { Express, Request, Response, NextFunction } from "express";
import session from "express-session";
import { scrypt, randomBytes, timingSafeEqual } from "crypto";
import { promisify } from "util";
import { storage } from "./storage";
import { User, InsertUser } from "@shared/schema";

declare global {
  namespace Express {
    // Definiert, dass User-Objekte im Express-Request die Felder aus unserem User-Typ haben
    interface User {
      id: number;
      username: string;
      password: string;
      discordUserId: string;
      isAdmin: boolean;
      lastLogin: Date | null;
    }
  }
}

const scryptAsync = promisify(scrypt);

export async function hashPassword(password: string) {
  const salt = randomBytes(16).toString("hex");
  const buf = (await scryptAsync(password, salt, 64)) as Buffer;
  return `${buf.toString("hex")}.${salt}`;
}

export async function comparePasswords(supplied: string, stored: string) {
  const [hashed, salt] = stored.split(".");
  const hashedBuf = Buffer.from(hashed, "hex");
  const suppliedBuf = (await scryptAsync(supplied, salt, 64)) as Buffer;
  return timingSafeEqual(hashedBuf, suppliedBuf);
}

// Middleware für Zugriffsrechteprüfung
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  if (!req.isAuthenticated()) {
    return res.status(401).json({ message: "Unauthorized" });
  }
  next();
}

// Middleware zum Überprüfen von Admin-Rechten
export function requireAdmin(req: Request, res: Response, next: NextFunction) {
  if (!req.isAuthenticated() || !req.user.isAdmin) {
    return res.status(403).json({ message: "Forbidden: Admin access required" });
  }
  next();
}

// Middleware zum Überprüfen, ob der Benutzer Besitzer einer Registrierung ist
export async function requireOwnership(req: Request, res: Response, next: NextFunction) {
  if (!req.isAuthenticated()) {
    return res.status(401).json({ message: "Unauthorized" });
  }

  const regId = parseInt(req.params.id);
  if (isNaN(regId)) {
    return res.status(400).json({ message: "Invalid ID format" });
  }

  const registration = await storage.getRegistration(regId);
  if (!registration) {
    return res.status(404).json({ message: "Registration not found" });
  }

  // Erlauben, wenn Benutzer Admin ist oder der Eigentümer der Registrierung
  if (req.user.isAdmin || req.user.discordUserId === registration.discordUserId) {
    return next();
  }

  return res.status(403).json({ 
    message: "Forbidden: You can only modify your own registrations" 
  });
}

export function setupAuth(app: Express) {
  const sessionSettings: session.SessionOptions = {
    secret: process.env.SESSION_SECRET || "default-secret-key-change-in-production",
    resave: false,
    saveUninitialized: false,
    cookie: {
      secure: process.env.NODE_ENV === "production",
      maxAge: 1000 * 60 * 60 * 24 // 24 Stunden
    }
  };

  app.use(session(sessionSettings));
  app.use(passport.initialize());
  app.use(passport.session());

  passport.use(
    new LocalStrategy(async (username, password, done) => {
      try {
        const user = await storage.getUserByUsername(username);
        if (!user || !(await comparePasswords(password, user.password))) {
          return done(null, false);
        } else {
          await storage.updateLastLogin(user.id);
          return done(null, user);
        }
      } catch (error) {
        return done(error);
      }
    }),
  );

  passport.serializeUser((user, done) => {
    done(null, user.id);
  });

  passport.deserializeUser(async (id: number, done) => {
    try {
      const user = await storage.getUser(id);
      done(null, user);
    } catch (error) {
      done(error);
    }
  });

  // Auth Endpoints
  app.post("/api/auth/register", async (req, res, next) => {
    try {
      const { username, password: rawPassword, discordUserId } = req.body;
      if (!username || !rawPassword || !discordUserId) {
        return res.status(400).json({ message: "Missing required fields" });
      }

      // Überprüfen, ob der Benutzername bereits existiert
      const existingUser = await storage.getUserByUsername(username);
      if (existingUser) {
        return res.status(400).json({ message: "Username already exists" });
      }

      // Überprüfen, ob die Discord-ID bereits existiert
      const discordUser = await storage.getUserByDiscordId(discordUserId);
      if (discordUser) {
        return res.status(400).json({ message: "Discord user already registered" });
      }

      // Neuen Benutzer erstellen
      const hashedPassword = await hashPassword(rawPassword);
      const user = await storage.createUser({
        username,
        password: hashedPassword,
        discordUserId,
        isAdmin: false // Standardmäßig kein Admin
      });

      // Sicherheitsrelevante Daten entfernen
      const { password, ...userResponse } = user;

      req.login(user, (err) => {
        if (err) return next(err);
        res.status(201).json(userResponse);
      });
    } catch (error) {
      res.status(500).json({ message: "An error occurred during registration" });
    }
  });

  app.post("/api/auth/login", (req, res, next) => {
    passport.authenticate("local", (err: Error, user: User, info: any) => {
      if (err) return next(err);
      if (!user) {
        return res.status(401).json({ message: "Invalid username or password" });
      }
      
      req.login(user, (err) => {
        if (err) return next(err);
        
        // Sicherheitsrelevante Daten entfernen
        const { password, ...userResponse } = user;
        
        res.json(userResponse);
      });
    })(req, res, next);
  });

  app.post("/api/auth/logout", (req, res) => {
    req.logout(() => {
      res.status(200).json({ message: "Logged out successfully" });
    });
  });

  app.get("/api/auth/user", (req, res) => {
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "Not authenticated" });
    }
    
    if (!req.user) {
      return res.status(401).json({ message: "Not authenticated" });
    }
    
    // Sicherheitsrelevante Daten entfernen
    const { password, ...userResponse } = req.user;
    
    res.json(userResponse);
  });

  // API Endpoint: Get all users (admin only)
  app.get("/api/auth/users", requireAdmin, async (req, res) => {
    try {
      // Alle Benutzer aus der Datenbank abrufen
      const users = await Promise.all(
        (await storage.getAllUsers()).map((user: User) => {
          // Passwörter aus der Antwort entfernen
          const { password, ...userWithoutPassword } = user;
          return userWithoutPassword;
        })
      );
      
      res.json(users);
    } catch (error) {
      res.status(500).json({ message: "An error occurred while fetching users" });
    }
  });

  // Admin-only Endpoint zum Setzen von Admin-Rechten
  app.patch("/api/auth/admin/:userId", requireAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      if (isNaN(userId)) {
        return res.status(400).json({ message: "Invalid user ID" });
      }

      const { isAdmin } = req.body;
      if (typeof isAdmin !== "boolean") {
        return res.status(400).json({ message: "isAdmin must be a boolean" });
      }

      // Nicht erlauben, eigene Admin-Rechte zu entfernen
      if (req.user && userId === req.user.id && !isAdmin) {
        return res.status(400).json({ message: "Cannot remove own admin rights" });
      }

      const updatedUser = await storage.updateUserAdmin(userId, isAdmin);
      if (!updatedUser) {
        return res.status(404).json({ message: "User not found" });
      }

      // Sicherheitsrelevante Daten entfernen
      const { password, ...userResponse } = updatedUser;

      res.json(userResponse);
    } catch (error) {
      res.status(500).json({ message: "An error occurred while updating admin status" });
    }
  });
}