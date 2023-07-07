""" Main Module """

import datetime
import json
import os
import time
from argparse import ArgumentParser
from typing import Union

import nicovideo  # pylint: disable=E0401
from fabric import colors  # pylint: disable=E0401

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
        return f'{label}: {count:,}' + colors.cyan(f' (+{count - count_before:,})')
    else:
        return f'{label}: {count:,}' + colors.red(f' ({count - count_before:,})')

def main():
    """ Main func """
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
        count = 0
        previous_data = None
        while True:
            count = count + 1
            data = video.get_metadata()
            print('\n' + colors.magenta(
                '--- nicovideo-countmonitor: '
                f'{datetime.datetime.now()} @ {data.videoid} ---',
                bold=True
            ))
            print(colors.cyan('== Metadata =='))
            print(f'Title: {data.title}')
            print(f'Owner: {str(data.owner)}')
            print(colors.cyan('== Counters =='))
            if previous_data:
                print(counts_comparing(
                    'Views   ',
                    data.counts.views,
                    previous_data.counts.views
                ))
                print(counts_comparing(
                    'Comments',
                    data.counts.comments,
                    previous_data.counts.comments
                ))
                print(counts_comparing('Mylists ',
                    data.counts.mylists,
                    previous_data.counts.mylists
                ))
                print(counts_comparing('Likes   ',
                    data.counts.likes,
                    previous_data.counts.likes
                ))
            else:
                print(counts_comparing('Views   ', data.counts.views))
                print(counts_comparing('Comments', data.counts.comments))
                print(counts_comparing('Mylists ', data.counts.mylists))
                print(counts_comparing('Likes   ', data.counts.likes))
            print(colors.cyan('== Series =='))
            if data.series:
                print(f'Title   : {data.series.title}')
                print('Next    : ' + data.series.prev_video.get_metadata().title
                    if data.series.prev_video else colors.yellow('No next video.'))
                print('Previous: ' + data.series.next_video.get_metadata().title
                    if data.series.next_video else colors.yellow('No previous video.'))
            else:
                print(colors.red('No series.'))
            print(colors.cyan('== Tags =='))
            for tag in data.tags:
                print(f'Tag: {tag.name}', colors.yellow('[Locked]') if tag.locked else '')
            if args.log:
                logdata = vars(data)
                logdata["datetime"] = datetime.datetime.now()
                logdata = dictvar2str(logdata.copy())
                jsonlog.append(logdata)
                with open(args.log, 'w', encoding='utf-8') as logfile:
                    logfile.write(json.dumps(jsonlog))
            if count >= int(args.count) and args.count != -1:
                break

            previous_data = data
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
                if previous_record:
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
                else:
                    print(counts_comparing('Views   ', record['counts']['views']))
                    print(counts_comparing('Comments', record['counts']['comments']))
                    print(counts_comparing('Mylists ', record['counts']['mylists']))
                    print(counts_comparing('Likes   ', record['counts']['likes']))
                print(colors.cyan('== Tags =='))
                for tag in record["tags"]:
                    if tag['locked']:
                        print(f'Tag: {tag["name"]}', colors.yellow('[Locked]'))
                    else:
                        print(f'Tag: {tag["name"]}')

                previous_record = record

if __name__ == '__main__':
    main()
