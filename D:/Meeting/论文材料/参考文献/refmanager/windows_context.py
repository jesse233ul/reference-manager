import ctypes
from pathlib import Path

try:
    import pythoncom
    import win32con
    import win32gui
    from win32com.shell import shell, shellcon
except ImportError:
    pythoncom = None
    win32con = None
    win32gui = None
    shell = None
    shellcon = None

def is_open_with_menu_text(text: str) -> bool:
    normalized = (
        text.replace("&", "")
        .replace("\t", " ")
        .replace("...", "")
        .replace("…", "")
        .strip()
        .lower()
    )
    return "打开方式" in normalized or "open with" in normalized


def windows_menu_item_text(hmenu, position: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    length = ctypes.windll.user32.GetMenuStringW(
        int(hmenu),
        position,
        buffer,
        len(buffer),
        win32con.MF_BYPOSITION,
    )
    if length <= 0:
        return ""
    return buffer.value


def keep_only_open_with_menu_item(hmenu) -> bool:
    count = win32gui.GetMenuItemCount(hmenu)
    keep_positions = {
        position
        for position in range(count)
        if is_open_with_menu_text(windows_menu_item_text(hmenu, position))
    }
    if not keep_positions:
        return False

    for position in range(count - 1, -1, -1):
        if position not in keep_positions:
            win32gui.RemoveMenu(hmenu, position, win32con.MF_BYPOSITION)
    return True


def show_windows_file_context_menu(path: Path, hwnd: int, x: int, y: int) -> bool:
    if not all([pythoncom, win32con, win32gui, shell, shellcon]):
        return False
    try:
        pythoncom.CoInitialize()
    except pythoncom.com_error:
        pass

    hmenu = None
    try:
        desktop = shell.SHGetDesktopFolder()
        parent_pidl = shell.SHParseDisplayName(str(path.parent), 0)[0]
        parent_folder = desktop.BindToObject(parent_pidl, None, shell.IID_IShellFolder)
        child_pidl = parent_folder.ParseDisplayName(hwnd, None, path.name)[1]
        context_result = parent_folder.GetUIObjectOf(hwnd, [child_pidl], shell.IID_IContextMenu, 0)
        context_menu = context_result[1] if isinstance(context_result, tuple) else context_result

        hmenu = win32gui.CreatePopupMenu()
        context_menu.QueryContextMenu(
            hmenu,
            0,
            1,
            0x7FFF,
            shellcon.CMF_NORMAL | shellcon.CMF_EXPLORE,
        )
        if not keep_only_open_with_menu_item(hmenu):
            return False
        command = win32gui.TrackPopupMenu(
            hmenu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RETURNCMD | win32con.TPM_RIGHTBUTTON,
            x,
            y,
            0,
            hwnd,
            None,
        )
        if command:
            context_menu.InvokeCommand(
                (0, hwnd, command - 1, None, None, win32con.SW_SHOWNORMAL, 0, None)
            )
        return True
    except Exception:
        return False
    finally:
        if hmenu:
            try:
                win32gui.DestroyMenu(hmenu)
            except Exception:
                pass

