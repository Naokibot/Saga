from __future__ import annotations

from dataclasses import dataclass
import locale as _locale
import os
import re
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DiagnosticSpec:
    id: str
    title_ja: str
    title_en: str
    explanation_ja: str
    explanation_en: str
    help_ja: str | None = None
    help_en: str | None = None
    docs_slug: str | None = None

    def title(self, language: str) -> str:
        return self.title_ja if language == "ja" else self.title_en

    def explanation(self, language: str) -> str:
        return self.explanation_ja if language == "ja" else self.explanation_en

    def help(self, language: str) -> str | None:
        return self.help_ja if language == "ja" else self.help_en


CATALOG: dict[str, DiagnosticSpec] = {
    "SAGA-L101": DiagnosticSpec(
        "SAGA-L101", "使用できない文字があります", "Unsupported character",
        "Sagaのソースとして解釈できない文字が含まれています。入力方式やコピー元を確認してください。",
        "The source contains a character that Saga cannot tokenize. Check the input method or copied text.",
        "全角記号や見た目が似た記号になっていないか確認してください。",
        "Check for full-width punctuation or visually similar Unicode characters.",
    ),
    "SAGA-L102": DiagnosticSpec(
        "SAGA-L102", "文字列が閉じられていません", "Unterminated string",
        "文字列を開始した引用符に対応する終了引用符がありません。",
        "A string literal was opened but no matching closing quote was found.",
        "文字列の最後に同じ種類の引用符を追加してください。", "Add the matching quote at the end of the string.",
    ),
    "SAGA-L103": DiagnosticSpec(
        "SAGA-L103", "数値リテラルの書き方が正しくありません", "Invalid numeric literal",
        "数値区切りや小数点の位置がSagaの数値構文に合っていません。",
        "The numeric separators or decimal point do not follow Saga numeric syntax.",
        "例: 1_000, 3.141_592 のように書けます。", "Examples: 1_000 and 3.141_592 are valid.",
    ),
    "SAGA-L104": DiagnosticSpec(
        "SAGA-L104", "ソースが正しいUTF-8ではありません", "Invalid UTF-8 source",
        "SagaソースはUTF-8で保存する必要があります。不正なバイト列は字句解析前に拒否されます。",
        "Saga source files must be encoded as UTF-8. Malformed byte sequences are rejected before tokenization.",
        "エディターの文字コードをUTF-8にして保存し直してください。",
        "Save the file again using UTF-8 encoding.",
    ),
    "SAGA-L105": DiagnosticSpec(
        "SAGA-L105", "識別子がNFC正規形ではありません", "Identifier is not NFC-normalized",
        "同じ見た目の識別子が異なるUnicode列として扱われることを防ぐため、Sagaの識別子はNFC正規形で記述します。",
        "Saga identifiers use Unicode NFC so visually identical names do not silently use different code-point sequences.",
        "エディターでUnicode NFC正規化してから保存してください。",
        "Normalize the identifier to Unicode NFC and save the file again.",
    ),
    "SAGA-L106": DiagnosticSpec(
        "SAGA-L106", "双方向制御文字をコード中では使用できません", "Bidirectional control character is not allowed in code",
        "文字の見た目とコンパイラが読む順序の不一致を避けるため、双方向テキスト制御文字は文字列リテラル以外では拒否されます。",
        "Bidirectional formatting controls are rejected outside string literals to reduce discrepancies between visual order and compiler interpretation.",
        "不可視の双方向制御文字を削除してください。必要な文字列データなら文字列リテラル内に置いてください。",
        "Remove the invisible bidi control. If it is intentional data, place it inside a string literal.",
    ),
    "SAGA-P101": DiagnosticSpec(
        "SAGA-P101", "閉じ記号が不足しています", "Missing closing delimiter",
        "開いた括弧・角括弧・ブロックに対応する閉じ記号が見つかりません。",
        "An opening parenthesis, bracket, or block is missing its closing delimiter.",
        "直前の ( [ { と対応する ) ] } を確認してください。", "Check the nearest ( [ { and add the matching ) ] }.",
    ),
    "SAGA-P102": DiagnosticSpec(
        "SAGA-P102", "ここには式が必要です", "Expected an expression",
        "演算子や代入の後など、値を表す式が必要な位置です。",
        "This position requires an expression that produces a value.",
        "変数、リテラル、関数呼び出しなどを置いてください。", "Provide a variable, literal, function call, or another expression.",
    ),
    "SAGA-T101": DiagnosticSpec(
        "SAGA-T101", "変更できない値へ代入しています", "Cannot assign to an immutable binding",
        "letで宣言した変数は変更できません。変更可能な状態は明示的にvarで宣言します。",
        "Bindings declared with let are immutable. Mutable state must be declared explicitly with var.",
        "変更が必要なら宣言を let から var に変更してください。", "If mutation is intended, change the declaration from let to var.",
    ),
    "SAGA-T102": DiagnosticSpec(
        "SAGA-T102", "名前が宣言されていません", "Unknown name",
        "この名前は現在のスコープで宣言されていません。スペルミスか、宣言順を確認してください。",
        "This name is not declared in the current scope. Check spelling and declaration order.",
        "候補が表示されている場合は、その名前への修正を検討してください。", "If a candidate is shown, consider replacing the name with it.",
    ),
    "SAGA-T103": DiagnosticSpec(
        "SAGA-T103", "型が一致していません", "Type mismatch",
        "渡した値の型と、その位置で必要な型が一致していません。Sagaは危険な暗黙変換を行いません。",
        "The supplied value has a different type from the type required here. Saga avoids unsafe implicit conversions.",
        "必要な型へ明示的に変換するか、宣言した型を見直してください。", "Convert explicitly to the required type or revise the declared type.",
    ),
    "SAGA-T104": DiagnosticSpec(
        "SAGA-T104", "条件式はboolである必要があります", "Condition must be bool",
        "Sagaでは数値や文字列を暗黙にtrue/falseへ変換しません。",
        "Saga does not implicitly convert numbers or text to true/false.",
        "例: if count > 0 { ... } のように比較式を書いてください。", "Write an explicit comparison, for example: if count > 0 { ... }.",
    ),
    "SAGA-T105": DiagnosticSpec(
        "SAGA-T105", "関数の引数が一致していません", "Function arguments do not match",
        "関数が要求する引数の個数または型と、呼び出し側が渡した値が一致しません。",
        "The call does not match the function's required argument count or types.",
        "関数定義の引数一覧を確認してください。", "Check the function declaration's parameter list.",
    ),
    "SAGA-T106": DiagnosticSpec(
        "SAGA-T106", "メンバーが見つかりません", "Unknown member",
        "この型・クラス・モジュールには指定されたフィールド、メソッド、関数がありません。",
        "The type, class, or module does not define the requested field, method, or function.",
        "候補が表示されている場合はスペルを修正してください。", "If a candidate is shown, correct the spelling.",
    ),
    "SAGA-T107": DiagnosticSpec(
        "SAGA-T107", "privateメンバーへ外部からアクセスしています", "Private member access",
        "privateメンバーは宣言したクラスの外側から直接アクセスできません。",
        "A private member cannot be accessed directly from outside its declaring class.",
        "公開メソッドを経由して必要な操作を行ってください。", "Use a public method to perform the required operation.",
    ),
    "SAGA-T108": DiagnosticSpec(
        "SAGA-T108", "同じ名前が重複しています", "Duplicate declaration",
        "同じスコープ内で同じ名前を複数回宣言しています。",
        "The same name is declared more than once in the same scope.",
        "どちらかの名前を変更するか、不要な宣言を削除してください。", "Rename one declaration or remove the duplicate.",
    ),
    "SAGA-T109": DiagnosticSpec(
        "SAGA-T109", "戻り値の経路が不足しています", "Missing return path",
        "値を返す関数で、処理経路によってreturnに到達しない可能性があります。",
        "A value-returning function has a control-flow path that may finish without returning a value.",
        "すべての分岐で値をreturnするようにしてください。", "Return a value on every possible control-flow path.",
    ),
    "SAGA-T110": DiagnosticSpec(
        "SAGA-T110", "override指定が正しくありません", "Invalid override declaration",
        "継承またはinterfaceの契約を置き換えるメソッドにはoverrideが必要で、対応する契約がない場所には指定できません。",
        "A method replacing an inherited or interface contract requires override, and override cannot be used without a matching contract.",
        "親クラスまたはinterfaceの同名メソッドとoverride指定を確認してください。",
        "Check the matching parent/interface method and the override marker.",
    ),
    "SAGA-T111": DiagnosticSpec(
        "SAGA-T111", "抽象型は直接作成できません", "Abstract type cannot be constructed",
        "abstract classまたはinterfaceは直接インスタンス化できません。具体クラスを作成してください。",
        "An abstract class or interface cannot be instantiated directly. Construct a concrete implementation instead.",
        "抽象メソッドを実装した具体クラスを作成してください。",
        "Construct a concrete class that implements the required abstract methods.",
    ),
    "SAGA-C480": DiagnosticSpec(
        "SAGA-C480", "制御周期契約の引数が正しくありません", "Invalid control-tick contract arguments",
        "@control_tick の周期契約は rate_hz と budget_us の2つの整数リテラルで指定します。",
        "A @control_tick timing contract takes exactly two integer literals: rate_hz and budget_us.",
        "例: @control_tick(20000, 35)", "Example: @control_tick(20000, 35).",
    ),
    "SAGA-C481": DiagnosticSpec(
        "SAGA-C481", "制御周期レートが範囲外です", "Control-tick rate is out of range",
        "rate_hz はコンパイル時に確定する1..1000000の整数でなければなりません。",
        "rate_hz must be a compile-time integer literal in 1..1,000,000.",
        "対象ハードウェアで実際に資格化する周期を指定してください。", "Use a rate that will be qualified on the target hardware.",
    ),
    "SAGA-C482": DiagnosticSpec(
        "SAGA-C482", "制御実行予算が正しくありません", "Invalid control-tick execution budget",
        "budget_us は正の整数リテラルで指定します。",
        "budget_us must be a positive integer literal.",
        "1周期内で許容する実行時間をマイクロ秒で指定してください。", "Specify the allowed execution time within one cycle in microseconds.",
    ),
    "SAGA-C483": DiagnosticSpec(
        "SAGA-C483", "制御実行予算が周期を超えています", "Control-tick budget exceeds its period",
        "budget_us * rate_hz が1000000を超えており、実行予算が1周期より長くなっています。",
        "budget_us * rate_hz exceeds 1,000,000, so the execution budget is longer than one declared cycle.",
        "budget_usを短くするかrate_hzを下げてください。", "Reduce budget_us or lower rate_hz.",
    ),
    "SAGA-R101": DiagnosticSpec(
        "SAGA-R101", "範囲外の位置へアクセスしています", "Index out of bounds",
        "リストまたは文字列の長さを超えた位置を読み取ろうとしました。",
        "The program attempted to access a list or text position outside its valid range.",
        "len(...)で長さを確認するか、安全なget系関数を使用してください。", "Check the length with len(...) or use a safe get operation.",
    ),
    "SAGA-R102": DiagnosticSpec(
        "SAGA-R102", "0では割れません", "Division by zero",
        "除数が0になっています。整数・Decimal・Rationalのいずれでも0除算は定義されません。",
        "The divisor is zero. Division by zero is undefined for int, decimal, and rational values.",
        "除算前に divisor != 0 を確認してください。", "Check divisor != 0 before dividing.",
    ),
    "SAGA-R103": DiagnosticSpec(
        "SAGA-R103", "必要な権限がありません", "Capability denied",
        "ファイル、ネットワーク、DB、プロセス等の外部操作には明示的な権限が必要です。",
        "External effects such as file, network, database, or process access require an explicit capability.",
        "必要最小限の --allow-* オプションだけを指定してください。", "Grant only the minimum required --allow-* capability.",
    ),
    "SAGA-R104": DiagnosticSpec(
        "SAGA-R104", "optionに値がありません", "Option has no value",
        "none()を値が存在するものとして取り出そうとしました。",
        "The program tried to unwrap none() as if it contained a value.",
        "is_some(...)で確認するか、unwrap_or(...)を使用してください。", "Check with is_some(...) or use unwrap_or(...).",
    ),
    "SAGA-R105": DiagnosticSpec(
        "SAGA-R105", "アサーションに失敗しました", "Assertion failed",
        "assertで指定した条件がfalseになりました。",
        "The condition passed to assert evaluated to false.",
        "表示された条件と入力値を確認してください。", "Inspect the asserted condition and the input values.",
    ),
}


def normalize_language(value: str | None) -> str:
    if value and value not in {"auto", ""}:
        value = value.lower().replace("_", "-")
        return "ja" if value.startswith("ja") else "en"
    env = os.environ.get("SAGA_LANG") or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG")
    if not env:
        try:
            env = _locale.getlocale()[0] or ""
        except Exception:
            env = ""
    return "ja" if env.lower().replace("_", "-").startswith("ja") else "en"



def get_spec(diagnostic_id: str) -> DiagnosticSpec | None:
    return CATALOG.get(diagnostic_id)


def all_specs() -> Iterable[DiagnosticSpec]:
    return (CATALOG[key] for key in sorted(CATALOG))


def localize_message(base_code: str, diagnostic_id: str, message: str, language: str, data: dict[str, str] | None = None) -> str:
    """Render detail without parsing implementation prose.

    Stable code/id and structured source ranges are the compatibility interface.
    The raw implementation message may remain Japanese for legacy debugging, but
    no diagnostic category, ID, exit status, or localization decision is inferred
    from it.
    """
    language = normalize_language(language)
    if language == "ja":
        return message
    spec = get_spec(diagnostic_id)
    token = (data or {}).get("token", "")
    if diagnostic_id == "SAGA-T101" and token:
        return f"`{token}` is immutable because it was declared with `let`."
    if diagnostic_id == "SAGA-T102" and token:
        return f"Name `{token}` is not declared in this scope."
    if diagnostic_id == "SAGA-T107" and token:
        return f"Private member `{token}` cannot be accessed from here."
    if diagnostic_id == "SAGA-T108" and token:
        return f"`{token}` is declared more than once in this scope."
    if spec is not None:
        return spec.title_en
    # Unknown implementation diagnostics deliberately use a stable phase-level
    # fallback instead of attempting to classify localized prose.
    phase = {
        "SAGA-L001": "Lexical error",
        "SAGA-P001": "Parse error",
        "SAGA-T001": "Type error",
        "SAGA-R001": "Runtime error",
        "SAGA-I001": "Implementation/input error",
    }
    return phase.get(base_code, "Saga diagnostic")

