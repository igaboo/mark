import re, os
from dotenv import load_dotenv
from discord import Intents
from discord.ext.commands import Bot
from bot_utils import send_message, delete_message_with_retry

load_dotenv()

intents = Intents.default()
intents.message_content = True
bot = Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready() -> None:
    """
    Log in as the bot.
    """
    print(f'Logged in as {bot.user} ({bot.user.id})')

@bot.event
async def on_message(message) -> None:
    """
    Check if the message contains a Facebook Marketplace URL and add it to the queue.
    """
    if message.author == bot.user: 
        return
    
    urls = re.findall(r'https://www\.facebook\.com/marketplace/[^\s]+', message.content)
    if urls:
        await delete_message_with_retry(message)
        await send_message(message, message.author, urls[0])
    
    await bot.process_commands(message)

bot.run(os.getenv('DB_TOKEN'))
