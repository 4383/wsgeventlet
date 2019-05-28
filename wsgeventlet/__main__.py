import argparse

import eventlet

from wsgeventlet import heartbeat


def main():
    parser = argparse.ArgumentParser(description='wsgeventlet POC.')
    parser.add_argument('--eventlet-turned-off', action='store_true',
                        help='turn off eventlet monkey patched environment')
    parser.add_argument("--heartbeat-timeout", help="the heartbeat timeout",
                        default=60)
    args = parser.parse_args()
    if not args.eventlet_turned_off:
        print("----------------------------------------------")
        print("/!\  Running a monkey patched environment  /!\\")
        print("----------------------------------------------")
        eventlet.monkey_patch()
    hb = heartbeat.Connection(args.heartbeat_timeout)


if __name__ == "__main__":
    main()
