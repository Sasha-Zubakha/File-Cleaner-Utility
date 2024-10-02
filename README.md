# File Cleaner Utility

The File Cleaner Utility is a cross-platform program that can be used on various operating systems, including Windows, Linux, and macOS. This Python-based utility helps you manage files on your computer by providing options to delete, copy, and move files based on criteria like file extension or size. The tool allows users to choose specific directories and manage files efficiently by offering several features such as sorting, size filtering, and generating a report of cleaned files.

## Features

- Manage files by copying, moving or deleting.
- Select specific directories for analysis.
- Filter files by extension and size.
- Enable or disable sorting of files (alphabetically or by size).
- Output detailed statistics of deleted files.
- View progress indicators for ongoing operations.

## Installation

1. Clone the repository or download the project file:
    ```bash
    git clone https://github.com/yourusername/cleaner-utility.git
    ```

2. Make sure you have Python 3 installed.

## Usage

### On Linux:

1. Open the terminal and navigate to the directory with the program:
    ```bash
    cd /path/to/program
    ```

2. Make the program executable:
    ```bash
    chmod +x Cleaner.py
    ```

3. Run the script:
    ```bash
    ./Cleaner.py
    ```

4. Follow the interactive prompts to configure paths, file formats, and other settings.

### On Windows:

1. Open Command Prompt and navigate to the directory with the program:
    ```cmd
    cd path\to\program
    ```

2. Run the script:
    ```cmd
    python Cleaner.py
    ```

3. Follow the interactive prompts to configure paths, file formats, and other settings.

## Settings

- The program stores settings such as directory paths, file size filters, and sorting preferences in a JSON file.
- Files are saved in the program directory where the program is launched.
- These settings can be modified within the program.

## License

This project is licensed under the Apache License 2.0 - see the **LICENSE** file for details.

---

© 2024 Alexander Zubakha. All rights reserved.