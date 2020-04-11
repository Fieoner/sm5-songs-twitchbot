#!/usr/bin/env python3

import sys
import os
import irc.bot
import requests
from glob import glob
from collections import defaultdict

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, token, channel):
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel

        # get channel id. Needed for v5 API calls
        url = 'https://api.twitch.tv/kraken/users?login=' + channel
        headers = {'Client-ID': client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
        r = requests.get(url, headers=headers).json()
        self.channel_id = r['users'][0]['_id']

        # create irc connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        print('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:'+token)], username, username)

        # get songs
        self.songs, self.packs = getSongsAndPacks()


    def on_welcome(self, c, e):
        print('Joining ' + self.channel)

        # you must request capabilities to use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

    def on_pubmsg(self, c, e):

        #if a message starts with a '!' try to run it as a command
        if e.arguments[0][:1] == '!':
            cmd = e.arguments[0].split(' ')[0][1:]
            print(f'Received command: {cmd} by user {e.tags[3]["value"]}')
            self.do_command(e, cmd)
        return

    def do_command(self, e, cmd):
        c = self.connection

        # Poll the API to get current game.
        if cmd == "game":
            url = 'https://api.twitch.tv/kraken/channels/' + self.channel_id
            headers = {'Client-ID': self.client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
            r = requests.get(url, headers=headers).json()
            c.privmsg(self.channel, r['display_name'] + ' is currently playing ' + r['game'])

        # Poll the API the get the current status of the stream
        elif cmd == "title":
            url = 'https://api.twitch.tv/kraken/channels/' + self.channel_id
            headers = {'Client-ID': self.client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
            r = requests.get(url, headers=headers).json()
            c.privmsg(self.channel, r['display_name'] + ' channel title is currently ' + r['status'].replace('\n', ''))

        # Provide basic information to viewers for specific commands
        elif cmd == "play":
            playwords = e.arguments[0].split(' ')[1:]
            play = ' '.join(playwords)
            matches = [ self.songs[song]['pack']+'/'+song+' - '+self.songs[song]['diffs']
                for song in self.songs
                if play.lower() in song.lower()]
            print(matches)
            if len(matches) == 0:
                c.privmsg(self.channel, 'No songs found')
            else:
                i = 0
                for m in matches:
                    i+=1
                    c.privmsg(self.channel, m)
                    if i >= 8:
                        tot = len(matches)
                        rem = tot - 8
                        c.privmsg(self.channel, str(rem)+' more matches')
                        break
        elif cmd == "packs":
            username = e.tags[3]["value"]
            i = 0
            while i < len(self.packs):
                msg = "  -  ".join(self.packs[i:i+3])
                i += 3
                c.privmsg(self.channel, f'/w {username} {msg}')

        # The command was not recognized
        else:
            c.privmsg(self.channel, "What do you mean " + cmd + "?? That's not even a command lol")

def getSongsAndPacks():
    err = 0
    songs = defaultdict(dict)
    packs = []
    for song in glob('C:\Games\Stepmania 5.1\Cache\Songs\*'):
        title = ""
        pack = ""
        diffs = []
        with open(song, 'r', encoding='utf-8', errors='ignore') as simfile:
            try:
                lines = simfile.readlines()
            except:
                err+=1
                continue
            for line in lines:
                if '#TITLE:' in line:
                    title = line.split(':')[1][0:-2]
                    break
            for i, line in enumerate(lines):
                if '#SONGFILENAME:' in line:
                    pack = line.split('/')[2]
                    if pack not in packs:
                        packs.append(pack)
                    continue
                if '#STEPSTYPE:dance-single;' in line:
                    d = lines[i+4].split(':')[1][0:-2]
                    diffs.append(d)
        diffs.sort(key=int)
        songs[title]['pack'] = pack
        songs[title]['diffs'] = ', '.join(diffs)
    print(str(err)+' failed')
    return (songs, packs)

def main():
    if len(sys.argv) < 2:
        print(f'usage: {sys.argv[0]} <keys file>')
        print('keys file must contain 4 lines:')
        print('\tusername')
        print('\tclient_id')
        print('\tapi token')
        print('\tchannel name')
        exit(1)
    else:
        with open(sys.argv[1], 'r') as f:
            lines = f.readlines()
            username  = lines[0].rstrip()
            client_id = lines[1].rstrip()
            token     = lines[2].rstrip()
            channel   = lines[3].rstrip()

    bot = TwitchBot(username, client_id, token, channel)
    bot.start()

if __name__ == "__main__":
    main()
