""" Main Module """

import datetime
import json
import os
import time
import statistics
import fcntl
from argparse import ArgumentParser
from typing import Union
from queue import Queue

import nicovideo  # pylint: disable=E0401
from fabric import colors  # pylint: disable=E0401

# Points: Views*3 + Comments*9 + Mylists*90 + Likes*30
# Speed : Views/sec*25 + Comments/sec*50 + Mylists/sec*1000 + Likes/sec*2000

parser = ArgumentParser(
    prog='nicovide-countmonitor',
    description='Monitor nicovideo\'s video counter.'
)
parser.add_argument('--video', '-v',
    help='Video ID',
    metavar='ID'
)
parser.add_argument('--readlog', '-r',
    default=False,
    action="store_true",
    help='Replay log file, do not monitor'
)
parser.add_argument('--interval', '-i',
    help='Interval second[s] (Ignored if --readlog specified)',
    default=10,
    metavar='second[s]'
)
parser.add_argument('--log', '-l',
    help='Logging file (json)',
    default=None
)
parser.add_argument('--count', '-c',
    help='Records to show',
    default=-1
)
args = parser.parse_args()

video = nicovideo.Video(args.video)

def dictvar2str(inputdata: dict) -> list:
    """ ex. {a, {"b": True}, [c, d]} -> {str(a), {"b": True}, [str(c), str(d)]} """
    for key, var in inputdata.items():
        if not isinstance(var, (str, int, float, bool, type(None), dict, list, tuple)):
            if var.__class__.__module__ == 'nicovideo':
                inputdata[key] = vars(var)
                inputdata = dictvar2str(inputdata)
            else:
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
            if var.__class__.__module__ == 'nicovideo':
                inputdata[index] = vars(var)
                inputdata = listvar2str(inputdata)
            else:
                inputdata[index] = str(var)
        if isinstance(var, (list, tuple)):
            inputdata[index] = listvar2str(var)
        if isinstance(var, dict):
            inputdata[index] = dictvar2str(var)
    return inputdata

def counts_comparing(label: str, count: int, count_before: Union[int, type(None)] = None) -> str:
    """ ex. label=Views, count=100, count_before=80 -> "Views: 100 (+20)" """
    if count_before is None:
        return f'{label}: {count:,}'
    elif count == count_before:
        return f'{label}: {count:,}'
    elif count > count_before:
        return f'{label}: {count:,}' + colors.cyan(f' (+{int(count - count_before):,})')
    else:
        return f'{label}: {count:,}' + colors.red(f' ({int(count - count_before):,})')

def loadlog(logpath: str):
    try:
        with open(logpath, 'r', encoding='utf-8') as logfile:
            fcntl.flock(logfile, fcntl.LOCK_SH)
            jsonlog = json.load(logfile)
            fcntl.flock(logfile, fcntl.LOCK_UN)
    except json.decoder.JSONDecodeError:
        if os.path.isfile(logpath):
            print('Error: Log file broken. Exitting...')
            exit(1)
    except FileNotFoundError:
        jsonlog = []
    return jsonlog

def dendou_iri_toka_check(views): #Kore eigode nante iuno?
    if views < 100000:
        if views >= 90000:
            return colors.red(f" [称号: 殿堂入り直前]") + " [殿堂入りまで残り{100000-views}再生]"
        else:
            return f" [称号: なし] [殿堂入りまで残り{100000-views}再生]"
    elif views < 1000000:
        if views >= 900000:
            return colors.red(f" [称号: 殿堂入り, 伝説入り直前]") + " [伝説入りまで残り{1000000-views}再生]"
        else:
            return f" [称号: 殿堂入り] [伝説入りまで残り{1000000-views}再生]"
    elif views < 10000000:
        if views >= 9000000:
            return colors.red(f" [称号: 伝説入り, 神話入り直前]") + " [神話入りまで残り{10000000-views}再生]"
        else:
            return f" [称号: 伝説入り] [神話入りまで残り{10000000-views}再生]"

def main():
    """ Main func """
    if args.log and not args.readlog:
        print('Logging enabled.')

    if not args.readlog:
        queue = Queue()
        count = 0
        previous_data = None
        speeds = []
        while True:
            count = count + 1
            data = video.get_metadata()
            queue.put('\n' + colors.magenta(
                '--- nicovideo-countmonitor: '
                f'{datetime.datetime.now()} @ {data.videoid} / interval: {args.interval}sec. ---',
                bold=True
            ))
            queue.put(colors.cyan('== Metadata =='))
            queue.put(f'Title: {data.title}')
            queue.put(f'Owner: {str(data.owner)}')
            queue.put(colors.cyan('== Counters =='))
            # Points
            points = data.counts.views*3+data.counts.comments*9+data.counts.mylists*90+data.counts.likes*30
            if previous_data:
                prev_points = previous_data.counts.views*3+previous_data.counts.comments*9+previous_data.counts.mylists*90+previous_data.counts.likes*30
                speed = round(((data.counts.views-previous_data.counts.views)*500+(data.counts.comments-previous_data.counts.comments)*5000+(data.counts.mylists-previous_data.counts.mylists)*20000+(data.counts.likes-previous_data.counts.likes)*40000)/int(args.interval), 2)
                queue.put(counts_comparing(
                    'Views   ',
                    data.counts.views,
                    previous_data.counts.views
                ) + dendou_iri_toka_check(data.counts.views))
                queue.put(counts_comparing(
                    'Comments',
                    data.counts.comments,
                    previous_data.counts.comments
                ))
                queue.put(counts_comparing('Mylists ',
                    data.counts.mylists,
                    previous_data.counts.mylists
                ))
                queue.put(counts_comparing('Likes   ',
                    data.counts.likes,
                    previous_data.counts.likes
                ))
                queue.put(counts_comparing('Points  ',
                    points,
                    prev_points
                ))
                if len(speeds) > 0:
                    queue.put(counts_comparing('Speed   ',
                        speed,
                        speeds[-1:][0]
                    ))
                else:
                    queue.put(counts_comparing('Speed   ', speed))
                speeds.append(speed)
                if len(speeds) > 0:
                    if len(speeds) > 1:
                        queue.put(counts_comparing('AvgSpeed',
                            round(statistics.mean(speeds), 2),
                            round(statistics.mean(speeds[:-1]), 2)
                        ))
                    else:
                        queue.put(counts_comparing("AvgSpeed", round(statistics.mean(speeds), 2)))
                else:
                    queue.put("AvgSpeed: -")
            else:
                queue.put(counts_comparing('Views   ', data.counts.views) + dendou_iri_toka_check(data.counts.views))
                queue.put(counts_comparing('Comments', data.counts.comments))
                queue.put(counts_comparing('Mylists ', data.counts.mylists))
                queue.put(counts_comparing('Likes   ', data.counts.likes))
                queue.put(counts_comparing('Points  ', points))
                queue.put("Speed   : -")
                queue.put("AvgSpeed: -")
            queue.put(colors.cyan('== Series =='))
            if data.series:
                queue.put(f'Title   : {data.series.title}')
                if data.series.prev_video:
                    queue.put('Previous: ' + data.series.prev_video.get_metadata().title)
                else:
                    queue.put('Previous: ' + colors.yellow('None'))
                if data.series.next_video:
                    queue.put('Next    : ' + data.series.next_video.get_metadata().title)
                else:
                    queue.put('Next    : ' + colors.yellow('None'))
            else:
                queue.put(colors.red('No series.'))
            queue.put(colors.cyan('== Tags =='))
            for tag in data.tags:
                if tag.locked:
                    queue.put('Tag ' + colors.yellow('[Locked]') + f': {tag.name} ')
                else:
                    queue.put(f'Tag         : {tag.name}')
            if args.log:
                jsonlog = loadlog(args.log)
                logdata = vars(data)
                logdata["datetime"] = datetime.datetime.now()
                logdata = dictvar2str(logdata.copy())
                jsonlog.append(logdata)
                with open(args.log, 'w', encoding='utf-8') as logfile:
                    fcntl.flock(logfile, fcntl.LOCK_EX)
                    logfile.write(json.dumps(jsonlog))
                    fcntl.flock(logfile, fcntl.LOCK_UN)
            for line in queue.queue:
                print(line)
            if count >= int(args.count) and args.count != -1:
                break

            previous_data = data
            time.sleep(int(args.interval))
    else:
        log = loadlog(args.log)
        if not log:
            raise Exception("Log file empty.")
        previous_record = None
        for record in log[-int(args.count):] if args.count != -1 else log:
            if (not args.video) or args.video == record["videoid"]:
                print('\n' + colors.magenta(
                    f'--- nicovideo-countmonitor: {record["datetime"]} @ {record["videoid"]} ---',
                    bold=True
                ))
                print(colors.cyan('== Metadata =='))
                print(f'Title: {record["title"]}')
                print(f'Owner: {record["owner"]["nickname"]} [ID: {record["owner"]["id"]}]')
                print(colors.cyan('== Counters =='))
                points = record['counts']['views']*3+record['counts']['comments']*9+record['counts']['mylists']*90+record['counts']['likes']*30
                if previous_record:
                    prev_points = previous_record['counts']['views']*3+previous_record['counts']['comments']*9+previous_record['counts']['mylists']*90+previous_record['counts']['likes']*30
                    print(counts_comparing(
                        'Views   ',
                        record['counts']['views'],
                        previous_record['counts']['views'] # pylint: disable=E1136
                    ))
                    print(counts_comparing(
                        'Comments',
                        record['counts']['comments'],
                        previous_record['counts']['comments'] # pylint: disable=E1136
                    ))
                    print(counts_comparing(
                        'Mylists ',
                        record['counts']['mylists'],
                        previous_record['counts']['mylists'] # pylint: disable=E1136
                    ))
                    print(counts_comparing(
                        'Likes   ',
                        record['counts']['likes'],
                        previous_record['counts']['likes'] # pylint: disable=E1136
                    ))
                    print(counts_comparing(
                        'Points  ',
                        points,
                        prev_points
                    ))
                else:
                    print(counts_comparing('Views   ', record['counts']['views']))
                    print(counts_comparing('Comments', record['counts']['comments']))
                    print(counts_comparing('Mylists ', record['counts']['mylists']))
                    print(counts_comparing('Likes   ', record['counts']['likes']))
                    print(counts_comparing('Points  ', points))
                print(colors.cyan('== Tags =='))
                for tag in record["tags"]:
                    if tag['locked']:
                        print(f'Tag: {tag["name"]}', colors.yellow('[Locked]'))
                    else:
                        print(f'Tag: {tag["name"]}')

                previous_record = record

if __name__ == '__main__':
    main()
