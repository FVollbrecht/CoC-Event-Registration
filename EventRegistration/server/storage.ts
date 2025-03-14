import { 
  InsertRegistration, 
  Registration, 
  InsertActivityLog, 
  ActivityLog, 
  EventConfig, 
  InsertEventConfig,
  User,
  InsertUser
} from "@shared/schema";

export interface IStorage {
  // User methods
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  getUserByDiscordId(discordUserId: string): Promise<User | undefined>;
  getAllUsers(): Promise<User[]>;
  createUser(user: InsertUser): Promise<User>;
  updateUserAdmin(userId: number, isAdmin: boolean): Promise<User | undefined>;
  updateLastLogin(userId: number): Promise<User | undefined>;
  
  // Registration methods
  getRegistrations(): Promise<Registration[]>;
  getRegistration(id: number): Promise<Registration | undefined>;
  getRegistrationByName(name: string): Promise<Registration | undefined>;
  getRegistrationsByDiscordUserId(discordUserId: string): Promise<Registration[]>;
  createRegistration(registration: InsertRegistration): Promise<Registration>;
  updateRegistration(id: number, count: number): Promise<Registration | undefined>;
  deleteRegistration(id: number): Promise<boolean>;
  
  // Activity log methods
  getActivityLogs(limit?: number): Promise<ActivityLog[]>;
  createActivityLog(log: InsertActivityLog): Promise<ActivityLog>;
  
  // Event config methods
  getEventConfig(): Promise<EventConfig>;
  updateEventConfig(config: Partial<InsertEventConfig>): Promise<EventConfig>;
  
  // Stats methods
  getCurrentRegistrationCount(): Promise<number>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private registrations: Map<number, Registration>;
  private activityLogs: ActivityLog[];
  private eventConfig: EventConfig;
  private userCurrentId: number;
  private registrationCurrentId: number;
  private activityLogCurrentId: number;

  constructor() {
    this.users = new Map();
    this.registrations = new Map();
    this.activityLogs = [];
    this.userCurrentId = 1;
    this.registrationCurrentId = 1;
    this.activityLogCurrentId = 1;
    
    // Default event config
    this.eventConfig = {
      id: 1,
      maxCapacity: 96,
      eventName: "Gaming Event",
      serverId: "",
      serverName: "CoC - hosted by WLS"
    };
  }

  // User methods
  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.userCurrentId++;
    // Der erste registrierte Benutzer wird automatisch zum Admin
    const user: User = { 
      ...insertUser, 
      id,
      isAdmin: insertUser.isAdmin || this.users.size === 0, // Der erste Benutzer wird automatisch Admin
      lastLogin: new Date() 
    };
    this.users.set(id, user);
    return user;
  }
  
  async updateUserAdmin(userId: number, isAdmin: boolean): Promise<User | undefined> {
    const user = await this.getUser(userId);
    if (!user) return undefined;
    
    const updatedUser: User = {
      ...user,
      isAdmin
    };
    
    this.users.set(userId, updatedUser);
    return updatedUser;
  }
  
  async updateLastLogin(userId: number): Promise<User | undefined> {
    const user = await this.getUser(userId);
    if (!user) return undefined;
    
    const updatedUser: User = {
      ...user,
      lastLogin: new Date()
    };
    
    this.users.set(userId, updatedUser);
    return updatedUser;
  }
  
  async getUserByDiscordId(discordUserId: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.discordUserId === discordUserId,
    );
  }
  
  async getAllUsers(): Promise<User[]> {
    return Array.from(this.users.values());
  }

  // Registration methods
  async getRegistrations(): Promise<Registration[]> {
    return Array.from(this.registrations.values());
  }

  async getRegistration(id: number): Promise<Registration | undefined> {
    return this.registrations.get(id);
  }

  async getRegistrationByName(name: string): Promise<Registration | undefined> {
    return Array.from(this.registrations.values()).find(
      (reg) => reg.name.toLowerCase() === name.toLowerCase()
    );
  }

  async getRegistrationsByDiscordUserId(discordUserId: string): Promise<Registration[]> {
    return Array.from(this.registrations.values()).filter(
      (reg) => reg.discordUserId === discordUserId
    );
  }

  async createRegistration(registration: InsertRegistration): Promise<Registration> {
    const id = this.registrationCurrentId++;
    const now = new Date();
    const newRegistration: Registration = { 
      ...registration, 
      id, 
      registeredAt: now 
    };
    
    this.registrations.set(id, newRegistration);
    
    // Add to activity log
    await this.createActivityLog({
      type: "register",
      oldCount: 0,
      newCount: registration.count,
      registrationId: id,
      name: registration.name
    });
    
    return newRegistration;
  }

  async updateRegistration(id: number, count: number): Promise<Registration | undefined> {
    const registration = this.registrations.get(id);
    if (!registration) return undefined;
    
    const oldCount = registration.count;
    const updatedRegistration = { ...registration, count };
    this.registrations.set(id, updatedRegistration);
    
    // Add to activity log
    await this.createActivityLog({
      type: "update",
      oldCount: oldCount,
      newCount: count,
      registrationId: id,
      name: registration.name
    });
    
    return updatedRegistration;
  }

  async deleteRegistration(id: number): Promise<boolean> {
    const registration = this.registrations.get(id);
    if (!registration) return false;
    
    const result = this.registrations.delete(id);
    
    // Add to activity log
    if (result) {
      await this.createActivityLog({
        type: "cancel",
        oldCount: registration.count,
        newCount: 0,
        registrationId: id,
        name: registration.name
      });
    }
    
    return result;
  }

  // Activity log methods
  async getActivityLogs(limit: number = 10): Promise<ActivityLog[]> {
    return this.activityLogs
      .sort((a, b) => {
        // Sicherstellen, dass die Timestamps nicht null sind
        const timeA = a.timestamp ? a.timestamp.getTime() : 0;
        const timeB = b.timestamp ? b.timestamp.getTime() : 0;
        return timeB - timeA;
      })
      .slice(0, limit);
  }

  async createActivityLog(log: InsertActivityLog): Promise<ActivityLog> {
    const id = this.activityLogCurrentId++;
    const now = new Date();
    
    // Stelle sicher, dass alle Felder definiert sind
    const safeLog: ActivityLog = {
      ...log,
      id,
      timestamp: now,
      oldCount: log.oldCount ?? null,
      newCount: log.newCount ?? null,
      registrationId: log.registrationId ?? null
    };
    
    this.activityLogs.push(safeLog);
    
    // Keep only the latest 100 logs
    if (this.activityLogs.length > 100) {
      this.activityLogs = this.activityLogs
        .sort((a, b) => {
          // Sicherstellen, dass die Timestamps nicht null sind
          const timeA = a.timestamp ? a.timestamp.getTime() : 0;
          const timeB = b.timestamp ? b.timestamp.getTime() : 0;
          return timeB - timeA;
        })
        .slice(0, 100);
    }
    
    return safeLog;
  }

  // Event config methods
  async getEventConfig(): Promise<EventConfig> {
    return this.eventConfig;
  }

  async updateEventConfig(config: Partial<InsertEventConfig>): Promise<EventConfig> {
    this.eventConfig = { ...this.eventConfig, ...config };
    return this.eventConfig;
  }

  // Stats methods
  async getCurrentRegistrationCount(): Promise<number> {
    const registrations = Array.from(this.registrations.values());
    return registrations.reduce((total, reg) => total + reg.count, 0);
  }
}

export const storage = new MemStorage();
