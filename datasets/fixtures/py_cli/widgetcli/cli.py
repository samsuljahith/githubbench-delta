import argparse

from widgetcli.store import WidgetStore


def main(argv=None):
    parser = argparse.ArgumentParser(prog='widgetcli')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='List widgets')
    add = sub.add_parser('add', help='Add a widget')
    add.add_argument('name')
    args = parser.parse_args(argv)
    store = WidgetStore()
    if args.command == 'list':
        for name in store.list_names():
            print(name)
        return 0
    if args.command == 'add':
        store.add(args.name)
        print(f'added {args.name}')
        return 0
    return 1
