"""换脸服务 — insightface"""

import cv2
import uuid
import numpy as np
from pathlib import Path
from backend.config import OUTPUT_DIR

_face_app = None
_swapper = None


def _init_models():
    """延迟初始化模型"""
    global _face_app, _swapper
    if _face_app is None:
        from insightface.app import FaceAnalysis
        _face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))

    if _swapper is None:
        import insightface.model_zoo
        model_path = Path.home() / ".insightface" / "models" / "buffalo_l" / "inswapper_128.onnx"
        if not model_path.exists():
            # 尝试从 insightface 默认路径加载
            _swapper = insightface.model_zoo.get_model("inswapper_128.onnx")
        else:
            _swapper = insightface.model_zoo.get_model(str(model_path))


async def face_swap_video(video_path: str, target_face_path: str) -> str:
    """对视频做人脸替换"""
    _init_models()

    # 加载目标人脸
    target_img = cv2.imread(target_face_path)
    if target_img is None:
        raise ValueError(f"无法读取目标图片: {target_face_path}")

    target_faces = _face_app.get(target_img)
    if not target_faces:
        raise ValueError("目标图片中未检测到人脸，请上传含清晰人脸的图片")

    target_face = target_faces[0]

    # 打开视频
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = str(OUTPUT_DIR / f"swapped_{uuid.uuid4().hex[:8]}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        source_faces = _face_app.get(frame)
        if source_faces:
            # 按面积取最大的人脸
            source_face = max(
                source_faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            )
            frame = _swapper.get(frame, source_face, target_face, paste_back=True)

        writer.write(frame)
        frame_count += 1

    cap.release()
    writer.release()

    if frame_count == 0:
        raise ValueError("视频帧为空，无法处理")

    return output_path
