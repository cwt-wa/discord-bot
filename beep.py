# bot.py
import os
import subprocess
from sseclient import SSEClient 
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SCRIPT = os.getenv('SCRIPT') or './handle.js'
client = discord.Client()

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
  if message.author == client.user:
    return
  if message.content.strip() == '!cwt':
    await message.channel.send("Beep Bop CWT Bot. I act upon commands (see !cwtcommands) but I also mirror the CWT chat.")
    return
  node = subprocess.run(
      ["node", SCRIPT, message.author.display_name, message.content.strip()],
      stdout=subprocess.PIPE).stdout.decode('utf8')
  try:
    result = list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]
    await message.channel.send(result)
  except:
    print(message.content, "did not yield a result")
client.run(TOKEN)

