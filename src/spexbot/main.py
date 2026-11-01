import logging
import os
from logging.handlers import RotatingFileHandler

import discord
import yaml

from spexbot.bot import SpexBot
from spexbot.helpers import database

CONFIG_PATH = os.path.join("./config.yaml")
DATABASE_PATH = os.path.join("./data.db")

handler = RotatingFileHandler("spexbot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")

with open(CONFIG_PATH) as config_file:
    config = yaml.load(config_file, Loader=yaml.Loader)


def main():
    print("Halloj!")
    discord.utils.setup_logging(handler=handler, level=logging.INFO)
    database.setup(DATABASE_PATH)
    bot = SpexBot(config, DATABASE_PATH)
    bot.run(config["token"])