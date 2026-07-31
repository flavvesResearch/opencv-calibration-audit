# OpenCV real-camera checkerboard fixture

- Source: OpenCV `samples/data/left01.jpg`, `left02.jpg`, and `left03.jpg`
- Pinned source commit: `e35ad60e4e1db55be854df5770f706af65803690`
- Source repository: `https://github.com/opencv/opencv`
- License: Apache-2.0; see `LICENSE.txt` in this directory
- Camera: left camera from OpenCV's stereo-calibration sample set; the camera
  make and model are not published with the sample
- Resolution: 640 × 480, 8-bit grayscale JPEG
- Target: 9 × 6 inner corners; physical square size is not published, so the
  integration test uses a nominal 30 mm scale

The files are base64-encoded only so this repository can carry the exact binary
fixtures through text-oriented patch tooling. Tests decode them byte-for-byte
before analysis.

Expected behavior:

- all three source views produce complete checkerboard detections;
- all three remain usable for calibration;
- `left02` and `left03` may receive a near-border warning because the estimated
  physical target boundary approaches or crosses the frame;
- the integration test derives dark and blurred near-duplicate cases from the
  real frames to exercise exposure, sharpness, and duplicate decisions without
  storing additional binaries;
- calibration is checked against broad plausibility bounds rather than exact
  floating-point output.
