# bot.py
import threading
import os
import re
import threading
import subprocess
import discord
from dotenv import load_dotenv
import json
import requests
from sseclient import SSEClient
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()


def log(prefix, s):
  logger.info("APP - %s - %s" % (str(prefix), str(s)))


class Env:
  
  def __init__(self, getenv):
    self.token = getenv('DISCORD_TOKEN')
    self.script = getenv('SCRIPT') or './'
    self.listen = getenv('LISTEN') == "1"
    self.channel = int(getenv('CHANNEL')) if getenv('CHANNEL') is not None else None


class BeepBoop:

  def __init__(self, client, url, getenv):
    self.client = client
    self.url = url
    self.env = Env(getenv)
    self.client.run(self.env.token)
    if self.env.listen:
      log('APP', 'you wanted me to listen, I listen')
      t = threading.Thread(target=self.listen, args=(self.send_message,))
      t.start()
      log('APP', "listen thread started")
      if self.env.channel is not None:
        log('APP', 'mirroring CWT chat to channel %s only.' % self.env.channel)
      else:
        log('APP', 'mirroring CWT chat to all channels on server.')
    else:
      log('not listening', 'listen by setting env LISTEN to 1')
      if self.env.channel is not None:
        log('APP', 'CHANNEL env is set, but you\'re not listening')


  def process_message(self, data, posted, cb):
    args = arguments(data)
    log('args', args)
    node = subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8')
    for channel in self.get_channels():
      if channel.id not in posted:
        posted[channel.id] = []
      if data["id"] in posted[channel.id]:
        log('message already received', channel.id)
        continue
      else:
        if data["newsType"] == "DISCORD_MESSAGE" and \
              re.search(r"\b%s\b" % channel.id, data["body"].split(',')[1]): 
          log('Discarding message sent from this same channel', str(channel.id));
          continue
        if self.env.channel is None or self.env.channel == channel.id:
          log(channel.id, 'sending to channel: ' + str(node))
          cb(channel.id, node)
          posted[channel.id].append(data["id"])


  def listen(self, cb):
    posted = {}
    while 1:
      log('', 'looping')
      messages = SSEClient(requests.get(self.url, stream=True))
      for msg in messages.events():
        if msg.event != "EVENT":
          continue
        data = json.loads(msg.data)
        log('EVENT', data)
        self.process_message(data, posted, cb)
      log('', 'out of loopery')


  def arguments(self, data):
    category = data["category"]
    username = data["author"]["username"]
    body = data["body"]
    newsType = data["newsType"]
    arr = ["node", self.env.script + 'format.js', category, username, body, newsType]
    return list(filter(lambda x: x is not None, arr));


  def send_message(channelId, message):
    self.client.loop.create_task(self.client.get_channel(channelId).send(message))


  def get_channels(self):
    for guild in self.client.guilds:
      for channel in guild.text_channels:
        yield channel


if __name__ == "__main__":
  beepBoop = BeepBoop(discord.Client(), url)

  @beepBop.client.event
  async def on_ready():
    # url = 'http://localhost:9000/api/message/listen'
    url = 'https://cwtsite.com/api/message/listen'
    log('', 'ready')


  @beepBop.client.event
  async def on_message(message):
    if message.author == client.user:
      return
    cmd = message.content.strip()
    log('on message', cmd)
    if cmd == '!cwt':
      await message.channel.send(
          "Beep Bop CWT Bot. I act upon commands (see !cwtcommands)"
          " but I also mirror the CWT chat.")
      return
    link = 'https://discord.com/channels/' + str(message.channel.id)
    node = subprocess.run(
        ["node", self.env.script + 'handle.js', 'DISCORD', link, message.author.display_name, cmd],
        stdout=subprocess.PIPE).stdout.decode('utf8')
    try:
      result = list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]
      log('responding', result)
      await message.channel.send(result)
    except:
      log(cmd, "did not yield a result")

