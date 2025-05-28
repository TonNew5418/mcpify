# Simple CLI Tool

This is a simple command-line interface (CLI) tool written in Python that supports multiple commands for basic operations. It uses the `argparse` module to handle command-line arguments and provides a straightforward way to execute various tasks.

## Features
- Print a greeting message with the `--hello` flag.
- Echo a provided message with the `--echo` option.
- Display the current time with the `--time` flag.
- Add two numbers with the `--add` option.

## Requirements
- Python 3.x

## Installation
1. Clone or download this repository.
2. Ensure Python 3 is installed on your system.
3. Save the script as `cli_tool.py`.

## Usage
Run the script from the command line using Python. The tool accepts one command at a time from the following options:

```bash
python cli_tool.py [command]
```

### Available Commands
- `--hello`: Prints a greeting message.
  ```bash
  python cli_tool.py --hello
  ```
  **Output**: `Hello there! CLI tool received your message.`

- `--echo MESSAGE`: Echoes the provided message.
  ```bash
  python cli_tool.py --echo "Hello, World!"
  ```
  **Output**: `Echo: Hello, World!`

- `--time`: Displays the current time in `YYYY-MM-DD HH:MM:SS` format.
  ```bash
  python cli_tool.py --time
  ```
  **Example Output**: `Current time: 2025-05-28 16:12:34`

- `--add NUM1 NUM2`: Adds two numbers and displays the result.
  ```bash
  python cli_tool.py --add 5.5 3.2
  ```
  **Output**: `Result: 5.5 + 3.2 = 8.7`

### Notes
- Only one command can be used at a time (commands are mutually exclusive).
- Use the `--help` flag to see all available commands and their descriptions:
  ```bash
  python cli_tool.py --help
  ```

## Error Handling
- If an invalid command or incorrect arguments are provided, the tool will display an error message.
- Pressing `Ctrl+C` during execution will gracefully exit with the message: `CLI tool: Interrupted, exiting...`.

## Example
```bash
$ python cli_tool.py --hello
Hello there! CLI tool received your message.

$ python cli_tool.py --echo "Test message"
Echo: Test message

$ python cli_tool.py --time
Current time: 2025-05-28 16:12:34

$ python cli_tool.py --add 10 20
Result: 10 + 20 = 30
```

## License
This project is licensed under the MIT License.
