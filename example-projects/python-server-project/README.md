# Simple Python Server

This is a simple command-line server written in Python that processes input from `stdin` and responds with appropriate output. The server runs in a loop, waiting for user input, and supports a small set of commands for basic interactions.

## Features

- Responds to a `hello` command with a greeting message.
- Echoes a provided message with the `echo` command.
- Displays the current time with the `time` command.
- Exits gracefully on `quit`, EOF, or keyboard interrupt (`Ctrl+C`).

## Requirements

- Python 3.x

## Installation

1. Clone or download this repository.
2. Ensure Python 3 is installed on your system.
3. Save the script as `server.py`.

## Usage

Run the server from the command line using Python. The server listens for input from `stdin` and processes commands one at a time.

```bash
python server.py
```

After starting, the server will display:
```
Server started. Waiting for input...
```

You can then type commands and press Enter to see the server's response.

### Available Commands

- `hello`: Prints a greeting message.

  **Input**: `hello`
  
  **Output**: `Hello there! Server received your message.`

- `echo <message>`: Echoes the provided message (everything after `echo `).

  **Input**: `echo Hello, World!`
  
  **Output**: `Echo: Hello, World!`

- `time`: Displays the current time in `YYYY-MM-DD HH:MM:SS` format.

  **Input**: `time`
  
  **Example Output**: `Current time: 2025-05-28 16:23:45`

- `quit`: Shuts down the server.

  **Input**: `quit`
  
  **Output**: `Server shutting down...`

### Notes

- Commands are case-insensitive (e.g., `HELLO`, `hello`, or `HeLlO` all work).
- Unknown commands will result in a message indicating the input was not recognized:

  **Input**: `invalid`
  
  **Output**: `Server received: 'invalid' - Unknown command`

- The server flushes output immediately (`flush=True`) to ensure real-time responses.
- Use `Ctrl+C` or `Ctrl+D` (EOF) to exit the server, which will display:
  ```
  Server: Interrupted, shutting down...
  ```
  or
  ```
  Server: EOF received, shutting down...
  ```

## Example Interaction

```bash
$ python server.py
Server started. Waiting for input...
hello
Hello there! Server received your message.
echo Test message
Echo: Test message
time
Current time: 2025-05-28 16:23:45
invalid
Server received: 'invalid' - Unknown command
quit
Server shutting down...
```

## Error Handling

- The server handles `EOFError` (e.g., `Ctrl+D`) and `KeyboardInterrupt` (e.g., `Ctrl+C`) gracefully, shutting down with an appropriate message.
- Invalid commands are reported without interrupting the server.

## License

This project is licensed under the MIT License.