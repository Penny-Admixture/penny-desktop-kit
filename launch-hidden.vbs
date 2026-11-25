' Launch penny-desktop-kit with NO console window at all.
' Penny 2026-11-19: background always -- the app itself runs under pyw
' (windowless), but a double-clicked .bat owns a cmd console, however
' briefly. Point the double-click / Startup / pinned entry at this
' .vbs instead of run.bat and the console never appears. The app
' window itself is unaffected. A startup failure goes to
' data\crash.log, not to any console (there is none).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\run.bat"
sh.Run """" & batPath & """", 0, False
