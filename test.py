import unittest
from unittest.mock import Mock, PropertyMock, AsyncMock, AsyncMock
from beep import BeepBoop, Listener, NodeRunner, EventHandler
from sseclient import Event
from discord import Guild, TextChannel
import json
import asyncio

class Env:
  
  def __init__(self, env):
    self.env = env

  def getenv(self, field):
    return self.env[field] if field in self.env else None

# todo append slash if it's not already there to SCRIPT env
#  and test this of course

class TestBeepBoop(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    cls.listener_mock = Mock()
    cls.listener_factory = lambda x: listener_mock()


  def test_init(self):
    client_mock = Mock()
    env = {"DISCORD_TOKEN": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, Env(env).getenv, self.listener_mock)
    client_mock.run.assert_called_once_with(env["DISCORD_TOKEN"])
    client_mock.listen.assert_not_called()


  def test_listen_not(self):
    client_mock = Mock()
    env = {}
    thread_factory_mock = Mock()
    beepBoop = BeepBoop(
        client_mock,
        Env(env).getenv,
        self.listener_mock,
        thread_factory_mock)
    thread_factory_mock.inst.assert_not_called()


  def test_listen_not(self):
    client_mock = Mock()
    endpoint = "http://example.com"
    env = {"LISTEN": "1", "CHANNEL": "1234", "CWT_MESSAGE_SSE_ENDPOINT": endpoint}
    thread_factory_mock = Mock()
    listener_mock = Mock()
    listener_factory = lambda x: listener_mock(*x, endpoint, None, None)
    beepBoop = BeepBoop(
        client_mock,
        Env(env).getenv, listener_factory,
        thread_factory_mock)
    thread_factory_mock.inst.assert_called_once()
    listener_mock.assert_called_once_with(
          client_mock, int(env["CHANNEL"]), endpoint, None, None)


class EventHandlerTest(unittest.TestCase):

  def create_channel_mock(self):
    channel_mock = Mock()
    guild_mock = Mock()
    type(guild_mock).id = PropertyMock(return_value=5)
    type(channel_mock).guild = guild_mock
    type(channel_mock).id = 1234
    type(channel_mock).send = AsyncMock(return_value=None)
    return channel_mock


  def create_message_mock(self, content, channel_mock):
    message_mock = Mock()
    author_mock = Mock()
    type(author_mock).display_name = PropertyMock(return_value="Zemke")
    type(message_mock).author = PropertyMock(return_value=author_mock)
    type(message_mock).content = PropertyMock(return_value=content)
    type(message_mock).channel = PropertyMock(return_value=channel_mock)
    return message_mock


  def test_on_message_beep_bop(self):
    client_mock = Mock()
    type(client_mock).user = PropertyMock(return_value=Mock())
    event_handler = EventHandler(client_mock, None)
    channel_mock = self.create_channel_mock()
    message_mock = self.create_message_mock("!cwt", channel_mock)
    actual = asyncio.get_event_loop().run_until_complete(
        event_handler.on_message(message_mock))
    message_mock.channel.send.assert_called_once_with(BeepBoop.say_beep_boop)


class NodeRunnerTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    pass

  def test_format_shoutbox(self):
    script = "~/with/trailing/slash/"
    node_runner = NodeRunner(script, lambda x: x)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "Here is a message",
      "newsType": None
    }
    actual = node_runner.format(message)
    self.assertEqual(
        actual,
        ["node", script + "format.js", message["category"], 
         message["author"]["username"], message["body"]])
  

  def test_format_news(self):
    script = "../src/no/trailing/slash"
    node_runner = NodeRunner(script, lambda x: x)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "BoolC,Taner,3,1",
      "newsType": "REPORT"
    }
    actual = node_runner.format(message)
    self.assertEqual(
        actual,
        ["node", script + "/format.js", message["category"], 
         message["author"]["username"], message["body"], message["newsType"]])


  def test_handle(self):
    script = "../src/no/trailing/slash"
    guildId = 1234
    channelId = 12345
    node = \
        "The CWT bot commands are !cwtchat, !cwtdice, !cwthell, !cwtterrain, " \
        "!cwtwinners, !cwtcommands, !cwtschedule, !cwtplayoffs, " \
        "!cwtwhatisthisthing, !cwtrafkagrass, !cwturl, !cwtgithub."
    def runner(arguments):
      link = 'https://discord.com/channels/1234/12345'
      self.assertEqual(
          arguments,
          ["node", script + "/handle.js", "DISCORD", link, "Zemke", "!cwtcommands"])
      return "getting current tournament\n" \
             "cmd !cwtcommands\n" \
             "RES xx %s\n" % node
    node_runner = NodeRunner(script, runner)
    actual = node_runner.handle("!cwtcommands", "Zemke", guildId, channelId)
    self.assertEqual(actual, node)


class ListenerTest(unittest.TestCase):

  def test_listen(self):
    script = "./"
    node_runner = NodeRunner(script, lambda x: x)
    channel = "1234"
    endpoint = "http://example.com"
    client_mock = Mock()
    guild_mock = Mock()
    channel_mock = Mock()
    type(channel_mock).id = PropertyMock(return_value=1234)
    type(guild_mock).text_channels = PropertyMock(return_value=[channel_mock])
    type(client_mock).guilds = PropertyMock(return_value=[guild_mock])
    message = {
      "id": 5000,
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "Here is a message",
      "newsType": None
    }
    events = [Event(event="EVENT", data=json.dumps(message))]
    open_stream = type("SSEClient", (object,), {"events": lambda x: events })
    listener = Listener(client_mock, channel, node_runner, open_stream)

    def cb_side_effect(channelId, content):
      self.assertEqual(channelId, 1234)
      self.assertEqual(
          content,
          ["node", script + "format.js", message["category"], 
           message["author"]["username"], message["body"]])

    cb_mock = Mock(side_effect=cb_side_effect)
    listener.listen(1, cb_mock)
    cb_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()

