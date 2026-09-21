"""
Diagnostic utility to inspect audio endpoints and WASAPI loopback channels.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.audio_capture import AudioCaptureWorker
import sounddevice as sd


def main():
    print("=" * 60)
    print(" Apex Screen Recorder - Audio Diagnostics")
    print("=" * 60)

    devices = AudioCaptureWorker.get_audio_devices()

    print("\n[WASAPI Loopback Devices (System Audio Capture Candidates)]:")
    if devices["loopback"]:
        for dev in devices["loopback"]:
            print(f"  * ID {dev['id']}: {dev['name']} (Outputs: {dev['max_outputs']}, Rate: {dev['default_samplerate']} Hz)")
    else:
        print("  ! No WASAPI loopback devices detected directly. Falling back to default output.")

    default_loop = AudioCaptureWorker.get_default_loopback_device()
    print(f"\nDefault Selected Loopback Device ID: {default_loop}")

    print("\n[Microphone / Input Devices]:")
    if devices["microphones"]:
        for dev in devices["microphones"]:
            print(f"  * ID {dev['id']}: {dev['name']} (Inputs: {dev['max_inputs']}, Rate: {dev['default_samplerate']} Hz)")
    else:
        print("  ! No microphone input devices found.")

    print("\nDiagnostics complete.")


if __name__ == "__main__":
    main()
