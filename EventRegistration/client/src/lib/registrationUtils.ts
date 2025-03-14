import { Registration } from "@shared/schema";

/**
 * Calculate the percentage of capacity filled
 */
export function calculatePercentFilled(currentCount: number, maxCapacity: number): number {
  return Math.floor((currentCount / maxCapacity) * 100);
}

/**
 * Format the user's initials from their discord username
 */
export function formatUserInitials(username: string): string {
  if (!username) return "??";
  
  // Handle usernames with discriminator (#1234)
  const parts = username.split("#");
  const name = parts[0];
  
  if (name.length <= 2) return name.toUpperCase();
  
  // Extract first two characters
  return name.slice(0, 2).toUpperCase();
}

/**
 * Get the activity type color
 */
export function getActivityTypeColor(type: string): string {
  switch (type) {
    case "register":
      return "#57F287"; // green
    case "update":
      return "#FEE75C"; // yellow
    case "cancel":
      return "#ED4245"; // red
    default:
      return "#5865F2"; // blurple
  }
}

/**
 * Format the count difference for activity logs
 */
export function formatCountDifference(oldCount: number, newCount: number): string {
  const diff = newCount - oldCount;
  if (diff > 0) return `+${diff}`;
  return diff.toString();
}

/**
 * Check if adding or updating a registration would exceed capacity
 */
export function wouldExceedCapacity(
  registrations: Registration[],
  count: number,
  maxCapacity: number,
  existingId?: number
): boolean {
  const currentTotal = registrations.reduce((sum, reg) => {
    // Skip the existing registration if updating
    if (existingId && reg.id === existingId) return sum;
    return sum + reg.count;
  }, 0);
  
  return currentTotal + count > maxCapacity;
}
