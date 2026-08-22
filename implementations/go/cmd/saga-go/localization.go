package main

import "strings"

var sagaLanguage = "en"

// Diagnostic IDs are the compatibility contract. Localized text is presentation only.
var diagnosticTranslations = map[string]map[string]string{
	"ja": {
		"SAGA-L101": "使用できない文字またはエスケープです", "SAGA-L102": "文字列が正しく閉じられていません", "SAGA-L103": "数値リテラルが正しくありません",
		"SAGA-L104": "ソースはUTF-8で保存してください", "SAGA-L105": "識別子はNFC正規化が必要です", "SAGA-L106": "双方向制御文字はソースで使用できません",
		"SAGA-P101": "構文を解析できません", "SAGA-P102": "ここには式または必要な構文要素が必要です", "SAGA-P103": "文字列補間が閉じられていません",
		"SAGA-T101": "letで宣言した値は変更できません", "SAGA-T102": "名前が宣言されていません", "SAGA-T103": "型が一致しません", "SAGA-T104": "条件式にはboolが必要です",
		"SAGA-T105": "関数の引数が一致しません", "SAGA-T106": "そのメンバーまたはモジュールは存在しません", "SAGA-T107": "privateメンバーにはアクセスできません",
		"SAGA-T108": "宣言が重複しています", "SAGA-T109": "すべての経路で値を返していません", "SAGA-T112": "matchがenumを網羅していません",
		"SAGA-R102": "0で除算できません", "SAGA-R104": "noneをunwrapできません", "SAGA-R140": "並行タスク境界を越えられない値です",
	},
	"fr": {"SAGA-T101": "Une valeur déclarée avec let est immuable", "SAGA-T102": "Nom non déclaré", "SAGA-T103": "Types incompatibles", "SAGA-R102": "Division par zéro"},
	"es": {"SAGA-T101": "Un valor declarado con let es inmutable", "SAGA-T102": "Nombre no declarado", "SAGA-T103": "Los tipos no coinciden", "SAGA-R102": "División por cero"},
	"de": {"SAGA-T101": "Ein mit let deklarierter Wert ist unveränderlich", "SAGA-T102": "Name ist nicht deklariert", "SAGA-T103": "Typen stimmen nicht überein", "SAGA-R102": "Division durch Null"},
}

func normalizeSagaLanguage(tag string) string {
	tag = strings.ToLower(strings.TrimSpace(tag))
	if tag == "" {
		return "en"
	}
	if j := strings.IndexAny(tag, "-_"); j >= 0 {
		tag = tag[:j]
	}
	switch tag {
	case "ja", "fr", "es", "de", "en":
		return tag
	}
	return "en"
}
func localizedMessage(e *SagaError) string {
	if sagaLanguage == "en" {
		return e.Message
	}
	if m := diagnosticTranslations[sagaLanguage]; m != nil {
		if x := m[e.ID]; x != "" {
			return x + " (" + e.Message + ")"
		}
	}
	return e.Message
}
