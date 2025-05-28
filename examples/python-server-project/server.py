#!/usr/bin/env python3
import time


def main():
    print("Server started. Waiting for input...", flush=True)

    while True:
        try:
            # Read a line from stdin
            line = input()

            # Process the input and send a response
            if line.lower() == "quit":
                print("Server shutting down...", flush=True)
                break
            elif line.lower() == "hello":
                print("Hello there! Server received your message.", flush=True)
            elif line.lower().startswith("echo "):
                message = line[5:]  # Remove 'echo ' prefix
                print(f"Echo: {message}", flush=True)
            elif line.lower() == "time":
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"Current time: {current_time}", flush=True)
            else:
                print(f"Server received: '{line}' - Unknown command", flush=True)

        except EOFError:
            print("Server: EOF received, shutting down...", flush=True)
            break
        except KeyboardInterrupt:
            print("Server: Interrupted, shutting down...", flush=True)
            break


if __name__ == "__main__":
    main()
