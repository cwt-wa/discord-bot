# bot.py
from operator import itemgetter
import os
import re
import threading
import discord
from dotenv import load_dotenv
import json
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def log(prefix, s):
  logger.info("APP - %s - %s" % (str(prefix), str(s)))


class Env:
  
  def __init__(self, getenv):
    self.token = getenv('DISCORD_TOKEN')
    self.script = getenv('SCRIPT') or './'
    self.listen = getenv('LISTEN') == "1"
    self.channel = int(getenv('CHANNEL')) if getenv('CHANNEL') is not None else None


class ThreadFactory:

  def __init__(self):
    import threading

  def inst(self, target, args):
    return threading.Thread(target=listener.listen, args=(self.send_message,))


class BeepBoop:

  say_beep_boop = \
      "Beep Bop CWT Bot. I act upon commands (see !cwtcommands)" \
      " but I also mirror the CWT chat."

  def __init__(self, client, getenv, listener_factory,
               thread_factory=ThreadFactory()):
    self.client = client
    self.env = Env(getenv)
    self.client.run(self.env.token)
    if self.env.listen:
      log('APP', 'you wanted me to listen, I listen')
      listener = listener_factory([self.client, self.env.channel])
      thread = thread_factory.inst(listener.listen, (-1, self.send_message))
      thread.start()
    else:
      log('not listening', 'listen by setting env LISTEN to 1')
      if self.env.channel is not None:
        log('APP', 'CHANNEL env is set, but you\'re not listening')


  def send_message(channelId, message):
    self.client.loop.create_task(self.client.get_channel(channelId).send(message))


class Listener:

  def __init__(self, client, channel_to_mirror_to, node_runner, open_stream):
    self.posted = {}
    self.client = client
    self.node_runner = node_runner
    self.open_stream = open_stream
    self.channel_to_mirror_to = \
        int(channel_to_mirror_to) if channel_to_mirror_to is not None else None
    if self.channel_to_mirror_to is not None:
      log('APP', 'mirroring CWT chat to channel %s only.' % self.channel_to_mirror_to)
    else:
      log('APP', 'mirroring CWT chat to all channels on server.')


  def listen(self, listen_iterations, cb):
    if listen_iterations == -1:
      while 1:
        self.loop()
    else:
      for _ in range(listen_iterations):
        self.loop(cb)


  def loop(self, cb):
    log('', 'looping')
    messages = self.open_stream()
    for msg in messages.events():
      if msg.event != "EVENT":
        continue
      data = json.loads(msg.data)
      log('EVENT', data)
      for channel in self.get_channels():
        self.process_message(data, channel.id, cb)
    log('', 'out of loopery')
    


  def process_message(self, data, channelId, cb):
    if channelId not in self.posted:
      self.posted[channelId] = []
    if data["id"] in self.posted[channelId]:
      log('message already received', channelId)
    else:
      if data["newsType"] == "DISCORD_MESSAGE" and \
            re.search(r"\b%s\b" % channelId, data["body"].split(',')[1]): 
        log('Discarding message sent from this same channel', str(channelId));
      elif self.channel_to_mirror_to is None or self.channel_to_mirror_to == channelId:
        formatted = self.node_runner.format(data)
        log(channelId, 'sending to channel: ' + str(formatted))
        cb(channelId, formatted)
        self.posted[channelId].append(data["id"])


  def get_channels(self):
    for guild in self.client.guilds:
      for channel in guild.text_channels:
        yield channel


class NodeRunner:

  def __init__(self, script, runner):
    self.script = script if script.endswith("/") else script + "/"
    self.runner = runner
    import subprocess


  def handle(self, cmd, display_name, guildId, channelId):
    link = ('https://discord.com/channels/%s/%s' % (str(guildId), str(channelId)))
    arguments = ["node", self.script + 'handle.js', 'DISCORD', link, display_name, cmd]
    node = self.runner(arguments)
    return list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]


  def format(self, data):
    category, author, body = itemgetter('category', 'author', 'body')(data)
    arguments = ["node", self.script + 'format.js', category, author["username"], body]
    if data["newsType"]:
      arguments.append(data["newsType"])
    return self.runner(arguments)


class EventHandler:

  def __init__(self, client, node_runner):
    self.client = client

  async def on_message(self, message):
    if message.author == self.client.user:
      return
    cmd = message.content.strip()
    logger.info("message: %s", cmd)
    if cmd == '!cwt':
      logger.info("Received !cwt command")
      await message.channel.send(BeepBoop.say_beep_boop)
    elif cmd.startswith("!cwt"):
      logger.info("commands starts with !cwt")
      try:
        result = self.node_runner.handle(
            cmd, message.author.display_name,
            message.channel.guild.id,  message.channel.id)
        logger.info("sending node result: %s", result)
        await message.channel.send(result)
      except:
        logger.warning("error handling command %s", cmd)

  def register(self):
    @self.client.event
    async def on_ready():
      logger.info("ready")

    @self.client.event
    async def on_message(message):
      self.on_message(message)


if __name__ == "__main__":
  load_dotenv()

  node_runner = NodeRunner(
      os.getenv("SCRIPT"),
      lambda args: subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8'))

  def listener_factory(*args):
    import requests
    from sseclient import SSEClient
    endpoint = os.getenv("CWT_MESSAGE_SSE_ENDPOINT")
    Listener(*args, node_runner, lambda x: SSEClient(requests.get(endpoint, stream=True)))

  beepBoop = BeepBoop(
      client = discord.Client(),
      getenv = os.getenv,
      listener_factory = listener_factory)

  EventHandler(beepBoop.client, node_runner).register()


