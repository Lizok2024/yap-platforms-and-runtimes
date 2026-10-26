# YAP Platforms and Runtimes

Проект по дисциплине «Платформы и среды выполнения языков программирования».

В проекте реализованы:

- интерпретация программы, представленной в виде JSON AST;
- интерпретация инструкций стековой машины;
- компиляция JSON AST в инструкции стековой машины;
- создание S-expressions, обращение к их полям по индексу и вывод списков `cons`/`nil`;
- класс `Interpreter` с процедурой `sum_arrays`, которая суммирует числа в массивах, в том числе во вложенных.

Для запуска нужен Python 3.10 или новее. Сторонние библиотеки не требуются.

## Файлы проекта

- `interpreter.py` — класс `Interpreter`, выполнение AST, процедура суммирования массивов и CLI.
- `main.py` — запуск AST-интерпретатора из стандартного ввода.
- `parser.py` — разбор JSON AST в объекты узлов.
- `ast_nodes.py` — узлы AST и их выполнение.
- `context.py`, `environment.py` — контекст исполнения и хранение переменных.
- `runtime_values.py` — значения S-expressions, индексирование и общий формат вывода.
- `compiler.py` — компилятор JSON AST в инструкции стековой машины.
- `stack_machine.py` — интерпретатор инструкций стековой машины.
- `program.json` — пример программы, вычисляющей факториал.
- `example_add.json` — простая программа, которая складывает 7 и 8; подходит для запуска через интерпретатор и после компиляции.
- `sum_arrays.json` — массивы для проверки процедуры `sum_arrays`.
- `machine_factorial.json`, `machine_example.json` — примеры программ стековой машины.
- `sexpressions.txt`, `sexpressions.json`, `compiled_sexpressions.json`, `sexpressions.expected.txt` — исходный пример для сайта, его AST, машинный код и ожидаемый вывод.
- `tests.py`, `test_interpreter.py`, `test_compiler.py`, `test_stack_machine.py`, `test_sexpressions.py` — тесты компонентов проекта.

## 1. Запуск AST-интерпретатора

Из корневой папки проекта запустите:

```powershell
Get-Content -Raw program.json | python main.py
```

Либо запустите файл напрямую через класс `Interpreter`:

```powershell
python interpreter.py program.json
```

`program.json` вычисляет факториал числа 5. Ожидаемый вывод:

```text
120
```

Также программа может быть передана через стандартный ввод. Если поле `input` задано в JSON, его значения используются для операций `read`.

## 2. Суммирование всех чисел в массивах

Процедура `Interpreter.sum_arrays(arrays)` принимает массив чисел или массивы массивов. Она проходит по вложенным массивам и возвращает сумму всех чисел. Пустые массивы дают вклад `0`. Строки, логические значения и другие нечисловые элементы вызывают ошибку.

Запуск примера из файла:

```powershell
python interpreter.py --sum-arrays sum_arrays.json
```

Содержимое `sum_arrays.json`:

```json
[
  [1, 2, 3],
  [4, 5],
  [],
  [6, [7, 8]]
]
```

Ожидаемый результат:

```text
36
```

Процедуру также можно вызвать из Python:

```python
from interpreter import Interpreter

result = Interpreter.sum_arrays([[1, 2, 3], [4, 5], [6, [7, 8]]])
print(result)
```

Результат — `36`.

## 3. Компиляция программы

Скомпилируйте пример факториала в инструкции стековой машины:

```powershell
python compiler.py program.json -o compiled_factorial.json
```

Посмотреть текстовый листинг вместо JSON:

```powershell
python compiler.py program.json --asm
```

Можно также передать исходный AST через стандартный ввод:

```powershell
Get-Content -Raw program.json | python compiler.py
```

## 4. Запуск стековой машины

После компиляции примера факториала запустите полученную программу:

```powershell
"5" | python stack_machine.py compiled_factorial.json
```

Ожидаемый результат — `120`.

Для простой проверки используйте `example_add.json`. Сначала выполните программу напрямую:

```powershell
python interpreter.py example_add.json
```

Затем скомпилируйте и запустите её на стековой машине:

```powershell
python compiler.py example_add.json -o compiled_add.json
"" | python stack_machine.py compiled_add.json
```

Во всех трёх случаях результат — `15`.

В репозитории есть и готовая программа стековой машины:

```powershell
"5" | python stack_machine.py machine_factorial.json
"10" | python stack_machine.py machine_example.json
```

Ожидаемые результаты — `120` и `7` соответственно.

Стековая машина поддерживает инструкции `READ`, `WRITE`, `LD`, `ST`, `CONST`, `BINOP`, `LABEL`, `JMP`, `JZ`, `JNZ`, `SEXP`, `ELEM`.

## 5. S-expressions и списки (ДЗ 5)

Ветка `hw5` продолжает `hw4`. Поддерживаются именованные конструкторы с любым числом полей, в том числе без полей, вложенные S-expressions и получение поля по индексу с нуля. Полями могут быть целые числа и другие S-expressions.

Исходная программа для [эталонного интерпретатора](https://dboulytchev.github.io/eval.html):

```text
{
  x = Pair(1, 2);
  write(x);
  write(x[0]);
  list = {1, 2, 3, 4};
  write(list);
  write(list[1]);
  write({});
}
```

Её вывод в этом проекте:

```text
Pair (1, 2)
1
{1, 2, 3, 4}
{2, 3, 4}
{}
```

Как и раньше, программы принимаются в виде JSON AST, скачанного с сайта. Для `Pair(1, 2)` формат AST — `{"sexp":"Pair","args":[{"const":1},{"const":2}]}`, для `x[0]` — `{"elem":{"var":"x"},"index":{"const":0}}`.

Литерал `{1, 2}` на сайте превращается в `cons(1, cons(2, nil))`. Конструкторы с именами `cons` и `nil` образуют список и выводятся в фигурных скобках. Регистр имени значим: `Cons(1, Nil)` выводится как обычный конструктор `Cons (1, Nil)`. У списка поле `0` — голова, поле `1` — хвост; индексирование обращается к полям узла, а не к позиции в развёрнутом списке. Неправильно сформированный `cons` выводится как обычный конструктор.

В [машине](https://dboulytchev.github.io/sm.html) используются те же JSON-инструкции, что на сайте:

```json
[
  {"CONST": 1},
  {"CONST": 2},
  {"SEXP": ["Pair", 2]},
  {"ST": "x"},
  {"LD": "x"},
  {"CONST": 0},
  "ELEM",
  "WRITE"
]
```

`SEXP` снимает указанное число полей и кладёт в стек одно значение, сохраняя порядок полей. Нулевая арность не снимает значений. `ELEM` снимает индекс, затем S-expression и кладёт выбранное поле. Отрицательный индекс, выход за границы и индекс нецелого типа вызывают ошибку. S-expressions нельзя использовать как целочисленные операнды или условия.

Расширенный пример с сайта сохранён в `sexpressions.json`, а его машинный JSON — в `compiled_sexpressions.json`. Запуск напрямую и через компилятор:

```powershell
python interpreter.py sexpressions.json
python compiler.py sexpressions.json -o compiled_sexpressions.json
"" | python stack_machine.py compiled_sexpressions.json
```

В `sexpressions.expected.txt` приведён ожидаемый вывод. Тесты сопоставляют вывод обоих интерпретаторов и машинный JSON компилятора с примерами, полученными от эталона.

## 6. Запуск тестов

Запустить все тесты:

```powershell
python -m unittest -v
python tests.py
```

Либо проверять части проекта отдельно:

```powershell
python -m unittest -v test_interpreter
python -m unittest -v test_compiler
python -m unittest -v test_stack_machine
python -m unittest -v test_sexpressions
```

## Ограничения

Компилятор поддерживает целочисленный JSON AST, S-expressions и списки `cons`/`nil`. Текст исходного языка разбирается на сайте; собственный текстовый парсер в проекте отсутствует. Массивы, строки, `.length` и изменение полей S-expressions пока не поддерживаются. `sum_arrays` — метод класса `Interpreter`, рассчитанный на JSON-массивы, в том числе вложенные; инструкция для вызова этой процедуры в целевом языке стековой машины не добавлялась.

## Авторы

Grankina Elizabeth

Sadygov Huseyn

Yaroslav Grigoriev

Berezhnoy Yan
