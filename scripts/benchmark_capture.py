"""
Benchmark utility to test screen frame grab throughput and latency.
"""

import time
import mss
import numpy as np


def main():
    print("=" * 60)
    print(" Apex Screen Recorder - Screen Capture Benchmark")
    print("=" * 60)

    with mss.MSS() as sct:
        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        print(f"Target Monitor: {mon['width']}x{mon['height']} @ pos ({mon['left']}, {mon['top']})")

        total_frames = 180
        print(f"Capturing {total_frames} raw frames...")

        start_time = time.perf_counter()
        for i in range(total_frames):
            sct_img = sct.grab(mon)
            # convert to numpy buffer
            frame = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape((mon['height'], mon['width'], 4))[:, :, :3]

        elapsed = time.perf_counter() - start_time
        fps = total_frames / elapsed
        latency_ms = (elapsed / total_frames) * 1000

        print(f"\nResults:")
        print(f"  * Total Time:   {elapsed:.3f} s")
        print(f"  * Average FPS:  {fps:.1f} FPS")
        print(f"  * Frame Latency:{latency_ms:.2f} ms / frame")

        if fps >= 60:
            print("  * Status: [EXCELLENT] Ultra-smooth 60+ FPS capture capable!")
        elif fps >= 30:
            print("  * Status: [GOOD] 30+ FPS capture capable.")
        else:
            print("  * Status: [WARNING] Capture speed below 30 FPS.")


if __name__ == "__main__":
    main()
