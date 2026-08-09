' Liga o Jarvis em segundo plano, sem abrir janela de terminal.
' Duplo clique neste arquivo para iniciar. Para desligar, use o Gerenciador de
' Tarefas e encerre o processo "pythonw.exe".
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strPasta = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Tenta o ambiente virtual .venv312 (Python 3.12, usado para o modo voz);
' se não existir, cai para .venv.
strPython = strPasta & "\.venv312\Scripts\pythonw.exe"
If Not objFSO.FileExists(strPython) Then
    strPython = strPasta & "\.venv\Scripts\pythonw.exe"
End If

objShell.CurrentDirectory = strPasta
objShell.Run """" & strPython & """ -m jarvis.main --modo voz", 0, False
