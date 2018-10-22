#!/usr/bin/python3

import sys, os, logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import barbot.config

config = barbot.config.load()

import barbot.logging

barbot.logging.configure()

import barbot.audio

barbot.audio.tts(sys.argv[1], sys.argv[2])

