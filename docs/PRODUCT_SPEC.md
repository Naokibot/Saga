# Saga Product Specification 0.4

## 優先順位

1. 学びやすさ
2. 書きやすさと読みやすさ
3. 間違いの見つけやすさ
4. 安全な既定値
5. 数値の正確さ
6. 実用アプリへの拡張性

## 言語設計

- セミコロン任意
- 型推論
- 1行関数
- 読みやすい`and/or/not`
- 変更不可の`let`を標準
- nullなし
- 正確なDecimalとRational
- クラス主コンストラクタ
- interface、abstract、generics、annotations
- `try/catch/finally/throw`

## 実行モデル

```text
Saga source
  -> Lexer
  -> Parser
  -> AST
  -> Static Type Checker
  -> Capability-secured Interpreter
  -> Standard modules / optional adapters
```

## 外部アクセス

ファイル、ネットワーク、DB、GUI、プラグインはCLIで明示的に許可します。初心者向けの短いAPIと、実行時の権限境界を両立させます。

## 実装対象

- コンソール・バッチ
- OOPアプリ
- 高精度計算
- デスクトップGUI
- REST API・ソケット
- SQLite・ORM・ドキュメントDB
- 並行・並列処理
- 画像、動画、ゲーム、クラウド、IoT、Sparkのアダプター
- Androidホストプロジェクト生成
- リフレクション、動的プラグイン、アノテーション処理

## 非目標または未完成

- Java/Python/C#の全ライブラリ互換
- JVMまたはネイティブ最適化コンパイラ
- 分散トランザクションコーディネータ
- 実運用向けパッケージレジストリ
- 安全重要システムの認証
