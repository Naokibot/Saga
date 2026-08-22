# Saga Offline Installer

このフォルダーと同梱wheelだけを使う、ユーザー単位のオフラインインストーラーです。遠隔URLからコードを取得しません。

Linux/macOS:

```bash
./install-saga.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-saga.ps1
```

既定では独立したPython仮想環境にインストールします。`--prefix`と`--bin-dir`で配置先を変更できます。
