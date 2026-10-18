# YAP Platforms and Runtimes

Проект по дисциплине «Платформы и среды выполнения языков программирования».

В проекте реализованы:

- интерпретация программы, представленной в виде JSON AST;
- интерпретация инструкций стековой машины;
- компиляция JSON AST в инструкции стековой машины;
- класс `Interpreter` с процедурой `sum_arrays`, которая суммирует числа в массивах, в том числе во вложенных.

Для запуска нужен Python 3.10 или новее. Сторонние библиотеки не требуются.

## Файлы проекта

- `interpreter.py` — класс `Interpreter`, выполнение AST, процедура суммирования массивов и CLI.
- `main.py` — запуск AST-интерпретатора из стандартного ввода.
- `parser.py` — разбор JSON AST в объекты узлов.
- `ast_nodes.py` — узлы AST и их выполнение.
- `context.py`, `environment.py` — контекст исполнения и хранение переменных.
- `compiler.py` — компилятор JSON AST в инструкции стековой машины.
- `stack_machine.py` — интерпретатор инструкций стековой машины.
- `program.json` — пример программы, вычисляющей факториал.
- `example_add.json` — простая программа, которая складывает 7 и 8; подходит для запуска через интерпретатор и после компиляции.
- `sum_arrays.json` — массивы для проверки процедуры `sum_arrays`.
- `machine_factorial.json`, `machine_example.json` — примеры программ стековой машины.
- `tests.py`, `test_interpreter.py`, `test_compiler.py`, `test_stack_machine.py` — тесты компонентов проекта.

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

Стековая машина поддерживает инструкции `READ`, `WRITE`, `LD`, `ST`, `CONST`, `BINOP`, `LABEL`, `JMP`, `JZ`, `JNZ`.

## 5. Запуск тестов

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
```

## Ограничения

Компилятор преобразует существующие узлы целочисленного JSON AST в инструкции текущей стековой машины. `sum_arrays` — метод класса `Interpreter`, рассчитанный на JSON-массивы, в том числе вложенные; инструкция для вызова этой процедуры в целевом языке стековой машины не добавлялась.

## Авторы

Grankina Elizabeth

Sadygov Huseyn

Yaroslav Grigoriev

Berezhnoy Yan
