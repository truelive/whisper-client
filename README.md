# Whisper Audio Client & Server

This project provides a simple Python client and server setup for recording audio based on voice activity and sending it to a local server endpoint.

The client listens to the microphone, automatically starts recording when speech is detected, stops after a period of silence, and then uploads the captured audio as a WAV file to the server.

## Features

*   **Voice Activity Detection (VAD):** Client only records when you are speaking, ignoring silence.
*   **Automatic Stop:** Recording ceases automatically after a configurable duration of silence.
*   **Pre/Post Buffering:** Captures a small amount of audio before speech starts and after it ends.
*   **HTTP Upload:** Sends the recorded audio (WAV format) to a specified server endpoint.
*   **Simple Server:** Includes a basic Flask server to receive and save the audio files.
*   **Configurable:** Client behavior (silence threshold, server URL) can be adjusted via command-line arguments.

## Requirements

*   Python 3.13
*   Pip (Python package installer)
*   Microphone connected to your system (for the client)
*   Portaudio library (often needed by `sounddevice` on macOS/Linux)
    *   On macOS: `brew install portaudio`
    *   On Debian/Ubuntu: `sudo apt-get install libportaudio2`

## Installation

1.  **Clone or Download:** Get the project files onto your local machine.
    ```bash
        git clone https://github.com/shverom/whisper-client.git
    ```
    
2.  **Create and Activate Virtual Environment :**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(On Windows use `venv\Scripts\activate`)*

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You need to run the server first, then run the client.

1.  **Run the Server:**
    TBD

2.  **Run the Client:**
    Open *another* terminal, navigate to the project directory, activate the virtual environment (if used), and run:
    ```bash
    python main.py
    ```
    The client will start listening. Speak into your microphone. It will detect your speech, record it, and stop after you remain silent for a short period. The recorded audio will then be sent to the server.

## Client Configuration (Command-Line Arguments)

You can customize the client's behavior using arguments:

*   `--url`: Specify the server URL (default: `http://localhost:5000/upload_audio`). 
*   `--threshold`: Set the RMS volume threshold for silence detection (default: `0.01`). Lower values are more sensitive. Adjust based on your mic and environment.
*   `--rate`: Set the audio sample rate in Hz (default: `16000`).
*   `--channels`: Set the number of audio channels (1 for mono, 2 for stereo) (default: `1`).

**Example:** Run the client connecting to a different server and using a higher silence threshold:
```bash
python /main.py --url http://localhost:8000/audio --threshold 0.02
```
