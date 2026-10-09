# Source and models

BioSentinel originated as a team project at [Xavierfied/BioSentinel-Vision-Zero](https://github.com/Xavierfied/BioSentinel-Vision-Zero). The owner's local checkout contains named team contributions. This snapshot preserves that lineage and adds session, challenge, upload, browser and verification remediation. It does not imply sole authorship or independently reproduced historical performance results.

Runtime providers: [Ultralytics](https://github.com/ultralytics/ultralytics), [akanametov/yolo-face](https://github.com/akanametov/yolo-face), [MediaPipe](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker), [DeepFace](https://github.com/serengil/deepface), [RetinaFace](https://github.com/serengil/retinaface), [MiniVision's Silent Face Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing). FaceNet weights come through DeepFace's model distribution. Each provider and asset retains its own license and usage terms; downloads do not grant unrestricted rights.

The directly downloaded assets match versioned provider downloads byte for byte:

| Asset | SHA-256 |
| --- | --- |
| MediaPipe face_landmarker.task, float16 version 1 | 64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff |
| yolo-face release 1.0.0, yolov8n-face.pt | d545bf1add5aa736a4febac4f4f9245a6d596cd0fe70d5d57989fe0cb9e626ca |

Real inference verification uses DeepFace's public `tests/unit/dataset/img1.jpg` locally. That picture is not included or embedded here. Synthetic protocol fixtures are generated in memory and explicitly labeled as tests.
