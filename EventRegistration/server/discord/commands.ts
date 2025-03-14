import { Message } from 'discord.js';
import { IStorage } from '../storage';

export async function handleRegCommand(message: Message, storage: IStorage) {
  try {
    // Parse the command: !reg #Name #Anzahl
    const content = message.content.trim();
    
    // Use regex to extract name and count from the message
    const regexMatch = content.match(/^!reg\s+#([^\s#]+)\s+#(\d+)$/);
    
    if (!regexMatch) {
      return message.reply(
        'Invalid format. Please use: `!reg #TeamName #NumberOfParticipants`\n' +
        'Example: `!reg #TeamAwesome #4`'
      );
    }
    
    const name = regexMatch[1];
    const count = parseInt(regexMatch[2], 10);
    
    if (isNaN(count) || count < 1) {
      return message.reply('The number of participants must be a positive number.');
    }
    
    // Prüfen, ob die Anzahl das Limit pro Benutzer überschreitet
    if (count > 18) {
      return message.reply('Du kannst maximal 18 Teilnehmer pro Team registrieren.');
    }
    
    // Check if team name already exists
    const existingRegistration = await storage.getRegistrationByName(name);
    
    // Alle Registrierungen des Nutzers abrufen, um das Gesamtlimit zu prüfen
    const userRegistrations = await storage.getRegistrationsByDiscordUserId(message.author.id);
    const currentUserTotal = userRegistrations.reduce((total, reg) => total + reg.count, 0);
    
    // Wenn dies eine Aktualisierung ist, ziehen wir die alte Anzahl ab
    let adjustedUserTotal = currentUserTotal;
    if (existingRegistration && existingRegistration.discordUserId === message.author.id) {
      adjustedUserTotal -= existingRegistration.count;
    }
    
    // Prüfen, ob die neue Gesamtzahl das Limit überschreitet
    if (adjustedUserTotal + count > 18) {
      return message.reply(`Du hast bereits ${adjustedUserTotal} Teilnehmer angemeldet. Mit dieser Anmeldung würdest du das Maximum von 18 Teilnehmern überschreiten.`);
    }
    
    if (existingRegistration) {
      const oldCount = existingRegistration.count;
      
      // If the user is the same, update the registration
      if (existingRegistration.discordUserId === message.author.id) {
        // Diese Prüfung ist bereits oben durchgeführt worden und redundant
      
        // Verify if the update would exceed capacity
        const currentTotal = await storage.getCurrentRegistrationCount();
        const config = await storage.getEventConfig();
        const difference = count - oldCount;
        
        if (currentTotal + difference > config.maxCapacity) {
          const availableSpots = config.maxCapacity - currentTotal + oldCount;
          return message.reply(
            `Cannot update to ${count} participants. Only ${availableSpots} spots are available.`
          );
        }
        
        // Update the registration
        await storage.updateRegistration(existingRegistration.id, count);
        
        return message.reply(
          `Updated registration for team "${name}" from ${oldCount} to ${count} participants.`
        );
      } else {
        return message.reply(
          `A team with the name "${name}" is already registered by another user.`
        );
      }
    }
    
    // Check if adding this registration would exceed capacity
    const currentTotal = await storage.getCurrentRegistrationCount();
    const config = await storage.getEventConfig();
    
    if (currentTotal + count > config.maxCapacity) {
      const availableSpots = config.maxCapacity - currentTotal;
      return message.reply(
        `Cannot register ${count} participants. Only ${availableSpots} spots are available.`
      );
    }
    
    // Create a new registration
    await storage.createRegistration({
      name,
      count,
      discordUserId: message.author.id,
      discordUsername: message.author.tag
    });
    
    // Calculate remaining spots
    const remainingSpots = config.maxCapacity - (currentTotal + count);
    
    return message.reply(
      `Successfully registered team "${name}" with ${count} participants.\n` +
      `Remaining spots: ${remainingSpots}/${config.maxCapacity}`
    );
    
  } catch (error) {
    console.error('Error handling registration command:', error);
    return message.reply('An error occurred while processing your registration. Please try again later.');
  }
}
