# bot.py
import os
import subprocess
import discord
from dotenv import load_dotenv
import json
import requests
import time
from sseclient import SSEClient


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SCRIPT = os.getenv('SCRIPT') or './'
LISTEN = os.getenv('LISTEN') == "1"
client = discord.Client()


async def listen():
  posted = {}
  starting = time.time()
  url = 'https://cwtsite.com/api/message/listen'
  # url = 'http://localhost:9000/api/message/listen'
  messages = SSEClient(requests.get(url, stream=True))
  for msg in messages.events():
    data = json.loads(msg.data)
    log('msg', data)
    if time.time() - starting <= 3:
      for channel in get_channels():
        if channel.id not in posted:
          posted[channel.id] = []
        posted[channel.id].append(data["id"])
      log('', "discarding as probable initial batch")
      continue
    args = arguments(data)
    log('args', args)
    node = subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8')
    log('node', node)
    for channel in get_channels():
      if channel.id not in posted:
        posted[channel.id] = []
      if data["id"] in posted[channel.id]:
        log('message already sent', channel.id)
      else:
        log('sending to channel', channel.id)
        await client.get_channel(channel.id).send(node)
        posted[channel.id].append(data["id"])


def get_channels():
  for guild in client.guilds:
    for channel in guild.text_channels:
      yield channel

def arguments(data):
  category = data["category"]
  username = data["author"]["username"]
  body = data["body"]
  newsType = data["newsType"]
  arr = ["node", SCRIPT + 'format.js', category, username, body, newsType]
  return list(filter(lambda x: x is not None, arr));


def log(prefix, s):
  timestamp = time.strftime("%Y-%m-%d %X")
  print("[%s] - %s - %s" % (timestamp, prefix, s));


@client.event
async def on_ready():
  log('', 'logged in')
  if LISTEN:
    log('listen', 'yes')
    await listen()
  else:
    log('not listening', 'listen by setting env LISTEN to 1')


@client.event
async def on_message(message):
  if message.author == client.user:
    return
  if message.content.strip() == '!cwt':
    await message.channel.send("Beep Bop CWT Bot. I act upon commands (see !cwtcommands) but I also mirror the CWT chat.")
    return
  node = subprocess.run(
      ["node", SCRIPT + 'handle.js', message.author.display_name, message.content.strip()],
      stdout=subprocess.PIPE).stdout.decode('utf8')
  try:
    result = list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]
    await message.channel.send(result)
  except:
    log(message.content, "did not yield a result")


client.run(TOKEN)

