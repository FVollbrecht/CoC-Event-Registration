import { Client, GatewayIntentBits, Events } from 'discord.js';
import { IStorage } from '../storage';
import { handleRegCommand } from './commands';

let client: Client | null = null;

export async function initializeBot(storage: IStorage) {
  if (!process.env.DISCORD_TOKEN) {
    console.warn('DISCORD_TOKEN not found in environment variables. Discord bot will not start.');
    return;
  }

  try {
    // Create a new client instance
    client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
      ],
    });

    // Handle ready event
    client.once(Events.ClientReady, (readyClient) => {
      console.log(`Discord bot logged in as ${readyClient.user.tag}`);
      
      // Store server info if available
      if (client?.guilds.cache.size) {
        const guild = client.guilds.cache.first();
        if (guild) {
          storage.updateEventConfig({
            serverId: guild.id,
            serverName: guild.name
          });
        }
      }
    });

    // Handle message creation event
    client.on(Events.MessageCreate, async (message) => {
      // Ignore messages from bots
      if (message.author.bot) return;
      
      // Process !reg command
      if (message.content.startsWith('!reg ')) {
        await handleRegCommand(message, storage);
      }
    });

    // Login to Discord
    await client.login(process.env.DISCORD_TOKEN);
    
    return client;
  } catch (error) {
    console.error('Failed to initialize Discord bot:', error);
  }
}

export function getClient() {
  return client;
}
