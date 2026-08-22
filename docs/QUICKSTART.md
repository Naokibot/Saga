# Saga 15分クイックスタート

## 基本

```saga
let name = "Aki"
var count = 0

for n in 1..5 {
    count = count + n
}

if count >= 10 {
    print(name, count)
}
```

## 関数とコレクション

```saga
fn square(value: int) = value * value
print(transform(square, [1, 2, 3]))
```

## クラス

```saga
class User(let name: text, private var score: int) {
    fn add(points: int) { self.score = self.score + points }
    fn label() = self.name + ": " + text(self.score)
}

let user = User("Aki", 0)
user.add(10)
print(user.label())
```

## 外部機能

```saga
use io
io.write_text("hello.txt", "Hello")
```

```bash
saga run main.saga --allow-write .
```

## 用途別プロジェクト

```bash
saga new my-api --template web
saga new my-desktop --template desktop
saga new my-android --template android
```
