from automation.core.adb import AdbClient, scale_point
from automation.core.vision import Detection, select_detection
from automation.core.workflow import CancellationToken


def test_scale_point_between_resolutions():
    assert scale_point((960, 540), (1920, 1080), (1280, 720)) == (640, 360)


def test_adb_arguments_keep_windows_path_as_one_argument():
    client = AdbClient(r"C:\Program Files\MuMu Player\adb.exe", "device-1", CancellationToken())
    assert client._args("shell", "wm", "size") == [r"C:\Program Files\MuMu Player\adb.exe", "-s", "device-1", "shell", "wm", "size"]


def test_selects_highest_confidence_matching_detection():
    detections = [Detection("button", 0.7, (0, 0, 2, 2)), Detection("button", 0.93, (10, 10, 20, 20)), Detection("other", 0.99, (0, 0, 1, 1))]
    assert select_detection(detections, "button", 0.6) == detections[1]

