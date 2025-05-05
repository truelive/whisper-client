#!/usr/bin/env python3

import sounddevice as sd
import soundfile as sf
import requests
import numpy as np
import io
import argparse
import sys
import queue
import time

# --- Configuration ---
DEFAULT_SERVER_URL = "http://localhost:5000/upload_audio" # URL of your local server endpoint
# DEFAULT_DURATION = 5  # Recording duration in seconds - No longer primary control
DEFAULT_SAMPLE_RATE = 16000 # Sample rate (samples per second) - 16kHz is common for speech
DEFAULT_CHANNELS = 1 # Mono audio
SILENCE_THRESHOLD = 0.01 # RMS threshold for silence detection (adjust based on your mic/environment)
SILENCE_DURATION_SEC = 1.5 # How many seconds of silence trigger stop
PRE_SPEECH_BUFFER_SEC = 0.3 # Keep some audio before speech starts
POST_SPEECH_BUFFER_SEC = 0.5 # Keep some audio after speech ends (part of SILENCE_DURATION_SEC)

audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(indata.copy())

def calculate_rms(audio_chunk):
    """Calculate Root Mean Square for a chunk."""
    if audio_chunk.size == 0:
        return 0
    return np.sqrt(np.mean(audio_chunk**2))

def record_until_silence(samplerate, channels, threshold, silence_sec, pre_buffer_sec, post_buffer_sec):
    """Records audio until a period of silence is detected."""
    print("Listening... Speak into the microphone. Recording starts on sound.")
    print(f"(Silence threshold RMS: {threshold:.3f}, Stop after: {silence_sec}s of silence)")

    block_duration = 0.1 # Process audio in 100ms chunks
    block_size = int(samplerate * block_duration)
    silence_blocks_needed = int(silence_sec / block_duration)
    pre_buffer_blocks = int(pre_buffer_sec / block_duration)
    post_buffer_blocks = int(post_buffer_sec / block_duration) # Part of silence_blocks_needed

    recorded_blocks = []
    silent_blocks_count = 0
    recording_started = False
    temp_buffer = [] # Holds pre-speech buffer

    try:
        with sd.InputStream(samplerate=samplerate, channels=channels,
                            blocksize=block_size, dtype='float32', # Use float32 for easier RMS calc
                            callback=audio_callback):
            while True:
                block = audio_queue.get()
                rms = calculate_rms(block)

                is_silent = rms < threshold

                if not recording_started:
                    temp_buffer.append(block)
                    if len(temp_buffer) > pre_buffer_blocks:
                        temp_buffer.pop(0) # Keep buffer size limited

                    if not is_silent:
                        print("Sound detected, recording started.")
                        recording_started = True
                        recorded_blocks.extend(temp_buffer) # Add pre-speech buffer
                        recorded_blocks.append(block)
                        silent_blocks_count = 0
                else:
                    recorded_blocks.append(block)
                    if is_silent:
                        silent_blocks_count += 1
                        if silent_blocks_count >= silence_blocks_needed:
                            print(f"Silence detected for {silence_sec}s. Stopping recording.")
                            break
                    else:
                        silent_blocks_count = 0 # Reset silence counter on sound

        if not recorded_blocks:
            print("No speech detected before timeout or error.")
            return None

        # Trim excessive silence at the end (keep post_buffer_blocks)
        num_blocks_to_keep = len(recorded_blocks) - max(0, silent_blocks_count - post_buffer_blocks)
        final_recording_float = np.concatenate(recorded_blocks[:num_blocks_to_keep])

        # Convert float32 recording back to int16 for sending
        final_recording_int16 = (final_recording_float * 32767).astype(np.int16)
        print(f"Recording finished. Total duration: {len(final_recording_int16)/samplerate:.2f}s")
        return final_recording_int16

    except Exception as e:
        print(f"Error during recording: {e}", file=sys.stderr)
        sys.exit(1)

def send_audio_to_server(audio_data, samplerate, server_url):
    """Sends the recorded audio data to the specified server URL."""
    print(f"Sending audio to {server_url}...")

    # Create an in-memory WAV file
    buffer = io.BytesIO()
    try:
        sf.write(buffer, audio_data, samplerate, format='WAV', subtype='PCM_16') # Already int16
        buffer.seek(0) # Rewind the buffer to the beginning
    except Exception as e:
        print(f"Error creating WAV file in memory: {e}", file=sys.stderr)
        return False

    # Prepare the file for the POST request
    files = {'audio': ('recording.wav', buffer, 'audio/wav')}

    # Send the POST request
    try:
        start_time = time.time()
        response = requests.post(server_url, files=files, timeout=30) # Added timeout
        end_time = time.time()
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Audio sent successfully in {end_time - start_time:.2f} seconds.")
        print(f"Server response: {response.status_code} - {response.text}")
        try:
            json_response = response.json()
            # Check if 'text' key exists before accessing and stripping
            if "text" in json_response and isinstance(json_response["text"], str):
                print("Parsed text:", json_response["text"].strip())
            else:
                print("Parsed JSON response (no 'text' field or not string):", json_response)
        except requests.exceptions.JSONDecodeError:
            print("Server response was not valid JSON.")
        return True
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the server at {server_url}.", file=sys.stderr)
        print("Please ensure the server is running and the URL is correct.", file=sys.stderr)
        return False
    except requests.exceptions.Timeout:
        print(f"Error: The request to {server_url} timed out.", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending audio: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server response content: {e.response.text}", file=sys.stderr)
        return False
    finally:
        buffer.close()


def main():
    parser = argparse.ArgumentParser(description="Record audio and send it to a local server.")
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_SERVER_URL,
        help=f"URL of the server endpoint to send audio to (default: {DEFAULT_SERVER_URL})"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SILENCE_THRESHOLD,
        help=f"RMS volume threshold to detect silence (default: {SILENCE_THRESHOLD})"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Sample rate in Hz (default: {DEFAULT_SAMPLE_RATE})"
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=DEFAULT_CHANNELS,
        choices=[1, 2],
        help=f"Number of audio channels (1 for mono, 2 for stereo) (default: {DEFAULT_CHANNELS})"
    )

    args = parser.parse_args()

    print("Starting audio recording client...")
    print(f"Server URL: {args.url}")
    # print(f"Duration: {args.duration}s") # Removed duration
    print(f"Sample Rate: {args.rate}Hz")
    print(f"Channels: {args.channels}")

    # 1. Record Audio
    audio_data = record_until_silence(args.rate, args.channels, args.threshold,
                                      SILENCE_DURATION_SEC, PRE_SPEECH_BUFFER_SEC, POST_SPEECH_BUFFER_SEC)

    # 2. Send Audio to Server
    if audio_data is not None:
        send_audio_to_server(audio_data, args.rate, args.url)

if __name__ == "__main__":
    main()
