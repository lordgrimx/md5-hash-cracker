# MD5 Hash Generator & Cracker

This project is a web application that allows users to generate MD5 hashes and attempt to crack them using a brute-force approach. The application is built using Flask for the backend and vanilla JavaScript for the frontend.

## Features

- **Generate MD5 Hash**: Users can generate an MD5 hash from a manually entered password or a randomly generated password.
- **Crack MD5 Hash**: Users can attempt to crack an MD5 hash using a brute-force method with multiprocessing support.
- **Real-time Status**: The application provides real-time updates on the cracking process, including the number of attempts and the status of each process.

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/lordgrimx/md5-hash-cracker.git
    cd md5-hash-cracker
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment**:
    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4. **Install the required packages**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Run the Flask application**:
    ```bash
    python app.py
    ```

2. **Open your web browser** and navigate to `http://127.0.0.1:5000`.

3. **Generate an MD5 Hash**:
    - Select "Manual" or "Random" for the password type.
    - Enter the password or specify the length for a random password.
    - Click "Generate Hash".

4. **Crack an MD5 Hash**:
    - Enter the MD5 hash you want to crack.
    - Specify the process multiplier (number of processes to use).
    - Click "Crack Hash".
    - The application will display real-time updates on the cracking process.

## Project Structure

- [app.py](http://_vscodecontentref_/0): The main Flask application file containing the backend logic.
- `templates/index.html`: The HTML template for the frontend.

