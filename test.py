import unittest
from unittest.mock import Mock, PropertyMock
from beep import BeepBoop, Listener, NodeRunner  # TODO split these
from sseclient import Event
from discord import Guild, TextChannel
import json

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
        Env(env).getenv,
        listener_factory,
        thread_factory_mock)
    thread_factory_mock.inst.assert_called_once()
    listener_mock.assert_called_once_with(
          client_mock, int(env["CHANNEL"]), endpoint, None, None)
  

class NodeRunnerTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    pass

  def format_shoutbox(self):
    script = "~/with/trailing/slash/"
    node_runner = NodeRunner(script, lambda x: x)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "Here is a message",
      "newsType": None
    }
    actual = self.node_runner.format(message)
    self.assertEqual(
        actual,
        ["node", script + "format.js", message["category"], 
         message["author"]["username"], message["body"]])
  

  def format_news(self):
    script = "../src/no/trailing/slash"
    node_runner = NodeRunner(script, lambda x: x)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "BoolC,Taner,3,1",
      "newsType": "REPORT"
    }
    actual = self.node_runner.format(message)
    self.assertEqual(
        actual,
        ["node", script + "/format.js", message["category"], 
         message["author"]["username"], message["body"], message["newsType"]])

  # TODO test command


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

