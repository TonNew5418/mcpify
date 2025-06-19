#!/usr/bin/env python3
import argparse
import time


def main() -> None:
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(
        description="A simple command-line tool that processes commands."
    )
    # 定义互斥组，确保只接受一个命令
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hello", action="store_true", help="Print a greeting message.")
    group.add_argument(
        "--echo", type=str, metavar="MESSAGE", help="Echo the provided message."
    )
    group.add_argument("--time", action="store_true", help="Print the current time.")
    group.add_argument(
        "--add", nargs=2, type=float, metavar=("NUM1", "NUM2"), help="Add two numbers."
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 处理命令
    if args.hello:
        print("Hello there! CLI tool received your message.")
    elif args.echo:
        print(f"Echo: {args.echo}")
    elif args.time:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Current time: {current_time}")
    elif args.add:
        result = args.add[0] + args.add[1]
        print(f"Result: {args.add[0]} + {args.add[1]} = {result}")
    else:
        print("Unknown command")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("CLI tool: Interrupted, exiting...")
        exit(1)
