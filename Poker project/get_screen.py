import win32gui

def enum_windows():
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                print(title)
    win32gui.EnumWindows(callback, None)

enum_windows()
