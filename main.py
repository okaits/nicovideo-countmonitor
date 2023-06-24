""" Main Module """

import datetime
import json
import time
import os
from argparse import ArgumentParser

import nicovideo  # pylint: disable=E0401

parser = ArgumentParser(prog='nicovide-countmonitor', description='Monitor nicovideo\'s video counter.')
parser.add_argument('--video', '-v', help='Video ID', metavar='ID')
parser.add_argument('--readlog', '-r', default=False, action="store_true", help='Read log file, do not monitor')
parser.add_argument('--interval', '-i', help='Interval second[s] (Ignored if --readlog specified)', default=10, metavar='second[s]')
parser.add_argument('--log', '-l', help='Logging file (json)', default=None)
args = parser.parse_args()

video = nicovideo.Video(args.video)

def dictvar2str(inputdata: dict) -> list:
    """ ex. {a, {"b": True}, [c, d]} -> {str(a), {"b": True}, [str(c), str(d)]} """
    for key, var in inputdata.items():
        if not isinstance(var, (str, int, float, bool, type(None), dict, list, tuple)):
            inputdata[key] = str(var)
        if isinstance(var, (list, tuple)):
            inputdata[key] = listvar2str(var)
        if isinstance(var, dict):
            inputdata[key] = dictvar2str(var)
    return inputdata

def listvar2str(inputdata: list) -> list:
    """ ex. [a, b, {"c": True}, [e]] -> [str(a), str(b), {"c": True}, [str(e)]] """
    for index, var in enumerate(inputdata):
        if not isinstance(var, (str, int, float, bool, type(None), dict, list, tuple)):
            inputdata[index] = str(var)
        if isinstance(var, (list, tuple)):
            inputdata[index] = listvar2str(var)
        if isinstance(var, dict):
            inputdata[index] = dictvar2str(var)
    return inputdata

if args.log and not args.readlog:
    print('Logging enabled.')
    try:
        with open(args.log, 'r', encoding='utf-8') as logfile:
            jsonlog = json.load(logfile)
    except json.decoder.JSONDecodeError:
        if os.path.isfile(args.log):
            print('Error: Log file broken. Exitting...')
            exit(1)
    except FileNotFoundError:
        jsonlog = []

if not args.readlog:
    while True:
        data = video.get_metadata()
        print(f'--- nicovideo-countmonitor: {datetime.datetime.now()} @ {data.videoid} ---')
        print(f'Title: {data.title}')
        print(f'Owner: {str(data.owner)}')
        print(str(data.counts))
        for tag in data.tags:
            print(f'Tag: {tag.name}', '(Locked)' if tag.locked else '')
        if args.log:
            logdata = vars(data)
            logdata["datetime"] = datetime.datetime.now()
            logdata = dictvar2str(logdata)
            jsonlog.append(logdata)
            with open(args.log, 'w', encoding='utf-8') as logfile:
                logfile.write(json.dumps(jsonlog))

        time.sleep(int(args.interval))
else:
    try:
        with open(args.log, 'r', encoding='utf-8') as logfile:
            log = json.load(logfile)
    except FileNotFoundError:
        print("Error: Log file not found.")
        exit(1)
    except json.decoder.JSONDecodeError:
        print("Error: Log file broken.")
        exit(1)
    for record in log:
        if (not args.video) or args.video == record["videoid"]:
            print(f'--- nicovideo-countmonitor: {record["datetime"]} @ {record["videoid"]} ---')
            print(f'Title: {record["title"]}')
            print(f'Owner: {record["owner"]}')
            for tag in record["tags"]:
                print(f'Tag: {tag}')
            print(record["counts"])
