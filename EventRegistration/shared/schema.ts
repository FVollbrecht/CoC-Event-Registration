import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  discordUserId: text("discord_user_id").notNull(),
  isAdmin: boolean("is_admin").notNull().default(false),
  lastLogin: timestamp("last_login").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
  discordUserId: true,
  isAdmin: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

// Registration schema for event participants
export const registrations = pgTable("registrations", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  count: integer("count").notNull(),
  discordUserId: text("discord_user_id").notNull(),
  discordUsername: text("discord_username").notNull(),
  registeredAt: timestamp("registered_at").defaultNow(),
});

export const insertRegistrationSchema = createInsertSchema(registrations).pick({
  name: true,
  count: true,
  discordUserId: true,
  discordUsername: true,
});

export type InsertRegistration = z.infer<typeof insertRegistrationSchema>;
export type Registration = typeof registrations.$inferSelect;

// Activity log for recent actions
export const activityLogs = pgTable("activity_logs", {
  id: serial("id").primaryKey(),
  type: text("type").notNull(), // "register", "update", "cancel"
  oldCount: integer("old_count"),
  newCount: integer("new_count"),
  registrationId: integer("registration_id"),
  name: text("name").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
});

export const insertActivityLogSchema = createInsertSchema(activityLogs).pick({
  type: true,
  oldCount: true,
  newCount: true,
  registrationId: true,
  name: true,
});

export type InsertActivityLog = z.infer<typeof insertActivityLogSchema>;
export type ActivityLog = typeof activityLogs.$inferSelect;

// Configuration for the event
export const eventConfig = pgTable("event_config", {
  id: serial("id").primaryKey(),
  maxCapacity: integer("max_capacity").notNull().default(96),
  eventName: text("event_name").notNull().default("Event"),
  serverId: text("server_id").notNull().default(""),
  serverName: text("server_name").notNull().default("Discord Server"),
});

export const insertEventConfigSchema = createInsertSchema(eventConfig).pick({
  maxCapacity: true,
  eventName: true,
  serverId: true,
  serverName: true,
});

export type InsertEventConfig = z.infer<typeof insertEventConfigSchema>;
export type EventConfig = typeof eventConfig.$inferSelect;
